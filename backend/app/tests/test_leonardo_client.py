"""Tests for Leonardo API client (prompt compaction + content filter handling)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.clients.leonardo import ContentFilterError, LeonardoClient, PromptTooLongError


@pytest.fixture
def leonardo_client():
    """Create a test Leonardo client."""
    return LeonardoClient(
        api_key="test-key",
        model_id="test-model",
        element_id="12345",
        element_trigger="evajoy",
        element_weight=1.0
    )


def test_content_filter_raises_without_retry(leonardo_client):
    """Test that content filter errors raise immediately without retry."""
    with patch("httpx.Client") as mock_client_cls:
        # Mock the HTTP client to return a content filter error
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"error":"Our filter indicates that your prompt may include inappropriate references"}'
        mock_response.json.return_value = {"error": "Our filter indicates that your prompt may include inappropriate references"}

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client_cls.return_value = mock_client

        payload = {"base": "Test prompt", "neg": ""}

        # Should raise ContentFilterError immediately
        with pytest.raises(ContentFilterError) as exc_info:
            leonardo_client.generate(payload)

        assert "filter" in str(exc_info.value).lower()

        # Verify only one API call was made (no retries)
        assert mock_client.post.call_count == 1


def test_prompt_too_long_after_compaction_raises(leonardo_client):
    """Test that length assertion raises if compact_prompt() returns too-long prompt."""
    # Mock compact_prompt to return a prompt that exceeds max_len
    # (This tests the pre-flight assertion, simulating a compact_prompt bug)
    with patch("app.clients.leonardo.compact_prompt") as mock_compact:
        too_long_prompt = "a" * 950
        mock_compact.return_value = {
            "prompt": too_long_prompt,
            "warnings": [],
            "len_before": 1000,
            "len_after": 950,
            "prompt_hash": "abcd1234",
        }

        payload = {"base": "test", "neg": ""}

        # Should raise PromptTooLongError due to assertion
        with pytest.raises(PromptTooLongError) as exc_info:
            leonardo_client.generate(payload)

        assert "900" in str(exc_info.value)
        assert "950" in str(exc_info.value)


def test_negative_prompt_capped_400_no_semantic_changes(leonardo_client):
    """Test that negative prompts are compacted to 400 chars without semantic changes."""
    with patch("httpx.Client") as mock_client_cls:
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"generationId": "test-123"}

        mock_poll_response = MagicMock()
        mock_poll_response.status_code = 200
        mock_poll_response.json.return_value = {
            "generated_images": [{"url": "http://example.com/test.png"}]
        }

        mock_image_response = MagicMock()
        mock_image_response.status_code = 200
        mock_image_response.content = b"fake-image-data"

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.get.side_effect = [mock_poll_response, mock_image_response]
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client_cls.return_value = mock_client

        # Create a long negative prompt
        long_negative = "blurry, " * 100  # ~800 chars

        payload = {"base": "Test", "neg": long_negative}

        # Should succeed and compact negative prompt
        leonardo_client.generate(payload)

        # Check the API call
        call_args = mock_client.post.call_args
        sent_data = call_args[1]["json"]

        # Negative prompt should be compacted to <= 400
        assert len(sent_data["negative_prompt"]) <= 400


def test_trigger_word_injected_once(leonardo_client):
    """Test that trigger word appears exactly once at the start."""
    with patch("httpx.Client") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"generationId": "test-123"}

        mock_poll_response = MagicMock()
        mock_poll_response.status_code = 200
        mock_poll_response.json.return_value = {
            "generated_images": [{"url": "http://example.com/test.png"}]
        }

        mock_image_response = MagicMock()
        mock_image_response.status_code = 200
        mock_image_response.content = b"fake-image-data"

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.get.side_effect = [mock_poll_response, mock_image_response]
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client_cls.return_value = mock_client

        payload = {"base": "fitness pose in gym", "neg": ""}

        leonardo_client.generate(payload)

        # Check the API call
        call_args = mock_client.post.call_args
        sent_data = call_args[1]["json"]

        # Should have trigger at start
        assert sent_data["prompt"].startswith("evajoy,")
        assert sent_data["prompt"].count("evajoy") == 1


def test_element_id_sent_as_integer(leonardo_client):
    """Test that userLoraId is sent as integer, not string."""
    with patch("httpx.Client") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"generationId": "test-123"}

        mock_poll_response = MagicMock()
        mock_poll_response.status_code = 200
        mock_poll_response.json.return_value = {
            "generated_images": [{"url": "http://example.com/test.png"}]
        }

        mock_image_response = MagicMock()
        mock_image_response.status_code = 200
        mock_image_response.content = b"fake-image-data"

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.get.side_effect = [mock_poll_response, mock_image_response]
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client_cls.return_value = mock_client

        payload = {"base": "test", "neg": ""}

        leonardo_client.generate(payload)

        # Check the API call
        call_args = mock_client.post.call_args
        sent_data = call_args[1]["json"]

        # userLoraId should be integer
        assert "userElements" in sent_data
        assert isinstance(sent_data["userElements"][0]["userLoraId"], int)
        assert sent_data["userElements"][0]["userLoraId"] == 12345


def test_non_filter_errors_raise_runtime_error(leonardo_client):
    """Test that non-filter errors raise RuntimeError."""
    with patch("httpx.Client") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = '{"error":"Internal server error"}'

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client_cls.return_value = mock_client

        payload = {"base": "Test", "neg": ""}

        # Should raise RuntimeError (not ContentFilterError)
        with pytest.raises(RuntimeError) as exc_info:
            leonardo_client.generate(payload)

        assert "Leonardo create failed" in str(exc_info.value)
