"""Concurrency control for Prompt Lab (minimal no-op stub).

In Prompt Lab mode, we only use Grok for prompt generation,
and throttling is not needed. This stub maintains import
compatibility without any actual rate limiting.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator


@contextmanager
def grok_slot() -> Generator[None, None, None]:
    """No-op context manager for Grok API calls.

    Prompt Lab doesn't need throttling; kept for import compatibility.

    Usage:
        with grok_slot():
            # Make Grok API call
            response = grok_client.generate(...)
    """
    yield


def status() -> dict[str, dict[str, int | None]]:
    """Return concurrency status (no-op stub).

    Kept for compatibility; not used in Prompt Lab.

    Returns:
        Minimal status dict indicating no active throttling
    """
    return {
        "grok": {
            "in_use": 0,
            "max": None,  # No limit
        }
    }
