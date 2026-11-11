from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import ShortStatus


# ==============================================================================
# Strict Gemini Structured Output Schema
# ==============================================================================

class SceneScript(BaseModel):
    scene_number: int = Field(
        ...,
        description="Número correlativo de la escena (del 1 al 5).",
    )
    narration_es: str = Field(
        ...,
        description="Voz en off en español con ritmo dinámico y de alta retención (máximo 22 palabras por escena).",
    )
    visual_prompt_en: str = Field(
        ...,
        description=(
            "Detailed visual prompt in English for 9:16 vertical video/image generation. "
            "CRITICAL: MUST strictly and literally depict the concrete physical subject, action, or object "
            "described in this scene's 'narration_es' (e.g. 'ATM machine credit card skimming device close up', "
            "'hand putting tape over laptop webcam', 'hand unplugging ethernet router cable'). "
            "Zero abstract metaphors or generic niche backgrounds."
        ),
    )
    duration_seconds: float = Field(
        ...,
        description="Duración estimada de la escena en segundos (ej. 7.0, 8.0).",
    )
    media_type: str = Field(
        "image",
        description="Tipo de medio audiovisual: 'video' para clip B-Roll vertical o 'image' para imagen artística generada con Flux.",
    )
    pexels_search_query: Optional[str] = Field(
        None,
        description=(
            "Exact literal search query in English (2 to 4 words) derived directly from the physical noun/action "
            "in this scene's 'narration_es' (e.g. 'ATM credit card skimmer', 'tape over laptop webcam', 'unplugging router cable')."
        ),
    )
    search_keywords_en: Optional[str] = Field(
        None,
        description=(
            "2 to 3 simple English literal nouns/action keywords from this scene's 'narration_es' for stock photo search "
            "(e.g. 'ATM credit card', 'laptop webcam tape', 'router ethernet cable')."
        ),
    )


class GeminiShortScript(BaseModel):
    title: str = Field(
        ...,
        description="Título clickbait intrigante, viral y con gancho para YouTube Shorts.",
    )
    description: str = Field(
        ...,
        description="Descripción persuasiva para YouTube Shorts que incluye hashtags relevantes (#Shorts).",
    )
    tags: List[str] = Field(
        ...,
        description="Lista de tags/etiquetas SEO optimizadas para el algoritmo de YouTube.",
    )
    scenes: List[SceneScript] = Field(
        ...,
        description="Lista estricta de 5 escenas consecutivas que componen el Short.",
    )


# ==============================================================================
# FastAPI CRUD Schemas (Pydantic v2)
# ==============================================================================

class ShortBase(BaseModel):
    niche: str = Field(
        ...,
        max_length=255,
        examples=["Ciberseguridad y Linux", "Finanzas y Cripto", "Misterios del Cosmos"],
        description="Nicho temático del canal de YouTube Shorts.",
    )
    topic: Optional[str] = Field(
        None,
        max_length=500,
        examples=["Cómo los hackers clonan señales de autos", "¿Por qué el agua caliente se congela más rápido?"],
        description="Tema específico o pregunta detonante. Si se omite, el ResearcherAgent generará un ángulo viral inédito.",
    )


class ShortCreate(ShortBase):
    pass


class ShortUpdate(BaseModel):
    niche: Optional[str] = None
    topic: Optional[str] = None
    title: Optional[str] = None
    status: Optional[ShortStatus] = None
    script_payload: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    audio_path: Optional[str] = None
    subtitle_path: Optional[str] = None
    video_path: Optional[str] = None
    youtube_video_id: Optional[str] = None


class ShortApprove(BaseModel):
    approved: bool = Field(True, description="Confirmación editorial para publicar el Short en YouTube.")


class SceneUpdateRequest(BaseModel):
    narration_es: Optional[str] = Field(None, description="Nueva locución en español para esta escena.")
    visual_prompt_en: Optional[str] = Field(None, description="Nuevo prompt visual para 9:16 en inglés.")
    media_type: Optional[str] = Field(None, description="Tipo de recurso visual: 'video' o 'image'.")
    pexels_search_query: Optional[str] = Field(None, description="Término de búsqueda B-Roll en inglés.")
    search_keywords_en: Optional[str] = Field(None, description="2 a 3 palabras clave simples en inglés para búsqueda de stock fotos.")


class ShortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    niche: str
    topic: str
    title: Optional[str] = None
    script_payload: Optional[Dict[str, Any]] = None
    status: ShortStatus
    error_message: Optional[str] = None
    audio_path: Optional[str] = None
    subtitle_path: Optional[str] = None
    video_path: Optional[str] = None
    youtube_video_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ShortListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[ShortResponse]
