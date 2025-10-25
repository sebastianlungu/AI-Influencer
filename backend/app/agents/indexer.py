from __future__ import annotations

import os
import shutil
import time

from app.core.storage import append_json_line


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
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    os.makedirs("app/data/generated", exist_ok=True)
    out = f"app/data/generated/{payload['id']}.mp4"
    shutil.move(video_path, out)

    meta = {
        "id": payload["id"],
        "path": out,
        "seed": payload["seed"],
        "status": "generated",
        "ts": int(time.time()),
    }

    append_json_line("app/data/videos.json", meta)
    return meta
