import asyncio
from concurrent.futures import ThreadPoolExecutor
import io
import logging
from pathlib import Path
import random
import re
import time
from typing import Any, Dict, List, Optional
import urllib.parse
import httpx
from PIL import Image, ImageDraw, ImageEnhance, ImageOps
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.core.config import settings
from app.core.dynamic_settings import get_active_config

logger = logging.getLogger(__name__)

# Semantic mapping of concrete physical nouns from Spanish narration to English anchors
NOUN_MAPPINGS_ES_TO_EN: Dict[str, str] = {
    # Banking, Cards & Money
    "cajero": "ATM machine",
    "cajeros": "ATM machine",
    "tarjeta": "credit card",
    "tarjetas": "credit cards",
    "banco": "bank vault",
    "bancos": "bank",
    "dinero": "cash money",
    "billete": "money banknotes",
    "billetes": "money banknotes",
    "billetera": "leather wallet",
    "cartera": "wallet",
    "skimmer": "card skimming device",
    "skimming": "card skimming device",
    "clonada": "card skimmer",
    "clonado": "card skimmer",
    "clonar": "card skimmer",
    # Computers, Phones & Hardware
    "webcam": "laptop webcam",
    "camara": "camera lens",
    "cámara": "camera lens",
    "camaras": "surveillance cameras",
    "cámaras": "surveillance cameras",
    "pantalla": "computer screen",
    "pantallas": "computer screens",
    "monitor": "computer monitor",
    "monitores": "computer monitors",
    "laptop": "laptop computer",
    "laptops": "laptop computers",
    "computadora": "computer",
    "computadoras": "computers",
    "computador": "computer",
    "pc": "desktop computer",
    "celular": "smartphone",
    "celulares": "smartphones",
    "telefono": "smartphone",
    "teléfono": "smartphone",
    "telefonos": "smartphones",
    "teléfonos": "smartphones",
    "teclado": "keyboard typing",
    "teclados": "keyboards",
    "mouse": "computer mouse",
    "raton": "computer mouse",
    "ratón": "computer mouse",
    "cable": "cable cord",
    "cables": "cables wires",
    "hdmi": "HDMI cable",
    "usb": "USB flash drive",
    "pendrive": "USB flash drive",
    "disco": "hard drive disk",
    "chip": "microchip circuit",
    "chips": "microchips",
    "router": "wifi router",
    "routers": "wifi routers",
    "modem": "modem router",
    "módem": "modem router",
    "wifi": "wifi router",
    "antena": "antenna rooftop",
    "antenas": "antennas",
    "servidor": "server rack lights",
    "servidores": "server racks",
    "enchufe": "electrical power plug",
    "bateria": "battery pack",
    "batería": "battery pack",
    "auriculares": "headphones",
    "audifonos": "headphones",
    "audífonos": "headphones",
    "microfono": "microphone",
    "micrófono": "microphone",
    "reloj": "smartwatch",
    "fibra": "fiber optic cable",
    # Security, Access & Surveillance
    "candado": "padlock",
    "candados": "padlocks",
    "llave": "metal key",
    "llaves": "keys",
    "cerradura": "door keyhole lock",
    "cerraduras": "locks",
    "contraseña": "password screen login",
    "contraseñas": "password login screen",
    "password": "password login screen",
    "codigo": "computer code screen",
    "código": "computer code screen",
    "huella": "fingerprint scan",
    "huellas": "fingerprints",
    "rostro": "facial recognition scan",
    "cara": "face scan",
    "ojo": "eye iris scan",
    "ojos": "eyes",
    "alarma": "security alarm",
    "policia": "police officer",
    "policía": "police officer",
    "hacker": "hacker typing laptop",
    "hackers": "hackers computers",
    "espia": "spy surveillance",
    "espía": "spy surveillance",
    "pegatina": "tape sticker",
    "cinta": "adhesive tape",
    "sticker": "tape sticker",
    # Vehicles, Physical World & Places
    "auto": "car vehicle",
    "autos": "cars",
    "coche": "car vehicle",
    "coches": "cars",
    "carro": "car vehicle",
    "vehiculo": "car vehicle",
    "vehículo": "car vehicle",
    "puerta": "door handle lock",
    "puertas": "doors",
    "ventana": "glass window",
    "ventanas": "windows",
    "lluvia": "heavy rain city",
    "fuego": "fire flames burning",
    "llamas": "fire flames",
    "agua": "glass of water",
    "cafe": "coffee cup mug",
    "café": "coffee cup mug",
    "vaso": "glass cup",
    "taza": "coffee mug",
    "libro": "open book reading",
    "libros": "books library",
    "papel": "document paper",
    "cuaderno": "handwritten notebook",
    "pasaporte": "passport document",
    "manos": "hands holding",
    "mano": "hand holding",
    "dedo": "finger pressing button",
    "dedos": "fingers typing",
    "oficina": "modern office desk",
    "edificio": "skyscraper building",
    "calle": "city street night",
    "ciudad": "city skyline night",
}


