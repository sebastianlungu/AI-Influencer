"""Abstract LLM interface for prompt generation (provider-agnostic)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMClient(ABC):
    """Abstract base class for LLM prompt generation clients.

    Allows swapping between Grok, Gemini, GPT without changing application code.
    """

    @abstractmethod
    def generate_prompt_bundle(
        self,
        setting: str,
        seed_words: list[str] | None = None,
        count: int = 1,
    ) -> list[dict[str, Any]]:
        """Generate prompt bundles (image + video + social).

        Args:
            setting: High-level setting (e.g., "Japan", "Santorini")
            seed_words: Optional embellisher keywords
            count: Number of bundles to generate (1-10)

        Returns:
            List of bundle dicts with keys:
            - id: Unique bundle ID (pr_...)
            - image_prompt: Image generation prompt dict
            - video_prompt: Video motion prompt dict

        Raises:
            RuntimeError: On API failures or missing credentials
        """
        pass

    @abstractmethod
    def suggest_motion(
        self,
        image_meta: dict[str, Any],
        duration_s: int = 6,
    ) -> dict[str, Any]:
        """Generate cinematic motion prompt for video.

        Args:
            image_meta: Image metadata dict
            duration_s: Video duration in seconds (default 6)

        Returns:
            Motion spec dict with keys:
            - motion_type: Camera motion type (pan|zoom|tilt|...)
            - motion_prompt: Detailed motion description
            - subject_motion: Character action

        Raises:
            RuntimeError: On API failures or missing credentials
        """
        pass

    @abstractmethod
    def generate_social_meta(
        self,
        media_meta: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate social media metadata (title, tags, hashtags).

        Args:
            media_meta: Media metadata dict

        Returns:
            Social meta dict with keys:
            - title: 40-60 char engaging title
            - tags: List of plain keywords (no #)
            - hashtags: List of hashtags (with #)

        Raises:
            RuntimeError: On API failures or missing credentials
        """
        pass

    def close(self) -> None:
        """Close client resources (optional, override if needed)."""
        pass

    def __enter__(self) -> LLMClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args) -> None:
        """Context manager exit."""
        self.close()


class GrokAdapter(LLMClient):
    """Adapter wrapping GrokClient to LLMClient interface."""

    def __init__(self, grok_client):
        """Initialize with GrokClient instance.

        Args:
            grok_client: Instance of app.grok.GrokClient
        """
        self._client = grok_client

    def generate_prompt_bundle(
        self,
        setting: str,
        seed_words: list[str] | None = None,
        count: int = 1,
    ) -> list[dict[str, Any]]:
        """Generate prompt bundles via Grok."""
        return self._client.generate_prompt_bundle(
            setting=setting,
            seed_words=seed_words,
            count=count,
        )

    def suggest_motion(
        self,
        image_meta: dict[str, Any],
        duration_s: int = 6,
    ) -> dict[str, Any]:
        """Generate motion prompt via Grok."""
        return self._client.suggest_motion(
            image_meta=image_meta,
            duration_s=duration_s,
        )

    def generate_social_meta(
        self,
        media_meta: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate social metadata via Grok."""
        return self._client.generate_social_meta(media_meta)

    def close(self) -> None:
        """Close Grok client."""
        self._client.close()
