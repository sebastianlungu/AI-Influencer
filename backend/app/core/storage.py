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
    p = os.path.normpath(os.path.join(*parts))
    # Check for .. in any component after normalization
    if ".." in p.split(os.sep):
        raise ValueError(f"Path traversal blocked: {p}")
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
