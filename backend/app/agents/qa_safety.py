from __future__ import annotations


def ensure(video_path: str, payload: dict) -> None:
    """Validates video safety and SFW compliance.

    This is a placeholder for external safety classifiers.
    Expand with actual NSFW detection, violence checks, etc.

    Args:
        video_path: Path to MP4 file
        payload: Variation dict (for logging)

    Raises:
        ValueError: If video violates safety policies
    """
    # TODO: Integrate external safety classifier
    # For now, pass through (SFW defaults enforced in prompt_config.json)
    pass
