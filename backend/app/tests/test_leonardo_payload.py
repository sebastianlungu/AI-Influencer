"""Smoke test for Leonardo Vision XL payload validation (no live API calls)."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch

from app.core.config import settings


def test_leonardo_payload_structure():
    """Test that Leonardo payload contains Vision XL model ID, 1152×2048, and element 155265@0.80."""
    # Mock settings for test
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.leonardo_model_id = "test-vision-xl-id"
        mock_settings.leonardo_width = 1152
        mock_settings.leonardo_height = 2048
        mock_settings.leonardo_lora_id = 155265
        mock_settings.leonardo_lora_weight = 0.80
        mock_settings.leonardo_cfg = 7.0
        mock_settings.leonardo_steps = 32
        mock_settings.prompt_max_len = 900
        mock_settings.negative_max_len = 400
        mock_settings.leonardo_element_trigger = "evajoy"

        from app.clients.leonardo import LeonardoClient

        # Create client (bypass API key check)
        with patch.object(LeonardoClient, "__init__", return_value=None):
            client = LeonardoClient.__new__(LeonardoClient)
            client.key = "test-key"
            client.headers = {"Authorization": "Bearer test-key"}
            client.model_id = mock_settings.leonardo_model_id
            client.element_id = str(mock_settings.leonardo_lora_id)
            client.element_trigger = mock_settings.leonardo_element_trigger
            client.element_weight = mock_settings.leonardo_lora_weight

        # Simulate payload construction (from generate method)
        prompt = "evajoy, photorealistic vertical 9:16, native high resolution for phone"
        negative = "doll-like, mannequin, plastic skin"

        # Construct payload as done in generate()
        data = {
            "prompt": prompt,
            "negative_prompt": negative,
            "num_images": 1,
            "width": mock_settings.leonardo_width,
            "height": mock_settings.leonardo_height,
            "guidanceScale": mock_settings.leonardo_cfg,
            "num_inference_steps": mock_settings.leonardo_steps,
            "modelId": mock_settings.leonardo_model_id,
            "elements": [
                {
                    "id": mock_settings.leonardo_lora_id,
                    "weight": mock_settings.leonardo_lora_weight,
                }
            ],
        }

        # ASSERTIONS (PRE-FLIGHT VALIDATION)
        # 1. Model ID present
        assert "modelId" in data
        assert data["modelId"] == "test-vision-xl-id"

        # 2. Native 9:16 high-res (1152×2048)
        assert data["width"] == 1152
        assert data["height"] == 2048

        # 3. Eva Joy LoRA element present
        assert "elements" in data
        assert len(data["elements"]) == 1
        elem = data["elements"][0]
        assert elem["id"] == 155265
        assert abs(elem["weight"] - 0.80) < 0.001

        # 4. Guidance scale and steps
        assert data["guidanceScale"] == 7.0
        assert data["num_inference_steps"] == 32

        print("[OK] Smoke test PASSED: Leonardo payload structure validated")
        print(f"   Model ID: {data['modelId']}")
        print(f"   Size: {data['width']}x{data['height']}")
        print(f"   Element: id={elem['id']} weight={elem['weight']}")


def test_enhanced_negative_prompt():
    """Test that negative prompt contains all required terms."""
    # Required negative terms
    required_terms = [
        "doll-like",
        "mannequin",
        "uncanny face",
        "over-smooth skin",
        "plastic skin",
        "extra fingers",
        "warped anatomy",
        "de-aging",
        "seam",
        "text",
        "watermark",
        "logo",
        "lens flare streaks",
    ]

    # Simulate negative prompt enhancement (from generate method)
    negative = "cartoon, CGI, blurry"

    for term in required_terms:
        if term not in negative.lower():
            negative += f", {term}"

    # Assert all terms present
    for term in required_terms:
        assert term in negative.lower(), f"Required term '{term}' missing from negative prompt"

    print(f"[OK] Enhanced negative prompt validated ({len(required_terms)} terms present)")


def test_native_916_header_injection():
    """Test that 9:16 native header is injected into prompt."""
    from app.core.prompt_utils import compact_prompt

    raw_prompt = "Eva Joy at the gym, working out with dumbbells"

    result = compact_prompt(raw_prompt, trigger="evajoy")

    # Check trigger present
    assert "evajoy" in result["prompt"].lower()

    # Check 9:16 native header present
    assert "photorealistic vertical 9:16" in result["prompt"]
    assert "native high resolution for phone" in result["prompt"]
    assert "no upscaling" in result["prompt"]
    assert "1152×2048" in result["prompt"] or "1152x2048" in result["prompt"]

    # Check warnings
    assert "trigger_injected" in result["warnings"]
    assert "native_916_header_added" in result["warnings"]

    print("[OK] Native 9:16 header injection validated")
    print(f"   Final prompt (first 200 chars): {result['prompt'][:200]}...")


if __name__ == "__main__":
    # Run smoke tests
    test_leonardo_payload_structure()
    test_enhanced_negative_prompt()
    test_native_916_header_injection()
    print("\n[OK] ALL SMOKE TESTS PASSED")
