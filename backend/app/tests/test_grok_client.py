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

from app.grok import GrokClient


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
@patch("app.clients.grok.add_cost")
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
@patch("app.clients.grok.add_cost")
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
@patch("app.clients.grok.add_cost")
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
@patch("app.clients.grok.add_cost")
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
@patch("app.clients.grok.add_cost")
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
@patch("app.clients.grok.add_cost")
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
    assert abs(cost_30 / cost_15 - Decimal("2.0")) < Decimal("0.1")  # Within 10% of 2x


@patch("app.grok.client.open")
@patch("app.grok.client.XAITransport")
@patch("app.grok.client.GrokClient._call_api")
@patch("app.grok.client.add_cost")
def test_prompt_bundle_character_limit_retry_success(mock_add_cost, mock_call_api, mock_transport, mock_open):
    """Test that over-limit prompts trigger retry and succeed on 2nd attempt."""
    from app.grok import GrokClient

    # Mock config file loading
    mock_persona = {"hair": "blonde", "eyes": "blue", "body": "athletic", "do": [], "dont": []}
    mock_variety = {"scene": ["gym"], "wardrobe": ["leggings"], "accessories": ["watch"],
                    "pose_microaction": ["squat"], "lighting": ["sunset"], "camera": ["50mm"],
                    "angle": ["low"], "negative": []}

    mock_file_persona = MagicMock()
    mock_file_persona.__enter__.return_value.read.return_value = json.dumps(mock_persona)
    mock_file_variety = MagicMock()
    mock_file_variety.__enter__.return_value.read.return_value = json.dumps(mock_variety)

    def open_side_effect(path, *args, **kwargs):
        if "persona.json" in str(path):
            return mock_file_persona
        elif "variety_bank.json" in str(path):
            return mock_file_variety
        raise FileNotFoundError(f"Unexpected file: {path}")

    mock_open.side_effect = open_side_effect

    # First response: prompt too long (2027 chars)
    long_prompt = "x" * 2027  # Exceeds 1500 limit
    response_over_limit = json.dumps([{
        "id": "pr_test1",
        "image_prompt": {
            "final_prompt": long_prompt,
            "negative_prompt": "cartoon",
            "width": 864,
            "height": 1536
        },
        "video_prompt": {
            "motion": "pan right",
            "character_action": "squatting",
            "environment": "gym",
            "duration_seconds": 6,
            "notes": "test"
        }
    }])

    # Second response: valid prompt (1200 chars)
    valid_prompt = "x" * 1200  # Within 1500 limit
    response_valid = json.dumps([{
        "id": "pr_test2",
        "image_prompt": {
            "final_prompt": valid_prompt,
            "negative_prompt": "cartoon",
            "width": 864,
            "height": 1536
        },
        "video_prompt": {
            "motion": "pan right",
            "character_action": "squatting",
            "environment": "gym",
            "duration_seconds": 6,
            "notes": "test"
        }
    }])

    # Mock API responses: first fails, second succeeds
    # _call_api returns content string (already extracted from JSON response)
    mock_call_api.side_effect = [response_over_limit, response_valid]

    # Generate bundles
    client = GrokClient(api_key="test-key", model="grok-4-fast-reasoning")
    bundles = client.generate_prompt_bundle(setting="Tokyo Gym", count=1)

    # Verify retry happened (2 calls)
    assert mock_call_api.call_count == 2

    # Verify final bundle is valid
    assert len(bundles) == 1
    assert len(bundles[0]["image_prompt"]["final_prompt"]) == 1200
    assert len(bundles[0]["image_prompt"]["final_prompt"]) <= 1500


