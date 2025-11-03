from __future__ import annotations

import json
import os
import threading
from typing import Any

LOCK = threading.Lock()


def safe_join(*parts: str) -> str:
    """Joins path components and validates against path traversal attacks.

    Args:
        *parts: Path components to join

    Returns:
        Normalized safe path

    Raises:
        ValueError: If path contains traversal attempts (..)
    """
    # Check for .. in any component BEFORE normalization
    # Check both forward and backward slashes for cross-platform security
    for part in parts:
        path_parts = part.replace("\\", "/").split("/")
        if ".." in path_parts:
            raise ValueError(f"Path traversal blocked: {part}")

    # Now safe to normalize
    p = os.path.normpath(os.path.join(*parts))
    return p


def _load(path: str) -> list[dict[str, Any]]:
    """Loads JSON array from file, returns empty list if file doesn't exist."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _dump(path: str, data: list[dict[str, Any]]) -> None:
    """Atomically writes JSON array to file using temp + rename."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def atomic_write(path: str, content: str) -> None:
    """Atomically writes string content to file using temp + rename.

    Args:
        path: Path to file
        content: String content to write

    Note:
        Thread-safe atomic write for any text content (JSON, logs, etc.)
        Uses temp + rename pattern to prevent corruption.
    """
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, path)


def append_json_line(
    path: str, item: dict[str, Any], schema: dict[str, Any] | None = None
) -> None:
    """Thread-safe append of a single item to JSON array file.

    Args:
        path: Path to JSON file
        item: Dictionary to append
        schema: Optional validation schema with "required" keys list

    Raises:
        ValueError: If item is missing required schema fields
    """
    # Validate schema if provided
    if schema and "required" in schema:
        for key in schema["required"]:
            if key not in item:
                raise ValueError(
                    f"Schema validation failed: missing required key '{key}' in item"
                )

    with LOCK:
        data = _load(path)
        data.append(item)
        _dump(path, data)


def read_json(path: str) -> list[dict[str, Any]]:
    """Thread-safe read of JSON array file.

    Args:
        path: Path to JSON file

    Returns:
        List of dictionaries
    """
    with LOCK:
        return _load(path)


def write_json(path: str, data: list[dict[str, Any]]) -> None:
    """Thread-safe atomic write of JSON array file.

    Args:
        path: Path to JSON file
        data: List of dictionaries to write
    """
    with LOCK:
        _dump(path, data)


def find_json_item(path: str, item_id: str) -> dict[str, Any] | None:
    """Thread-safe search for item by ID in JSON array file.

    Args:
        path: Path to JSON file
        item_id: ID to search for

    Returns:
        Dictionary if found, None otherwise
    """
    with LOCK:
        data = _load(path)
        for item in data:
            if item.get("id") == item_id:
                return item
        return None


def update_json_item(
    path: str, item_id: str, updates: dict[str, Any]
) -> dict[str, Any]:
    """Thread-safe update of a single item by ID in JSON array file.

    Args:
        path: Path to JSON file
        item_id: ID of item to update
        updates: Dictionary of fields to update

    Returns:
        Updated item dictionary

    Raises:
        ValueError: If item with given ID not found
    """
    with LOCK:
        data = _load(path)
        for i, item in enumerate(data):
            if item.get("id") == item_id:
                # Merge updates into existing item
                data[i] = {**item, **updates}
                _dump(path, data)
                return data[i]
        raise ValueError(f"Item with id '{item_id}' not found in {path}")
