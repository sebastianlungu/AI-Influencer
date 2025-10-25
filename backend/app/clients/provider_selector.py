from __future__ import annotations

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


class _Leonardo:
    """Leonardo.ai image generation client."""

    def __init__(self, key: str | None):
        _guard("LEONARDO", key)
        self.key = key

    def generate(self, payload: dict) -> str:
        """Generates an image from a variation payload.

        Args:
            payload: Variation dict with prompt, seed, etc.

        Returns:
            Path to generated PNG file

        Raises:
            NotImplementedError: Placeholder for actual API integration
        """
        raise NotImplementedError("Wire Leonardo API here")


class _Pika:
    """Pika Labs image-to-video client."""

    def __init__(self, key: str | None):
        _guard("PIKA", key)
        self.key = key

    def img2vid(self, image: str, payload: dict) -> str:
        """Converts an image to video.

        Args:
            image: Path to input PNG
            payload: Variation dict with duration params

        Returns:
            Path to generated MP4 file

        Raises:
            NotImplementedError: Placeholder for actual API integration
        """
        raise NotImplementedError("Wire Pika API here")


class _Shotstack:
    """Shotstack video editing client."""

    def __init__(self, key: str | None):
        _guard("SHOTSTACK", key)
        self.key = key

    def simple_polish(self, video: str, payload: dict) -> str:
        """Applies music and effects to video.

        NO text overlays, captions, watermarks, or voice.

        Args:
            video: Path to input MP4
            payload: Variation dict with effect params

        Returns:
            Path to edited MP4 file

        Raises:
            NotImplementedError: Placeholder for actual API integration
        """
        raise NotImplementedError("Wire Shotstack API here")


def image_client() -> _Leonardo:
    """Returns configured Leonardo client with guards applied."""
    return _Leonardo(settings.leonardo_api_key)


def video_client() -> _Pika:
    """Returns configured Pika client with guards applied."""
    return _Pika(settings.pika_api_key)


def edit_client() -> _Shotstack:
    """Returns configured Shotstack client with guards applied."""
    return _Shotstack(settings.shotstack_api_key)
