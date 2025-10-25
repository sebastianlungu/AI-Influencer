from __future__ import annotations

from app.clients.provider_selector import video_client


def from_image(image: str, payload: dict) -> str:
    """Converts an image to video.

    Args:
        image: Path to input PNG
        payload: Variation dict with duration params

    Returns:
        Path to generated MP4 file

    Raises:
        RuntimeError: If ALLOW_LIVE=false or API key missing
        NotImplementedError: When Pika API is not yet wired
    """
    return video_client().img2vid(image, payload)
