from __future__ import annotations

from app.clients.provider_selector import image_client


def generate(payload: dict) -> str:
    """Generates an image from a variation payload.

    Args:
        payload: Variation dict with prompt, seed, etc.

    Returns:
        Path to generated PNG file

    Raises:
        RuntimeError: If ALLOW_LIVE=false or API key missing
        NotImplementedError: When Leonardo API is not yet wired
    """
    return image_client().generate(payload)
