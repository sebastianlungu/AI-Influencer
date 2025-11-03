"""Image indexer agent for rating workflow.

Indexes generated images to images.json with pending_review status.
Images are then reviewed by user and rated (dislike/like/superlike).
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone

from app.core.storage import append_json_line, safe_join


def index(image_path: str, payload: dict) -> dict:
    """Indexes a generated image to images.json for review.

    Moves image to app/data/generated/images/ and adds metadata entry.

    Args:
        image_path: Path to generated PNG/JPG image
        payload: Variation dict with id, base, neg, seed, variation, meta

    Returns:
        Metadata dict that was written to images.json

    Raises:
        FileNotFoundError: If image_path doesn't exist
        ValueError: If payload is missing required fields
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Validate required payload fields
    required_fields = ["id", "base", "neg", "seed", "variation", "meta"]
    for field in required_fields:
        if field not in payload:
            raise ValueError(f"Payload missing required field: {field}")

    # Move image to generated/images directory
    os.makedirs("app/data/generated/images", exist_ok=True)
    ext = os.path.splitext(image_path)[1]  # .png or .jpg
    out = safe_join("app", "data", "generated", "images", f"{payload['id']}{ext}")
    shutil.move(image_path, out)

    # Build metadata entry
    meta = {
        "id": payload["id"],
        "image_path": out,
        "status": "pending_review",
        "rating": None,
        "prompt": {
            "base": payload["base"],
            "neg": payload["neg"],
            "seed": payload["seed"],
            "variation": payload.get("variation", ""),
        },
        "meta": payload.get("meta", {}),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rated_at": None,
        "generation_params": payload.get("generation_params", {}),
    }

    # Validate schema before writing
    schema = {
        "required": ["id", "image_path", "status", "prompt", "meta", "created_at"]
    }
    append_json_line("app/data/images.json", meta, schema=schema)

    return meta