class VisualGeneratorAgent(BaseAgent):
    """Bulletproof Hybrid Visual Generator Agent:
    - Real 9:16 vertical B-Roll video clips from Pexels API when scene media_type == 'video'.
    - High-definition vertical 9:16 images from Pollinations AI (Flux model with immediate Turbo retry).
    - Real stock photography fallback (Pexels Photos, LoremFlickr, Picsum) with cinematic grading.
    - Zero blue canvas fallback with text: guarantees 100% photographic and cinematic visuals.
    """

    PEXELS_VIDEOS_ENDPOINT = "https://api.pexels.com/videos/search"
    PEXELS_PHOTOS_ENDPOINT = "https://api.pexels.com/v1/search"
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    def __init__(self) -> None:
        super().__init__(name="visual_generator")
        self.target_width = 1080
        self.target_height = 1920

    @classmethod
    def extract_literal_nouns_from_narration(cls, narration_es: str) -> List[str]:
        """Extract concrete physical objects and action nouns from Spanish narration
        using semantic term mapping.
        """
        if not narration_es:
            return []
        clean_text = re.sub(r"[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]", " ", narration_es.lower())
        words = clean_text.split()
        extracted: List[str] = []
        for w in words:
            mapped = NOUN_MAPPINGS_ES_TO_EN.get(w)
            if mapped and mapped not in extracted:
                extracted.append(mapped)
        return extracted

    @classmethod
    def build_aligned_scene_prompts(cls, scene_data: Dict[str, Any]) -> Dict[str, str]:
        """Build strictly aligned search queries and prompts enforcing literal Script-to-Visual Alignment.
        Guarantees that the physical subject or action of narration_es is prioritized
        at the very beginning of the prompt and search query.
        """
        narration_es = scene_data.get("narration_es", "")
        extracted_nouns = cls.extract_literal_nouns_from_narration(narration_es)

        raw_kw = scene_data.get("search_keywords_en") or ""
        clean_kw = re.sub(r"[^a-zA-Z0-9\s]", " ", raw_kw).strip()

        raw_pexels = scene_data.get("pexels_search_query") or ""
        clean_pexels = re.sub(r"[^a-zA-Z0-9\s]", " ", raw_pexels).strip()

        # 1. Determine focal anchor (physical concrete object/subject)
        if clean_kw:
            focal_anchor = clean_kw
        elif clean_pexels:
            focal_anchor = clean_pexels
        elif extracted_nouns:
            focal_anchor = " ".join(extracted_nouns[:2])
        else:
            focal_anchor = "technology hardware"

        # 2. Pexels query (2 to 4 words strictly describing the physical action/subject)
        if clean_pexels and len(clean_pexels.split()) <= 4:
            pexels_query = clean_pexels
        elif clean_kw and len(clean_kw.split()) <= 4:
            pexels_query = clean_kw
        elif extracted_nouns:
            pexels_query = " ".join(extracted_nouns[:3])
        else:
            pexels_query = focal_anchor

        # 3. Reinforced Pollinations Prompt:
        # Prepend focal anchor to visual_prompt_en so the physical subject is
        # placed in the highest-attention initial tokens of the prompt.
        raw_prompt = scene_data.get("visual_prompt_en") or ""
        clean_prompt = re.sub(r"[^a-zA-Z0-9\s]", " ", raw_prompt).strip()

        focal_first_word = focal_anchor.split()[0].lower() if focal_anchor else ""
        if focal_first_word and focal_first_word in clean_prompt.lower()[:35]:
            reinforced_prompt = clean_prompt
        else:
            reinforced_prompt = f"{focal_anchor}, {clean_prompt}" if clean_prompt else focal_anchor

        # 4. Reinforced Stock Photo Keywords (for Pexels Photos / LoremFlickr)
        if clean_kw:
            stock_keywords = " ".join(clean_kw.split()[:3])
        elif extracted_nouns:
            stock_keywords = " ".join(extracted_nouns[:2])
        else:
            stock_keywords = focal_anchor

        return {
            "focal_anchor": focal_anchor,
            "pexels_query": pexels_query,
            "reinforced_prompt": reinforced_prompt,
            "stock_keywords": stock_keywords,
        }

    def generate_fallback_image(
        self,
        scene_number: int,
        output_path: Path,
    ) -> str:
        """Create a dark, cinematic gradient background with subtle bokeh lighting.
        Contains ZERO text overlays so viewers never see fallback error text.
        """
        self.logger.warning("Generating textless cinematic background for Scene #%d...", scene_number)
        image = Image.new("RGB", (self.target_width, self.target_height), color=(10, 14, 23))
        draw = ImageDraw.Draw(image)

        # Smooth dark cinematic vertical gradient
        colors = [
            (8, 12, 20),
            (16, 20, 32),
            (24, 28, 45),
            (18, 22, 35),
            (9, 13, 22),
        ]
        step_height = self.target_height // len(colors)
        for i, color in enumerate(colors):
            y_start = i * step_height
            y_end = (i + 1) * step_height if i < len(colors) - 1 else self.target_height
            draw.rectangle([0, y_start, self.target_width, y_end], fill=color)

        # Soft decorative bokeh light orbs
        for _ in range(8):
            rx = random.randint(100, self.target_width - 100)
            ry = random.randint(200, self.target_height - 200)
            radius = random.randint(80, 220)
            alpha_color = (
                random.randint(40, 70),
                random.randint(50, 90),
                random.randint(90, 150),
            )
            draw.ellipse(
                [rx - radius, ry - radius, rx + radius, ry + radius],
                outline=alpha_color,
                width=3,
            )

        image.save(output_path, "JPEG", quality=92)
        return str(output_path)

    def download_pexels_video_sync(
        self,
        scene_number: int,
        query: str,
        output_path: Path,
        api_key: str,
    ) -> Optional[str]:
        """Query Pexels Video Search API, select the highest quality vertical mp4 clip,
        and download it to output_path.
        """
        if not api_key:
            return None

        clean_query = query.strip()
        if not clean_query:
            clean_query = "cinematic vertical footage"

        params = {
            "query": clean_query,
            "orientation": "portrait",
            "size": "medium",
            "per_page": 5,
        }
        headers = {
            "Authorization": api_key,
            "User-Agent": self.USER_AGENT,
        }

        try:
            self.logger.info(
                "Searching Pexels B-Roll Video for Scene #%d [query: '%s']...",
                scene_number,
                clean_query,
            )
            with httpx.Client(timeout=18.0, follow_redirects=True) as client:
                resp = client.get(self.PEXELS_VIDEOS_ENDPOINT, params=params, headers=headers)
                if resp.status_code != 200:
                    self.logger.warning(
                        "Pexels API responded with status %d for query '%s'",
                        resp.status_code,
                        clean_query,
                    )
                    return None

                data = resp.json()
                videos = data.get("videos") or []
                if not videos:
                    # Retry with simplified 2-word core focal query if original query had > 2 words
                    words = clean_query.split()
                    if len(words) > 2:
                        simplified_query = " ".join(words[:2])
                        self.logger.info(
                            "No videos for '%s'. Retrying Pexels with simplified query: '%s'...",
                            clean_query,
                            simplified_query,
                        )
                        params["query"] = simplified_query
                        retry_resp = client.get(self.PEXELS_VIDEOS_ENDPOINT, params=params, headers=headers)
                        if retry_resp.status_code == 200:
                            videos = retry_resp.json().get("videos") or []

                if not videos:
                    self.logger.warning("No Pexels videos found for query '%s'", clean_query)
                    return None

                # Find candidate vertical video file
                selected_download_url = None
                for vid in videos:
                    video_files = vid.get("video_files") or []
                    for vf in video_files:
                        if vf.get("file_type") == "video/mp4":
                            w = vf.get("width") or 0
                            h = vf.get("height") or 0
                            if h > w:  # Portrait
                                selected_download_url = vf.get("link")
                                break
                    if selected_download_url:
                        break

                if not selected_download_url:
                    for vid in videos:
                        video_files = vid.get("video_files") or []
                        for vf in video_files:
                            if vf.get("file_type") == "video/mp4" and vf.get("link"):
                                selected_download_url = vf.get("link")
                                break
                        if selected_download_url:
                            break

                if not selected_download_url:
                    return None

                self.logger.info("Downloading Pexels video clip for Scene #%d...", scene_number)
                vid_resp = client.get(selected_download_url, timeout=25.0)
                if vid_resp.status_code == 200 and len(vid_resp.content) >= 15360:
                    with open(output_path, "wb") as f:
                        f.write(vid_resp.content)
                    self.logger.info(
                        "Successfully downloaded Pexels B-Roll video for Scene #%d (%.1f KB) to '%s'",
                        scene_number,
                        len(vid_resp.content) / 1024,
                        output_path,
                    )
                    return str(output_path)
                else:
                    self.logger.warning("Failed to download video stream from Pexels for Scene #%d", scene_number)
                    return None

        except Exception as e:
            self.logger.warning("Pexels video download error for Scene #%d: %s", scene_number, e)
            return None

    def download_pollinations_image_sync(
        self,
        scene_number: int,
        prompt: str,
        output_path: Path,
    ) -> Optional[str]:
        """Download high-definition vertical image from Pollinations AI:
        - Sanitizes prompt to max 25 words with alphanumeric characters.
        - First attempt with model=flux.
        - Immediate retry with model=turbo if flux fails or returns < 15KB.
        - Validates image decodability with Pillow before saving.
        """
        # Sanitize prompt: remove quotes, slashes, punctuation that break URLs
        clean_words = re.sub(r"[^a-zA-Z0-9\s]", " ", prompt).split()
        clean_prompt = " ".join(clean_words[:25])
        if not clean_prompt:
            clean_prompt = "cinematic atmospheric vertical background"

        encoded_prompt = urllib.parse.quote(clean_prompt)
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/jpeg,image/*,*/*;q=0.8",
        }

        # Attempts: First Flux, then Turbo
        models_to_try = ["flux", "turbo"]
        for model in models_to_try:
            seed = random.randint(100000, 9999999)
            url = (
                f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                f"?width={self.target_width}&height={self.target_height}&model={model}&nologo=true&seed={seed}"
            )
            try:
                self.logger.info(
                    "Requesting Pollinations image for Scene #%d [model=%s, timeout=25s]...",
                    scene_number,
                    model,
                )
                with httpx.Client(timeout=25.0, follow_redirects=True, headers=headers) as client:
                    resp = client.get(url)
                    if resp.status_code == 200 and len(resp.content) >= 15360:
                        # Verify bytes represent a valid decodeable image
                        img = Image.open(io.BytesIO(resp.content))
                        img.verify()
                        with open(output_path, "wb") as f:
                            f.write(resp.content)
                        self.logger.info(
                            "Successfully fetched Scene #%d (%s) image from Pollinations (%.1f KB).",
                            scene_number,
                            model,
                            len(resp.content) / 1024,
                        )
                        return str(output_path)
                    else:
                        self.logger.warning(
                            "Pollinations %s returned status %d (size: %d bytes) for Scene #%d",
                            model,
                            resp.status_code,
                            len(resp.content),
                            scene_number,
                        )
            except Exception as e:
                self.logger.warning("Pollinations %s error for Scene #%d: %s", model, scene_number, e)

        return None

    def download_stock_photo_fallback(
        self,
        scene_number: int,
        keywords: str,
        output_path: Path,
        pexels_api_key: Optional[str] = None,
    ) -> Optional[str]:
        """Download a real, high-resolution vertical photo from Pexels Photos,
        LoremFlickr or Picsum, and apply cinematic grading and 1080x1920 cropping.
        """
        clean_kw = re.sub(r"[^a-zA-Z0-9\s]", " ", keywords).strip()
        search_kw = " ".join(clean_kw.split()[:3]) or "technology hardware"
        self.logger.info(
            "Searching real stock photo fallback for Scene #%d [keywords: '%s']...",
            scene_number,
            search_kw,
        )

        headers = {
            "User-Agent": self.USER_AGENT,
        }

        # 1. Try Pexels Photos API if key is available
        if pexels_api_key:
            try:
                pex_headers = {
                    "Authorization": pexels_api_key,
                    "User-Agent": self.USER_AGENT,
                }
                params = {
                    "query": search_kw,
                    "orientation": "portrait",
                    "per_page": 5,
                }
                with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                    resp = client.get(self.PEXELS_PHOTOS_ENDPOINT, params=params, headers=pex_headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        photos = data.get("photos") or []
                        if photos:
                            photo_url = photos[0].get("src", {}).get("large2x") or photos[0].get("src", {}).get("original")
                            if photo_url:
                                img_resp = client.get(photo_url, timeout=20.0)
                                if img_resp.status_code == 200 and len(img_resp.content) >= 15360:
                                    return self._process_and_save_photo(img_resp.content, output_path, scene_number, "Pexels Photo")
            except Exception as e:
                self.logger.warning("Pexels photo search failed for Scene #%d: %s", scene_number, e)

        # 2. Try LoremFlickr with category keywords
        try:
            encoded_kw = urllib.parse.quote(search_kw.replace(" ", ","))
            lorem_url = f"https://loremflickr.com/{self.target_width}/{self.target_height}/{encoded_kw}"
            with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
                resp = client.get(lorem_url)
                if resp.status_code == 200 and len(resp.content) >= 15360:
                    return self._process_and_save_photo(resp.content, output_path, scene_number, "LoremFlickr")
        except Exception as e:
            self.logger.warning("LoremFlickr photo search failed for Scene #%d: %s", scene_number, e)

        # 3. Try Picsum Photos with random seed
        try:
            seed = random.randint(100, 99999)
            picsum_url = f"https://picsum.photos/{self.target_width}/{self.target_height}?random={seed}"
            with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
                resp = client.get(picsum_url)
                if resp.status_code == 200 and len(resp.content) >= 15360:
                    return self._process_and_save_photo(resp.content, output_path, scene_number, "Picsum Photos")
        except Exception as e:
            self.logger.warning("Picsum Photos search failed for Scene #%d: %s", scene_number, e)

        return None

    def _process_and_save_photo(
        self,
        raw_bytes: bytes,
        output_path: Path,
        scene_number: int,
        provider_name: str,
    ) -> str:
        """Fit image to 1080x1920, apply subtle cinematic darkening so subtitles pop, and save."""
        img = Image.open(io.BytesIO(raw_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Fit to 1080x1920 keeping aspect ratio
        fitted = ImageOps.fit(img, (self.target_width, self.target_height), method=Image.Resampling.LANCZOS)

        # Cinematic color enhancement
        graded = ImageEnhance.Brightness(fitted).enhance(0.86)
        graded = ImageEnhance.Contrast(graded).enhance(1.10)

        graded.save(output_path, "JPEG", quality=92)
        self.logger.info(
            "Successfully saved real stock photo from %s for Scene #%d (%.1f KB) to '%s'",
            provider_name,
            scene_number,
            output_path.stat().st_size / 1024,
            output_path,
        )
        return str(output_path)

    def process_scene_visual_sync(
        self,
        scene_number: int,
        scene_data: Dict[str, Any],
        visuals_dir: Path,
        pexels_api_key: Optional[str] = None,
    ) -> str:
        """Process visual for a single scene with strict Script-to-Visual Alignment
        and bulletproof fallback:
        1. Pexels B-Roll Video if media_type == 'video' and pexels_api_key exists.
        2. Pollinations AI (Flux model with immediate Turbo retry).
        3. Real stock photograph fallback (Pexels Photos, LoremFlickr, Picsum) with cinematic grading.
        4. Textless cinematic bokeh canvas as last-ditch offline fallback.
        """
        media_type = (scene_data.get("media_type") or "image").lower()
        aligned = self.build_aligned_scene_prompts(scene_data)
        focal_anchor = aligned["focal_anchor"]
        pexels_query = aligned["pexels_query"]
        visual_prompt = aligned["reinforced_prompt"]
        search_keywords = aligned["stock_keywords"]

        narration_preview = (scene_data.get("narration_es") or "")[:50]
        self.logger.info(
            "Scene #%d Alignment [Narration: '%s...'] -> Focal: '%s' | PexelsQuery: '%s' | MediaType: %s",
            scene_number,
            narration_preview,
            focal_anchor,
            pexels_query,
            media_type,
        )

        # 1. Attempt Pexels Video B-Roll
        if media_type == "video" and pexels_api_key:
            mp4_path = visuals_dir / f"scene_{scene_number}.mp4"
            downloaded = self.download_pexels_video_sync(scene_number, pexels_query, mp4_path, pexels_api_key)
            if downloaded and Path(downloaded).exists():
                return downloaded
            self.logger.info("Pexels video not available for Scene #%d. Falling back to image pipeline.", scene_number)

        jpg_path = visuals_dir / f"scene_{scene_number}.jpg"

        # 2. Pollinations AI (Flux -> Turbo)
        pollinations_res = self.download_pollinations_image_sync(scene_number, visual_prompt, jpg_path)
        if pollinations_res and Path(pollinations_res).exists():
            return pollinations_res

        # 3. Real Stock Photo Fallback
        self.logger.warning(
            "Pollinations failed for Scene #%d. Activating real stock photo fallback...",
            scene_number,
        )
        stock_res = self.download_stock_photo_fallback(scene_number, search_keywords, jpg_path, pexels_api_key)
        if stock_res and Path(stock_res).exists():
            return stock_res

        # 4. Textless cinematic gradient canvas (zero error text)
        return self.generate_fallback_image(scene_number, jpg_path)

    def generate_single_scene(
        self,
        short_id: int,
        scene_number: int,
        scene_data: Dict[str, Any],
        pexels_api_key: Optional[str] = None,
    ) -> str:
        """Regenerate a single scene visual surgically."""
        visuals_dir = Path(settings.MEDIA_DIR) / "visuals" / str(short_id)
        visuals_dir.mkdir(parents=True, exist_ok=True)
        return self.process_scene_visual_sync(
            scene_number=scene_number,
            scene_data=scene_data,
            visuals_dir=visuals_dir,
            pexels_api_key=pexels_api_key,
        )

    async def run(
        self,
        input_data: Dict[str, Any],
        db_session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Download or generate visuals for all 5 scenes using controlled concurrency
        (max_workers=2 with staggered dispatch) to prevent 429 rate-limiting.
        """
        t0 = time.perf_counter()
        short_id = input_data.get("short_id")
        script_payload = input_data.get("script_payload") or {}
        scenes = script_payload.get("scenes", [])

        if not short_id:
            raise ValueError("VisualGeneratorAgent requires 'short_id'")
        if not scenes:
            raise ValueError("VisualGeneratorAgent requires 'scenes' inside 'script_payload'")

        # Retrieve dynamic Pexels API Key
        config = await get_active_config(db_session)
        pexels_api_key = config.pexels_api_key

        visuals_dir = Path(settings.MEDIA_DIR) / "visuals" / str(short_id)
        visuals_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            "Starting controlled hybrid visual generation for Short #%s (5 scenes, max_workers=2, has_pexels=%s)...",
            short_id,
            bool(pexels_api_key),
        )

        loop = asyncio.get_running_loop()

        def _parallel_fetch():
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = []
                for s in scenes:
                    s_num = s.get("scene_number", 1)
                    fut = executor.submit(
                        self.process_scene_visual_sync,
                        s_num,
                        s,
                        visuals_dir,
                        pexels_api_key,
                    )
                    futures.append((s_num, fut))
                    # Stagger requests by 1.0s to avoid sudden burst to external APIs
                    time.sleep(1.0)

                results = []
                for s_num, fut in futures:
                    results.append((s_num, fut.result()))
                results.sort(key=lambda x: x[0])
                return [r[1] for r in results]

        scene_visual_paths = await loop.run_in_executor(None, _parallel_fetch)
        elapsed = time.perf_counter() - t0
        self.logger.info("VisualGeneratorAgent completed in %.2f seconds for %d scenes.", elapsed, len(scenes))

        return {
            "status": "success",
            "agent": self.name,
            "short_id": short_id,
            "scene_visual_paths": scene_visual_paths,
            "duration_seconds": elapsed,
        }
