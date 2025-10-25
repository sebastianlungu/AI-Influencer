from __future__ import annotations

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
    # Check provider key availability (NOT the values!)
    providers = {
        "leonardo": "configured" if settings.leonardo_api_key else "key_missing",
        "pika": "configured" if settings.pika_api_key else "key_missing",
        "shotstack": "configured" if settings.shotstack_api_key else "key_missing",
        "tiktok": "configured"
        if (settings.tiktok_client_key and settings.tiktok_client_secret)
        else "key_missing",
    }

    return {
        "ok": True,
        "allow_live": settings.allow_live,
        "scheduler_enabled": settings.enable_scheduler,
        "batch_size": settings.batch_size,
        "max_parallel": settings.max_parallel,
        "providers": providers,
    }
