"""Video prompting agent for motion generation.

Translates static image metadata into cinematic camera movement prompts for Veo 3.
Uses Grok AI to generate diverse, context-aware motion with 6s constraints.
"""

from __future__ import annotations

from app.clients.provider_selector import prompting_client
from app.core.logging import log
from app.core.motion_dedup import get_previous_prompts, store_motion_prompt


def generate_motion_prompt(
    image_meta: dict,
    video_id: str | None = None,
    regeneration_count: int = 0,
) -> str:
    """Generate cinematic motion prompt from image metadata using Grok.

    Calls Grok's suggest_motion() to produce context-aware camera movement
    that fits 6 seconds and follows strict motion rules (single subtle camera
    move + subject micro-motion, no speech/text/logos/whip pans).

    Args:
        image_meta: Diversity bank metadata from image generation
        video_id: Video identifier for per-video deduplication (optional)
        regeneration_count: Number of times video has been regenerated

    Returns:
        Cinematic motion prompt string suitable for Veo 3

    Examples:
        >>> meta = {"location": "rooftop terrace", "pose": "standing confident"}
        >>> generate_motion_prompt(meta, video_id="20251024-0001")
        "gentle pan right to left following the natural eye line with subtle lens breathing and soft focus transition"
    """
    # Load previous prompts from motion dedup store if video_id is provided
    previous_prompts = get_previous_prompts(video_id) if video_id else []

    log.info(
        f"MOTION_PROMPT_GENERATE image_location={image_meta.get('location', 'unknown')} "
        f"regen_count={regeneration_count}"
    )

    try:
        # Call Grok to generate motion specification
        grok = prompting_client()
        motion_spec = grok.suggest_motion(
            image_meta=image_meta,
            duration_s=6,  # Enforce 6s duration
        )

        # Extract full motion prompt
        motion_prompt = motion_spec.get("motion_prompt", "")

        # If this exact prompt was used before, regenerate (max 2 attempts)
        if motion_prompt in previous_prompts:
            log.warning(f"Motion prompt duplicate detected, regenerating...")
            for attempt in range(2):
                motion_spec = grok.suggest_motion(image_meta=image_meta, duration_s=6)
                motion_prompt = motion_spec.get("motion_prompt", "")
                if motion_prompt not in previous_prompts:
                    break

        log.info(
            f"MOTION_PROMPT_SUCCESS type={motion_spec.get('motion_type', 'unknown')} "
            f"prompt_len={len(motion_prompt)}"
        )

        # Store motion prompt for deduplication if video_id provided
        if video_id:
            store_motion_prompt(video_id, motion_prompt)

        return motion_prompt

    except Exception as e:
        log.error(f"MOTION_PROMPT_FAILED error={str(e)}, falling back to static")
        # Fallback to static shot if Grok fails
        return "static frame with natural breathing and subtle atmospheric movement"


def generate_veo_prompt(
    image_path: str,
    image_meta: dict,
    duration_s: int = 6,  # Updated default to 6s
    video_id: str | None = None,
    regeneration_count: int = 0,
) -> dict:
    """Generate complete Veo 3 generation payload from image.

    Uses Grok AI to generate context-aware motion prompts with 6s constraints.

    Args:
        image_path: Path to source image
        image_meta: Diversity bank metadata from image generation
        duration_s: Video duration in seconds (default 6, enforced by Grok)
        video_id: Video identifier for per-video motion deduplication
        regeneration_count: Number of times video has been regenerated

    Returns:
        Dict with Veo 3 generation parameters:
            - image_path: Source image path
            - variation: Motion prompt for Veo (used as "prompt" in Veo API)
            - duration_s: Video duration (exactly 6 seconds)
            - aspect_ratio: Video aspect ratio (9:16 for vertical)
    """
    motion_prompt = generate_motion_prompt(
        image_meta=image_meta,
        video_id=video_id,
        regeneration_count=regeneration_count,
    )

    return {
        "image_path": image_path,
        "variation": motion_prompt,  # Veo API expects "variation" field
        "duration_s": 6,  # Always 6 seconds (overrides duration_s param)
        "aspect_ratio": "9:16",
    }
