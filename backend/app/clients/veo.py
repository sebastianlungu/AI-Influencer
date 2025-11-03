from __future__ import annotations

import base64
import json
import os
import tempfile
import time
from decimal import Decimal
from pathlib import Path

from google.cloud import aiplatform
from google.oauth2 import service_account

from app.core import concurrency, cost
from app.core.config import settings
from app.core.logging import log
from app.core.paths import get_data_path


class VeoVideoClient:
    """
    Google Veo 3 video generation client via Vertex AI.

    Generates video from image using Veo 3.0 model.
    SynthID watermark is automatically embedded and cannot be disabled.
    """

    def __init__(self) -> None:
        """Initialize Veo client with GCP credentials validation."""
        if not settings.allow_live:
            raise RuntimeError(
                "Live calls disabled (ALLOW_LIVE=false). "
                "Set ALLOW_LIVE=true in .env to enable paid API calls."
            )

        # Validate GCP project ID
        if not settings.gcp_project_id:
            raise RuntimeError(
                "GCP_PROJECT_ID is missing. "
                "Set GCP_PROJECT_ID in .env to enable Veo API calls."
            )

        # Validate GCP credentials
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not creds_path:
            raise RuntimeError(
                "GOOGLE_APPLICATION_CREDENTIALS is missing. "
                "Set GOOGLE_APPLICATION_CREDENTIALS to path of your GCP service account JSON."
            )

        if not os.path.exists(creds_path):
            raise RuntimeError(
                f"GCP service account file not found: {creds_path}. "
                "Ensure GOOGLE_APPLICATION_CREDENTIALS points to a valid JSON file."
            )

        # Initialize Vertex AI
        try:
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            aiplatform.init(
                project=settings.gcp_project_id,
                location=settings.gcp_location,
                credentials=credentials,
            )
            log.info(
                f"veo_init project={settings.gcp_project_id} "
                f"location={settings.gcp_location} model={settings.veo_model_id}"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Vertex AI: {e}") from e

        self.model_id = settings.veo_model_id
        self.aspect = settings.veo_aspect
        self.duration = settings.veo_duration_seconds
        self.num_results = settings.veo_num_results

    def img2vid(self, image_path: str, payload: dict) -> str:
        """
        Generate video from image using Veo 3.

        Args:
            image_path: Path to input PNG image
            payload: Generation context with 'id', 'seed', 'variation' keys

        Returns:
            Path to generated MP4 file

        Raises:
            RuntimeError: On API failures or timeout
        """
        vid_id = payload.get("id", "unknown")
        seed = payload.get("seed", 0)
        variation_text = payload.get("variation", "")

        log.info(
            f"veo_img2vid_start id={vid_id} seed={seed} image_path={image_path} "
            f"aspect={self.aspect} duration={self.duration}"
        )

        # Estimate cost (Veo 3 pricing: ~$0.05/second)
        estimated_cost = Decimal(str(0.05 * self.duration))
        cost.add_cost(estimated_cost, "veo")

        try:
            # Read and encode image to base64
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            # Prepare Veo 3 request
            # Veo expects a prompt describing the desired motion/animation
            # We use the variation text as the prompt
            prompt = variation_text or "Subtle motion, cinematic quality"

            # Build request payload
            request_payload = {
                "instances": [
                    {
                        "prompt": prompt,
                        "image": {
                            "bytesBase64Encoded": image_b64,
                        },
                        "parameters": {
                            "aspectRatio": self.aspect,
                            "durationSeconds": self.duration,
                            "numResults": self.num_results,
                            "seed": seed,
                        },
                    }
                ]
            }

            # Call Vertex AI Prediction API
            endpoint = aiplatform.Endpoint(
                endpoint_name=f"projects/{settings.gcp_project_id}/locations/{settings.gcp_location}/publishers/google/models/{self.model_id}"
            )

            start_time = time.time()
            # Acquire concurrency slot (max 1 concurrent Veo request)
            with concurrency.veo_slot():
                response = endpoint.predict(
                    instances=request_payload["instances"],
                    timeout=120.0,  # 2 minutes max for video generation
                )
            elapsed = time.time() - start_time

            log.info(
                f"veo_api_response id={vid_id} elapsed_s={round(elapsed, 2)} "
                f"predictions_count={len(response.predictions) if response.predictions else 0}"
            )

            # Parse response
            if not response.predictions:
                raise RuntimeError(f"Veo returned no predictions for {vid_id}")

            prediction = response.predictions[0]
            if not prediction.get("video"):
                raise RuntimeError(f"Veo prediction missing video data for {vid_id}")

            # Decode video from base64
            video_b64 = prediction["video"].get("bytesBase64Encoded")
            if not video_b64:
                raise RuntimeError(f"Veo prediction missing video bytes for {vid_id}")

            video_bytes = base64.b64decode(video_b64)

            # Write to output file with cleanup on failure
            output_dir = get_data_path("generated")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{vid_id}_veo.mp4"

            try:
                with open(output_path, "wb") as f:
                    f.write(video_bytes)
            except Exception as write_error:
                # Clean up partial file if write failed
                if output_path.exists():
                    try:
                        output_path.unlink()
                        log.warning(f"Cleaned up partial file: {output_path}")
                    except Exception as cleanup_error:
                        log.error(f"Failed to clean up partial file {output_path}: {cleanup_error}")
                raise write_error

            log.info(
                f"veo_img2vid_complete id={vid_id} output_path={str(output_path)} "
                f"size_kb={len(video_bytes) // 1024} cost_usd={float(estimated_cost)}"
            )

            return str(output_path)

        except Exception as e:
            log.error(f"veo_img2vid_failed id={vid_id} error={str(e)}", exc_info=True)
            raise RuntimeError(f"Veo img2vid failed for {vid_id}: {e}") from e
