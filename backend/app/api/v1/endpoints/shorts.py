import logging
from pathlib import Path
import shutil
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.agents.ffmpeg_renderer import FFmpegRendererAgent
from app.agents.subtitle_whisper import SubtitleWhisperAgent
from app.agents.visual_generator import VisualGeneratorAgent
from app.agents.voice_tts import VoiceTTSAgent
from app.core.config import settings
from app.core.constants import ShortStatus
from app.core.dynamic_settings import get_active_config
from app.db.session import get_db
from app.models.short import Short
from app.schemas.short import (
    SceneUpdateRequest,
    ShortApprove,
    ShortCreate,
    ShortListResponse,
    ShortResponse,
)
from app.worker.celery_app import celery_app
from app.worker.tasks import generate_short_pipeline, publish_to_youtube

logger = logging.getLogger(__name__)

router = APIRouter()


def remove_short_media_files(short_id: int) -> None:
    """Safely delete all local media files associated with a short."""
    try:
        media_root = Path(settings.MEDIA_DIR)
        shutil.rmtree(media_root / "audio" / str(short_id), ignore_errors=True)
        shutil.rmtree(media_root / "visuals" / str(short_id), ignore_errors=True)
        shutil.rmtree(media_root / "subtitles" / str(short_id), ignore_errors=True)
        (media_root / "renders" / f"short_{short_id}.mp4").unlink(missing_ok=True)
    except Exception as e:
        logger.warning("Error deleting media files for Short #%d: %s", short_id, e)


@router.post(
    "/",
    response_model=ShortResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear y encolar generación de YouTube Short",
)
async def create_short(
    short_in: ShortCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Crea un nuevo registro de YouTube Short en PostgreSQL y encola la tarea
    en segundo plano de Celery para investigación, guion y generación multimedia.
    """
    short = Short(
        niche=short_in.niche,
        topic=short_in.topic or "",
        status=ShortStatus.PENDING,
    )
    db.add(short)
    await db.commit()
    await db.refresh(short)

    # Disparar pipeline asíncrono con Celery
    try:
        task = generate_short_pipeline.delay(short.id)
        logger.info(
            "Enqueued Celery task %s for Short id=%d (niche='%s')",
            task.id,
            short.id,
            short.niche,
        )
    except Exception as exc:
        logger.error("Failed to enqueue Celery task: %s", exc)
        short.status = ShortStatus.FAILED
        short.error_message = f"Error encolando tarea de Celery: {str(exc)}"
        await db.commit()
        await db.refresh(short)

    return short


@router.get(
    "/",
    response_model=ShortListResponse,
    summary="Listar todos los Shorts con paginación",
)
async def list_shorts(
    skip: int = Query(0, ge=0, description="Registros a omitir"),
    limit: int = Query(50, ge=1, le=100, description="Límite por página"),
    niche: Optional[str] = Query(None, description="Filtrar por nicho"),
    status: Optional[ShortStatus] = Query(None, description="Filtrar por estado"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Lista todos los YouTube Shorts creados con soporte de paginación y filtros."""
    base_query = select(Short)

    if niche:
        base_query = base_query.where(Short.niche == niche)
    if status:
        base_query = base_query.where(Short.status == status)

    # Total count query
    count_stmt = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Paginated rows query
    paged_stmt = base_query.order_by(Short.id.desc()).offset(skip).limit(limit)
    rows_result = await db.execute(paged_stmt)
    items = rows_result.scalars().all()

    return ShortListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=items,
    )


@router.get(
    "/{short_id}",
    response_model=ShortResponse,
    summary="Obtener detalle y assets de un Short",
)
async def get_short_detail(
    short_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Obtiene el detalle completo de un Short por ID, incluyendo estado actual,
    script_payload, rutas de audio maestro, subtítulos .ass y video renderizado .mp4.
    """
    short = await db.get(Short, short_id)
    if not short:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"YouTube Short con id {short_id} no encontrado.",
        )
    return short


@router.post(
    "/{short_id}/approve",
    response_model=ShortResponse,
    summary="Aprobar Short y disparar publicación a YouTube",
)
async def approve_short_post(
    short_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Aprueba un Short renderizado (READY_FOR_REVIEW) y encola la publicación
    automática en YouTube Shorts.
    """
    short = await db.get(Short, short_id)
    if not short:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"YouTube Short con id {short_id} no encontrado.",
        )

    if short.status not in (ShortStatus.READY_FOR_REVIEW, ShortStatus.APPROVED, ShortStatus.FAILED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El Short debe estar en estado READY_FOR_REVIEW para aprobarse (estado actual: {short.status}).",
        )

    short.status = ShortStatus.APPROVED
    short.error_message = None
    await db.commit()
    await db.refresh(short)

    publish_to_youtube.delay(short.id)
    logger.info("Enqueued YouTube publication task for Short #%d", short.id)
    return short


