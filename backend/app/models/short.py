from typing import Any, Dict, Optional
from sqlalchemy import JSON, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import ShortStatus
from app.db.base import Base


class Short(Base):
    __tablename__ = "shorts"

    # Niche and Topic definitions
    niche: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    topic: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Generated Script Structure (JSONB in PostgreSQL)
    script_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
    )

    # Pipeline Processing Status
    status: Mapped[ShortStatus] = mapped_column(
        Enum(ShortStatus, name="short_status_enum", native_enum=False),
        default=ShortStatus.PENDING,
        index=True,
        nullable=False,
    )

    # Error handling & Traceback
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Generated Media Assets
    audio_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    subtitle_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    video_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # External Publication Tracking
    youtube_video_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
