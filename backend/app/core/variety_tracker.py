"""Variety tracking for posted content locations."""

from __future__ import annotations

import json
import re  # Keep this import even though regex was replaced with string operations
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

LOCK = Lock()


def extract_location_from_prompt(prompt: str) -> str | None:
    """
    Extract location from prompt text.

    Pattern: "captured in [shot] at [LOCATION]"
    Returns the location text (everything after "at " until end or major punctuation).

    Example:
        Input: "captured in medium shot at a luxury Tokyo penthouse rooftop..."
        Output: "a luxury Tokyo penthouse rooftop"
    """
    # Find "captured in" pattern (case insensitive)
    prompt_lower = prompt.lower()
    captured_idx = prompt_lower.find("captured in")
    if captured_idx == -1:
        return None

    # Find " at " after "captured in"
    at_idx = prompt_lower.find(" at ", captured_idx)
    if at_idx == -1:
        return None

    # Extract everything after " at "
    location_start = at_idx + 4  # len(" at ") = 4
    location = prompt[location_start:]

    # Truncate at first major punctuation (., !, ?)
    for punct in ['.', '!', '?']:
        punct_idx = location.find(punct)
        if punct_idx != -1:
            location = location[:punct_idx]
            break

    location = location.strip()

    # Truncate at first comma or semicolon for cleaner storage
    for sep in [',', ';']:
        sep_idx = location.find(sep)
        if sep_idx != -1:
            location = location[:sep_idx]
            break

    return location.strip() if location else None


def load_recent_locations(file_path: str) -> list[str]:
    """Load recent posted locations from tracking file."""
    path = Path(file_path)
    if not path.exists():
        return []

    with LOCK:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("recent_locations", [])
        except (json.JSONDecodeError, OSError):
            return []


def save_location(file_path: str, location: str) -> None:
    """
    Append location to recent posted locations with rolling window.

    Args:
        file_path: Path to recent_posted_combinations.json
        location: Location string extracted from prompt
    """
    path = Path(file_path)

    with LOCK:
        # Load existing data
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                data = {"recent_locations": [], "max_size": 20}
        else:
            data = {"recent_locations": [], "max_size": 20}

        recent = data.get("recent_locations", [])
        max_size = data.get("max_size", 20)

        # Create entry with timestamp
        entry = {
            "location": location,
            "posted_at": datetime.utcnow().isoformat() + "Z"
        }

        # Append and enforce rolling window
        recent.append(entry)
        if len(recent) > max_size:
            recent = recent[-max_size:]

        data["recent_locations"] = recent

        # Atomic write: temp file → rename
        temp_path = path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_path.replace(path)
        except OSError:
            if temp_path.exists():
                temp_path.unlink()
            raise


def get_recent_location_strings(file_path: str, limit: int = 20) -> list[str]:
    """
    Get list of recent location strings for Grok prompt.

    Returns only the location text, not the full entries.
    Used to tell Grok which locations to avoid.
    """
    path = Path(file_path)
    if not path.exists():
        return []

    with LOCK:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                recent = data.get("recent_locations", [])
                # Return last N location strings only
                return [entry["location"] for entry in recent[-limit:]]
        except (json.JSONDecodeError, OSError, KeyError):
            return []
