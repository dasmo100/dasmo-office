import os
from typing import Any, Dict, List, Optional
from google import genai
from google.genai import types
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.core.config import settings
from app.core.dynamic_settings import get_active_config
from app.models.short import Short


class ResearcherAgent(BaseAgent):
    """Researches trends, analyzes existing database history to prevent repetition,
    and generates high-retention, counter-intuitive topics using Gemini.
    Consults dynamic settings stored in PostgreSQL first, falling back to .env.
    """

    def __init__(self) -> None:
        super().__init__(name="researcher")

    async def get_recent_topics(
        self,
        db_session: AsyncSession,
        niche: str,
        limit: int = 20,
    ) -> List[str]:
        """Fetch the last N topics generated in PostgreSQL to ensure novelty."""
        stmt = (
            select(Short.topic)
            .where(Short.niche == niche, Short.topic.is_not(None))
            .order_by(Short.id.desc())
            .limit(limit)
        )
        result = await db_session.execute(stmt)
        return [row[0] for row in result.fetchall() if row[0]]

    async def run(
        self,
        input_data: Dict[str, Any],
        db_session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Execute researcher stage.

        If 'topic' is already provided, validates and passes it forward.
        If only 'niche' is provided, queries PostgreSQL for the last 20 topics,
        prompts Gemini, and generates a fresh, viral angle.
        """
        niche = input_data.get("niche", "").strip()
        topic = input_data.get("topic")

        if topic and topic.strip():
            self.logger.info("Specific topic provided by user: '%s'", topic)
            return {
                "status": "success",
                "agent": self.name,
                "niche": niche,
                "topic": topic.strip(),
                "source": "user_provided",
            }

        # Resolve active configuration dynamically
        config = await get_active_config(db_session)
        api_key = config.gemini_api_key
        model_id = config.gemini_model or "gemini-2.5-flash"

        if not api_key:
            raise ValueError(
                "No Gemini API key configured. Please configure your GEMINI_API_KEY "
                "in the Web Dashboard Settings or in your .env file."
            )

        client = genai.Client(api_key=api_key)

        self.logger.info("No topic provided. Querying DB history for niche '%s'...", niche)
        recent_topics: List[str] = []
        if db_session is not None:
            recent_topics = await self.get_recent_topics(db_session, niche=niche, limit=20)
            self.logger.info("Found %d recent topics in DB to avoid.", len(recent_topics))

        excluded_list_str = (
            "\n".join([f"- {t}" for t in recent_topics])
            if recent_topics
            else "(Aún no hay temas previos registrados en este nicho)"
        )

        research_prompt = f"""Actúa como un estratega de contenido viral de YouTube Shorts y analista de tendencias.
Tu misión es formular un tema o ángulo sumamente impactante, contraintuitivo y de máxima retención para el siguiente nicho:

NICHO: "{niche}"

REGLAS ESTRICTAS DE NOVEDAD:
1. El tema propuesto DEBE ser específico, intrigante o desafiar el sentido común.
2. NO uses fórmulas genéricas como "5 tips para..." o "Qué es...".
3. PROHIBIDO REPETIR o crear variaciones obvias de estos últimos 20 temas ya publicados:
{excluded_list_str}

RESPONDE ÚNICAMENTE con el tema/ángulo propuesto en una sola frase directa (máximo 15 palabras), sin comillas, sin viñetas y sin introducciones."""

        self.logger.info("Invoking Gemini (%s) for novel topic generation...", model_id)
        response = client.models.generate_content(
            model=model_id,
            contents=research_prompt,
            config=types.GenerateContentConfig(
                temperature=0.85,
            ),
        )

        generated_topic = response.text.strip().strip('"').strip("'")
        self.logger.info("Generated novel topic: '%s'", generated_topic)

        return {
            "status": "success",
            "agent": self.name,
            "niche": niche,
            "topic": generated_topic,
            "source": "gemini_researcher",
            "model_used": model_id,
            "excluded_topics_count": len(recent_topics),
        }
