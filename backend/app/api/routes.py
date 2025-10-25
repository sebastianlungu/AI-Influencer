from __future__ import annotations

from fastapi import APIRouter

from app.coordinator.orchestrator import run_cycle
from app.core.config import settings

router = APIRouter()


@router.post("/cycle/generate")
def cycle_generate(n: int | None = None) -> dict:
    """Triggers a generation cycle.

    Args:
        n: Number of variations to generate (defaults to COORDINATOR_BATCH_SIZE)

    Returns:
        Dict with ok status and list of generated video metadata

    Raises:
        RuntimeError: If ALLOW_LIVE=false or API keys missing
        RuntimeError: If budget exceeded
    """
    batch_size = n if n is not None else settings.batch_size
    items = run_cycle(batch_size)
    return {"ok": True, "items": items}


@router.get("/healthz")
def healthz() -> dict:
    """Health check endpoint.

    Returns:
        Dict with status and basic info
    """
    return {
        "status": "healthy",
        "allow_live": settings.allow_live,
        "scheduler_enabled": settings.enable_scheduler,
    }
