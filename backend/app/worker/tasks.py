import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path
import time
import traceback
from typing import Any, Dict
from sqlalchemy import func, select

from app.agents.ffmpeg_renderer import FFmpegRendererAgent
from app.agents.researcher import ResearcherAgent
from app.agents.scriptwriter_gemini import ScriptwriterGeminiAgent
from app.agents.subtitle_whisper import SubtitleWhisperAgent
from app.agents.visual_generator import VisualGeneratorAgent
from app.agents.voice_tts import VoiceTTSAgent
from app.agents.youtube_publisher import YouTubePublisherAgent
from app.core.constants import ShortStatus
from app.core.dynamic_settings import get_active_config
from app.db.session import get_worker_db
from app.models.settings import SystemSetting
from app.models.short import Short
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _execute_generate_short_pipeline(short_id: int) -> Dict[str, Any]:
    """Execute complete end-to-end multi-agent Short creation pipeline with
    individual stage timing and asyncpg NullPool connection safety.
    """
    total_start = time.perf_counter()
    timers: Dict[str, float] = {}

    async with get_worker_db() as db:
        short = await db.get(Short, short_id)
        if not short:
            raise ValueError(f"Short with id {short_id} was not found in database.")

        try:
            logger.info("==================================================================")
            logger.info("PIPELINE START: Generating Short #%d ('%s')", short_id, short.niche)
            logger.info("==================================================================")

            short.error_message = None

            # ------------------------------------------------------------------
            # Phase 1: Research Stage & Phase 2: Gemini Scriptwriting Stage
            # ------------------------------------------------------------------
            t_script_start = time.perf_counter()
            if not short.script_payload or "scenes" not in short.script_payload:
                short.status = ShortStatus.RESEARCHING
                await db.commit()
                await db.refresh(short)

                researcher = ResearcherAgent()
                research_result = await researcher.run(
                    {"niche": short.niche, "topic": short.topic},
                    db_session=db,
                )

                generated_topic = research_result.get("topic")
                if generated_topic:
                    short.topic = generated_topic

                await db.commit()
                await db.refresh(short)

                # Scriptwriter
                scriptwriter = ScriptwriterGeminiAgent()
                script_result = await scriptwriter.run(
                    {"niche": short.niche, "topic": short.topic},
                    db_session=db,
                )

                script_payload = script_result.get("script_payload")
                short.script_payload = script_payload
                if script_payload and "title" in script_payload:
                    short.title = script_payload["title"]

                short.status = ShortStatus.SCRIPTED
                await db.commit()
                await db.refresh(short)
            else:
                logger.info("Short #%d already has script_payload. Skipping script generation.", short_id)
                if short.status != ShortStatus.SCRIPTED:
                    short.status = ShortStatus.SCRIPTED
                    await db.commit()
                    await db.refresh(short)

            timers["scriptwriting"] = time.perf_counter() - t_script_start
            logger.info("[TIMER] Scriptwriting / Idea finished in %.2fs", timers["scriptwriting"])

            # ------------------------------------------------------------------
            # Phase 3: Media Generation (Voice TTS, Visuals & Subtitles)
            # ------------------------------------------------------------------
            short.status = ShortStatus.GENERATING_MEDIA
            await db.commit()
            await db.refresh(short)
            logger.info("Stage: GENERATING_MEDIA for Short #%d", short_id)

            # 3.1: Concurrent Voice TTS (edge-tts + ffprobe + master.mp3)
            t_tts = time.perf_counter()
            voice_agent = VoiceTTSAgent()
            tts_result = await voice_agent.run(
                {"short_id": short.id, "script_payload": short.script_payload},
                db_session=db,
            )
            master_audio_path = tts_result["master_audio_path"]
            scene_durations = tts_result["scene_durations"]
            short.audio_path = master_audio_path
            await db.commit()
            timers["voice_tts"] = time.perf_counter() - t_tts
            logger.info("[TIMER] Concurrent Voice TTS finished in %.2fs", timers["voice_tts"])

            # 3.2: Parallel Visuals (Pollinations AI model=flux / Pexels B-Roll Video / Pillow fallback)
            t_vis = time.perf_counter()
            visual_agent = VisualGeneratorAgent()
            visual_result = await visual_agent.run(
                {
                    "short_id": short.id,
                    "script_payload": short.script_payload,
                },
                db_session=db,
            )
            scene_visual_paths = visual_result["scene_visual_paths"]
            timers["visuals"] = time.perf_counter() - t_vis
            logger.info("[TIMER] Parallel Visuals finished in %.2fs", timers["visuals"])

            # 3.3: Word-Level Subtitles (Singleton faster-whisper)
            t_sub = time.perf_counter()
            subtitle_agent = SubtitleWhisperAgent()
            subtitle_result = await subtitle_agent.run({
                "short_id": short.id,
                "audio_path": master_audio_path,
            })
            subtitles_path = subtitle_result["subtitles_path"]
            short.subtitle_path = subtitles_path
            await db.commit()
            timers["subtitles"] = time.perf_counter() - t_sub
            logger.info("[TIMER] Subtitles Whisper finished in %.2fs", timers["subtitles"])

            # ------------------------------------------------------------------
            # Phase 4: FFmpeg Ultra-Fast Parallel 9:16 Rendering & BGM
            # ------------------------------------------------------------------
            t_rend = time.perf_counter()
            short.status = ShortStatus.RENDERING
            await db.commit()
            await db.refresh(short)

            renderer = FFmpegRendererAgent()
            render_result = await renderer.run({
                "short_id": short.id,
                "scene_visual_paths": scene_visual_paths,
                "scene_durations": scene_durations,
                "master_audio_path": master_audio_path,
                "subtitles_path": subtitles_path,
            })

            video_path = render_result["video_path"]
            short.video_path = video_path
            short.status = ShortStatus.READY_FOR_REVIEW
            short.error_message = None
            await db.commit()
            await db.refresh(short)

            timers["rendering"] = time.perf_counter() - t_rend
            total_elapsed = time.perf_counter() - total_start
            timers["total"] = total_elapsed

            logger.info("==================================================================")
            logger.info("PIPELINE COMPLETE: Short #%d is READY_FOR_REVIEW in %.2f seconds!", short_id, total_elapsed)
            logger.info("TIMING BREAKDOWN:")
            logger.info(" - Scriptwriting:   %.2fs", timers.get("scriptwriting", 0))
            logger.info(" - Voice TTS:       %.2fs", timers.get("voice_tts", 0))
            logger.info(" - Visuals:         %.2fs", timers.get("visuals", 0))
            logger.info(" - Subtitles ASS:   %.2fs", timers.get("subtitles", 0))
            logger.info(" - FFmpeg Render:   %.2fs", timers.get("rendering", 0))
            logger.info(" - TOTAL PIPELINE:  %.2fs", total_elapsed)
            logger.info("Output Video: '%s'", video_path)
            logger.info("==================================================================")

            return {
                "status": "READY_FOR_REVIEW",
                "short_id": short_id,
                "title": short.title,
                "video_path": video_path,
                "audio_path": master_audio_path,
                "subtitle_path": subtitles_path,
                "timers": timers,
            }

        except Exception as exc:
            await db.rollback()
            error_trace = traceback.format_exc()
            logger.error("Pipeline execution failed for Short #%d: %s\n%s", short_id, str(exc), error_trace)

            try:
                short = await db.get(Short, short_id)
                if short:
                    short.status = ShortStatus.FAILED
                    short.error_message = f"{str(exc)}\n\nTraceback:\n{error_trace}"
                    await db.commit()
            except Exception as persist_err:
                logger.error("Failed to persist FAILED status: %s", persist_err)

            raise exc


