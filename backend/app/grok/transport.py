"""HTTP transport layer for xAI Grok API.

Handles:
- Session management with httpx.Client
- Exponential backoff with jitter for retries
- Retry-After header support
- Rate limiting with monotonic token bucket
- User-Agent and auth headers
"""

from __future__ import annotations

import random
import threading
import time
from typing import Any

import httpx

from app.core.logging import log


class XAITransport:
    """HTTP transport for xAI Grok API with retries and rate limiting."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.x.ai/v1",
        timeout_connect_s: float = 10.0,
        timeout_read_s: float = 30.0,
        max_retries: int = 3,
        rps: float = 2.0,
    ):
        """
        Initialize transport layer.

        Args:
            api_key: xAI API key
            base_url: API base URL
            timeout_connect_s: Connection timeout in seconds
            timeout_read_s: Read timeout in seconds
            max_retries: Maximum retry attempts for retryable errors
            rps: Requests per second rate limit (default 2.0)
        """
        if not api_key:
            raise ValueError("API key cannot be empty")

        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.rps = rps

        # Create persistent HTTP session
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(connect=timeout_connect_s, read=timeout_read_s),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ai-influencer/1.0",
            },
        )

        # Rate limiter state (thread-safe)
        self._last_request_time = 0.0
        self._rate_lock = threading.Lock()

    def _rate_limit(self) -> None:
        """Enforce rate limiting using monotonic token bucket."""
        with self._rate_lock:
            now = time.monotonic()
            min_interval = 1.0 / self.rps
            elapsed = now - self._last_request_time

            if elapsed < min_interval:
                wait = min_interval - elapsed
                time.sleep(wait)

            self._last_request_time = time.monotonic()

    def _retry_sleep(self, attempt: int, retry_after: float | None = None) -> None:
        """Sleep with exponential backoff and jitter.

        Args:
            attempt: Current retry attempt number (0-indexed)
            retry_after: Optional Retry-After value in seconds from server
        """
        if retry_after is not None:
            # Honor server's Retry-After header
            sleep_time = retry_after
        else:
            # Exponential backoff: 0.5s, 1s, 2s with jitter
            base_delay = 0.5 * (2**attempt)
            jitter = random.uniform(0, 0.5)
            sleep_time = base_delay + jitter

        log.debug(f"TRANSPORT: Retry sleep {sleep_time:.2f}s (attempt {attempt + 1})")
        time.sleep(sleep_time)

    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        POST JSON to API endpoint with retries and rate limiting.

        Args:
            path: API path (e.g., "chat/completions")
            payload: JSON payload dict

        Returns:
            Response JSON dict

        Raises:
            RuntimeError: On non-retryable errors or max retries exceeded
            httpx.HTTPStatusError: On 4xx client errors (non-retryable)
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        last_exception: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                # Enforce rate limit
                self._rate_limit()

                # Make request
                log.debug(f"TRANSPORT: POST {path} (attempt {attempt + 1}/{self.max_retries})")
                response = self.client.post(url, json=payload)

                # Check for retryable errors
                if response.status_code in {429, 500, 502, 503, 504}:
                    # Extract Retry-After header if present
                    retry_after = None
                    if "Retry-After" in response.headers:
                        try:
                            retry_after = float(response.headers["Retry-After"])
                        except ValueError:
                            pass

                    log.warning(
                        f"TRANSPORT: Retryable error {response.status_code} on {path}"
                    )

                    if attempt < self.max_retries - 1:
                        self._retry_sleep(attempt, retry_after)
                        continue
                    else:
                        # Max retries exceeded
                        response.raise_for_status()

                # Raise on 4xx client errors (non-retryable)
                response.raise_for_status()

                # Success
                return response.json()

            except httpx.HTTPStatusError as e:
                # 4xx errors are non-retryable
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    body_preview = e.response.text[:500] if e.response.text else "(no body)"
                    log.error(
                        f"TRANSPORT: Non-retryable HTTP {e.response.status_code} on {path}: {body_preview}"
                    )
                    raise RuntimeError(
                        f"HTTP {e.response.status_code} on {path}: {body_preview}"
                    ) from e

                last_exception = e
                if attempt < self.max_retries - 1:
                    self._retry_sleep(attempt)
                    continue
                else:
                    raise RuntimeError(
                        f"Max retries exceeded for {path}: {str(e)}"
                    ) from e

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                # Network errors are retryable
                log.warning(f"TRANSPORT: Network error on {path}: {str(e)}")
                last_exception = e
                if attempt < self.max_retries - 1:
                    self._retry_sleep(attempt)
                    continue
                else:
                    raise RuntimeError(
                        f"Max retries exceeded for {path}: {str(e)}"
                    ) from e

        # Should never reach here, but just in case
        raise RuntimeError(
            f"Unexpected retry loop exit for {path}: {last_exception}"
        )

    def close(self) -> None:
        """Close the HTTP client session."""
        self.client.close()

    def __enter__(self) -> XAITransport:
        """Context manager entry."""
        return self

    def __exit__(self, *args) -> None:
        """Context manager exit."""
        self.close()
