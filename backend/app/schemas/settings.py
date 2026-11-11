from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gemini_api_key_masked: Optional[str] = Field(
        None,
        description="Enmascaramiento seguro de la API Key de Gemini",
    )
    has_gemini_key: bool = Field(
        False,
        description="Indica si existe una clave de Gemini configurada activa",
    )
    gemini_model: str = Field(
        "gemini-2.5-flash",
        description="ID del modelo de Gemini seleccionado (ej. gemini-2.5-flash, gemini-3-flash-preview)",
    )
    tts_voice: str = Field(
        "es-MX-JorgeNeural",
        description="Voz de Edge TTS",
    )
    tts_rate: str = Field(
        "+10%",
        description="Velocidad del audio de voz",
    )
    youtube_refresh_token_masked: Optional[str] = Field(
        None,
        description="Enmascaramiento del refresh token de YouTube",
    )
    has_youtube_token: bool = Field(
        False,
        description="Indica si YouTube OAuth 2.0 está conectado",
    )
    pixabay_api_key_masked: Optional[str] = Field(
        None,
        description="Enmascaramiento seguro de la API Key de Pixabay (••••••••)",
    )
    has_pixabay_key: bool = Field(
        False,
        description="Indica si existe una clave de Pixabay configurada activa",
    )
    auto_schedule_enabled: bool = Field(
        False,
        description="Indica si el piloto automático de Celery Beat está activo",
    )
    default_niche: str = Field(
        "Ciberseguridad y Linux",
        description="Nicho predeterminado para el piloto automático diario",
    )
    daily_target_count: int = Field(
        1,
        description="Cantidad objetivo de Shorts a crear por día automáticamente",
    )
    updated_at: Optional[datetime] = None


class SettingsUpdate(BaseModel):
    gemini_api_key: Optional[str] = Field(
        None,
        description="Nueva clave de API de Gemini (dejar en blanco si no se desea modificar)",
    )
    gemini_model: Optional[str] = Field(
        None,
        description="ID del modelo de Gemini a utilizar (ej. gemini-2.5-flash, gemini-3-flash-preview)",
    )
    tts_voice: Optional[str] = Field(
        None,
        description="Voz de Edge TTS para el narrador",
    )
    tts_rate: Optional[str] = Field(
        None,
        description="Velocidad del habla (ej. +10%, +0%)",
    )
    youtube_refresh_token: Optional[str] = Field(
        None,
        description="Refresh Token de YouTube OAuth 2.0",
    )
    pixabay_api_key: Optional[str] = Field(
        None,
        description="API Key de Pixabay para videos B-Roll y fotografías stock",
    )
    auto_schedule_enabled: Optional[bool] = Field(
        None,
        description="Activar o desactivar el piloto automático de Celery Beat",
    )
    default_niche: Optional[str] = Field(
        None,
        description="Nicho por defecto para generación automática",
    )
    daily_target_count: Optional[int] = Field(
        None,
        description="Meta de Shorts diarios",
    )


class SettingRevealResponse(BaseModel):
    field: str = Field(..., description="Nombre del campo de credencial revelado")
    value: Optional[str] = Field(None, description="Valor real de la clave en texto plano")
