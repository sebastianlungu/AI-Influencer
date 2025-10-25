from __future__ import annotations

import os
import shutil
import time

from app.core.storage import append_json_line, safe_join


def index(video_path: str, payload: dict) -> dict:
    """Indexes a completed video to videos.json.

    Moves video to app/data/generated/ and adds metadata entry.

    Args:
        video_path: Path to final edited MP4
        payload: Variation dict with id, seed, etc.

    Returns:
        Metadata dict that was written to videos.json

    Raises:
        FileNotFoundError: If video_path doesn't exist
        ValueError: If payload['id'] contains path traversal attempts
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    os.makedirs("app/data/generated", exist_ok=True)
    # Use safe_join to prevent path traversal attacks
    out = safe_join("app", "data", "generated", f"{payload['id']}.mp4")
    shutil.move(video_path, out)

    meta = {
        "id": payload["id"],
        "path": out,
        "seed": payload["seed"],
        "status": "generated",
        "ts": int(time.time()),
    }

    # Validate schema before writing to videos.json
    schema = {"required": ["id", "path", "status", "ts"]}
    append_json_line("app/data/videos.json", meta, schema=schema)
    return meta
