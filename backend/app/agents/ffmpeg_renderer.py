import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import math
from pathlib import Path
import subprocess
import time
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.core.config import settings

logger = logging.getLogger(__name__)


def run_ffmpeg_process(
    cmd: List[str],
    timeout: int = 75,
    error_context: str = "FFmpeg",
) -> None:
    """Executes an FFmpeg command with strict deadlock prevention:
    - stdout is discarded via subprocess.DEVNULL so pipes never saturate.
    - stderr is piped and captured only on error.
    - timeout=75 enforces hard termination before hanging.
    - Resources and file descriptors are properly released on exceptions.
    """
    try:
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=True,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error("[%s] TIMEOUT after %ds: %s", error_context, timeout, " ".join(cmd[:8]))
        raise RuntimeError(f"{error_context} timed out after {timeout} seconds") from exc
    except subprocess.CalledProcessError as exc:
        err_msg = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else str(exc)
        logger.error("[%s] FAILED (code %d): %s", error_context, exc.returncode, err_msg[-500:])
        raise RuntimeError(f"{error_context} failed with exit code {exc.returncode}: {err_msg[-300:]}") from exc


def ensure_background_music() -> Path:
    """Verifies that /media/music/bg_ambient.mp3 exists; if not, generates
    a subtle, high-quality ambient synthetic drone using FFmpeg.
    """
    music_dir = Path(settings.MEDIA_DIR) / "music"
    music_dir.mkdir(parents=True, exist_ok=True)
    bg_music_path = music_dir / "bg_ambient.mp3"

    if not bg_music_path.exists():
        logger.info("Generating automatic ambient background music track at '%s'...", bg_music_path)
        cmd = [
            "ffmpeg",
            "-y",
            "-threads", "2",
            "-f", "lavfi",
            "-i", "aevalsrc=0.03*sin(2*PI*110*t)+0.02*sin(2*PI*164.81*t)+0.015*sin(2*PI*220*t):s=44100:d=120",
            "-af", "lowpass=f=450,volume=0.8",
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            str(bg_music_path),
        ]
        run_ffmpeg_process(cmd, timeout=30, error_context="Generate Background Music")
        logger.info("Background music generated successfully.")

    return bg_music_path


def ensure_transition_whoosh_sfx() -> Path:
    """Verifies that /media/music/whoosh_sfx.wav exists; if not, synthesizes
    a subtle transition whoosh sound effect using FFmpeg anoisesrc & afade.
    """
    music_dir = Path(settings.MEDIA_DIR) / "music"
    music_dir.mkdir(parents=True, exist_ok=True)
    whoosh_path = music_dir / "whoosh_sfx.wav"

    if not whoosh_path.exists():
        logger.info("Generating transition whoosh SFX at '%s'...", whoosh_path)
        cmd = [
            "ffmpeg",
            "-y",
            "-threads", "2",
            "-f", "lavfi",
            "-i", "anoisesrc=d=0.35:c=pink:r=44100,lowpass=f=1200,afade=t=in:ss=0:d=0.15,afade=t=out:st=0.18:d=0.17,volume=0.5",
            "-c:a", "pcm_s16le",
            str(whoosh_path),
        ]
        run_ffmpeg_process(cmd, timeout=30, error_context="Generate Transition SFX")
        logger.info("Transition whoosh SFX generated successfully.")

    return whoosh_path


