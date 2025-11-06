"""Prompt compaction utilities (format/length only, no semantic changes)."""

from __future__ import annotations

import hashlib
import re


def compact_prompt(raw: str, *, max_len: int = 900, trigger: str | None = None) -> dict:
    """Compact prompt for Leonardo API compliance (format/length only, no semantic changes).

    Args:
        raw: Raw prompt text from Grok
        max_len: Maximum length (default 900 for Leonardo)
        trigger: Optional trigger word to ensure appears once at start

    Returns:
        Dict with keys:
            - prompt: Compacted prompt string
            - warnings: List of formatting changes made
            - len_before: Original length
            - len_after: Final length
            - prompt_hash: SHA256 hash of final prompt (for logging)
    """
    warnings = []
    len_before = len(raw)
    text = raw

    # 1. Strip markdown code fences and blocks
    if "```" in text:
        # Match ``` with optional language, any content, and closing ```
        text = re.sub(r'```[a-z]*.*?```', '', text, flags=re.DOTALL)
        warnings.append("removed_code_fences")

    # 2. Strip markdown formatting (lists, headings, blockquotes)
    if re.search(r'(^#+\s|^>\s|^[-*]\s)', text, re.MULTILINE):
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)  # Headings
        text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)   # Blockquotes
        text = re.sub(r'^[-*]\s+', '', text, flags=re.MULTILINE)  # Lists
        warnings.append("removed_markdown")

    # 3. Remove URLs
    if re.search(r'https?://', text):
        text = re.sub(r'https?://\S+', '', text)
        warnings.append("removed_urls")

    # 4. Remove emojis (Unicode emoji ranges)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE
    )
    if emoji_pattern.search(text):
        text = emoji_pattern.sub('', text)
        warnings.append("removed_emojis")

    # 5. Collapse excessive punctuation (3+ repeated → 1)
    if re.search(r'([.!?,;:]){3,}', text):
        text = re.sub(r'([.!?,;:]){3,}', r'\1', text)
        warnings.append("collapsed_punctuation")

    # 6. Deduplicate excessive adjectives (formatting only - remove obvious duplicates)
    # Pattern: "very very" → "very", "ultra super ultra" → "ultra super"
    excessive_words = r'\b(very|ultra|super|extremely|insanely|absolutely)\b'
    original = text
    # Remove consecutive duplicates of these words
    text = re.sub(rf'({excessive_words})\s+\1', r'\1', text, flags=re.IGNORECASE)
    if text != original:
        warnings.append("deduped_adjectives")

    # 7. Collapse whitespace (multiple spaces/newlines → single space)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    # 8. Ensure single trigger at start if provided + add 9:16 native header
    if trigger and trigger.strip():
        trigger_clean = trigger.strip()
        # Check if trigger already exists (case-insensitive)
        trigger_pattern = re.compile(re.escape(trigger_clean), re.IGNORECASE)

        # Remove all occurrences of trigger
        text = trigger_pattern.sub('', text).strip()

        # Prepend trigger + native 9:16 header once with separator
        header = "photorealistic vertical 9:16, native high resolution for phone, no upscaling, compose for 864×1536"
        text = f"{trigger_clean}, {header}; {text}"
        warnings.append("trigger_injected")
        warnings.append("native_916_header_added")

    # 9. Truncate to max_len (prefer clause boundaries)
    if len(text) > max_len:
        # Try to find last punctuation within acceptable range
        search_start = max(0, max_len - 80)  # Look in last 80 chars before limit
        truncate_at = max_len

        # Search for clause boundaries (., ;, :, !) in reverse from max_len
        for i in range(max_len - 1, search_start - 1, -1):
            if text[i] in '.;:!':
                truncate_at = i + 1  # Include the punctuation
                break

        text = text[:truncate_at].strip()
        warnings.append("truncated")

    len_after = len(text)
    prompt_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

    return {
        "prompt": text,
        "warnings": warnings,
        "len_before": len_before,
        "len_after": len_after,
        "prompt_hash": prompt_hash,
    }
