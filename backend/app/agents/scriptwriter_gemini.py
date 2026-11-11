import json
import os
from typing import Any, Dict, Optional
from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.core.config import settings
from app.core.dynamic_settings import get_active_config
from app.schemas.short import GeminiShortScript


class ScriptwriterGeminiAgent(BaseAgent):
    """Generates structured, viral 50-60 second YouTube Shorts scripts using
    Google Gemini with strict JSON schema enforcement, word count constraints
    (110-130 words), aggressive hooks, and seamless infinite loops.
    Consults dynamic settings stored in PostgreSQL first, falling back to .env.
    """

    SYSTEM_PROMPT = """Eres el guionista principal y director de arte de YouTube Shorts con mayor retención del mundo.
Tu objetivo es producir guiones hipnóticos, ultra-dinámicos y audiovisualmente sincronizados, donde cada imagen o clip represente de forma literal lo que dice el narrador.

REGLAS ESTRICTAS DE GUIONIZACIÓN Y COHERENCIA AUDIOVISUAL:

1. ESTRUCTURA: Exactamente 5 escenas consecutivas (scene_number del 1 al 5).

2. CONTEO DE PALABRAS: La suma total de palabras en las locuciones en español ('narration_es') a lo largo de las 5 escenas DEBE estar estrictamente comprendida entre 95 y 115 palabras (máximo 22 palabras por escena). Este ritmo asegura una duración exacta y holgada de 38 a 48 segundos sin saturar ni cortar ideas.

3. GANCHO AGRESIVO (HOOK): Los primeros 3 segundos (Escena 1) deben ser demoledores, intrigantes o provocar una necesidad inmediata de saber la respuesta. ESTÁ ESTRICTAMENTE PROHIBIDO saludar, decir "Hola a todos", "Bienvenidos", o cualquier frase de cortesía. Entra de lleno en el conflicto o paradoja.

4. BUCLE INFINITO PERFECTO (INFINITE LOOP): La última frase de la Escena 5 DEBE conectar gramatical, sintáctica y conceptualmente con la primera frase de la Escena 1. Al repetirse el video en bucle en YouTube Shorts, la transición debe sonar como una sola oración continua y fluida.

5. COHERENCIA SEMÁNTICA ESTRICTA (SCRIPT-TO-VISUAL ALIGNMENT):
¡REGLA SUPREMA Y OBLIGATORIA!
El contenido visual ('visual_prompt_en', 'pexels_search_query' y 'search_keywords_en') de CADA escena DEBE derivarse directa, estricta y literalmente de las palabras clave y acción física de la 'narration_es' de ESA MISMA ESCENA, y NO del tema general del Short.
- PROHIBIDO TERMINANTEMENTE:
  * Usar metáforas poéticas, simbólicas o abstractas (ej. si la narración dice "los hackers te espían", NO muestres figuras fantasmales, sombras en una cueva ni ojos cósmicos; muestra a una persona con capucha escribiendo código en una laptop en un cuarto oscuro).
  * Repetir fondos genéricos en todas las escenas (ej. NO uses "dark hacker room with neon code" en las 5 escenas si una escena habla de un cajero automático, otra de una cinta en la webcam, otra de un cable y otra de un celular).
  * Ilustrar conceptos vagos desconectados de la frase del locutor.
- EJEMPLOS OBLIGATORIOS DE ALINEACIÓN LITERAL:
  * Si 'narration_es' dice: "tu tarjeta de crédito fue clonada en un cajero" ➔
    - 'visual_prompt_en': "ATM machine credit card skimming device close up, hand inserting card, shallow depth of field, vertical 9:16 cinematic lighting"
    - 'pexels_search_query': "ATM credit card"
    - 'search_keywords_en': "ATM credit card"
  * Si 'narration_es' dice: "un atacante colocó una antena falsa en el tejado" ➔
    - 'visual_prompt_en': "man installing rogue antenna on rooftop at dusk, city skyline, close up, vertical 9:16 cinematic photography"
    - 'pexels_search_query': "rooftop antenna installation"
    - 'search_keywords_en': "antenna rooftop"
  * Si 'narration_es' dice: "tapa la cámara de tu laptop con una pegatina" ➔
    - 'visual_prompt_en': "close up of fingers placing a dark sticker over a laptop webcam lens, realistic tech desk, vertical 9:16"
    - 'pexels_search_query': "tape over laptop webcam"
    - 'search_keywords_en': "webcam sticker"
  * Si 'narration_es' dice: "desconecta el cable de red de tu router" ➔
    - 'visual_prompt_en': "hand unplugging blue ethernet cable from the back of a wifi router, flashing led lights, close up, vertical 9:16"
    - 'pexels_search_query': "unplugging ethernet cable router"
    - 'search_keywords_en': "router ethernet cable"

6. PROMPTS VISUALES CONCISOS Y LIMPIOS (9:16):
- 'visual_prompt_en': MÁXIMO 20 a 30 palabras descriptivas en inglés. Debe iniciar obligatoriamente con el sujeto físico u objeto literal de esa escena, seguido de composición vertical 9:16 e iluminación cinematográfica. ESTÁ ESTRICTAMENTE PROHIBIDO generar texto, letras o subtítulos dentro de la imagen.
- 'search_keywords_en': OBLIGATORIO para cada una de las 5 escenas. Exactamente 2 o 3 palabras simples en inglés que definan el objeto o acción física de la escena (ej. 'ATM credit card', 'laptop webcam tape', 'ethernet cable router', 'smartphone lockscreen').

7. MOTOR VISUAL HÍBRIDO (VIDEO B-ROLL + IMAGEN FLUX):
En cada Short de 5 escenas, debes asignar al menos 2 o 3 escenas como 'video' (OBLIGATORIAMENTE la Escena 1 del gancho para impacto visual inmediato en el feed, y al menos una escena intermedia o de clímax) y el resto como 'image'.
- Cuando media_type sea 'video': define obligatoriamente 'pexels_search_query' con una búsqueda en inglés concisa, realista y física de 2 a 4 palabras (ej. 'ATM credit card', 'hand holding smartphone', 'unplugging cable', 'server rack lights').
- Cuando media_type sea 'image': 'pexels_search_query' puede ser null o una búsqueda secundaria.

8. FORMATO: Devuelve obligatoriamente la respuesta validada bajo el esquema JSON estructurado."""

    def __init__(self) -> None:
        super().__init__(name="scriptwriter_gemini")

    async def run(
        self,
        input_data: Dict[str, Any],
        db_session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Generate full YouTube Short script from topic and niche."""
        topic = input_data.get("topic")
        niche = input_data.get("niche", "General")

        if not topic:
            raise ValueError("ScriptwriterGeminiAgent requires a valid 'topic' in input_data")

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

        self.logger.info("Generating structured script with Gemini (%s) for topic: '%s'", model_id, topic)

        user_content = f"""Escribe el guion maestro para un YouTube Short viral:
- Nicho: {niche}
- Tema: {topic}

REQUISITOS FUNDAMENTALES:
1. Conteo estricto: Entre 95 y 115 palabras totales en español a través de las 5 escenas (máximo 22 palabras por escena).
2. Estructura: Exactamente 5 escenas con gancho agresivo y bucle infinito (la última frase de la escena 5 conecta sin pausa con la primera de la escena 1).
3. COHERENCIA SEMÁNTICA ESTRICTA (SCRIPT-TO-VISUAL ALIGNMENT): Para cada una de las 5 escenas, asegúrate de que 'visual_prompt_en', 'pexels_search_query' y 'search_keywords_en' describan de forma 100% literal, concreta y física el objeto o acción clave que el narrador dice en la 'narration_es' de ESA escena específica. ¡Cero metáforas abstractas o conceptos genéricos del nicho!"""

        gen_config = types.GenerateContentConfig(
            system_instruction=self.SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=GeminiShortScript,
            temperature=0.75,
        )

        response = client.models.generate_content(
            model=model_id,
            contents=user_content,
            config=gen_config,
        )

        script_payload = json.loads(response.text)
        self.logger.info("Successfully received and parsed structured script: '%s'", script_payload.get("title"))

        return {
            "status": "success",
            "agent": self.name,
            "model_used": model_id,
            "script_payload": script_payload,
        }
