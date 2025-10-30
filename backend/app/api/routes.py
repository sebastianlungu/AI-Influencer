from __future__ import annotations

import os

from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.coordinator.orchestrator import run_cycle
from app.core.config import settings

router = APIRouter()

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)


@router.post("/cycle/generate")
@limiter.limit("5/minute")
def cycle_generate(request: Request, n: int | None = None) -> dict:
    """Triggers a generation cycle.

    Rate limited to 5 requests per minute per client.

    Args:
        request: FastAPI request object (for rate limiting)
        n: Number of variations to generate (defaults to COORDINATOR_BATCH_SIZE)

    Returns:
        Dict with ok status and list of generated video metadata

    Raises:
        RuntimeError: If ALLOW_LIVE=false or API keys missing
        RuntimeError: If budget exceeded
        HTTPException: 429 if rate limit exceeded
    """
    batch_size = n if n is not None else settings.batch_size
    items = run_cycle(batch_size)
    return {"ok": True, "items": items}


@router.get("/healthz")
def healthz() -> dict:
    """Health check endpoint with provider readiness status.

    Returns:
        Dict with status and provider configuration (NO SECRETS)
    """
    # Check GCP credentials for Veo
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    creds_exists = bool(creds_path and os.path.exists(creds_path))

    veo_status = "not_configured"
    if settings.video_provider == "veo":
        if settings.gcp_project_id and creds_exists:
            veo_status = "configured"
        else:
            veo_status = "key_missing"

    # Check provider key availability (NOT the values!)
    providers = {
        "veo": veo_status,
        "leonardo": "configured" if settings.leonardo_api_key else "key_missing",
        "pika": "configured" if settings.pika_api_key else "key_missing",
        "shotstack": "configured" if settings.shotstack_api_key else "key_missing",
        "tiktok": "configured"
        if (settings.tiktok_client_key and settings.tiktok_client_secret)
        else "key_missing",
    }

    # Add Veo configuration info (no secrets)
    veo_config = {}
    if settings.video_provider == "veo":
        veo_config = {
            "gcp_project_id": settings.gcp_project_id or "not_set",
            "gcp_location": settings.gcp_location,
            "veo_model_id": settings.veo_model_id,
            "veo_aspect": settings.veo_aspect,
            "veo_duration_seconds": settings.veo_duration_seconds,
            "credentials_file_exists": creds_exists,
        }

    # Add Leonardo configuration info (no secrets)
    leonardo_config = {
        "model_id": settings.leonardo_model_id or "default",
    }

    # Add Shotstack configuration info (no secrets)
    shotstack_config = {
        "region": settings.shotstack_region,
        "resolution": settings.output_resolution,
        "soundtrack_url_configured": bool(settings.soundtrack_url),
    }

    return {
        "ok": True,
        "allow_live": settings.allow_live,
        "scheduler_enabled": settings.enable_scheduler,
        "batch_size": settings.batch_size,
        "max_parallel": settings.max_parallel,
        "video_provider": settings.video_provider,
        "providers": providers,
        "veo_config": veo_config,
        "leonardo_config": leonardo_config,
        "shotstack_config": shotstack_config,
    }
