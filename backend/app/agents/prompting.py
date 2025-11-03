from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path

from app.clients.provider_selector import prompting_client
from app.core.ids import deterministic_id
from app.core.logging import log
from app.core.paths import get_data_path
from app.core.storage import atomic_write


def _calculate_diversity_weights(
    diversity_banks: dict[str, list[str]], diversity_usage: dict
) -> dict[str, dict[str, float]]:
    """Calculate inverse frequency weights for diversity bank items.

    Items used less frequently get higher weights to encourage variety.

    Args:
        diversity_banks: Available items in each diversity category
        diversity_usage: Usage tracking data from diversity_usage.json

    Returns:
        Dict mapping category → item → weight (0.2 to 1.0)
            - Never used: 1.0
            - Used 1-2 times: 0.7
            - Used 3+ times: 0.2
    """
    window_size = diversity_usage.get("window_size", 50)
    weights = {}

    for category, items in diversity_banks.items():
        category_usage = diversity_usage.get(category, {})
        category_weights = {}

        for item in items:
            # Get usage count in rolling window
            usage_data = category_usage.get(item, {"count": 0})
            count = usage_data.get("count", 0)

            # Calculate weight based on usage frequency
            if count == 0:
                weight = 1.0  # Never used - highest priority
            elif count <= 2:
                weight = 0.7  # Lightly used
            else:
                weight = 0.2  # Heavily used - lowest priority

            # Take first 50 chars of item as key (for readability)
            item_key = item[:50] if len(item) > 50 else item
            category_weights[item_key] = weight

        weights[category] = category_weights

    return weights


def _build_preference_hints(weights: dict[str, dict[str, float]]) -> str:
    """Build preference hints for Grok system prompt.

    Suggests underused items to encourage diversity.

    Args:
        weights: Category → item → weight mapping

    Returns:
        Human-readable preference hint string
    """
    hints = []

    for category, item_weights in weights.items():
        # Find top 3 underused items (highest weights)
        sorted_items = sorted(
            item_weights.items(), key=lambda x: x[1], reverse=True
        )[:3]

        # Only add hint if there are underused items
        if sorted_items and sorted_items[0][1] >= 0.7:
            underused = [item for item, weight in sorted_items if weight >= 0.7]
            if underused:
                hints.append(
                    f"**{category.upper()}**: Prefer underused options like: {', '.join(underused[:2])}"
                )

    if not hints:
        return ""

    return (
        "\n\n**DIVERSITY PREFERENCES** (to avoid repetition):\n"
        + "\n".join(hints)
        + "\n"
    )


def _update_diversity_usage(
    diversity_usage_path: Path, variations: list[dict], window_size: int = 50
) -> None:
    """Update diversity usage tracking after generation.

    Increments usage counts for items used in variations.
    Maintains rolling window by removing oldest entries when window_size exceeded.

    Args:
        diversity_usage_path: Path to diversity_usage.json
        variations: List of variation dicts with meta field
        window_size: Rolling window size for tracking (default 50)
    """
    # Load current usage
    if diversity_usage_path.exists():
        with open(diversity_usage_path, "r", encoding="utf-8") as f:
            usage = json.load(f)
    else:
        usage = {
            "locations": {},
            "poses": {},
            "outfits": {},
            "accessories": {},
            "lighting": {},
            "camera": {},
            "props": {},
            "creative_twists": {},
            "window_size": window_size,
            "last_updated_at": None,
        }

    # Update counts for each variation
    for var in variations:
        meta = var.get("meta", {})
        timestamp = datetime.now(timezone.utc).isoformat()

        for category, value in meta.items():
            if not value:
                continue

            category_key = category if category in usage else f"{category}s"
            if category_key not in usage:
                usage[category_key] = {}

            # Initialize or update item
            if value not in usage[category_key]:
                usage[category_key][value] = {"count": 0, "last_used_at": timestamp}

            usage[category_key][value]["count"] += 1
            usage[category_key][value]["last_used_at"] = timestamp

    # Trim counts exceeding window size
    # (Reset counts that are too old based on total usage across all categories)
    total_usage = sum(
        sum(item["count"] for item in cat_data.values())
        for cat_data in usage.values()
        if isinstance(cat_data, dict)
    )

    if total_usage > window_size:
        # Reset all counts proportionally to maintain rolling window
        for category, cat_data in usage.items():
            if isinstance(cat_data, dict):
                for item, item_data in cat_data.items():
                    # Decay old counts
                    cat_data[item]["count"] = max(0, item_data["count"] - 1)

    usage["last_updated_at"] = datetime.now(timezone.utc).isoformat()

    # Write atomically
    atomic_write(diversity_usage_path, json.dumps(usage, indent=2))
    log.info(f"Updated diversity usage tracking")


