from __future__ import annotations

import json
import random

from app.core.ids import deterministic_id
from app.core.paths import get_data_path


def propose(n: int) -> list[dict]:
    """Proposes N variation payloads from prompt_config.json.

    Args:
        n: Number of variations to generate

    Returns:
        List of variation dictionaries with deterministic IDs

    Raises:
        FileNotFoundError: If prompt_config.json is missing
    """
    config_path = get_data_path("prompt_config.json")
    if not config_path.exists():
        raise FileNotFoundError(
            f"{config_path} not found. Create it with base_prompt and negative_prompt."
        )

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    base = cfg.get("base_prompt", "")
    negatives = cfg.get("negative_prompt", "")

    if not base:
        raise ValueError("base_prompt is empty in prompt_config.json")

    seeds = [random.randint(1, 2**31 - 1) for _ in range(n)]
    out = []

    for s in seeds:
        payload = {"base": base, "neg": negatives, "seed": s}
        payload["id"] = deterministic_id(payload)
        out.append(payload)

    return out
