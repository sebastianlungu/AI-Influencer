"""
Unit tests for Grok API client.

Tests prompt generation, error handling, retries, and cost tracking.
Uses mocked HTTP responses to avoid live API calls.
"""

from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.clients.grok import GrokClient


@pytest.fixture
def mock_grok_response():
    """Fixture providing a valid Grok API response."""
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps([
                        {
                            "base": "ultra-realistic portrait of Eva Joy doing weighted squats in luxury Bali gym at sunset, wearing teal athletic set; muscular defined legs, strong form; golden hour sunlight streaming through windows; 85mm lens shallow depth of field; professional DSLR; natural highlights on muscles; tropical palm trees visible in background",
                            "variation": "Weighted squats in Bali luxury gym at sunset",
                            "meta": {
                                "location": "luxury hotel rooftop gym with city skyline",
                                "pose": "weighted squat mid-rep",
                                "outfit": "teal athletic matching set (crop top + shorts)",
                                "activity": "strength training with free weights",
                                "lighting": "golden hour sunlight (warm, soft)",
                                "camera": "85mm portrait lens with shallow depth of field",
                            },
                        },
                        {
                            "base": "ultra-realistic portrait of Eva Joy in warrior yoga pose on Santorini cliffside at sunrise; arms extended, strong balanced stance; athletic feminine physique; white yoga outfit; cool fresh sunrise light; 50mm lens f/1.8; blue domes and white buildings in background; Mediterranean aesthetic",
                            "variation": "Warrior yoga pose on Santorini cliffside at sunrise",
                            "meta": {
                                "location": "Santorini white buildings and blue domes backdrop",
                                "pose": "warrior yoga pose with arms extended",
                                "outfit": "all-white matching activewear",
                                "activity": "yoga flow sequence",
                                "lighting": "sunrise light (cool, fresh)",
                                "camera": "50mm lens at f/1.8 for bokeh",
                            },
                        },
                    ])
                }
            }
        ]
    }


@pytest.fixture
def character_profile():
    """Fixture providing Eva Joy character profile."""
    return {
        "name": "Eva Joy",
        "physical": {
            "body_type": "muscular, defined, athletic, curvy, feminine",
            "hair": "long, slightly wavy, dark brown (brunette)",
            "eyes": "expressive green eyes",
        },
        "style": {
            "makeup": "soft natural makeup, subtle glow",
            "vibe": "confident, strong, feminine",
        },
        "fitness_focus": ["strength training", "yoga"],
    }


@pytest.fixture
def diversity_banks():
    """Fixture providing diversity banks."""
    return {
        "locations": ["Bali gym", "Santorini cliffside", "Dubai beach"],
        "poses": ["weighted squat", "warrior yoga pose", "deadlift"],
        "outfits": ["teal set", "white yoga outfit", "black leggings"],
        "activities": ["strength training", "yoga", "HIIT"],
        "lighting": ["golden hour", "sunrise", "studio lighting"],
        "camera": ["85mm portrait", "50mm f/1.8", "24mm wide"],
    }


def test_grok_client_initialization():
    """Test GrokClient initialization with API key."""
    client = GrokClient(api_key="test-key-123", model="grok-2-1212")
    assert client.api_key == "test-key-123"
    assert client.model == "grok-2-1212"


def test_grok_client_requires_api_key():
    """Test that GrokClient raises error when API key is empty."""
    with pytest.raises(ValueError, match="API key cannot be empty"):
        GrokClient(api_key="", model="grok-2-1212")


@patch("app.clients.grok.httpx.Client")
@patch("app.core.cost.add_cost")
def test_generate_variations_success(
    mock_add_cost,
    mock_httpx_client,
    mock_grok_response,
    character_profile,
    diversity_banks,
):
    """Test successful variation generation with valid Grok response."""
    # Mock HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_grok_response

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

    # Create client and generate variations
    client = GrokClient(api_key="test-key", model="grok-2-1212")
    variations = client.generate_variations(
        character_profile=character_profile,
        diversity_banks=diversity_banks,
        n=2,
        negative_prompt="cartoon, anime, nudity",
    )

    # Assertions
    assert len(variations) == 2
    assert variations[0]["base"].startswith("ultra-realistic portrait of Eva Joy")
    assert variations[0]["variation"] == "Weighted squats in Bali luxury gym at sunset"
    assert variations[0]["meta"]["location"] == "luxury hotel rooftop gym with city skyline"
    assert variations[0]["neg"] == "cartoon, anime, nudity"

    assert variations[1]["base"].startswith("ultra-realistic portrait of Eva Joy")
    assert variations[1]["meta"]["activity"] == "yoga flow sequence"

    # Verify cost tracking was called
    mock_add_cost.assert_called_once()
    assert mock_add_cost.call_args[0][1] == "grok"  # Service name


