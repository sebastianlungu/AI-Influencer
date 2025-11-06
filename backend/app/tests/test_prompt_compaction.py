"""Tests for prompt compaction (format/length only, no SFW redrafting)."""

from __future__ import annotations

from app.core.prompt_utils import compact_prompt


def test_compaction_trims_markdown_and_emojis():
    """Test that markdown and emojis are removed."""
    raw = "# Heading\n\nTest prompt with 🔥 emoji and ```code block```"
    result = compact_prompt(raw, max_len=900)

    assert "```" not in result["prompt"]
    assert "🔥" not in result["prompt"]
    assert "#" not in result["prompt"]
    assert "removed_code_fences" in result["warnings"]
    assert "removed_emojis" in result["warnings"]
    assert "removed_markdown" in result["warnings"]


def test_compaction_dedups_adjectives_and_cuts_at_boundary():
    """Test that duplicate adjectives are removed and truncation respects boundaries."""
    raw = "very very intense workout with ultra ultra energy"
    result = compact_prompt(raw, max_len=900)

    # Should deduplicate "very very" → "very" and "ultra ultra" → "ultra"
    assert result["prompt"].count("very") == 1
    assert result["prompt"].count("ultra") == 1
    assert "deduped_adjectives" in result["warnings"]


def test_trigger_injected_once_at_head():
    """Test that trigger word appears exactly once at the start."""
    raw = "Beautiful fitness model in gym"
    result = compact_prompt(raw, max_len=900, trigger="evajoy")

    # Trigger should be at start with comma separator
    assert result["prompt"].startswith("evajoy,")
    assert result["prompt"].count("evajoy") == 1
    assert "trigger_injected" in result["warnings"]


def test_trigger_not_duplicated_if_already_present():
    """Test that trigger is not duplicated if already in prompt."""
    raw = "evajoy in fitness pose"
    result = compact_prompt(raw, max_len=900, trigger="evajoy")

    # Should still have exactly one occurrence at start
    assert result["prompt"].startswith("evajoy,")
    assert result["prompt"].count("evajoy") == 1


def test_compaction_enforces_max_len_900():
    """Test that prompts are truncated to max length."""
    # Create a prompt longer than 900 chars
    raw = "A detailed fitness scene " * 50  # ~1250 chars

    result = compact_prompt(raw, max_len=900)

    assert result["len_after"] <= 900
    assert "truncated" in result["warnings"]
    assert result["len_before"] > 900


def test_compaction_truncates_at_clause_boundary():
    """Test that truncation prefers clause boundaries."""
    # Create prompt with punctuation near the limit
    raw = "A" * 850 + ". More text that should be cut off because it exceeds limit."

    result = compact_prompt(raw, max_len=900)

    # Should truncate at the period, not mid-word
    assert result["prompt"].endswith(".")
    assert result["len_after"] <= 900


def test_url_removal():
    """Test that URLs are removed from prompts."""
    raw = "Check out https://example.com for fitness tips"
    result = compact_prompt(raw, max_len=900)

    assert "https://" not in result["prompt"]
    assert "removed_urls" in result["warnings"]


def test_whitespace_collapse():
    """Test that excessive whitespace is collapsed."""
    raw = "Fitness    model\n\n\nwith    multiple    spaces"
    result = compact_prompt(raw, max_len=900)

    # Should be collapsed to single spaces
    assert "    " not in result["prompt"]
    assert "\n\n" not in result["prompt"]
    assert "Fitness model with multiple spaces" in result["prompt"]


def test_punctuation_collapse():
    """Test that excessive punctuation is collapsed."""
    raw = "Amazing fitness scene!!!! Great workout......"
    result = compact_prompt(raw, max_len=900)

    # Should collapse to single punctuation
    assert "!!!!" not in result["prompt"]
    assert "......" not in result["prompt"]
    assert "collapsed_punctuation" in result["warnings"]


def test_compaction_returns_correct_metadata():
    """Test that compaction returns all required metadata."""
    raw = "Test prompt"
    result = compact_prompt(raw, max_len=900)

    assert "prompt" in result
    assert "warnings" in result
    assert "len_before" in result
    assert "len_after" in result
    assert "prompt_hash" in result
    assert isinstance(result["warnings"], list)
    assert result["len_before"] == len(raw)
    assert result["len_after"] == len(result["prompt"])


def test_compaction_no_warnings_for_clean_prompt():
    """Test that clean prompts don't generate unnecessary warnings."""
    raw = "Simple fitness scene"
    result = compact_prompt(raw, max_len=900)

    # Should have no warnings except maybe whitespace normalization
    assert len(result["warnings"]) == 0 or result["warnings"] == []


def test_compaction_with_negative_prompt():
    """Test compaction works for negative prompts (no trigger)."""
    raw = "blurry, low quality, distorted"
    result = compact_prompt(raw, max_len=400, trigger=None)

    assert result["len_after"] <= 400
    # Should not have trigger_injected warning
    assert "trigger_injected" not in result["warnings"]
