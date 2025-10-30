from __future__ import annotations

import time
import tempfile
from decimal import Decimal

import httpx

from app.core.config import settings
from app.core.cost import add_cost
from app.core.logging import log
from app.core.paths import get_data_path

BASE_URL = "https://cloud.leonardo.ai/api/rest/v1"


class LeonardoClient:
    """Leonardo AI image generation client."""

    def __init__(self, api_key: str | None = None, model_id: str | None = None):
        self.key = api_key or settings.leonardo_api_key
        if not self.key:
            raise RuntimeError("LEONARDO_API_KEY missing")
        self.model_id = model_id or settings.leonardo_model_id
        self.headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }

    def generate(self, payload: dict) -> str:
        """Generate an image from a prompt.

        Args:
            payload: Dictionary containing 'base' (prompt) and optional 'neg' (negative prompt)

        Returns:
            Path to the generated image file

        Raises:
            RuntimeError: If generation fails or times out
        """
        # Conservative cost estimate (adjust with real metering)
        add_cost(Decimal("0.02"), "leonardo")

        prompt = payload.get("base", "")
        negative = payload.get("neg", "")

        data = {
            "prompt": prompt,
            "negative_prompt": negative,
            "num_images": 1,
        }
        if self.model_id:
            data["modelId"] = self.model_id

        with httpx.Client(timeout=60) as client:
            # Create generation
            r = client.post(f"{BASE_URL}/generations", headers=self.headers, json=data)
            if r.status_code >= 400:
                log.error(f"leonardo_create_failed status={r.status_code} body={r.text}")
                raise RuntimeError(f"Leonardo create failed: {r.text}")

            gen = r.json()
            # Different API versions return different shapes
            gen_id = (
                gen.get("sdGenerationJob", {}).get("generationId")
                or gen.get("generationId")
            )
            if not gen_id:
                log.error(f"leonardo_missing_id response={gen}")
                raise RuntimeError("Leonardo: generationId missing in response")

            log.info(f"leonardo_generation_started id={gen_id}")

            # Poll generation until assets are ready (up to 60 seconds)
            for attempt in range(60):
                time.sleep(1)
                g = client.get(f"{BASE_URL}/generations/{gen_id}", headers=self.headers)
                if g.status_code >= 400:
                    log.error(
                        f"leonardo_poll_failed status={g.status_code} body={g.text}"
                    )
                    raise RuntimeError(f"Leonardo poll failed: {g.text}")

                gj = g.json()
                # Search for assets in different response shapes
                assets = (
                    gj.get("generated_images")
                    or gj.get("generations_by_pk", {}).get("generated_images")
                    or gj.get("images")
                    or []
                )

                if assets:
                    url = assets[0].get("url") or assets[0].get("image_url")
                    if not url:
                        log.error(f"leonardo_missing_url asset={assets[0]}")
                        raise RuntimeError("Leonardo: asset URL missing")

                    # Download image
                    img_resp = client.get(url)
                    if img_resp.status_code >= 400:
                        log.error(
                            f"leonardo_download_failed status={img_resp.status_code}"
                        )
                        raise RuntimeError(
                            f"Leonardo image download failed: {img_resp.text}"
                        )

                    # Save to data directory
                    data_dir = get_data_path()
                    tmp = tempfile.NamedTemporaryFile(
                        delete=False, suffix=".png", dir=str(data_dir)
                    )
                    tmp.write(img_resp.content)
                    tmp.flush()
                    tmp.close()

                    log.info(f"leonardo_image_ok path={tmp.name}")
                    return tmp.name

            log.error(f"leonardo_timeout id={gen_id}")
            raise RuntimeError("Leonardo: generation timed out after 60s")