@patch("app.clients.grok.httpx.Client")
@patch("app.core.cost.add_cost")
def test_generate_variations_with_markdown_code_block(
    mock_add_cost,
    mock_httpx_client,
    character_profile,
    diversity_banks,
):
    """Test parsing when Grok returns JSON wrapped in markdown code block."""
    # Mock response with markdown code block
    variations_data = [
        {
            "base": "Test prompt",
            "variation": "Test variation",
            "meta": {"location": "test", "pose": "test"},
        }
    ]
    markdown_response = {
        "choices": [
            {"message": {"content": f"```json\n{json.dumps(variations_data)}\n```"}}
        ]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = markdown_response

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

    # Generate variations
    client = GrokClient(api_key="test-key", model="grok-2-1212")
    variations = client.generate_variations(
        character_profile=character_profile,
        diversity_banks=diversity_banks,
        n=1,
        negative_prompt="",
    )

    assert len(variations) == 1
    assert variations[0]["base"] == "Test prompt"


@patch("app.clients.grok.httpx.Client")
@patch("app.core.cost.add_cost")
def test_generate_variations_invalid_json(
    mock_add_cost,
    mock_httpx_client,
    character_profile,
    diversity_banks,
):
    """Test error handling when Grok returns invalid JSON."""
    # Mock response with invalid JSON
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "This is not valid JSON"}}]
    }

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

    # Should raise RuntimeError on invalid JSON
    client = GrokClient(api_key="test-key", model="grok-2-1212")
    with pytest.raises(RuntimeError, match="Failed to parse Grok response"):
        client.generate_variations(
            character_profile=character_profile,
            diversity_banks=diversity_banks,
            n=1,
            negative_prompt="",
        )


@patch("app.clients.grok.httpx.Client")
@patch("app.core.cost.add_cost")
@patch("app.clients.grok.time.sleep")  # Mock sleep to speed up test
def test_generate_variations_retry_on_500(
    mock_sleep,
    mock_add_cost,
    mock_httpx_client,
    mock_grok_response,
    character_profile,
    diversity_banks,
):
    """Test retry logic on 500 server error."""
    # First call: 500 error, second call: success
    mock_error_response = MagicMock()
    mock_error_response.status_code = 500
    mock_error_response.text = "Internal Server Error"

    mock_success_response = MagicMock()
    mock_success_response.status_code = 200
    mock_success_response.json.return_value = mock_grok_response

    mock_client_instance = MagicMock()
    mock_client_instance.post.side_effect = [mock_error_response, mock_success_response]
    mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

    # Generate variations (should succeed after retry)
    client = GrokClient(api_key="test-key", model="grok-2-1212")
    variations = client.generate_variations(
        character_profile=character_profile,
        diversity_banks=diversity_banks,
        n=2,
        negative_prompt="",
    )

    assert len(variations) == 2
    assert mock_client_instance.post.call_count == 2  # Initial + 1 retry
    mock_sleep.assert_called()  # Verify backoff sleep was called


@patch("app.clients.grok.httpx.Client")
@patch("app.core.cost.add_cost")
def test_generate_variations_fail_on_400(
    mock_add_cost,
    mock_httpx_client,
    character_profile,
    diversity_banks,
):
    """Test immediate failure on 400 bad request (non-retryable)."""
    # Mock 400 error
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request: Invalid model"

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

    # Should fail immediately without retries
    client = GrokClient(api_key="test-key", model="grok-2-1212")
    with pytest.raises(RuntimeError, match="Grok API error 400"):
        client.generate_variations(
            character_profile=character_profile,
            diversity_banks=diversity_banks,
            n=2,
            negative_prompt="",
        )

    # Verify only 1 call (no retries on 400)
    assert mock_client_instance.post.call_count == 1


@patch("app.clients.grok.httpx.Client")
@patch("app.core.cost.add_cost")
def test_cost_tracking_scales_with_batch_size(
    mock_add_cost, mock_httpx_client, mock_grok_response, character_profile, diversity_banks
):
    """Test that cost estimate scales with batch size."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_grok_response

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

    client = GrokClient(api_key="test-key", model="grok-2-1212")

    # Generate with n=15 (baseline)
    client.generate_variations(
        character_profile=character_profile,
        diversity_banks=diversity_banks,
        n=15,
        negative_prompt="",
    )
    cost_15 = mock_add_cost.call_args[0][0]

    # Reset mock
    mock_add_cost.reset_mock()

    # Generate with n=30 (double)
    client.generate_variations(
        character_profile=character_profile,
        diversity_banks=diversity_banks,
        n=30,
        negative_prompt="",
    )
    cost_30 = mock_add_cost.call_args[0][0]

    # Cost should approximately double
    assert cost_30 > cost_15
    assert abs(cost_30 / cost_15 - 2.0) < 0.1  # Within 10% of 2x
