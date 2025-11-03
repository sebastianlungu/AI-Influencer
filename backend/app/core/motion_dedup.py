"""Per-video motion prompt deduplication.

Tracks motion prompts used for each video to prevent repeats within the same video.
Each video gets its own JSON file in app/data/motion/<video_id>.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.logging import log

MOTION_DIR = Path(__file__).parent.parent.parent / "app" / "data" / "motion"


def get_previous_prompts(video_id: str) -> list[str]:
    """Get all previous motion prompts used for this video.

    Args:
        video_id: Video identifier (e.g., "20251024-0001")

    Returns:
        List of motion prompts previously used for this video
    """
    MOTION_DIR.mkdir(parents=True, exist_ok=True)
    motion_file = MOTION_DIR / f"{video_id}.json"

    if not motion_file.exists():
        return []

    try:
        with open(motion_file, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("tried_prompts", [])
    except (json.JSONDecodeError, OSError) as e:
        log.warning(f"Failed to load motion history for {video_id}: {e}")
        return []


def store_motion_prompt(video_id: str, motion_prompt: str) -> None:
    """Store a motion prompt for this video.

    Args:
        video_id: Video identifier
        motion_prompt: Motion prompt that was used
    """
    MOTION_DIR.mkdir(parents=True, exist_ok=True)
    motion_file = MOTION_DIR / f"{video_id}.json"

    # Load existing data
    if motion_file.exists():
        try:
            with open(motion_file, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {"video_id": video_id, "tried_prompts": []}
    else:
        data = {"video_id": video_id, "tried_prompts": []}

    # Append new prompt if not already present
    if motion_prompt not in data["tried_prompts"]:
        data["tried_prompts"].append(motion_prompt)

    # Atomic write (temp + rename)
    temp_file = motion_file.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_file.replace(motion_file)
        log.debug(f"Stored motion prompt for {video_id} (total: {len(data['tried_prompts'])})")
    except OSError as e:
        log.error(f"Failed to store motion prompt for {video_id}: {e}")
        if temp_file.exists():
            temp_file.unlink()


def clear_motion_history(video_id: str) -> None:
    """Clear motion history for a video (e.g., when video is deleted).

    Args:
        video_id: Video identifier
    """
    motion_file = MOTION_DIR / f"{video_id}.json"
    if motion_file.exists():
        try:
            motion_file.unlink()
            log.debug(f"Cleared motion history for {video_id}")
        except OSError as e:
            log.warning(f"Failed to clear motion history for {video_id}: {e}")
