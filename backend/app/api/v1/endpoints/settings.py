import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dynamic_settings import (
    get_active_config,
    get_or_create_settings,
    mask_secret,
)
from app.db.session import get_db
from app.schemas.settings import SettingsResponse, SettingsUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=SettingsResponse,
    include_in_schema=False,
)
@router.get(
    "/",
    response_model=SettingsResponse,
    summary="Get active system settings with masked secrets",
)
async def get_system_settings(db: AsyncSession = Depends(get_db)):
    """
    Retrieve active runtime settings (Gemini, Edge TTS, YouTube, Auto-Pilot) with
    sensitive keys safely masked for frontend administration.
    """
    row = await get_or_create_settings(db)
    active = await get_active_config(db)

    return SettingsResponse(
        gemini_api_key_masked=mask_secret(active.gemini_api_key),
        has_gemini_key=bool(active.gemini_api_key),
        gemini_model=active.gemini_model,
        tts_voice=active.tts_voice,
        tts_rate=active.tts_rate,
        youtube_refresh_token_masked=mask_secret(active.youtube_refresh_token),
        has_youtube_token=bool(active.youtube_refresh_token),
        pexels_api_key_masked=mask_secret(active.pexels_api_key),
        has_pexels_key=bool(active.pexels_api_key),
        auto_schedule_enabled=active.auto_schedule_enabled,
        default_niche=active.default_niche,
        daily_target_count=active.daily_target_count,
        updated_at=row.updated_at,
    )


@router.put(
    "",
    response_model=SettingsResponse,
    include_in_schema=False,
)
@router.put(
    "/",
    response_model=SettingsResponse,
    summary="Update system settings dynamically in real-time",
)
async def update_system_settings(
    payload: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Hot-updates runtime credentials, models, voices and auto-pilot in PostgreSQL
    without requiring container restarts.
    """
    row = await get_or_create_settings(db)

    if payload.gemini_api_key is not None:
        key_val = payload.gemini_api_key.strip()
        if key_val:
            row.gemini_api_key = key_val

    if payload.gemini_model is not None and payload.gemini_model.strip():
        row.gemini_model = payload.gemini_model.strip()

    if payload.tts_voice is not None and payload.tts_voice.strip():
        row.tts_voice = payload.tts_voice.strip()

    if payload.tts_rate is not None and payload.tts_rate.strip():
        row.tts_rate = payload.tts_rate.strip()

    if payload.youtube_refresh_token is not None:
        token_val = payload.youtube_refresh_token.strip()
        if token_val:
            row.youtube_refresh_token = token_val

    if payload.pexels_api_key is not None:
        pexels_val = payload.pexels_api_key.strip()
        if pexels_val:
            row.pexels_api_key = pexels_val

    if payload.auto_schedule_enabled is not None:
        row.auto_schedule_enabled = payload.auto_schedule_enabled

    if payload.default_niche is not None and payload.default_niche.strip():
        row.default_niche = payload.default_niche.strip()

    if payload.daily_target_count is not None and payload.daily_target_count > 0:
        row.daily_target_count = payload.daily_target_count

    await db.commit()
    await db.refresh(row)
    active = await get_active_config(db)

    logger.info("System settings updated: model=%s, auto_pilot=%s", active.gemini_model, active.auto_schedule_enabled)

    return SettingsResponse(
        gemini_api_key_masked=mask_secret(active.gemini_api_key),
        has_gemini_key=bool(active.gemini_api_key),
        gemini_model=active.gemini_model,
        tts_voice=active.tts_voice,
        tts_rate=active.tts_rate,
        youtube_refresh_token_masked=mask_secret(active.youtube_refresh_token),
        has_youtube_token=bool(active.youtube_refresh_token),
        pexels_api_key_masked=mask_secret(active.pexels_api_key),
        has_pexels_key=bool(active.pexels_api_key),
        auto_schedule_enabled=active.auto_schedule_enabled,
        default_niche=active.default_niche,
        daily_target_count=active.daily_target_count,
        updated_at=row.updated_at,
    )
