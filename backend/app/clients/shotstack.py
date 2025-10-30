from __future__ import annotations

import os
import time
import tempfile
from decimal import Decimal
from pathlib import Path

import httpx

from app.core.config import settings
from app.core.cost import add_cost
from app.core.logging import log
from app.core.paths import get_data_path


def _base_url() -> str:
    """Get Shotstack API base URL for the configured region."""
    region = settings.shotstack_region.lower()
    return f"https://api.shotstack.io/{region}/stage"


class ShotstackClient:
    """Shotstack video editing client.

    Strips audio from source video and adds licensed soundtrack.
    """

    def __init__(
        self,
        api_key: str | None = None,
        soundtrack_url: str | None = None,
        resolution: str | None = None,
    ):
        self.key = api_key or settings.shotstack_api_key
        if not self.key:
            raise RuntimeError("SHOTSTACK_API_KEY missing")

        self.soundtrack_url = soundtrack_url or settings.soundtrack_url
        if not self.soundtrack_url:
            raise RuntimeError("SOUNDTRACK_URL missing")

        self.resolution = resolution or settings.output_resolution
        self.headers = {"x-api-key": self.key, "Content-Type": "application/json"}

    def simple_polish(self, video_path: str, payload: dict) -> str:
        """Strip audio from video and add licensed soundtrack.

        Args:
            video_path: Path to source video file
            payload: Dictionary containing optional 'length' (duration in seconds)

        Returns:
            Path to the edited video file

        Raises:
            RuntimeError: If render fails or times out

        Note:
            Some Shotstack plans don't accept file:// sources. If you encounter
            errors, consider pre-uploading the video to a signed URL (S3/GCS)
            and using that URL instead of file://.
        """
        # Conservative cost estimate (adjust with real metering)
        add_cost(Decimal("0.02"), "shotstack")

        length = payload.get("length", 8)
        abs_path = str(Path(video_path).resolve())

        # Build timeline: video clip (muted) + soundtrack
        body = {
            "timeline": {
                "tracks": [
                    {
                        "clips": [
                            {
                                "asset": {
                                    "type": "video",
                                    "src": f"file://{abs_path}",
                                    "volume": 0,  # Mute original audio
                                },
                                "start": 0,
                                "length": length,
                                "fit": "contain",
                            }
                        ]
                    },
                    {
                        "clips": [
                            {
                                "asset": {
                                    "type": "audio",
                                    "src": self.soundtrack_url,
                                },
                                "start": 0,
                                "length": length,
                            }
                        ]
                    },
                ]
            },
            "output": {"format": "mp4", "resolution": self.resolution},
        }

        base = _base_url()
        with httpx.Client(timeout=60) as client:
            # Create render
            r = client.post(f"{base}/render", headers=self.headers, json=body)
            if r.status_code >= 400:
                log.error(
                    f"shotstack_create_failed status={r.status_code} body={r.text}"
                )
                raise RuntimeError(f"Shotstack render create failed: {r.text}")

            render = r.json()
            rid = render.get("response", {}).get("id") or render.get("id")
            if not rid:
                log.error(f"shotstack_missing_id response={render}")
                raise RuntimeError("Shotstack: render id missing")

            log.info(f"shotstack_render_started id={rid}")

            # Poll render status (up to 2 minutes)
            for attempt in range(120):
                time.sleep(1)
                g = client.get(f"{base}/render/{rid}", headers=self.headers)
                if g.status_code >= 400:
                    log.error(
                        f"shotstack_poll_failed status={g.status_code} body={g.text}"
                    )
                    raise RuntimeError(f"Shotstack render poll failed: {g.text}")

                js = g.json()
                status = js.get("response", {}).get("status") or js.get("status")

                if status in ("done", "completed"):
                    url = js.get("response", {}).get("url") or js.get("url")
                    if not url:
                        log.error(f"shotstack_missing_url response={js}")
                        raise RuntimeError("Shotstack: completed but no URL")

                    # Download final video
                    mp4_resp = client.get(url)
                    if mp4_resp.status_code >= 400:
                        log.error(
                            f"shotstack_download_failed status={mp4_resp.status_code}"
                        )
                        raise RuntimeError(
                            f"Shotstack download failed: {mp4_resp.text}"
                        )

                    # Save to data directory
                    data_dir = get_data_path()
                    tmp = tempfile.NamedTemporaryFile(
                        delete=False, suffix=".mp4", dir=str(data_dir)
                    )
                    tmp.write(mp4_resp.content)
                    tmp.flush()
                    tmp.close()

                    log.info(f"shotstack_edit_ok path={tmp.name}")
                    return tmp.name

                if status in ("failed", "errored", "cancelled"):
                    error = js.get("response", {}).get("error") or status
                    log.error(f"shotstack_render_failed id={rid} status={status}")
                    raise RuntimeError(f"Shotstack render failed: {error}")

            log.error(f"shotstack_timeout id={rid}")
            raise RuntimeError("Shotstack: render timed out after 120s")