@patch("app.grok.client.open")
@patch("app.grok.client.XAITransport")
@patch("app.grok.client.GrokClient._call_api")
@patch("app.grok.client.add_cost")
def test_prompt_bundle_character_limit_fail_loud(mock_add_cost, mock_call_api, mock_transport, mock_open):
    """Test that 3 over-limit attempts raise RuntimeError with clear message."""
    from app.grok import GrokClient

    # Mock config file loading
    mock_persona = {"hair": "blonde", "eyes": "blue", "body": "athletic", "do": [], "dont": []}
    mock_variety = {"scene": ["gym"], "wardrobe": ["leggings"], "accessories": ["watch"],
                    "pose_microaction": ["squat"], "lighting": ["sunset"], "camera": ["50mm"],
                    "angle": ["low"], "negative": []}

    mock_file_persona = MagicMock()
    mock_file_persona.__enter__.return_value.read.return_value = json.dumps(mock_persona)
    mock_file_variety = MagicMock()
    mock_file_variety.__enter__.return_value.read.return_value = json.dumps(mock_variety)

    def open_side_effect(path, *args, **kwargs):
        if "persona.json" in str(path):
            return mock_file_persona
        elif "variety_bank.json" in str(path):
            return mock_file_variety
        raise FileNotFoundError(f"Unexpected file: {path}")

    mock_open.side_effect = open_side_effect

    # All 3 attempts: prompt too long (2027 chars)
    long_prompt = "x" * 2027  # Exceeds 1500 limit
    response_over_limit = json.dumps([{
        "id": "pr_test",
        "image_prompt": {
            "final_prompt": long_prompt,
            "negative_prompt": "cartoon",
            "width": 864,
            "height": 1536
        },
        "video_prompt": {
            "motion": "pan right",
            "character_action": "squatting",
            "environment": "gym",
            "duration_seconds": 6,
            "notes": "test"
        }
    }])

    # All attempts return over-limit prompt
    mock_call_api.side_effect = [response_over_limit, response_over_limit, response_over_limit]

    # Should fail loud after 3 attempts
    client = GrokClient(api_key="test-key", model="grok-4-fast-reasoning")
    with pytest.raises(RuntimeError, match="Character limit exceeded on attempt 3/3"):
        client.generate_prompt_bundle(setting="Tokyo Gym", count=1)

    # Verify 3 attempts were made
    assert mock_call_api.call_count == 3


@patch("app.grok.client.open")
@patch("app.grok.client.XAITransport")
@patch("app.grok.client.GrokClient._call_api")
@patch("app.grok.client.add_cost")
def test_prompt_bundle_character_limit_validation(mock_add_cost, mock_call_api, mock_transport, mock_open):
    """Test that prompts within limit pass validation without retry."""
    from app.grok import GrokClient

    # Mock config file loading
    mock_persona = {"hair": "blonde", "eyes": "blue", "body": "athletic", "do": [], "dont": []}
    mock_variety = {"scene": ["gym"], "wardrobe": ["leggings"], "accessories": ["watch"],
                    "pose_microaction": ["squat"], "lighting": ["sunset"], "camera": ["50mm"],
                    "angle": ["low"], "negative": []}

    mock_file_persona = MagicMock()
    mock_file_persona.__enter__.return_value.read.return_value = json.dumps(mock_persona)
    mock_file_variety = MagicMock()
    mock_file_variety.__enter__.return_value.read.return_value = json.dumps(mock_variety)

    def open_side_effect(path, *args, **kwargs):
        if "persona.json" in str(path):
            return mock_file_persona
        elif "variety_bank.json" in str(path):
            return mock_file_variety
        raise FileNotFoundError(f"Unexpected file: {path}")

    mock_open.side_effect = open_side_effect

    # Valid prompt (1000 chars - within target and limit)
    valid_prompt = "x" * 1000
    response_valid = json.dumps([{
        "id": "pr_test",
        "image_prompt": {
            "final_prompt": valid_prompt,
            "negative_prompt": "cartoon",
            "width": 864,
            "height": 1536
        },
        "video_prompt": {
            "motion": "pan right",
            "character_action": "squatting",
            "environment": "gym",
            "duration_seconds": 6,
            "notes": "test"
        }
    }])

    mock_call_api.return_value = response_valid

    # Generate bundles
    client = GrokClient(api_key="test-key", model="grok-4-fast-reasoning")
    bundles = client.generate_prompt_bundle(setting="Tokyo Gym", count=1)

    # Verify no retry (only 1 call)
    assert mock_call_api.call_count == 1

    # Verify bundle is valid
    assert len(bundles) == 1
    assert len(bundles[0]["image_prompt"]["final_prompt"]) == 1000
    assert len(bundles[0]["image_prompt"]["final_prompt"]) <= 1500
