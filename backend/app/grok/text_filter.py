"""Text filter for cleaning up banned words from generated prompts."""

from __future__ import annotations

import re

# Banned words to remove from prompts (easily extensible)
BANNED_WORDS = [
    "faint",
    "glint",
    "glinting",
    "glints",
    "ethereal",
    "air",
    "delicate",
]


def filter_banned_words(text: str) -> tuple[str, list[str]]:
    """
    Remove banned words from text.

    Args:
        text: Input text to clean

    Returns:
        Tuple of (cleaned_text, list_of_removed_words)
    """
    if not text:
        return text, []

    removed = []
    cleaned = text

    for word in BANNED_WORDS:
        # Build regex pattern to match word with word boundaries
        # Case-insensitive, matches whole words only
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)

        # Find all matches to track what was removed
        matches = pattern.findall(cleaned)
        if matches:
            removed.extend(matches)

        # Remove the word
        cleaned = pattern.sub('', cleaned)

    # Clean up any double spaces, leading/trailing spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # Remove duplicate entries from removed list
    removed = list(set(removed))

    return cleaned, removed
