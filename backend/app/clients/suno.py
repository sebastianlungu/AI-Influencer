from __future__ import annotations

import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import requests

from app.core.config import settings
from app.core.cost import add_cost
from app.core.logging import log
from app.core.paths import get_data_path


class SunoClient:
    """Suno API client for music generation.

    Generates short instrumental music clips for fitness videos.
    Polls for completion and downloads audio files.
    """

    BASE_URL = "https://api.suno.ai/v1"  # Placeholder - update with actual Suno API URL
    MAX_POLL_ATTEMPTS = 60  # Poll for up to 2 minutes (60 × 2s = 120s)
    POLL_INTERVAL_S = 2.0

    def __init__(self, api_key: str, model: str = "chirp-v3"):
        """Initialize Suno client.

        Args:
            api_key: Suno API key
            model: Model name (default: chirp-v3)

        Raises:
            RuntimeError: If API key is missing
        """
        if not api_key:
            raise RuntimeError("SUNO_API_KEY is required")

        self.api_key = api_key
        self.model = model
        self.timeout_s = 30  # HTTP request timeout

        log.info(f"SunoClient initialized: model={model}")

    def generate_clip(self, music_brief: dict[str, Any], seconds: int = 6) -> str:
        """Generate music clip from Grok-provided brief.

        Args:
            music_brief: Music spec from Grok with keys: style, mood, tempo, instruments, prompt
            seconds: Duration in seconds (default 6)

        Returns:
            Local path to downloaded audio file (MP3)

        Raises:
            RuntimeError: If generation fails or times out
        """
        log.info(f"SUNO_REQUEST seconds={seconds} style={music_brief.get('style', 'unknown')[:30]}")

        # Extract prompt from Grok brief
        prompt = music_brief.get("prompt", "")
        if not prompt:
            # Fallback: construct prompt from brief components
            style = music_brief.get("style", "ambient cinematic")
            mood = music_brief.get("mood", "uplifting")
            tempo = music_brief.get("tempo", "moderate")
            instruments = music_brief.get("instruments", "piano, strings")
            prompt = f"{style}, {mood}, {tempo}, {instruments}, {seconds}s instrumental"

        # Track cost (estimated ~$0.10 per 6s clip)
        estimated_cost = Decimal("0.10") * (seconds / 6)
        add_cost(estimated_cost, "suno")

        # Submit generation request
        payload = {
            "model": self.model,
            "prompt": prompt,
            "duration": seconds,
            "instrumental": True,  # No vocals
            "style": music_brief.get("style", settings.suno_style_hints_default),
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            # Submit generation request
            resp = requests.post(
                f"{self.BASE_URL}/generate",
                headers=headers,
                json=payload,
                timeout=self.timeout_s,
            )
            resp.raise_for_status()

            data = resp.json()
            generation_id = data.get("id")

            if not generation_id:
                raise RuntimeError(f"Suno API did not return generation ID: {data}")

            log.info(f"SUNO_GENERATION_STARTED id={generation_id}")

            # Poll for completion
            audio_url = self._poll_for_completion(generation_id)

            # Download audio file
            audio_path = self._download_audio(audio_url, generation_id)

            log.info(f"SUNO_SUCCESS path={Path(audio_path).name}")
            return audio_path

        except requests.exceptions.Timeout:
            raise RuntimeError(f"Suno API timeout after {self.timeout_s}s")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(
                f"Suno API error: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            raise RuntimeError(f"Suno generation failed: {str(e)}")

    def _poll_for_completion(self, generation_id: str) -> str:
        """Poll Suno API until generation is complete.

        Args:
            generation_id: ID of generation request

        Returns:
            URL to download audio file

        Raises:
            RuntimeError: If polling times out or generation fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        for attempt in range(self.MAX_POLL_ATTEMPTS):
            time.sleep(self.POLL_INTERVAL_S)

            try:
                resp = requests.get(
                    f"{self.BASE_URL}/generations/{generation_id}",
                    headers=headers,
                    timeout=self.timeout_s,
                )
                resp.raise_for_status()

                data = resp.json()
                status = data.get("status")

                if status == "completed":
                    audio_url = data.get("audio_url")
                    if not audio_url:
                        raise RuntimeError(f"Completed generation has no audio_url: {data}")
                    return audio_url

                elif status == "failed":
                    error_msg = data.get("error", "Unknown error")
                    raise RuntimeError(f"Suno generation failed: {error_msg}")

                # Still processing
                log.debug(
                    f"SUNO_POLLING attempt={attempt + 1}/{self.MAX_POLL_ATTEMPTS} status={status}"
                )

            except requests.exceptions.HTTPError as e:
                if e.response.status_code >= 500:
                    # Retryable server error
                    log.warning(f"Suno poll error {e.response.status_code}, retrying...")
                    continue
                else:
                    # Non-retryable error
                    raise RuntimeError(
                        f"Suno polling error: {e.response.status_code} - {e.response.text}"
                    )

        # Timeout
        raise RuntimeError(
            f"Suno generation timeout after {self.MAX_POLL_ATTEMPTS * self.POLL_INTERVAL_S}s"
        )

    def _download_audio(self, audio_url: str, generation_id: str) -> str:
        """Download generated audio file.

        Args:
            audio_url: URL to download audio from
            generation_id: Generation ID (for filename)

        Returns:
            Local path to downloaded audio file

        Raises:
            RuntimeError: If download fails
        """
        # Ensure audio directory exists
        audio_dir = get_data_path("generated/audio")
        audio_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        audio_path = audio_dir / f"suno_{generation_id}.mp3"

        try:
            resp = requests.get(audio_url, timeout=60)  # 1 minute for download
            resp.raise_for_status()

            with open(audio_path, "wb") as f:
                f.write(resp.content)

            log.info(f"SUNO_DOWNLOAD path={audio_path.name} size={len(resp.content)} bytes")
            return str(audio_path)

        except requests.exceptions.HTTPError as e:
            raise RuntimeError(
                f"Suno audio download failed: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            raise RuntimeError(f"Suno audio download failed: {str(e)}")