def propose(n: int) -> list[dict]:
    """Proposes N diverse variation payloads using Grok API.

    Uses Grok to generate creative, varied fitness content prompts for Eva Joy.
    Variations are deduplicated against history.json to prevent repeats.

    Args:
        n: Number of unique variations to generate

    Returns:
        List of variation dictionaries with:
            - base: Full image prompt
            - neg: Negative prompt
            - variation: Human-readable description
            - meta: Structured metadata (location, pose, outfit, etc.)
            - seed: Random seed for reproducibility
            - id: Deterministic content hash

    Raises:
        FileNotFoundError: If prompt_config.json is missing
        ValueError: If required config fields are missing
        RuntimeError: If Grok API fails or returns invalid data
    """
    # Load configuration
    config_path = get_data_path("prompt_config.json")
    if not config_path.exists():
        raise FileNotFoundError(
            f"{config_path} not found. Create it with character_profile and diversity_banks."
        )

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Validate required fields
    if "character_profile" not in cfg:
        raise ValueError("character_profile missing in prompt_config.json")
    if "diversity_banks" not in cfg:
        raise ValueError("diversity_banks missing in prompt_config.json")
    if "negative_prompt" not in cfg:
        raise ValueError("negative_prompt missing in prompt_config.json")

    character_profile = cfg["character_profile"]
    diversity_banks = cfg["diversity_banks"]
    negative_prompt = cfg["negative_prompt"]

    # Load history for deduplication
    history_path = get_data_path("history.json")
    if history_path.exists():
        with open(history_path, "r", encoding="utf-8") as f:
            history_data = json.load(f)
            if isinstance(history_data, dict):
                history_hashes = set(history_data.get("hashes", []))
                max_size = history_data.get("max_size", 5000)
            else:
                # Legacy format: just array
                history_hashes = set(history_data) if isinstance(history_data, list) else set()
                max_size = 5000
    else:
        history_hashes = set()
        max_size = 5000

    log.info(f"Loaded {len(history_hashes)} hashes from history")

    # Load diversity usage for weighted sampling
    diversity_usage_path = get_data_path("diversity_usage.json")
    if diversity_usage_path.exists():
        with open(diversity_usage_path, "r", encoding="utf-8") as f:
            diversity_usage = json.load(f)
    else:
        diversity_usage = {}

    # Calculate weights and build preference hints
    weights = _calculate_diversity_weights(diversity_banks, diversity_usage)
    preference_hints = _build_preference_hints(weights)

    # Count preference hints (can't use backslash in f-string expression)
    hint_count = len([h for h in preference_hints.split('\n') if h.strip()])
    log.info(f"Diversity sampling enabled: {hint_count} preference hints")

    # Generate variations using Grok
    # Request more than needed to account for potential duplicates
    request_count = min(n + 5, n * 2)  # Request extra, cap at 2x
    log.info(f"Requesting {request_count} variations from Grok (target: {n} unique)")

    grok = prompting_client()
    raw_variations = grok.generate_variations(
        character_profile=character_profile,
        diversity_banks=diversity_banks,
        n=request_count,
        negative_prompt=negative_prompt,
        preference_hints=preference_hints,  # Guide Grok toward underused items
    )

    # Process variations: add seeds, generate IDs, deduplicate
    unique_variations = []
    new_hashes = []

    for raw_var in raw_variations:
        # Add random seed for reproducibility
        seed = random.randint(1, 2**31 - 1)
        raw_var["seed"] = seed

        # Generate deterministic ID based on content
        var_id = deterministic_id({
            "base": raw_var["base"],
            "neg": raw_var["neg"],
            "seed": seed,
        })
        raw_var["id"] = var_id

        # Check if duplicate
        if var_id in history_hashes:
            log.debug(f"Skipping duplicate variation: {var_id}")
            continue

        # Add to unique list
        unique_variations.append(raw_var)
        new_hashes.append(var_id)

        # Stop if we have enough unique variations
        if len(unique_variations) >= n:
            break

    log.info(
        f"Generated {len(unique_variations)} unique variations "
        f"({len(raw_variations) - len(unique_variations)} duplicates filtered)"
    )

    # Update history
    if new_hashes:
        _update_history(history_path, history_hashes, new_hashes, max_size)

    # Update diversity usage tracking
    if unique_variations:
        _update_diversity_usage(diversity_usage_path, unique_variations, window_size=50)

    # Warn if we couldn't generate enough unique variations
    if len(unique_variations) < n:
        log.warning(
            f"Only generated {len(unique_variations)} unique variations (requested {n}). "
            f"Try increasing diversity or clearing history."
        )

    return unique_variations


def _update_history(
    history_path: Path,
    existing_hashes: set[str],
    new_hashes: list[str],
    max_size: int,
) -> None:
    """
    Update history.json with new hashes, maintaining rolling window.

    Args:
        history_path: Path to history.json
        existing_hashes: Set of existing hashes
        new_hashes: List of new hashes to add
        max_size: Maximum number of hashes to keep (FIFO)
    """
    # Combine existing and new (convert set to list to maintain order)
    all_hashes = list(existing_hashes) + new_hashes

    # Trim to max_size (keep most recent)
    if len(all_hashes) > max_size:
        all_hashes = all_hashes[-max_size:]

    # Write atomically
    history_data = {
        "hashes": all_hashes,
        "max_size": max_size,
    }
    atomic_write(history_path, json.dumps(history_data, indent=2))
    log.info(f"Updated history: {len(all_hashes)} total hashes")
