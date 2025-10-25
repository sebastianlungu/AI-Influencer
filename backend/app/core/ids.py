from __future__ import annotations

import hashlib
import json


def deterministic_id(payload: dict) -> str:
    """Generates a deterministic 16-char hash from a payload dict.

    The hash is stable across calls with identical payloads. This ensures
    deduplication works correctly and re-running the same input produces
    the same ID.

    **Fields affecting output (must be in payload for determinism):**
    - `base`: Base prompt text
    - `neg`: Negative prompt text
    - `seed`: Random seed for generation
    - (Future: `model`, `cfg_scale`, `steps`, etc. if added)

    **Stability guarantee:** Same payload → same ID, different seed → different ID

    Args:
        payload: Dictionary containing all output-affecting parameters.
                 Currently expects: base, neg, seed.

    Returns:
        16-character hex hash (truncated SHA256)

    Example:
        >>> payload = {"base": "...", "neg": "...", "seed": 12345}
        >>> id1 = deterministic_id(payload)
        >>> id2 = deterministic_id(payload)
        >>> assert id1 == id2  # Deterministic
    """
    s = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]
