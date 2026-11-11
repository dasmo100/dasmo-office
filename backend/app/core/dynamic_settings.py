import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory, get_worker_db
from app.models.settings import SystemSetting

logger = logging.getLogger(__name__)


def mask_secret(secret: Optional[str]) -> Optional[str]:
    """Mask a secret key showing first 6 and last 4 characters for security."""
    if not secret:
        return None
    s = secret.strip()
    if len(s) <= 8:
        return "••••••••"
    return f"{s[:6]}••••••••{s[-4:]}"


class ActiveConfig:
    def __init__(
        self,
        gemini_api_key: str,
        gemini_model: str,
        tts_voice: str,
        tts_rate: str,
        youtube_refresh_token: str,
        auto_schedule_enabled: bool = False,
        default_niche: str = "Ciberseguridad y Linux",
        daily_target_count: int = 1,
        pexels_api_key: str = "",
    ):
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        self.tts_voice = tts_voice
        self.tts_rate = tts_rate
        self.youtube_refresh_token = youtube_refresh_token
        self.auto_schedule_enabled = auto_schedule_enabled
        self.default_niche = default_niche
        self.daily_target_count = daily_target_count
        self.pexels_api_key = pexels_api_key


async def get_or_create_settings(db: AsyncSession) -> SystemSetting:
    """Fetch the singleton SystemSetting row, creating it with defaults if missing."""
    result = await db.execute(select(SystemSetting).order_by(SystemSetting.id.asc()).limit(1))
    system_setting = result.scalar_one_or_none()
    if not system_setting:
        system_setting = SystemSetting(
            id=1,
            gemini_api_key=settings.GEMINI_API_KEY or None,
            gemini_model="gemini-2.5-flash",
            tts_voice=settings.DEFAULT_TTS_VOICE or "es-MX-JorgeNeural",
            tts_rate=settings.DEFAULT_TTS_RATE or "+10%",
            youtube_refresh_token=settings.YOUTUBE_REFRESH_TOKEN or None,
            pexels_api_key=settings.PEXELS_API_KEY or None,
            auto_schedule_enabled=False,
            default_niche="Ciberseguridad y Linux",
            daily_target_count=1,
        )
        db.add(system_setting)
        await db.commit()
        await db.refresh(system_setting)
    return system_setting


async def get_active_config(db: Optional[AsyncSession] = None) -> ActiveConfig:
    """
    Returns active configuration, checking PostgreSQL system_settings first,
    falling back to .env variables.
    """
    if db is not None:
        return await _resolve_active_config(db)

    async with get_worker_db() as session:
        return await _resolve_active_config(session)


async def _resolve_active_config(session: AsyncSession) -> ActiveConfig:
    row = await get_or_create_settings(session)

    gemini_key = (row.gemini_api_key.strip() if row.gemini_api_key else "") or settings.GEMINI_API_KEY
    gemini_model = (row.gemini_model.strip() if row.gemini_model else "") or "gemini-2.5-flash"
    tts_voice = (row.tts_voice.strip() if row.tts_voice else "") or settings.DEFAULT_TTS_VOICE
    tts_rate = (row.tts_rate.strip() if row.tts_rate else "") or settings.DEFAULT_TTS_RATE
    youtube_token = (row.youtube_refresh_token.strip() if row.youtube_refresh_token else "") or settings.YOUTUBE_REFRESH_TOKEN
    pexels_key = (row.pexels_api_key.strip() if row.pexels_api_key else "") or settings.PEXELS_API_KEY
    auto_schedule = bool(row.auto_schedule_enabled)
    default_niche = row.default_niche or "Ciberseguridad y Linux"
    daily_target = row.daily_target_count or 1

    return ActiveConfig(
        gemini_api_key=gemini_key,
        gemini_model=gemini_model,
        tts_voice=tts_voice,
        tts_rate=tts_rate,
        youtube_refresh_token=youtube_token,
        auto_schedule_enabled=auto_schedule,
        default_niche=default_niche,
        daily_target_count=daily_target,
        pexels_api_key=pexels_key,
    )
