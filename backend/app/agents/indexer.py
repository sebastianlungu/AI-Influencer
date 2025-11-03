"""Video indexer agent for rating workflow.

Indexes generated videos to videos.json with pending_review status.
Videos reference their source image_id and include motion prompt metadata.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone

from app.core.storage import append_json_line, safe_join


def index(video_path: str, payload: dict, image_id: str, motion_prompt: str) -> dict:
    """Indexes a completed video to videos.json for review.

    Moves video to app/data/generated/videos/ and adds metadata entry.

    Args:
        video_path: Path to final edited MP4
        payload: Variation dict with id, seed, etc.
        image_id: Reference to source image ID in images.json
        motion_prompt: Cinematic camera movement prompt used for video generation

    Returns:
        Metadata dict that was written to videos.json

    Raises:
        FileNotFoundError: If video_path doesn't exist
        ValueError: If required fields are missing
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    if not image_id:
        raise ValueError("image_id is required")
    if not motion_prompt:
        raise ValueError("motion_prompt is required")

    # Move video to generated/videos directory
    os.makedirs("app/data/generated/videos", exist_ok=True)
    out = safe_join("app", "data", "generated", "videos", f"{payload['id']}.mp4")
    shutil.move(video_path, out)

    # Build metadata entry
    meta = {
        "id": payload["id"],
        "image_id": image_id,
        "video_path": out,
        "thumb_path": None,  # Can be generated later if needed
        "status": "pending_review",
        "rating": None,
        "video_meta": {
            "motion_prompt": motion_prompt,
            "duration_s": payload.get("duration_s", 8),
            "regeneration_count": 0,
            "previous_motion_prompts": [],
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rated_at": None,
        "posted_at": None,
        "tiktok_post_id": None,
        "generation_params": payload.get("generation_params", {}),
    }

    # Validate schema before writing
    schema = {"required": ["id", "image_id", "video_path", "status", "created_at"]}
    append_json_line("app/data/videos.json", meta, schema=schema)

    return meta