@celery_app.task(
    bind=True,
    name="app.worker.tasks.generate_short_pipeline",
    soft_time_limit=180,
    time_limit=240,
)
def generate_short_pipeline(self: Any, short_id: int) -> Dict[str, Any]:
    """Celery background worker task orchestrating the complete Short generation pipeline."""
    logger.info("Celery task started: generate_short_pipeline for Short ID: %s", short_id)
    return asyncio.run(_execute_generate_short_pipeline(short_id))


@celery_app.task(
    bind=True,
    name="app.worker.tasks.publish_to_youtube",
    soft_time_limit=180,
    time_limit=240,
)
def publish_to_youtube(self: Any, short_id: int) -> Dict[str, Any]:
    """Asynchronous task for uploading approved video to YouTube Shorts."""
    logger.info("Executing YouTube upload task for Short ID: %s", short_id)
    return asyncio.run(_execute_publish_to_youtube(short_id))


async def _execute_publish_to_youtube(short_id: int) -> Dict[str, Any]:
    """Internal coroutine for publishing an approved Short to YouTube."""
    async with get_worker_db() as db:
        short = await db.get(Short, short_id)
        if not short:
            raise ValueError(f"Short #{short_id} not found.")

        if not short.video_path or not Path(short.video_path).exists():
            raise FileNotFoundError(f"Video file for Short #{short_id} not found at '{short.video_path}'")

        try:
            publisher = YouTubePublisherAgent()
            payload = short.script_payload or {}
            result = await publisher.run(
                {
                    "short_id": short.id,
                    "video_path": short.video_path,
                    "title": short.title or payload.get("title", f"Short #{short.id}"),
                    "description": payload.get("description", "#Shorts #AI"),
                    "tags": payload.get("tags", ["Shorts", "AI"]),
                    "category_id": "28",
                    "privacy_status": "private",
                },
                db_session=db,
            )

            youtube_id = result.get("youtube_video_id")
            short.youtube_video_id = youtube_id
            short.status = ShortStatus.PUBLISHED
            short.error_message = None
            await db.commit()
            await db.refresh(short)

            return {
                "status": "PUBLISHED",
                "short_id": short.id,
                "youtube_video_id": youtube_id,
                "youtube_url": result.get("youtube_url"),
            }

        except Exception as exc:
            await db.rollback()
            error_trace = traceback.format_exc()
            logger.error("YouTube upload failed for Short #%d: %s", short_id, str(exc))
            short = await db.get(Short, short_id)
            if short:
                short.error_message = f"YouTube Upload Failed: {str(exc)}\n\nTraceback:\n{error_trace}"
                await db.commit()
            raise exc


