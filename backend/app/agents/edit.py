from __future__ import annotations

from app.clients.provider_selector import edit_client


def polish(video: str, payload: dict) -> str:
    """Applies music and effects to video.

    IMPORTANT: NO text overlays, captions, watermarks, voice, or subtitles.
    Only music and visual effects are allowed.

    Args:
        video: Path to input MP4
        payload: Variation dict with effect params

    Returns:
        Path to edited MP4 file

    Raises:
        RuntimeError: If ALLOW_LIVE=false or API key missing
        NotImplementedError: When Shotstack API is not yet wired
    """
    return edit_client().simple_polish(video, payload)
