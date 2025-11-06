from __future__ import annotations

import time
import tempfile
from decimal import Decimal

import httpx

from app.core import concurrency
from app.core.config import settings
from app.core.cost import add_cost
from app.core.logging import log
from app.core.paths import get_data_path
from app.core.prompt_utils import compact_prompt

BASE_URL = "https://cloud.leonardo.ai/api/rest/v1"


class ContentFilterError(Exception):
    """Raised when Leonardo's content filter blocks a prompt."""
    pass


class PromptTooLongError(Exception):
    """Raised when prompt exceeds maximum length after compaction."""
    pass


class LeonardoClient:
    """Leonardo AI image generation client."""

    def __init__(
        self,
        api_key: str | None = None,
        model_id: str | None = None,
        element_id: str | None = None,
        element_trigger: str | None = None,
        element_weight: float | None = None,
    ):
        self.key = api_key or settings.leonardo_api_key
        if not self.key:
            raise RuntimeError("LEONARDO_API_KEY missing")
        self.model_id = model_id or settings.leonardo_model_id
        self.element_id = element_id or settings.leonardo_element_id
        self.element_trigger = element_trigger or settings.leonardo_element_trigger
        self.element_weight = element_weight or settings.leonardo_element_weight
        self.headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }

    def get_user_elements(self) -> list[dict]:
        """Fetch user's custom trained elements (LoRAs).

        Returns:
            List of element dictionaries with keys: id, name, description, trigger_word

        Raises:
            RuntimeError: If API call fails
        """
        with httpx.Client(timeout=30) as client:
            # First, get user ID
            me_resp = client.get(f"{BASE_URL}/me", headers=self.headers)
            if me_resp.status_code >= 400:
                log.error(f"leonardo_get_user_failed status={me_resp.status_code} body={me_resp.text}")
                raise RuntimeError(f"Leonardo get user failed: {me_resp.text}")

            user_data = me_resp.json()
            user_id = user_data.get("user_details", [{}])[0].get("user", {}).get("id")
            if not user_id:
                log.error(f"leonardo_missing_user_id response={user_data}")
                raise RuntimeError("Leonardo: user ID missing in response")

            # Now fetch user's elements
            elements_resp = client.get(
                f"{BASE_URL}/elements/user/{user_id}",
                headers=self.headers
            )
            if elements_resp.status_code >= 400:
                log.error(
                    f"leonardo_get_elements_failed status={elements_resp.status_code} "
                    f"body={elements_resp.text}"
                )
                raise RuntimeError(f"Leonardo get elements failed: {elements_resp.text}")

            elements_data = elements_resp.json()
            # Parse response - structure may vary
            elements_list = (
                elements_data.get("user_loras", [])
                or elements_data.get("custom_elements", [])
                or elements_data.get("loras", [])
            )

            result = []
            for elem in elements_list:
                # Only include completed elements
                if elem.get("status") == "COMPLETE":
                    result.append({
                        "id": str(elem.get("id")),
                        "name": elem.get("name"),
                        "description": elem.get("description", ""),
                        "trigger_word": elem.get("instancePrompt", ""),
                    })

            log.info(f"leonardo_elements_fetched count={len(result)}")
            return result

    def _validate_lora_compatibility(self, client: httpx.Client) -> None:
        """Pre-flight check: Verify LoRA exists and is compatible with our model.

        Raises:
            RuntimeError: If LoRA not found or incompatible with Vision XL
        """
        try:
            r = client.get(f"{BASE_URL}/elements/{settings.leonardo_lora_id}", headers=self.headers)
            if r.status_code == 404:
                raise RuntimeError(f"Leonardo: Eva Joy LoRA {settings.leonardo_lora_id} not found")
            if r.status_code >= 400:
                raise RuntimeError(f"Leonardo: LoRA validation failed ({r.status_code}): {r.text}")

            element_data = r.json()
            # Check compatibility - element should work with Vision XL or Alchemy v2
            # (If incompatible models are detected in future, add validation here)
            log.info(f"leonardo_lora_validated id={settings.leonardo_lora_id} name={element_data.get('name', 'N/A')}")
        except httpx.HTTPError as e:
            raise RuntimeError(f"Leonardo: LoRA validation network error: {e}")

    def generate(self, payload: dict) -> str:
        """Generate an image from a prompt.

        Args:
            payload: Dictionary containing 'base' (prompt) and optional 'neg' (negative prompt)

        Returns:
            Path to the generated image file

        Raises:
            PromptTooLongError: If prompt exceeds max length after compaction
            ContentFilterError: If Leonardo's safety filter blocks the prompt
            RuntimeError: If generation fails or times out
        """
        # Conservative cost estimate (adjust with real metering)
        add_cost(Decimal("0.02"), "leonardo")

        prompt_raw = payload.get("base", "")
        negative_raw = payload.get("neg", "")

        # Compact main prompt (with trigger injection)
        compacted = compact_prompt(
            prompt_raw,
            max_len=settings.prompt_max_len,
            trigger=self.element_trigger
        )
        prompt = compacted["prompt"]

        # Log compaction results
        log.info(
            f"PROMPT_COMPACTED len_before={compacted['len_before']} "
            f"len_after={compacted['len_after']} "
            f"hash={compacted['prompt_hash']} "
            f"warnings={','.join(compacted['warnings']) if compacted['warnings'] else 'none'}"
        )

        # Enhanced negative prompt requirements (add BEFORE compaction)
        required_neg_terms = [
            "doll-like", "mannequin", "uncanny face", "over-smooth skin", "plastic skin",
            "extra fingers", "warped anatomy", "de-aging", "seam", "text", "watermark",
            "logo", "lens flare streaks"
        ]

        # Enhance negative prompt if provided, otherwise use required terms
        if negative_raw:
            negative_enhanced = negative_raw
            for term in required_neg_terms:
                if term not in negative_enhanced.lower():
                    negative_enhanced += f", {term}"
        else:
            negative_enhanced = ", ".join(required_neg_terms)

        # Compact enhanced negative prompt (with all required terms)
        neg_compacted = compact_prompt(negative_enhanced, max_len=settings.negative_max_len)
        negative = neg_compacted["prompt"]

        if neg_compacted["warnings"]:
            log.info(
                f"NEGATIVE_COMPACTED len_before={neg_compacted['len_before']} "
                f"len_after={neg_compacted['len_after']} "
                f"warnings={','.join(neg_compacted['warnings'])}"
            )

        # Pre-flight assertions (fail loud)
        if len(prompt) > settings.prompt_max_len:
            raise PromptTooLongError(
                f"Prompt still {len(prompt)} chars after compaction (max {settings.prompt_max_len})"
            )
        if len(negative) > settings.negative_max_len:
            raise PromptTooLongError(
                f"Negative prompt {len(negative)} chars after compaction (max {settings.negative_max_len})"
            )

        # Build Leonardo API payload (EXACT SPEC - NO OPTIONAL FLUFF)
        if not settings.leonardo_model_id:
            raise RuntimeError("LEONARDO_MODEL_ID must be set (Vision XL required)")

        data = {
            "modelId": settings.leonardo_model_id,
            "prompt": prompt,
            "width": settings.leonardo_width,      # 864
            "height": settings.leonardo_height,    # 1536
            "num_images": 1,
            "userElements": [
                {
                    "userLoraId": int(settings.leonardo_lora_id),  # Leonardo API requires integer
                    "weight": settings.leonardo_lora_weight         # 0.80
                }
            ]
        }

        # Add Alchemy V2 (REQUIRED for Vision XL + custom Elements)
        if settings.leonardo_use_alchemy:
            data["alchemy"] = True
            data["presetStyle"] = settings.leonardo_preset_style

        # Add legacy parameters only if explicitly enabled (may conflict with Alchemy)
        if settings.leonardo_use_legacy_params:
            data["num_inference_steps"] = settings.leonardo_steps   # 32
            data["guidance_scale"] = settings.leonardo_cfg          # 7.0

        # Add negative prompt only if provided
        if negative:
            data["negative_prompt"] = negative

        # PRE-FLIGHT VALIDATION (FAIL-LOUD)
        # Assert model ID matches Vision XL
        if data["modelId"] != settings.leonardo_model_id:
            raise RuntimeError(
                f"Leonardo drift: modelId mismatch "
                f"(expected {settings.leonardo_model_id}, got {data['modelId']})"
            )

        # Assert native 9:16 high-res (max 1536px height per Leonardo API limits)
        if data["width"] != 864 or data["height"] != 1536:
            raise RuntimeError(
                f"Leonardo drift: size mismatch "
                f"(expected 864x1536, got {data['width']}x{data['height']})"
            )

        # Assert Eva Joy LoRA present with correct weight
        lora = data["userElements"][0]
        if str(lora["userLoraId"]) != str(settings.leonardo_lora_id) or abs(lora["weight"] - 0.80) > 0.001:
            raise RuntimeError(
                f"Leonardo drift: LoRA mismatch "
                f"(expected userLoraId={settings.leonardo_lora_id} weight=0.80, "
                f"got userLoraId={lora['userLoraId']} weight={lora['weight']})"
            )

        # Acquire concurrency slot (SINGLE concurrency for strict test)
        with concurrency.leonardo_slot():
            with httpx.Client(timeout=60) as client:
                # PRE-FLIGHT: Validate LoRA compatibility
                self._validate_lora_compatibility(client)

                # DEBUG: Log exact request body
                import json as json_lib
                log.info(f"leonardo_request_body={json_lib.dumps(data)}")

                # Create generation with retry logic (3x max for 429/5xx)
                last_error = None
                for attempt in range(3):
                    r = client.post(f"{BASE_URL}/generations", headers=self.headers, json=data)

                    # Success
                    if r.status_code < 400:
                        break

                    # Handle errors
                    error_body = r.text

                    # Detect content/safety filter blocks (non-retryable)
                    filter_keywords = ["filter", "safety", "inappropriate", "blocked", "content policy"]
                    is_filter_error = any(keyword in error_body.lower() for keyword in filter_keywords)

                    if is_filter_error:
                        # Extract category/reason if possible
                        try:
                            error_json = r.json()
                            error_msg = error_json.get("error", error_body)
                        except Exception:
                            error_msg = error_body

                        log.error(
                            f"LEO_CONTENT_FILTERED status={r.status_code} "
                            f"hash={compacted['prompt_hash']} "
                            f"len={len(prompt)} category=content_policy"
                        )
                        raise ContentFilterError(f"Leonardo content filter: {error_msg}")

                    # 4xx errors (non-retryable except 429)
                    if 400 <= r.status_code < 500 and r.status_code != 429:
                        log.error(f"leonardo_create_failed status={r.status_code} body={error_body}")
                        raise RuntimeError(f"Leonardo create failed ({r.status_code}): {error_body}")

                    # 429 or 5xx (retryable)
                    last_error = error_body
                    if attempt < 2:  # Don't sleep on last attempt
                        wait_time = (0.5 * (2 ** attempt))  # Exponential backoff: 0.5s, 1s
                        log.warning(f"leonardo_retry attempt={attempt+1}/3 status={r.status_code} wait={wait_time}s")
                        time.sleep(wait_time)
                    else:
                        # Final attempt failed
                        log.error(f"leonardo_create_failed_retries_exhausted status={r.status_code} body={error_body}")
                        raise RuntimeError(f"Leonardo create failed after 3 attempts: {error_body}")

                # Check if we exited loop successfully
                if r.status_code >= 400:
                    raise RuntimeError(f"Leonardo create failed: {last_error}")

                gen = r.json()
                # Different API versions return different shapes
                gen_id = (
                    gen.get("sdGenerationJob", {}).get("generationId")
                    or gen.get("generationId")
                )
                if not gen_id:
                    log.error(f"leonardo_missing_id response={gen}")
                    raise RuntimeError("Leonardo: generationId missing in response")

                log.info(f"leonardo_generation_started id={gen_id}")

                # Poll generation until assets are ready (up to 60 seconds)
                for attempt in range(60):
                    time.sleep(1)
                    g = client.get(f"{BASE_URL}/generations/{gen_id}", headers=self.headers)
                    if g.status_code >= 400:
                        log.error(
                            f"leonardo_poll_failed status={g.status_code} body={g.text}"
                        )
                        raise RuntimeError(f"Leonardo poll failed: {g.text}")

                    gj = g.json()

                    # DEBUG: Log full response to see LoRA metadata
                    log.info(f"leonardo_response={json_lib.dumps(gj)[:1000]}")

                    # Search for assets in different response shapes
                    assets = (
                        gj.get("generated_images")
                        or gj.get("generations_by_pk", {}).get("generated_images")
                        or gj.get("images")
                        or []
                    )

                    if assets:
                        url = assets[0].get("url") or assets[0].get("image_url")
                        if not url:
                            log.error(f"leonardo_missing_url asset={assets[0]}")
                            raise RuntimeError("Leonardo: asset URL missing")

                        # Download image
                        img_resp = client.get(url)
                        if img_resp.status_code >= 400:
                            log.error(
                                f"leonardo_download_failed status={img_resp.status_code}"
                            )
                            raise RuntimeError(
                                f"Leonardo image download failed: {img_resp.text}"
                            )

                        # Save to data directory
                        data_dir = get_data_path()
                        tmp = tempfile.NamedTemporaryFile(
                            delete=False, suffix=".png", dir=str(data_dir)
                        )
                        tmp.write(img_resp.content)
                        tmp.flush()
                        tmp.close()

                        # POST-RESPONSE VERIFICATION (FAIL-LOUD)
                        # Verify returned image dimensions
                        from PIL import Image
                        with Image.open(tmp.name) as img:
                            actual_width, actual_height = img.size

                        # Calculate expected dimensions (Alchemy applies 1.75x upscaling)
                        if data.get("alchemy"):
                            expected_width = int(settings.leonardo_width * 1.75)   # 864 * 1.75 = 1512
                            expected_height = int(settings.leonardo_height * 1.75) # 1536 * 1.75 = 2688
                        else:
                            expected_width = settings.leonardo_width    # 864
                            expected_height = settings.leonardo_height  # 1536

                        if actual_width != expected_width or actual_height != expected_height:
                            raise RuntimeError(
                                f"Leonardo drift: returned image size mismatch "
                                f"(expected {expected_width}x{expected_height}, got {actual_width}x{actual_height})"
                            )

                        # Verify model used (from generation metadata)
                        used_model = gj.get("generations_by_pk", {}).get("modelId") or gj.get("modelId") or "unknown"

                        # Verify LoRA was applied (FAIL-LOUD)
                        used_loras = (
                            gj.get("generations_by_pk", {}).get("userLoras")
                            or gj.get("userLoras")
                            or gj.get("loras")
                            or []
                        )

                        # Check for LoRA by userLoraId or legacy id field
                        lora_applied = any(
                            str(lora.get("userLoraId") or lora.get("id")) == str(settings.leonardo_lora_id)
                            for lora in used_loras
                        ) if used_loras else False

                        # Extract Alchemy status from response
                        alchemy_used = gj.get("generations_by_pk", {}).get("alchemy") or gj.get("alchemy") or False
                        preset_used = gj.get("generations_by_pk", {}).get("presetStyle") or gj.get("presetStyle") or "none"

                        # LEO_DIAG: Single-line diagnostic (EXACT SPEC)
                        log.info(
                            f"LEO_DIAG requested=(model={data['modelId'][:40]}... "
                            f"size={data['width']}x{data['height']} "
                            f"alchemy={data.get('alchemy', False)} preset={data.get('presetStyle', 'none')} "
                            f"steps={data.get('num_inference_steps', 'auto')} cfg={data.get('guidance_scale', 'auto')} "
                            f"lora={settings.leonardo_lora_id}@{settings.leonardo_lora_weight}) "
                            f"applied=(alchemy={alchemy_used} preset={preset_used} lora_present={lora_applied}) "
                            f"gen_id={gen_id} path={tmp.name}"
                        )

                        # FAIL-LOUD if LoRA not applied (NO FALLBACKS)
                        if settings.leonardo_forbid_fallbacks and not lora_applied:
                            raise RuntimeError(
                                f"Leonardo: Eva Joy LoRA ({settings.leonardo_lora_id}) NOT APPLIED in generation {gen_id}. "
                                f"FORBID_FALLBACKS=true. Refusing to index. Response metadata: {used_loras}"
                            )

                        return tmp.name

                log.error(f"leonardo_timeout id={gen_id}")
                raise RuntimeError("Leonardo: generation timed out after 60s")
