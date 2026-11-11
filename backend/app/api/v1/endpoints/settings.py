import logging
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dynamic_settings import (
    get_active_config,
    get_or_create_settings,
    invalidate_settings_cache,
    is_valid_secret,
    mask_secret,
)
from app.db.session import get_db
from app.models.settings import SystemSetting
from app.schemas.settings import (
    SettingRevealResponse,
    SettingsResponse,
    SettingsUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_SECRET_FIELDS = {
    "gemini_api_key",
    "pixabay_api_key",
    "youtube_refresh_token",
}


def _build_settings_response(row: SystemSetting) -> SettingsResponse:
    has_gemini = is_valid_secret(row.gemini_api_key)
    has_pixabay = is_valid_secret(row.pixabay_api_key)
    has_youtube = is_valid_secret(row.youtube_refresh_token)

    return SettingsResponse(
        gemini_api_key_masked=mask_secret(row.gemini_api_key),
        has_gemini_key=has_gemini,
        gemini_model=row.gemini_model or "gemini-2.5-flash",
        tts_voice=row.tts_voice or "es-MX-JorgeNeural",
        tts_rate=row.tts_rate or "+10%",
        youtube_refresh_token_masked=mask_secret(row.youtube_refresh_token),
        has_youtube_token=has_youtube,
        pixabay_api_key_masked=mask_secret(row.pixabay_api_key),
        has_pixabay_key=has_pixabay,
        auto_schedule_enabled=bool(row.auto_schedule_enabled),
        default_niche=row.default_niche or "Ciberseguridad y Linux",
        daily_target_count=row.daily_target_count or 1,
        updated_at=row.updated_at,
    )


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
    return _build_settings_response(row)


@router.get(
    "/reveal",
    response_model=SettingRevealResponse,
    summary="Reveal plain text secret key",
)
async def reveal_system_setting(
    field: str = Query(..., description="Nombre del campo a revelar (gemini_api_key, pixabay_api_key, youtube_refresh_token)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns real plain-text secret value directly from SystemSetting PostgreSQL row.
    """
    if field not in ALLOWED_SECRET_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Campo '{field}' no es un secreto permitido. Campos válidos: {sorted(list(ALLOWED_SECRET_FIELDS))}",
        )

    row = await get_or_create_settings(db)
    raw_val = getattr(row, field, None)
    real_val = raw_val.strip() if is_valid_secret(raw_val) else ""

    return SettingRevealResponse(field=field, value=real_val)


@router.delete(
    "/key/{field_name}",
    response_model=SettingsResponse,
    summary="Delete a secret key from database",
)
async def delete_system_setting_key(
    field_name: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Sets the secret column in PostgreSQL to None, deleting it and invalidating hot cache.
    """
    if field_name not in ALLOWED_SECRET_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Campo '{field_name}' no es un secreto permitido. Campos válidos: {sorted(list(ALLOWED_SECRET_FIELDS))}",
        )

    row = await get_or_create_settings(db)
    setattr(row, field_name, None)
    await db.commit()
    await db.refresh(row)
    await invalidate_settings_cache()

    logger.info("Secret key '%s' deleted from system_settings", field_name)
    return _build_settings_response(row)


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

    # Note: if empty string is passed, it clears the key (sets to None)
    if payload.gemini_api_key is not None:
        key_val = payload.gemini_api_key.strip()
        row.gemini_api_key = key_val if key_val else None

    if payload.gemini_model is not None and payload.gemini_model.strip():
        row.gemini_model = payload.gemini_model.strip()

    if payload.tts_voice is not None and payload.tts_voice.strip():
        row.tts_voice = payload.tts_voice.strip()

    if payload.tts_rate is not None and payload.tts_rate.strip():
        row.tts_rate = payload.tts_rate.strip()

    if payload.youtube_refresh_token is not None:
        token_val = payload.youtube_refresh_token.strip()
        row.youtube_refresh_token = token_val if token_val else None

    if payload.pixabay_api_key is not None:
        pixabay_val = payload.pixabay_api_key.strip()
        row.pixabay_api_key = pixabay_val if pixabay_val else None

    if payload.auto_schedule_enabled is not None:
        row.auto_schedule_enabled = payload.auto_schedule_enabled

    if payload.default_niche is not None and payload.default_niche.strip():
        row.default_niche = payload.default_niche.strip()

    if payload.daily_target_count is not None and payload.daily_target_count > 0:
        row.daily_target_count = payload.daily_target_count

    await db.commit()
    await db.refresh(row)
    await invalidate_settings_cache()

    logger.info("System settings updated: model=%s, auto_pilot=%s", row.gemini_model, row.auto_schedule_enabled)
    return _build_settings_response(row)
