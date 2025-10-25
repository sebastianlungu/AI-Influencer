from __future__ import annotations

import hashlib
import json


def deterministic_id(payload: dict) -> str:
    """Generates a deterministic 16-char hash from a payload dict.

    Args:
        payload: Dictionary containing prompt, seed, and other params

    Returns:
        16-character hex hash
    """
    s = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]