class FFmpegRendererAgent(BaseAgent):
    """Pro FFmpeg Renderer (Optimized Low-CPU & Deadlock-Free Architecture):
    - Strict CPU & Resource Control: -threads 2 -c:v libx264 -preset ultrafast -tune fastdecode -crf 24 on all renders.
    - Infinite Loop & Audio Desync Prevention in B-Roll: -t {duration:.2f} right after input and -an flag to strip stock audio.
    - Deadlock Prevention: stdout=DEVNULL, stderr=PIPE, timeout=75 on all subprocess executions.
    - Fast Normalization: Every clip strictly conformed to 1080x1920 @ 30 FPS before final concatenation.
    - Professional audio chain: loudnorm -16 LUFS voiceover, -10% looped ambient BGM, 22% transition whoosh SFX.
    """

    def __init__(self) -> None:
        super().__init__(name="ffmpeg_renderer")
        self.fps = 30
        self.target_width = 1080
        self.target_height = 1920
        ensure_background_music()
        ensure_transition_whoosh_sfx()

    @staticmethod
    def get_duration(file_path: Path) -> float:
        """Query precise floating point duration of media file using ffprobe with timeout."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ]
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=15,
                check=True,
            )
            return float(result.stdout.strip())
        except Exception as exc:
            logger.warning("ffprobe failed for %s: %s; falling back to 5.0s", file_path, exc)
            return 5.0

    def render_scene_clip(
        self,
        visual_path: Path,
        duration: float,
        output_clip_path: Path,
        scene_idx: int,
    ) -> str:
        """Render an individual 9:16 scene clip standardized strictly to 1080x1920 @ 30 FPS.
        Applies -threads 2 -c:v libx264 -preset ultrafast -tune fastdecode -crf 24.
        For B-Roll video, strips stock audio (-an) and enforces exact time trimming (-t).
        """
        is_video = visual_path.suffix.lower() == ".mp4"
        clip_duration = duration + 0.1
        total_frames = math.ceil(clip_duration * self.fps)
        color_grading = "eq=contrast=1.08:saturation=1.15:brightness=-0.03"

        # Universal 1080x1920 @ 30 FPS normalization filter
        norm_filter = (
            f"scale={self.target_width}:{self.target_height}:force_original_aspect_ratio=increase,"
            f"crop={self.target_width}:{self.target_height},"
            f"setsar=1,"
            f"fps={self.fps}"
        )

        if is_video:
            # Real B-Roll Video: Loop, cut by time immediately, strip audio (-an), and normalize
            filter_chain = f"{norm_filter},{color_grading}"
            cmd = [
                "ffmpeg",
                "-y",
                "-threads", "2",
                "-stream_loop", "-1",
                "-i", str(visual_path),
                "-t", f"{clip_duration:.2f}",
                "-an",
                "-vf", filter_chain,
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-tune", "fastdecode",
                "-crf", "24",
                "-threads", "2",
                "-pix_fmt", "yuv420p",
                str(output_clip_path),
            ]
            self.logger.info("Rendering B-Roll VIDEO scene #%d (duration: %.2fs, -threads 2, -an)...", scene_idx, clip_duration)
        else:
            # Image: Alternates camera movement based on scene number
            if scene_idx % 2 == 1:
                # Odd scenes (1, 3, 5): Dynamic Zoom-In to center
                zoom_expr = "min(zoom+0.0015,1.15)"
                x_expr = "iw/2-(iw/zoom/2)"
                y_expr = "ih/2-(ih/zoom/2)"
            else:
                # Even scenes (2, 4): Dynamic Zoom-Out from 1.16x to 1.0x
                zoom_expr = "if(lte(zoom,1.0),1.16,max(1.001,zoom-0.0015))"
                x_expr = "iw/2-(iw/zoom/2)"
                y_expr = "ih/2-(ih/zoom/2)"

            filter_chain = (
                f"zoompan=z='{zoom_expr}':d={total_frames}:x='{x_expr}':y='{y_expr}':"
                f"s={self.target_width}x{self.target_height}:fps={self.fps},"
                f"{norm_filter},"
                f"vignette=PI/5,"
                f"{color_grading}"
            )
            cmd = [
                "ffmpeg",
                "-y",
                "-threads", "2",
                "-i", str(visual_path),
                "-t", f"{clip_duration:.2f}",
                "-vf", filter_chain,
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-tune", "fastdecode",
                "-crf", "24",
                "-threads", "2",
                "-pix_fmt", "yuv420p",
                str(output_clip_path),
            ]
            self.logger.info("Rendering Dynamic IMAGE scene #%d (duration: %.2fs, -threads 2)...", scene_idx, clip_duration)

        run_ffmpeg_process(cmd, timeout=75, error_context=f"Render Scene #{scene_idx} Clip")
        return str(output_clip_path)

    def composite_final_short(
        self,
        clip_paths: List[Path],
        master_audio_path: Path,
        subtitles_path: Path,
        output_video_path: Path,
        scene_durations: Optional[List[float]] = None,
    ) -> None:
        """Concatenate all scene clips, apply tpad clone to prevent audio clipping,
        mix voiceover with studio-grade loudnorm (-16 LUFS), loop background music at 10%,
        inject whoosh transition SFX at 22%, and burn in kinetic .ass subtitles.
        Restricted to -threads 2 -c:v libx264 -preset ultrafast -tune fastdecode -crf 24.
        """
        concat_txt = output_video_path.parent / f"concat_{output_video_path.stem}.txt"
        with open(concat_txt, "w", encoding="utf-8") as f:
            for clip in clip_paths:
                f.write(f"file '{clip.as_posix()}'\n")

        bg_music_path = ensure_background_music()
        whoosh_sfx_path = ensure_transition_whoosh_sfx()
        escaped_sub_path = str(subtitles_path).replace("\\", "/").replace(":", "\\:")

        # Calculate exact cut timestamps for transition SFX
        cut_ms: List[int] = []
        if scene_durations and len(scene_durations) > 1:
            running_dur = 0.0
            for d in scene_durations[:-1]:
                running_dur += d
                cut_ms.append(int(running_dur * 1000))

        has_sfx = len(cut_ms) > 0

        cmd = [
            "ffmpeg",
            "-y",
            "-threads", "2",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_txt),
            "-i", str(master_audio_path),
            "-stream_loop", "-1",
            "-i", str(bg_music_path),
        ]

        if has_sfx:
            cmd.extend(["-i", str(whoosh_sfx_path)])

            num_cuts = len(cut_ms)
            split_labels = "".join(f"[s{i}]" for i in range(num_cuts))
            filter_parts = [f"[3:a]asplit={num_cuts}{split_labels}"]
            delayed_labels = []
            for i, ms in enumerate(cut_ms):
                delayed_labels.append(f"[w{i}]")
                filter_parts.append(f"[s{i}]adelay={ms}|{ms},volume=0.22[w{i}]")

            filter_parts.append(f"{''.join(delayed_labels)}amix=inputs={num_cuts}:dropout_transition=0[sfx_all]")
            filter_parts.append("[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,apad=pad_dur=0.25[voice_clean]")
            filter_parts.append("[2:a]volume=0.10[bgm]")
            filter_parts.append("[voice_clean][bgm][sfx_all]amix=inputs=3:duration=first:dropout_transition=2[aout]")
            audio_filter = ";".join(filter_parts)
        else:
            audio_filter = (
                "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,apad=pad_dur=0.25[voice_clean];"
                "[2:a]volume=0.10[bgm];"
                "[voice_clean][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            )

        # Video Filter: tpad clones the last frame for 2.0s so -shortest terminates exclusively on audio!
        video_filter = f"[0:v]tpad=stop_mode=clone:stop_duration=2.0,subtitles='{escaped_sub_path}'[vout]"
        full_filter_complex = f"{video_filter};{audio_filter}"

        cmd.extend([
            "-filter_complex", full_filter_complex,
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "fastdecode",
            "-crf", "24",
            "-threads", "2",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_video_path),
        ])

        self.logger.info("Compositing final 9:16 Short (threads 2, ultrafast, crf 24): '%s'...", output_video_path)
        run_ffmpeg_process(cmd, timeout=75, error_context="Final Short Compositing")

        if concat_txt.exists():
            try:
                concat_txt.unlink()
            except Exception:
                pass

        # Audio-first verification with ffprobe
        try:
            vid_dur = self.get_duration(output_video_path)
            aud_dur = self.get_duration(master_audio_path)
            self.logger.info(
                "Audio-first duration check: video=%.3fs, master_audio=%.3fs (difference: %.3fs)",
                vid_dur,
                aud_dur,
                vid_dur - aud_dur,
            )
        except Exception as e:
            self.logger.warning("Could not measure final duration comparison: %s", e)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Render all scene clips in parallel (max_workers=2) and assemble final MP4."""
        t0 = time.perf_counter()
        short_id = input_data.get("short_id")
        scene_visual_paths = input_data.get("scene_visual_paths") or []
        scene_durations = input_data.get("scene_durations") or []
        master_audio_path_str = input_data.get("master_audio_path")
        subtitles_path_str = input_data.get("subtitles_path")

        if not short_id:
            raise ValueError("FFmpegRendererAgent requires 'short_id'")
        if not scene_visual_paths or not scene_durations:
            raise ValueError("FFmpegRendererAgent requires 'scene_visual_paths' and 'scene_durations'")
        if not master_audio_path_str or not subtitles_path_str:
            raise ValueError("FFmpegRendererAgent requires 'master_audio_path' and 'subtitles_path'")

        renders_dir = Path(settings.MEDIA_DIR) / "renders"
        renders_dir.mkdir(parents=True, exist_ok=True)
        temp_clips_dir = renders_dir / f"temp_{short_id}"
        temp_clips_dir.mkdir(parents=True, exist_ok=True)

        output_video = renders_dir / f"short_{short_id}.mp4"

        self.logger.info("Stage: Parallel RENDERING 1080x1920 Short #%s (%d clips, max_workers=2, CPU-controlled)...", short_id, len(scene_visual_paths))

        loop = asyncio.get_running_loop()

        # Render scene clips concurrently with max_workers=2 to cap CPU usage
        def _render_clips_parallel():
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = []
                for idx, (visual_path_str, duration) in enumerate(zip(scene_visual_paths, scene_durations), start=1):
                    clip_file = temp_clips_dir / f"clip_{idx}.mp4"
                    futures.append((
                        idx,
                        clip_file,
                        executor.submit(
                            self.render_scene_clip,
                            Path(visual_path_str),
                            duration,
                            clip_file,
                            idx,
                        )
                    ))

                results = []
                for idx, clip_file, fut in futures:
                    fut.result()
                    results.append((idx, clip_file))
                results.sort(key=lambda x: x[0])
                return [r[1] for r in results]

        clip_paths = await loop.run_in_executor(None, _render_clips_parallel)

        # Composite into final MP4 with BGM, SFX, loudnorm and Subtitles
        def _composite():
            self.composite_final_short(
                clip_paths=clip_paths,
                master_audio_path=Path(master_audio_path_str),
                subtitles_path=Path(subtitles_path_str),
                output_video_path=output_video,
                scene_durations=scene_durations,
            )

        await loop.run_in_executor(None, _composite)

        # Clean up temporary scene clips
        for clip in clip_paths:
            try:
                clip.unlink(missing_ok=True)
            except Exception:
                pass
        try:
            temp_clips_dir.rmdir()
        except Exception:
            pass

        elapsed = time.perf_counter() - t0
        self.logger.info("FFmpegRendererAgent finished in %.2f seconds at '%s'", elapsed, output_video)

        return {
            "status": "success",
            "agent": self.name,
            "short_id": short_id,
            "video_path": str(output_video),
            "elapsed_seconds": elapsed,
        }
