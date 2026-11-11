import asyncio
from pathlib import Path
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple
import edge_tts
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.core.config import settings
from app.core.dynamic_settings import get_active_config


class VoiceTTSAgent(BaseAgent):
    """Synthesizes high-fidelity voice narration for each scene concurrently using edge-tts
    and asyncio.gather, extracts exact durations with ffprobe, and merges all scenes
    into a unified master audio track.
    """

    def __init__(self) -> None:
        super().__init__(name="voice_tts")

    @staticmethod
    def get_audio_duration(file_path: Path) -> float:
        """Measure the exact duration in seconds of an audio file using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())

    def concatenate_audio_files(
        self,
        audio_files: List[Path],
        output_path: Path,
    ) -> None:
        """Concatenate individual scene MP3s into a single master MP3 using FFmpeg's
        audio concat filter with clean PCM re-encoding and a 0.35s tail padding
        (apad=pad_dur=0.35) so the final word is never clipped or truncated.
        """
        inputs = []
        filter_inputs = ""
        for i, audio_file in enumerate(audio_files):
            inputs.extend(["-i", str(audio_file)])
            filter_inputs += f"[{i}:a]"

        filter_complex = f"{filter_inputs}concat=n={len(audio_files)}:v=0:a=1,apad=pad_dur=0.35[outa]"

        cmd = [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[outa]",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(output_path),
        ]
        self.logger.info("Concatenating %d audio scenes with audio concat filter & apad=0.35s...", len(audio_files))
        subprocess.run(cmd, capture_output=True, text=True, check=True)

    async def _synthesize_scene_file(
        self,
        scene_number: int,
        narration: str,
        audio_dir: Path,
        voice: str,
        rate: str,
    ) -> Tuple[int, str, float]:
        """Synthesize a single scene audio with retry and voice fallback."""
        scene_file = audio_dir / f"scene_{scene_number}.mp3"
        clean_text = narration.strip()
        self.logger.info("Generating concurrent TTS for Scene #%d: '%s'...", scene_number, clean_text[:35])

        voices_to_try = [voice, "es-MX-DaliaNeural", "es-ES-AlvaroNeural"]
        last_exc = None
        for v in voices_to_try:
            for attempt in range(2):
                try:
                    communicate = edge_tts.Communicate(text=clean_text, voice=v, rate=rate)
                    await communicate.save(str(scene_file))
                    if scene_file.exists() and scene_file.stat().st_size > 500:
                        duration = self.get_audio_duration(scene_file)
                        self.logger.info(
                            "Scene #%d duration measured via ffprobe: %.3f seconds (voice: %s)",
                            scene_number,
                            duration,
                            v,
                        )
                        return scene_number, str(scene_file), duration
                except Exception as e:
                    last_exc = e
                    self.logger.warning(
                        "edge-tts attempt %d failed for Scene #%d (voice=%s): %s",
                        attempt + 1,
                        scene_number,
                        v,
                        e,
                    )
                    await asyncio.sleep(0.5)

        raise RuntimeError(f"Failed to synthesize audio for Scene #{scene_number}: {last_exc}")

    async def synthesize_single_scene(
        self,
        short_id: int,
        scene_number: int,
        narration_es: str,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> Tuple[str, float]:
        """Regenerate a single scene audio."""
        config = await get_active_config(db_session)
        v = voice or config.tts_voice or "es-MX-JorgeNeural"
        r = rate or config.tts_rate or "+10%"

        audio_dir = Path(settings.MEDIA_DIR) / "audio" / str(short_id)
        audio_dir.mkdir(parents=True, exist_ok=True)

        _, path, duration = await self._synthesize_scene_file(
            scene_number=scene_number,
            narration=narration_es,
            audio_dir=audio_dir,
            voice=v,
            rate=r,
        )
        return path, duration

    async def run(
        self,
        input_data: Dict[str, Any],
        db_session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Synthesize audio for all scenes in parallel using asyncio.gather."""
        t0 = time.perf_counter()
        short_id = input_data.get("short_id")
        script_payload = input_data.get("script_payload") or {}
        scenes = script_payload.get("scenes", [])

        if not short_id:
            raise ValueError("VoiceTTSAgent requires a valid 'short_id'")
        if not scenes:
            raise ValueError("VoiceTTSAgent requires 'scenes' inside 'script_payload'")

        # Resolve active config dynamically
        config = await get_active_config(db_session)
        default_voice = config.tts_voice or "es-MX-JorgeNeural"
        default_rate = config.tts_rate or "+10%"

        audio_dir = Path(settings.MEDIA_DIR) / "audio" / str(short_id)
        audio_dir.mkdir(parents=True, exist_ok=True)

        voice = input_data.get("voice", default_voice)
        rate = input_data.get("rate", default_rate)

        self.logger.info(
            "Starting concurrent TTS synthesis for Short #%s with voice '%s' (rate: %s)...",
            short_id,
            voice,
            rate,
        )

        tasks = []
        for idx, scene in enumerate(scenes, start=1):
            scene_number = scene.get("scene_number", idx)
            narration = scene.get("narration_es", "").strip()
            if not narration:
                raise ValueError(f"Scene #{scene_number} has an empty 'narration_es'")

            tasks.append(
                self._synthesize_scene_file(
                    scene_number=scene_number,
                    narration=narration,
                    audio_dir=audio_dir,
                    voice=voice,
                    rate=rate,
                )
            )

        # Execute all 5 audio scenes concurrently
        results: List[Tuple[int, str, float]] = await asyncio.gather(*tasks)
        results.sort(key=lambda x: x[0])

        scene_audio_paths = [r[1] for r in results]
        scene_durations = [r[2] for r in results]

        # Build master.mp3
        master_audio_file = audio_dir / "master.mp3"
        self.concatenate_audio_files(
            audio_files=[Path(p) for p in scene_audio_paths],
            output_path=master_audio_file,
        )

        total_duration = self.get_audio_duration(master_audio_file)
        elapsed = time.perf_counter() - t0
        self.logger.info(
            "VoiceTTSAgent completed in %.2f seconds. Master audio duration: %.3fs",
            elapsed,
            total_duration,
        )

        return {
            "status": "success",
            "agent": self.name,
            "short_id": short_id,
            "voice_used": voice,
            "master_audio_path": str(master_audio_file),
            "scene_audio_paths": scene_audio_paths,
            "scene_durations": scene_durations,
            "total_duration": total_duration,
            "elapsed_seconds": elapsed,
        }
