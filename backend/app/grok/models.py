"""Pydantic models for Grok API responses.

Validates LLM output structure before returning to callers.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class Variation(BaseModel):
    """Single prompt variation for image generation."""

    base: str = Field(..., min_length=40, description="Full image prompt")
    neg: str = Field(default="", description="Negative prompt")
    variation: str = Field(..., max_length=80, description="Human-readable variation description")
    meta: dict[str, Any] = Field(default_factory=dict, description="Structured metadata")

    @field_validator("base")
    @classmethod
    def validate_base_length(cls, v: str) -> str:
        """Ensure base prompt is reasonable length (advisory, not enforced)."""
        # No hard limit - allow longer prompts for manual curation
        return v


class ImagePrompt(BaseModel):
    """Image generation prompt with dimensions."""

    final_prompt: str = Field(..., min_length=200, max_length=4096, description="Complete image prompt (advisory max: 1500 for Leonardo)")
    negative_prompt: str = Field(default="", description="Negative prompt for quality")
    width: int = Field(default=864, description="Image width in pixels")
    height: int = Field(default=1536, description="Image height in pixels")

    @field_validator("width", "height")
    @classmethod
    def validate_dimensions(cls, v: int) -> int:
        """Ensure dimensions are positive."""
        if v <= 0:
            raise ValueError(f"Dimension must be positive, got {v}")
        return v


class VideoPrompt(BaseModel):
    """Video generation prompt with single motion line."""

    line: str = Field(..., min_length=110, max_length=160, description="Single motion line (handheld only, no environment)")

    @field_validator("line")
    @classmethod
    def validate_line(cls, v: str) -> str:
        """Validate motion line format."""
        if not v.startswith("natural, realistic — "):
            raise ValueError("Motion line must start with 'natural, realistic — '")
        if "handheld" not in v.lower():
            raise ValueError("Motion line must contain 'handheld'")
        if not v.endswith("."):
            raise ValueError("Motion line must end with a period")
        return v


class PromptBundle(BaseModel):
    """Complete prompt bundle with image and video prompts."""

    id: str = Field(..., min_length=1, description="Unique bundle ID")
    image_prompt: ImagePrompt = Field(..., description="Image generation prompt")
    video_prompt: VideoPrompt = Field(..., description="Video generation prompt")


class MotionSpec(BaseModel):
    """Motion specification for video generation."""

    motion_type: str = Field(
        ...,
        description="Type of camera motion (pan, zoom, tilt, dolly, static, tracking, crane)"
    )
    motion_prompt: str = Field(..., min_length=20, description="Detailed motion description")
    subject_motion: str = Field(..., min_length=10, description="Subject/character motion")

    @field_validator("motion_type")
    @classmethod
    def validate_motion_type(cls, v: str) -> str:
        """Ensure motion type is valid."""
        valid_types = {"pan", "zoom", "tilt", "dolly", "static", "tracking", "crane"}
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid motion type: {v}. Must be one of {valid_types}")
        return v.lower()


class SocialMeta(BaseModel):
    """Social media metadata for a prompt bundle."""

    title: str = Field(..., min_length=10, max_length=100, description="Engaging title (40-60 chars)")
    caption: str | None = Field(None, min_length=40, max_length=200, description="Motivational caption with 1 emoji (40-120 chars)")
    tags: list[str] = Field(default_factory=list, description="Plain keywords (no #)")
    hashtags: list[str] = Field(default_factory=list, description="Hashtags (with #)")


class MusicBrief(BaseModel):
    """Music generation brief for Suno."""

    style: str = Field(..., min_length=3, description="Music style/genre")
    mood: str = Field(..., min_length=3, description="Mood/emotion")
    tempo: str = Field(..., min_length=3, description="Tempo (slow, medium, fast, etc.)")
    instruments: str = Field(..., min_length=3, description="Instrument descriptions")
    prompt: str = Field(..., min_length=20, description="Complete music generation prompt")
