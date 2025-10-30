from __future__ import annotations

from app.clients.leonardo import LeonardoClient
from app.clients.shotstack import ShotstackClient
from app.clients.veo import VeoVideoClient
from app.core.config import settings


def _guard(name: str, key: str | None) -> None:
    """Validates that live calls are enabled and API key is present.

    Args:
        name: Provider name (for error messages)
        key: API key value

    Raises:
        RuntimeError: If ALLOW_LIVE=false or key is missing
    """
    if not settings.allow_live:
        raise RuntimeError(
            "Live calls disabled (ALLOW_LIVE=false). "
            "Set ALLOW_LIVE=true in .env to enable paid API calls."
        )
    if not key:
        raise RuntimeError(
            f"{name}_API_KEY is missing. "
            f"Set {name.upper()}_API_KEY in .env to enable {name} API calls."
        )


def image_client() -> LeonardoClient:
    """Returns configured Leonardo client with guards applied."""
    _guard("LEONARDO", settings.leonardo_api_key)
    return LeonardoClient(
        api_key=settings.leonardo_api_key, model_id=settings.leonardo_model_id
    )


def video_client() -> VeoVideoClient:
    """Returns configured Veo 3 video generation client.

    Veo 3 generates video from images via Vertex AI.
    SynthID watermark is automatically embedded.
    """
    return VeoVideoClient()


def edit_client() -> ShotstackClient:
    """Returns configured Shotstack client with guards applied."""
    _guard("SHOTSTACK", settings.shotstack_api_key)
    return ShotstackClient(
        api_key=settings.shotstack_api_key,
        soundtrack_url=settings.soundtrack_url,
        resolution=settings.output_resolution,
    )
