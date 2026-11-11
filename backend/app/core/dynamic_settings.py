import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory, get_worker_db
from app.models.settings import SystemSetting

logger = logging.getLogger(__name__)


def is_valid_secret(secret: Optional[str]) -> bool:
    """Return True if secret is present and not an unconfigured placeholder."""
    if not secret:
        return False
    v = secret.strip()
    if not v:
        return False
    if v.startswith("your_") and v.endswith("_here"):
        return False
    return True


def mask_secret(secret: Optional[str]) -> Optional[str]:
    """Mask a secret key for security (returns ••••••••)."""
    if not is_valid_secret(secret):
        return None
    return "••••••••"


async def invalidate_settings_cache() -> None:
    """Invalidate runtime/hot caches across the application."""
    logger.debug("System settings hot cache invalidated.")


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
        pixabay_api_key: str = "",
    ):
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        self.tts_voice = tts_voice
        self.tts_rate = tts_rate
        self.youtube_refresh_token = youtube_refresh_token
        self.auto_schedule_enabled = auto_schedule_enabled
        self.default_niche = default_niche
        self.daily_target_count = daily_target_count
        self.pixabay_api_key = pixabay_api_key


async def get_or_create_settings(db: AsyncSession) -> SystemSetting:
    """Fetch the singleton SystemSetting row, creating it with defaults if missing."""
    result = await db.execute(select(SystemSetting).order_by(SystemSetting.id.asc()).limit(1))
    system_setting = result.scalar_one_or_none()
    if not system_setting:
        init_gemini = settings.GEMINI_API_KEY if is_valid_secret(settings.GEMINI_API_KEY) else None
        init_yt = settings.YOUTUBE_REFRESH_TOKEN if is_valid_secret(settings.YOUTUBE_REFRESH_TOKEN) else None
        init_pixabay = settings.PIXABAY_API_KEY if is_valid_secret(settings.PIXABAY_API_KEY) else None

        system_setting = SystemSetting(
            id=1,
            gemini_api_key=init_gemini,
            gemini_model="gemini-2.5-flash",
            tts_voice=settings.DEFAULT_TTS_VOICE or "es-MX-JorgeNeural",
            tts_rate=settings.DEFAULT_TTS_RATE or "+10%",
            youtube_refresh_token=init_yt,
            pixabay_api_key=init_pixabay,
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

    def _resolve(db_val: Optional[str], env_val: Optional[str]) -> str:
        if is_valid_secret(db_val):
            return db_val.strip()
        # If DB row is not set, fallback to valid env value
        if db_val is None and is_valid_secret(env_val):
            return env_val.strip()
        return ""

    gemini_key = _resolve(row.gemini_api_key, settings.GEMINI_API_KEY)
    gemini_model = (row.gemini_model.strip() if row.gemini_model else "") or "gemini-2.5-flash"
    tts_voice = (row.tts_voice.strip() if row.tts_voice else "") or settings.DEFAULT_TTS_VOICE
    tts_rate = (row.tts_rate.strip() if row.tts_rate else "") or settings.DEFAULT_TTS_RATE
    youtube_token = _resolve(row.youtube_refresh_token, settings.YOUTUBE_REFRESH_TOKEN)
    pixabay_key = _resolve(row.pixabay_api_key, settings.PIXABAY_API_KEY)
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
        pixabay_api_key=pixabay_key,
    )
