from typing import Optional
from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SystemSetting(Base):
    """
    Model for dynamic runtime configuration stored in PostgreSQL.
    Allows changing Gemini API Key, Model ID, TTS voice, YouTube
    tokens, and Celery Beat Auto-Pilot in real-time from the dashboard
    without restarting containers.
    """
    __tablename__ = "system_settings"

    # AI Text & Research Settings
    gemini_api_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gemini_model: Mapped[str] = mapped_column(
        String(100),
        default="gemini-2.5-flash",
        nullable=False,
    )

    # Edge TTS Audio Voice Settings
    tts_voice: Mapped[str] = mapped_column(
        String(100),
        default="es-MX-JorgeNeural",
        nullable=False,
    )
    tts_rate: Mapped[str] = mapped_column(
        String(50),
        default="+10%",
        nullable=False,
    )

    # YouTube Data API v3 OAuth Settings
    youtube_refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Pixabay Video & Image API Settings
    pixabay_api_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Auto-Pilot (Celery Beat) Settings
    auto_schedule_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_niche: Mapped[str] = mapped_column(
        String(255),
        default="Ciberseguridad y Linux",
        nullable=False,
    )
    daily_target_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