@router.patch(
    "/{short_id}/approve",
    response_model=ShortResponse,
    summary="Aprobar o rechazar publicación del Short (PATCH)",
)
async def approve_short_upload_patch(
    short_id: int,
    approval: ShortApprove,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Endpoint alternativo para aprobar/rechazar mediante payload JSON."""
    short = await db.get(Short, short_id)
    if not short:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"YouTube Short con id {short_id} no encontrado.",
        )

    if approval.approved:
        short.status = ShortStatus.APPROVED
        short.error_message = None
        publish_to_youtube.delay(short.id)
    else:
        short.status = ShortStatus.FAILED
        short.error_message = "Publicación rechazada por el usuario."

    await db.commit()
    await db.refresh(short)
    return short


@router.post(
    "/{short_id}/retry",
    response_model=ShortResponse,
    summary="Reintentar pipeline de un Short",
)
async def retry_short_pipeline(
    short_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Reintenta la ejecución de un Short que haya fallado o necesite regenerarse."""
    short = await db.get(Short, short_id)
    if not short:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"YouTube Short con id {short_id} no encontrado.",
        )

    short.status = ShortStatus.PENDING
    short.error_message = None
    await db.commit()
    await db.refresh(short)

    generate_short_pipeline.delay(short.id)
    logger.info("Re-enqueued pipeline generation for Short #%d", short.id)
    return short