@celery_app.task(name="app.worker.tasks.auto_pilot_daily_shorts")
def auto_pilot_daily_shorts() -> Dict[str, Any]:
    """Celery Beat automated scheduled task creating daily YouTube Shorts."""
    return asyncio.run(_execute_auto_pilot())


async def _execute_auto_pilot() -> Dict[str, Any]:
    """Check active autopilot settings and enqueue new Short if quota allows."""
    async with get_worker_db() as db:
        config = await get_active_config(db)
        if not config.auto_schedule_enabled:
            logger.info("Celery Beat: Auto-Pilot is disabled. Skipping creation.")
            return {"status": "skipped", "reason": "auto_pilot_disabled"}

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = select(func.count(Short.id)).where(Short.created_at >= today_start)
        count_res = await db.execute(stmt)
        today_count = count_res.scalar_one()

        if today_count >= config.daily_target_count:
            logger.info(
                "Celery Beat: Daily target reached (%d/%d created today). Skipping.",
                today_count,
                config.daily_target_count,
            )
            return {"status": "skipped", "reason": "daily_quota_reached", "created_today": today_count}

        logger.info("Celery Beat: Launching auto-pilot Short for niche '%s'...", config.default_niche)
        new_short = Short(
            niche=config.default_niche,
            topic="",
            status=ShortStatus.PENDING,
        )
        db.add(new_short)
        await db.commit()
        await db.refresh(new_short)

        generate_short_pipeline.delay(new_short.id)
        logger.info("Celery Beat: Auto-pilot enqueued Short #%d", new_short.id)
        return {"status": "created", "short_id": new_short.id, "niche": config.default_niche}
