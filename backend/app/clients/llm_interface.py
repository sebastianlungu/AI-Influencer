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
        setting_id: str,
        location_label: str,
        location_path: str,
        seed_words: list[str] | None = None,
        count: int = 1,
        bind_scene: bool = True,
        bind_pose_microaction: bool = True,
        bind_lighting: bool = True,
        bind_camera: bool = True,
        bind_angle: bool = True,
        bind_accessories: bool = True,
        bind_wardrobe: bool = True,  # STEP 2: Wardrobe binding ON by default
        single_accessory: bool = True,
        motion_variations: int = 3,
    ) -> list[dict[str, Any]]:
        """Generate prompt bundles (image + video + social).

        Args:
            setting_id: Location ID (e.g., "japan", "us-new_york-manhattan-times_square")
            location_label: Human-readable location name (e.g., "Japan", "Times Square — Manhattan, NY")
            location_path: Full path to location JSON file
            seed_words: Optional embellisher keywords
            count: Number of bundles to generate (1-10)
            bind_scene: Bind scene from location JSON
            bind_pose_microaction: Bind pose/micro-action (VERBATIM enforcement)
            bind_lighting: Bind lighting
            bind_camera: Bind camera
            bind_angle: Bind angle
            bind_accessories: Bind accessories
            bind_wardrobe: Bind wardrobe (top+bottom); else inspire-only
            single_accessory: If True, bind exactly 1 accessory; if False, bind 2
            motion_variations: Number of motion variations to generate per bundle (1-5)

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
        setting_id: str,
        location_label: str,
        location_path: str,
        seed_words: list[str] | None = None,
        count: int = 1,
        bind_scene: bool = True,
        bind_pose_microaction: bool = True,
        bind_lighting: bool = True,
        bind_camera: bool = True,
        bind_angle: bool = True,
        bind_accessories: bool = True,
        bind_wardrobe: bool = True,  # STEP 2: Wardrobe binding ON by default
        single_accessory: bool = True,
        motion_variations: int = 3,
    ) -> list[dict[str, Any]]:
        """Generate prompt bundles via Grok."""
        return self._client.generate_prompt_bundle(
            setting_id=setting_id,
            location_label=location_label,
            location_path=location_path,
            seed_words=seed_words,
            count=count,
            bind_scene=bind_scene,
            bind_pose_microaction=bind_pose_microaction,
            bind_lighting=bind_lighting,
            bind_camera=bind_camera,
            bind_angle=bind_angle,
            bind_accessories=bind_accessories,
            bind_wardrobe=bind_wardrobe,
            single_accessory=single_accessory,
            motion_variations=motion_variations,
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