@router.patch(
    "/{short_id}/scenes/{scene_number}",
    response_model=ShortResponse,
    summary="Actualizar y regenerar quirúrgicamente una sola escena",
)
async def update_and_regenerate_scene(
    short_id: int,
    scene_number: int,
    payload: SceneUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Regenera quirúrgicamente el audio y/o imagen de una sola escena específica
    y recompone el Short en pocos segundos sin relanzar todo el pipeline.
    """
    short = await db.get(Short, short_id)
    if not short:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Short #{short_id} no encontrado.",
        )

    if not short.script_payload or "scenes" not in short.script_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Short #{short_id} aún no posee guion estructurado.",
        )

    scenes = short.script_payload.get("scenes", [])
    target_scene = next((s for s in scenes if s.get("scene_number") == scene_number), None)
    if not target_scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Escena #{scene_number} no encontrada en Short #{short_id}.",
        )

    # 1. Update text and media fields if supplied
    narration_changed = False
    if payload.narration_es is not None and payload.narration_es.strip():
        target_scene["narration_es"] = payload.narration_es.strip()
        narration_changed = True

    visual_changed = False
    if payload.visual_prompt_en is not None and payload.visual_prompt_en.strip():
        target_scene["visual_prompt_en"] = payload.visual_prompt_en.strip()
        visual_changed = True

    if payload.media_type is not None and payload.media_type.strip():
        new_mtype = payload.media_type.strip().lower()
        if new_mtype != target_scene.get("media_type"):
            target_scene["media_type"] = new_mtype
            visual_changed = True

    if payload.pexels_search_query is not None:
        target_scene["pexels_search_query"] = payload.pexels_search_query.strip()
        visual_changed = True

    if payload.search_keywords_en is not None:
        target_scene["search_keywords_en"] = payload.search_keywords_en.strip()
        visual_changed = True

    # 2. Regenerate audio for this scene if narration changed (or audio missing)
    audio_dir = Path(settings.MEDIA_DIR) / "audio" / str(short.id)
    audio_dir.mkdir(parents=True, exist_ok=True)
    scene_audio_file = audio_dir / f"scene_{scene_number}.mp3"

    voice_agent = VoiceTTSAgent()
    if narration_changed or not scene_audio_file.exists():
        logger.info("Regenerating audio for Scene #%d...", scene_number)
        _, new_duration = await voice_agent.synthesize_single_scene(
            short_id=short.id,
            scene_number=scene_number,
            narration_es=target_scene["narration_es"],
            db_session=db,
        )
        target_scene["duration_seconds"] = new_duration

    # 3. Regenerate visual for this scene if prompt/media_type changed (or file missing)
    visuals_dir = Path(settings.MEDIA_DIR) / "visuals" / str(short.id)
    visuals_dir.mkdir(parents=True, exist_ok=True)
    scene_mp4 = visuals_dir / f"scene_{scene_number}.mp4"
    scene_jpg = visuals_dir / f"scene_{scene_number}.jpg"

    visual_agent = VisualGeneratorAgent()
    config = await get_active_config(db)
    if visual_changed or (not scene_mp4.exists() and not scene_jpg.exists()):
        logger.info("Regenerating visual for Scene #%d...", scene_number)
        visual_agent.generate_single_scene(
            short_id=short.id,
            scene_number=scene_number,
            scene_data=target_scene,
            pixabay_api_key=config.pixabay_api_key,
        )

    # 4. Rebuild master audio
    scene_audio_files = [audio_dir / f"scene_{s['scene_number']}.mp3" for s in scenes]
    master_audio_path = audio_dir / "master.mp3"
    voice_agent.concatenate_audio_files(scene_audio_files, master_audio_path)
    short.audio_path = str(master_audio_path)

    # 5. Re-generate word-level ASS subtitles
    subtitle_agent = SubtitleWhisperAgent()
    sub_res = await subtitle_agent.run({
        "short_id": short.id,
        "audio_path": str(master_audio_path),
    })
    short.subtitle_path = sub_res["subtitles_path"]

    # 6. Fast Re-rendering with FFmpeg (detecting .mp4 vs .jpg per scene)
    scene_visual_paths = []
    for s in scenes:
        s_num = s.get("scene_number", 1)
        v_mp4 = visuals_dir / f"scene_{s_num}.mp4"
        v_jpg = visuals_dir / f"scene_{s_num}.jpg"
        if v_mp4.exists() and (s.get("media_type") == "video" or not v_jpg.exists()):
            scene_visual_paths.append(str(v_mp4))
        else:
            scene_visual_paths.append(str(v_jpg))
    scene_durations = [s.get("duration_seconds", 4.0) for s in scenes]

    renderer = FFmpegRendererAgent()
    rend_res = await renderer.run({
        "short_id": short.id,
        "scene_visual_paths": scene_visual_paths,
        "scene_durations": scene_durations,
        "master_audio_path": str(master_audio_path),
        "subtitles_path": short.subtitle_path,
    })

    short.video_path = rend_res["video_path"]
    short.status = ShortStatus.READY_FOR_REVIEW
    short.error_message = None

    # Mark JSONB updated
    updated_payload = dict(short.script_payload)
    updated_payload["scenes"] = list(scenes)
    short.script_payload = updated_payload
    flag_modified(short, "script_payload")
    await db.commit()
    await db.refresh(short)

    logger.info("Surgical scene regeneration completed for Short #%d, Scene #%d", short.id, scene_number)
    return short


@router.delete(
    "/queue/clear",
    summary="Limpiar Shorts estancados en cola o fallidos y vaciar Redis",
)
async def clear_stale_queue(
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Elimina en lote todos los Shorts que estén en estado PENDING, RESEARCHING,
    GENERATING_MEDIA, RENDERING o FAILED (conservando únicamente READY_FOR_REVIEW y PUBLISHED).
    Limpia también la cola de Celery en Redis y los archivos multimedia asociados.
    """
    stale_statuses = [
        ShortStatus.PENDING,
        ShortStatus.RESEARCHING,
        ShortStatus.GENERATING_MEDIA,
        ShortStatus.RENDERING,
        ShortStatus.FAILED,
    ]
    stmt = select(Short).where(Short.status.in_(stale_statuses))
    result = await db.execute(stmt)
    stale_shorts = result.scalars().all()

    deleted_ids = []
    for s in stale_shorts:
        deleted_ids.append(s.id)
        remove_short_media_files(s.id)
        await db.delete(s)

    await db.commit()

    # Purge Celery & Redis queue
    try:
        with celery_app.connection_for_write() as conn:
            conn.default_channel.client.delete("celery")
    except Exception as e:
        logger.warning("Could not delete celery redis key: %s", e)

    try:
        celery_app.control.purge()
    except Exception as e:
        logger.warning("Could not purge celery tasks: %s", e)

    logger.info("Cleared %d stale shorts from DB and purged Celery queue.", len(deleted_ids))
    return {
        "status": "success",
        "deleted_count": len(deleted_ids),
        "deleted_ids": deleted_ids,
    }


@router.delete(
    "/{short_id}",
    summary="Eliminar un YouTube Short individual y sus archivos",
)
async def delete_short(
    short_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Elimina el registro de PostgreSQL, revoca la tarea de Celery si sigue activa
    y borra todos los archivos de audio, visuales, subtítulos y video renderizado.
    """
    short = await db.get(Short, short_id)
    if not short:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"YouTube Short con id {short_id} no encontrado.",
        )

    # Revoke Celery task if still active
    try:
        inspector = celery_app.control.inspect()
        active_tasks = inspector.active() or {}
        for worker_name, tasks in active_tasks.items():
            for task in tasks:
                args = task.get("args") or []
                if args and args[0] == short_id:
                    celery_app.control.revoke(task.get("id"), terminate=True)
                    logger.info("Revoked active Celery task %s for Short #%d", task.get("id"), short_id)
    except Exception as e:
        logger.warning("Could not inspect/revoke Celery task: %s", e)

    remove_short_media_files(short_id)
    await db.delete(short)
    await db.commit()

    logger.info("Deleted Short #%d and all media assets.", short_id)
    return {"status": "deleted", "id": short_id}


