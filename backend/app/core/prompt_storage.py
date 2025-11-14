"""
Prompt bundle storage with rolling window (keep last 100).

Uses JSONL format (one JSON object per line) for efficient appending.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

LOCK = threading.Lock()
MAX_PROMPTS = 100  # Rolling window size


def ensure_prompts_dir(prompts_dir: str) -> None:
    """Ensure prompts output directory exists."""
    Path(prompts_dir).mkdir(parents=True, exist_ok=True)


def get_prompts_file(prompts_dir: str) -> str:
    """Get path to prompts.jsonl file."""
    ensure_prompts_dir(prompts_dir)
    return os.path.join(prompts_dir, "prompts.jsonl")


def _load_jsonl(path: str) -> list[dict[str, Any]]:
    """Load all entries from JSONL file."""
    if not os.path.exists(path):
        return []

    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue
    return entries


def _dump_jsonl(path: str, entries: list[dict[str, Any]]) -> None:
    """Atomically write entries to JSONL file using temp + rename."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def append_prompt_bundle(
    prompts_dir: str,
    bundle: dict[str, Any],
    setting: str,
    seed_words: list[str] | None = None,
) -> None:
    """
    Append prompt bundle to prompts.jsonl with rolling window.

    Args:
        prompts_dir: Directory for prompts output
        bundle: Prompt bundle dict (id, image_prompt, video_prompt)
        setting: High-level setting used
        seed_words: Optional seed words used

    Note:
        Keeps only last MAX_PROMPTS entries (rolling window).
    """
    path = get_prompts_file(prompts_dir)

    # Create enriched entry with timestamp and metadata
    entry = {
        "id": bundle["id"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "setting": setting,
        "seed_words": seed_words or [],
        "image_prompt": bundle["image_prompt"],
        "video_prompt": bundle["video_prompt"],
        "social_meta": bundle.get("social_meta", {}),
    }

    with LOCK:
        entries = _load_jsonl(path)
        entries.append(entry)

        # Enforce rolling window: keep last MAX_PROMPTS only
        if len(entries) > MAX_PROMPTS:
            entries = entries[-MAX_PROMPTS:]

        _dump_jsonl(path, entries)


def read_recent_prompts(prompts_dir: str, limit: int = 20) -> list[dict[str, Any]]:
    """
    Read recent prompt bundles (newest first).

    Args:
        prompts_dir: Directory for prompts output
        limit: Max number of bundles to return

    Returns:
        List of prompt bundle dicts (newest first)
    """
    path = get_prompts_file(prompts_dir)

    with LOCK:
        entries = _load_jsonl(path)
        # Reverse to get newest first
        return list(reversed(entries[-limit:]))


def find_prompt_bundle(prompts_dir: str, bundle_id: str) -> dict[str, Any] | None:
    """
    Find prompt bundle by ID.

    Args:
        prompts_dir: Directory for prompts output
        bundle_id: Prompt bundle ID (pr_...)

    Returns:
        Prompt bundle dict if found, None otherwise
    """
    path = get_prompts_file(prompts_dir)

    with LOCK:
        entries = _load_jsonl(path)
        for entry in entries:
            if entry.get("id") == bundle_id:
                return entry
        return None


# ============================================================================
# Prompt State Management (Used/Unused Tracking)
# ============================================================================

def get_states_file(prompts_dir: str) -> str:
    """Get path to prompt_states.json file."""
    ensure_prompts_dir(prompts_dir)
    return os.path.join(prompts_dir, "prompt_states.json")


def load_prompt_states(prompts_dir: str) -> dict[str, dict[str, Any]]:
    """Load all prompt states from JSON file.

    Args:
        prompts_dir: Directory for prompts output

    Returns:
        Dict mapping bundle_id -> {used: bool, updated_at: ISO8601}
    """
    states_file = get_states_file(prompts_dir)

    if not os.path.exists(states_file):
        return {}

    try:
        with open(states_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Corrupted file - return empty dict
        return {}


def save_prompt_states(prompts_dir: str, states: dict[str, dict[str, Any]]) -> None:
    """Save prompt states to JSON file (atomic write).

    Args:
        prompts_dir: Directory for prompts output
        states: States dict to save
    """
    states_file = get_states_file(prompts_dir)
    tmp_file = states_file + ".tmp"

    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(states, f, indent=2, ensure_ascii=False)

    os.replace(tmp_file, states_file)


def update_prompt_state(prompts_dir: str, bundle_id: str, used: bool) -> None:
    """Update used state for a prompt bundle.

    Args:
        prompts_dir: Directory for prompts output
        bundle_id: Prompt bundle ID (pr_...)
        used: Whether prompt has been used

    Note:
        Thread-safe with file locking
    """
    with LOCK:
        states = load_prompt_states(prompts_dir)

        states[bundle_id] = {
            "used": used,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

        save_prompt_states(prompts_dir, states)


def get_prompt_state(prompts_dir: str, bundle_id: str) -> dict[str, Any] | None:
    """Get state for a specific prompt bundle.

    Args:
        prompts_dir: Directory for prompts output
        bundle_id: Prompt bundle ID (pr_...)

    Returns:
        State dict {used: bool, updated_at: str} or None if not tracked
    """
    states = load_prompt_states(prompts_dir)
    return states.get(bundle_id)
