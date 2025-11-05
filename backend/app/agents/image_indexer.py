"""Image indexer agent for rating workflow.

Indexes generated shots with dual exports (9:16 + 4:5) to images.json.
Images are then reviewed by user and rated (dislike/like/superlike).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from app.core.storage import append_json_line


def index(shot_meta, payload: dict) -> dict:
    """Indexes a generated shot with dual exports to images.json for review.

    Mobile-first indexing: stores both 9:16 video source and 4:5 feed export paths.

    Args:
        shot_meta: ShotMeta object from shot_processor with export paths
        payload: Variation dict with id, base, neg, seed, variation, meta

    Returns:
        Metadata dict that was written to images.json

    Raises:
        ValueError: If payload is missing required fields
    """
    # Validate required payload fields
    required_fields = ["id", "base", "neg", "seed", "variation", "meta"]
    for field in required_fields:
        if field not in payload:
            raise ValueError(f"Payload missing required field: {field}")

    # Build metadata entry with dual exports
    meta = {
        "id": payload["id"],
        "shot_id": shot_meta.shot_id,
        "status": "pending_review",
        "rating": None,
        "preferred_export": None,  # Set by rating: "4x5" for like, "9x16" for superlike
        "exports": {
            "master_9x16": shot_meta.master_9x16_path,
            "video_9x16_1080x1920": shot_meta.video_9x16_path,
            "feed_4x5_1080x1350": shot_meta.feed_4x5_path,
        },
        "composition": {
            "warning": shot_meta.composition_warning,
            "reason": shot_meta.composition_reason,
        },
        "prompt": {
            "base": payload["base"],
            "neg": payload["neg"],
            "seed": payload["seed"],
            "variation": payload.get("variation", ""),
        },
        "meta": payload.get("meta", {}),
        "created_at": shot_meta.created_at,
        "rated_at": None,
        "generation_params": payload.get("generation_params", {}),
    }

    # Validate schema before writing
    schema = {
        "required": [
            "id",
            "shot_id",
            "status",
            "exports",
            "composition",
            "prompt",
            "meta",
            "created_at",
        ]
    }
    append_json_line("app/data/images.json", meta, schema=schema)

    return meta
