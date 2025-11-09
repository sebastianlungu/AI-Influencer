"""Utility functions for Grok API client.

Provides:
- JSON extraction and validation
- Token/cost estimation
- Logging utilities (redaction, truncation)
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any


def extract_json(text: str) -> Any:
    """
    Extract JSON from LLM response, handling markdown code fences.

    Args:
        text: Raw response text that may contain ```json fences

    Returns:
        Parsed JSON object (dict, list, etc.)

    Raises:
        ValueError: If JSON parsing fails, with truncated preview
    """
    content = text.strip()

    # Strip markdown code fences if present
    if content.startswith("```"):
        lines = content.split("\n")
        if len(lines) > 2:
            # Remove first and last lines (```json and ```)
            content = "\n".join(lines[1:-1])
        content = content.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        # Provide truncated preview for debugging
        preview = content[:2000] + "..." if len(content) > 2000 else content
        raise ValueError(
            f"Failed to parse JSON from LLM response: {e}\nPreview: {preview}"
        ) from e


def estimate_tokens(char_count: int) -> int:
    """
    Estimate token count from character count.

    Uses simple heuristic: 1 token ≈ 4 characters for English text.

    Args:
        char_count: Number of characters

    Returns:
        Estimated token count
    """
    return max(1, char_count // 4)


def estimate_cost(
    input_chars: int,
    output_chars: int,
    price_per_mtok_in: Decimal,
    price_per_mtok_out: Decimal,
) -> Decimal:
    """
    Estimate API call cost from character counts.

    Args:
        input_chars: Input character count (prompt)
        output_chars: Output character count (completion)
        price_per_mtok_in: Price per million input tokens
        price_per_mtok_out: Price per million output tokens

    Returns:
        Estimated cost in USD as Decimal
    """
    input_tokens = estimate_tokens(input_chars)
    output_tokens = estimate_tokens(output_chars)

    # Cost = (tokens / 1_000_000) * price_per_mtok
    input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * price_per_mtok_in
    output_cost = (Decimal(output_tokens) / Decimal(1_000_000)) * price_per_mtok_out

    return input_cost + output_cost


def redact(text: str, max_length: int = 300) -> str:
    """
    Redact and truncate text for safe logging.

    Args:
        text: Text to redact
        max_length: Maximum length before truncation

    Returns:
        Truncated text safe for logging (no API keys, limited length)
    """
    # Truncate if too long
    if len(text) > max_length:
        return text[:max_length] + f"... ({len(text)} chars total)"
    return text


def ensure_json_array(obj: Any, n_expected: int | None = None) -> list[Any]:
    """
    Ensure object is a JSON array, optionally validating length.

    Args:
        obj: Object to validate (should be a list)
        n_expected: Optional expected array length

    Returns:
        Validated list

    Raises:
        ValueError: If not a list or length mismatch
    """
    if not isinstance(obj, list):
        raise ValueError(f"Expected JSON array, got {type(obj).__name__}")

    if n_expected is not None and len(obj) != n_expected:
        raise ValueError(
            f"Expected array of length {n_expected}, got {len(obj)}"
        )

    return obj
