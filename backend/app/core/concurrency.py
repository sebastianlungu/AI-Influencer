"""Concurrency limiting for external API clients.

Enforces max concurrent requests per service using threading semaphores.
Limits are internal and opaque to UI/frontend.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Generator

from app.core.logging import log

# Semaphores for each service (limits based on API rate limits and system capacity)
_grok_semaphore = threading.Semaphore(3)  # Max 3 concurrent Grok requests
_veo_semaphore = threading.Semaphore(1)  # Max 1 concurrent Veo request (long-running)
_suno_semaphore = threading.Semaphore(2)  # Max 2 concurrent Suno requests
_leonardo_semaphore = threading.Semaphore(2)  # Max 2 concurrent Leonardo requests


@contextmanager
def grok_slot() -> Generator[None, None, None]:
    """Acquire a Grok API slot, blocking if at capacity.

    Usage:
        with grok_slot():
            # Make Grok API call
            response = grok_client.generate(...)
    """
    log.debug("CONCURRENCY: Waiting for Grok slot...")
    _grok_semaphore.acquire()
    try:
        log.debug("CONCURRENCY: Grok slot acquired")
        yield
    finally:
        _grok_semaphore.release()
        log.debug("CONCURRENCY: Grok slot released")


@contextmanager
def veo_slot() -> Generator[None, None, None]:
    """Acquire a Veo API slot, blocking if at capacity.

    Usage:
        with veo_slot():
            # Make Veo API call
            video_path = veo_client.img2vid(...)
    """
    log.debug("CONCURRENCY: Waiting for Veo slot...")
    _veo_semaphore.acquire()
    try:
        log.debug("CONCURRENCY: Veo slot acquired")
        yield
    finally:
        _veo_semaphore.release()
        log.debug("CONCURRENCY: Veo slot released")


@contextmanager
def suno_slot() -> Generator[None, None, None]:
    """Acquire a Suno API slot, blocking if at capacity.

    Usage:
        with suno_slot():
            # Make Suno API call
            audio_path = suno_client.generate_clip(...)
    """
    log.debug("CONCURRENCY: Waiting for Suno slot...")
    _suno_semaphore.acquire()
    try:
        log.debug("CONCURRENCY: Suno slot acquired")
        yield
    finally:
        _suno_semaphore.release()
        log.debug("CONCURRENCY: Suno slot released")


@contextmanager
def leonardo_slot() -> Generator[None, None, None]:
    """Acquire a Leonardo API slot, blocking if at capacity.

    Usage:
        with leonardo_slot():
            # Make Leonardo API call
            image_path = leonardo_client.generate(...)
    """
    log.debug("CONCURRENCY: Waiting for Leonardo slot...")
    _leonardo_semaphore.acquire()
    try:
        log.debug("CONCURRENCY: Leonardo slot acquired")
        yield
    finally:
        _leonardo_semaphore.release()
        log.debug("CONCURRENCY: Leonardo slot released")


def get_concurrency_stats() -> dict[str, dict[str, int]]:
    """Get current concurrency usage stats for all services.

    Returns:
        Dict with format:
        {
            "grok": {"limit": 3, "available": 2, "in_use": 1},
            "veo": {"limit": 1, "available": 0, "in_use": 1},
            "suno": {"limit": 2, "available": 2, "in_use": 0},
            "leonardo": {"limit": 2, "available": 1, "in_use": 1},
        }
    """
    return {
        "grok": {
            "limit": 3,
            "available": _grok_semaphore._value,
            "in_use": 3 - _grok_semaphore._value,
        },
        "veo": {
            "limit": 1,
            "available": _veo_semaphore._value,
            "in_use": 1 - _veo_semaphore._value,
        },
        "suno": {
            "limit": 2,
            "available": _suno_semaphore._value,
            "in_use": 2 - _suno_semaphore._value,
        },
        "leonardo": {
            "limit": 2,
            "available": _leonardo_semaphore._value,
            "in_use": 2 - _leonardo_semaphore._value,
        },
    }
