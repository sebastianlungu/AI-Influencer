from __future__ import annotations

from app.clients.grok import GrokClient
from app.clients.leonardo import LeonardoClient
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


def prompting_client() -> GrokClient:
    """Returns configured Grok client with guards applied.

    Grok generates diverse, creative image prompts for Eva Joy fitness content.
    """
    _guard("GROK", settings.grok_api_key)
    return GrokClient(
        api_key=settings.grok_api_key,
        model=settings.grok_model,
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
