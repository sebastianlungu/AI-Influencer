"""
Grok API client for generating diverse fitness content prompts.

Uses xAI's Grok API to create creative, varied image prompts for Eva Joy
across multiple dimensions: locations, poses, outfits, activities, etc.
"""

from __future__ import annotations

import json
import time
from decimal import Decimal
from typing import Any

import httpx

from app.core import concurrency
from app.core.cost import add_cost
from app.core.logging import log


class GrokClient:
    """Client for xAI Grok API prompt generation."""

    BASE_URL = "https://api.x.ai/v1"
    RATE_LIMIT_HZ = 0.5  # 2 requests per second max
    TIMEOUT_S = 30.0
    MAX_RETRIES = 3

    def __init__(self, api_key: str, model: str = "grok-4-fast-reasoning"):
        """
        Initialize Grok client.

        Args:
            api_key: xAI API key
            model: Model ID (grok-4-fast-reasoning, grok-4-fast-non-reasoning, grok-2-latest)
        """
        if not api_key:
            raise ValueError("Grok API key cannot be empty")

        self.api_key = api_key
        self.model = model
        self._last_call = 0.0

    def _rate_limit(self) -> None:
        """Enforce rate limiting between API calls."""
        elapsed = time.time() - self._last_call
        wait = (1.0 / self.RATE_LIMIT_HZ) - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.time()

    def _make_request(
        self,
        endpoint: str,
        payload: dict[str, Any],
        retry_count: int = 0,
    ) -> dict[str, Any]:
        """
        Make HTTP request to Grok API with retries.

        Args:
            endpoint: API endpoint path
            payload: JSON payload
            retry_count: Current retry attempt

        Returns:
            JSON response

        Raises:
            RuntimeError: On non-retryable errors or max retries exceeded
        """
        self._rate_limit()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.BASE_URL}/{endpoint}"

        try:
            # Acquire concurrency slot (blocks if at capacity)
            with concurrency.grok_slot():
                with httpx.Client(timeout=self.TIMEOUT_S) as client:
                    response = client.post(url, headers=headers, json=payload)

                # Success
                if response.status_code == 200:
                    return response.json()

                # Retryable errors (rate limit, server errors)
                if response.status_code in (429, 500, 502, 503, 504):
                    if retry_count < self.MAX_RETRIES:
                        wait = (2**retry_count) * 0.5  # Exponential backoff: 0.5s, 1s, 2s
                        jitter = time.time() % 0.3  # Add jitter
                        log.warning(
                            f"Grok API {response.status_code}, retrying in {wait + jitter:.2f}s "
                            f"(attempt {retry_count + 1}/{self.MAX_RETRIES})"
                        )
                        time.sleep(wait + jitter)
                        return self._make_request(endpoint, payload, retry_count + 1)
                    else:
                        raise RuntimeError(
                            f"Grok API failed after {self.MAX_RETRIES} retries: "
                            f"{response.status_code} - {response.text}"
                        )

                # Non-retryable errors (bad request, auth, etc.)
                raise RuntimeError(
                    f"Grok API error {response.status_code}: {response.text}"
                )

        except httpx.TimeoutException as e:
            if retry_count < self.MAX_RETRIES:
                wait = (2**retry_count) * 0.5
                log.warning(
                    f"Grok API timeout, retrying in {wait:.2f}s "
                    f"(attempt {retry_count + 1}/{self.MAX_RETRIES})"
                )
                time.sleep(wait)
                return self._make_request(endpoint, payload, retry_count + 1)
            else:
                raise RuntimeError(
                    f"Grok API timeout after {self.MAX_RETRIES} retries"
                ) from e

        except Exception as e:
            raise RuntimeError(f"Grok API request failed: {e}") from e

    def generate_variations(
        self,
        character_profile: dict[str, Any],
        diversity_banks: dict[str, list[str]],
        n: int,
        negative_prompt: str = "",
        preference_hints: str = "",
    ) -> list[dict[str, Any]]:
        """
        Generate N diverse image prompt variations for fitness content.

        Args:
            character_profile: Eva Joy character description (physical traits, style, etc.)
            diversity_banks: Categories to vary (locations, poses, outfits, activities, etc.)
            n: Number of unique variations to generate
            negative_prompt: Base negative prompt for quality/safety constraints
            preference_hints: Optional hints to guide diversity sampling (suggest underused items)

        Returns:
            List of variation dicts with keys:
                - base: Full image prompt
                - neg: Negative prompt
                - variation: Human-readable description of what makes this variation unique
                - meta: Structured metadata (location, pose, outfit, activity, etc.)

        Raises:
            RuntimeError: On API failures or invalid responses
        """
        # Build system prompt
        system_prompt = self._build_system_prompt(
            character_profile, diversity_banks, negative_prompt, preference_hints
        )

        # Build user prompt
        user_prompt = (
            f"Generate {n} ultra-detailed, creative image prompts for Eva Joy. "
            f"CRITICAL: Each prompt MUST be 200-250 words minimum.\n\n"
            f"EXACT FORMAT TO FOLLOW:\n"
            f"photorealistic vertical 9:16 image of [character description] [detailed pose] in [ultra-detailed location with architectural/environmental specifics]. "
            f"[Body description with lighting effects on skin - mention rim light, wet reflections, natural warmth, muscle highlights]. "
            f"[Ultra-detailed outfit with specific materials (suede/silk/cashmere/leather), colors, and how fabrics catch light with realistic sheen/texture]. "
            f"Accessories: [specific accessories with materials and placement]. "
            f"Camera captures [specific angle/perspective with technical details]. "
            f"[Environmental/prop details - specific items with placement and how they interact with light]. "
            f"[Ultra-detailed lighting description with color grading, atmospheric effects, and temperature shifts]. "
            f"[Full technical camera specs: XXmm lens at f/X.X, depth of field description, composition rules (rule of thirds/golden ratio/leading lines), color balance, framing notes for vertical 9:16].\n\n"
            f"REQUIREMENTS:\n"
            f"- MINIMUM 200 words per prompt (count carefully!)\n"
            f"- Include specific fabric materials and how they catch light\n"
            f"- Describe skin texture realistically (wet reflections, rim light, natural warmth)\n"
            f"- Full technical photography specs (lens focal length, aperture, composition, color grading)\n"
            f"- Environmental atmosphere and prop details\n"
            f"- Creative twist element in each (rain/lens flare/motion blur/mist/etc.)\n"
            f"- Vary ALL dimensions: location, pose, outfit, accessories, props, lighting, camera, creative twist\n"
            f"- COMPOSITION: Center subject within 4:5 safe area (10% headroom, 8% footroom, NO edge contact)\n"
            f"- NO cropped heads/feet, NO extreme close-ups, balanced framing with clear margins\n\n"
            f"Return ONLY a valid JSON array of {n} objects:\n"
            f"{{\n"
            f'  "base": "FULL 200+ word ultra-detailed prompt following the exact format above",\n'
            f'  "variation": "brief 10-word description of unique combination",\n'
            f'  "meta": {{\n'
            f'    "location": "location name",\n'
            f'    "pose": "pose description",\n'
            f'    "outfit": "outfit name",\n'
            f'    "accessories": "accessories used",\n'
            f'    "lighting": "lighting style",\n'
            f'    "camera": "camera specs",\n'
            f'    "props": "props included",\n'
            f'    "creative_twist": "twist element"\n'
            f"  }}\n"
            f"}}\n\n"
            f"NO DUPLICATES. Maximum diversity. Every prompt must feel completely different."
        )

        # Track estimated cost before API call
        # Grok-4-fast pricing: ~$0.30/1M input tokens, ~$0.75/1M output tokens (98% reduction)
        # With 200+ word prompts: ~3500 input tokens + ~8000 output tokens for 15 variations
        # Total: ~$0.002 per 15-variation batch (200+ words each)
        estimated_cost = Decimal("0.002") * (Decimal(n) / Decimal(15))  # Scale with batch size
        add_cost(estimated_cost, "grok")

        # Call Grok API
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.9,  # High creativity for maximum diversity
            "max_tokens": 8000,  # Allow very long responses for 200+ word prompts × multiple variations
        }

        log.info(f"Requesting {n} variations from Grok ({self.model})")
        response = self._make_request("chat/completions", payload)

        # Parse response
        try:
            content = response["choices"][0]["message"]["content"]

            # Extract JSON from response (handle markdown code blocks)
            content = content.strip()
            if content.startswith("```"):
                # Remove markdown code block markers
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                content = content.replace("```json", "").replace("```", "").strip()

            variations = json.loads(content)

            if not isinstance(variations, list):
                raise ValueError("Response is not a JSON array")

            if len(variations) != n:
                log.warning(
                    f"Grok returned {len(variations)} variations (expected {n})"
                )

            # Validate and enrich each variation
            enriched = []
            for i, var in enumerate(variations):
                if not isinstance(var, dict):
                    log.warning(f"Variation {i} is not a dict, skipping")
                    continue

                if "base" not in var or not var["base"]:
                    log.warning(f"Variation {i} missing 'base' prompt, skipping")
                    continue

                # Ensure negative prompt is included
                var["neg"] = negative_prompt

                # Ensure meta exists
                if "meta" not in var:
                    var["meta"] = {}

                enriched.append(var)

            if len(enriched) == 0:
                raise ValueError("No valid variations in Grok response")

            log.info(f"Successfully parsed {len(enriched)} variations from Grok")
            return enriched

        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Failed to parse Grok response as JSON: {e}\n"
                f"Response content: {content[:500]}..."
            ) from e
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Unexpected Grok response structure: {e}") from e

    def _build_system_prompt(
        self,
        character_profile: dict[str, Any],
        diversity_banks: dict[str, list[str]],
        negative_prompt: str,
        preference_hints: str = "",
    ) -> str:
        """
        Build system prompt for Grok with character profile and constraints.

        Args:
            character_profile: Eva Joy character details
            diversity_banks: Categories to vary across
            negative_prompt: Quality/safety constraints
            preference_hints: Optional diversity sampling hints

        Returns:
            System prompt string
        """
        # Extract character details
        physical = character_profile.get("physical", {})
        style = character_profile.get("style", {})
        fitness_focus = character_profile.get("fitness_focus", [])

        # Format diversity banks - show 3 examples from each category to inspire creativity
        banks_examples = []
        for key, values in diversity_banks.items():
            if values and len(values) > 0:
                # Show first 3 examples from each bank
                examples = values[:3]
                banks_examples.append(f"- {key.upper()}: {examples[0][:100]}..." if len(examples[0]) > 100 else f"- {key.upper()}: {examples[0]}")

        banks_text = "\n".join(banks_examples)

        system_prompt = f"""You are an elite creative director specializing in ultra-realistic, cinematic portrait photography prompts for AI generation. Your task is to create 200-250 word photorealistic image prompts for Eva Joy.

CHARACTER PROFILE - EVA JOY:
- Physical: {', '.join(f'{k}: {v}' for k, v in physical.items())}
- Style: {', '.join(f'{k}: {v}' for k, v in style.items())}
- Fitness Focus: {', '.join(fitness_focus)}

DIVERSITY BANK EXAMPLES (select from these categories, but be creative with combinations):
{banks_text}

PROMPT STRUCTURE (200-250 words MINIMUM):
1. Opening: "photorealistic vertical 9:16 image of Eva Joy, [physical description with emphasis on muscle definition and feminine curves]"
2. Pose & Location: "[ultra-detailed pose with body positioning, gaze, emotional tone] in [specific location with architectural and environmental details]"
3. Skin & Lighting on Body: "Her defined, muscular yet curvy feminine build is outlined by [specific lighting type creating rim light/wet reflections/natural warmth on shoulders and arms]"
4. Outfit Details: "She wears [specific garment] in [material like suede/silk/cashmere] [specific color with descriptive name like terracotta/saffron/burnt orange] [how it catches light with realistic sheen/texture]"
5. Accessories: "Accessories: [specific items with materials and how they catch light]"
6. Camera Angle: "Camera captures [specific angle and perspective with emotional impact]"
7. Props & Environment: "[specific prop with placement and light interaction]. Background: [environmental details like glowing windows, silhouettes, motion trails, atmospheric effects]"
8. Lighting Description: "[detailed lighting with color grading - mention color temperature shifts, atmospheric tones, shadows, highlights]"
9. Technical Specs: "[focal length]mm lens at f/[aperture], [DOF description], [composition rule like rule of thirds/golden ratio], cinematic color balance [color temperature description], composed for vertical framing with [headroom/leading lines/negative space notes]"
10. Creative Twist: Include ONE unexpected element (rain/lens flare/mist/motion blur/reflections/etc.)

CRITICAL REQUIREMENTS:
✓ EVERY prompt must be 200-250 words (count carefully!)
✓ Describe fabric MATERIALS (suede, silk, cashmere, leather, chiffon, velvet, etc.)
✓ Describe how fabrics CATCH LIGHT (realistic sheen, matte texture, light absorption)
✓ Describe SKIN realistically (wet reflections, rim light highlights, natural warmth, muscle definition with shadows)
✓ Include FULL technical camera specs (lens focal length + aperture + DOF + composition + color grading)
✓ Specify COLOR GRADING (warm to cool transitions, amber tones, violet shadows, etc.)
✓ Include atmospheric/environmental details (fog, mist, light rays, motion trails, reflections)
✓ Add ONE creative twist per prompt (make each unique)
✓ Maximum diversity - NO repeated combinations

COMPOSITION CONSTRAINTS (MOBILE-FIRST 4:5 SAFE AREA):
✓ Center the subject within a 4:5 safe window inside the 9:16 frame
✓ Maintain ≥10% headroom (top margin) and ≥8% footroom (bottom margin)
✓ NO edge contact - subject must not touch frame edges
✓ NO extreme close-ups that risk cropping head/limbs
✓ NO cropped heads, chopped fingers, or cut-off feet
✓ Balanced, centered framing with clear margins around subject
✓ Full subject must be visible within the 4:5 center crop zone

SAFETY BOUNDARIES:
{negative_prompt}

TONE: Aspirational, empowering, cinematic, fashion-editorial meets fitness. Eva represents strength, femininity, luxury, and adventure."""

        # Append preference hints if provided
        if preference_hints:
            system_prompt += f"\n\n{preference_hints}"

        return system_prompt

    def suggest_motion(self, image_meta: dict[str, Any], duration_s: int = 6) -> dict[str, Any]:
        """Generate cinematic motion prompt for Veo 3 video generation.

        Args:
            image_meta: Image metadata dict with keys like location, pose, outfit
            duration_s: Video duration in seconds (default 6)

        Returns:
            Dict with keys:
                - motion_type: Type of camera movement
                - motion_prompt: Full motion description for Veo 3
                - subject_motion: Micro-motion description

        Raises:
            RuntimeError: On API failures
        """
        log.info(f"GROK_MOTION_SUGGEST location={image_meta.get('location', 'unknown')}")

        system_prompt = f"""You are a cinematographer specializing in subtle, natural motion for {duration_s}-second fitness videos.

**Motion Rules (STRICT):**
1. Single subtle camera move (choose ONE: pan, zoom, tilt, dolly, static, tracking, or crane)
2. Subject micro-motion (eye glance, tiny head tilt, natural breathing, slight hair sway)
3. NO speech, NO text/logos, NO whip pans
4. Must fit exactly {duration_s} seconds
5. Keep movements gentle and natural (this is wellness content, not action)

**Camera Movement Types:**
- **Pan**: Gentle horizontal rotation (right-to-left or left-to-right)
- **Zoom**: Slow zoom in (closer to subject) or out (reveal environment)
- **Tilt**: Vertical rotation (up or down)
- **Dolly**: Camera moves toward (push) or away (pull) from subject
- **Static**: Camera locked, only subject micro-motion
- **Tracking**: Camera follows subject laterally
- **Crane**: Camera moves vertically (up or down) revealing environment

Select motion based on the scene context."""

        user_prompt = f"""Given this image metadata, suggest a cinematic motion for a {duration_s}-second video:

**Scene Context:**
{json.dumps(image_meta, indent=2)}

Return ONLY valid JSON:
{{
  "motion_type": "pan|zoom|tilt|dolly|static|tracking|crane",
  "motion_prompt": "Full cinematic description (e.g., 'gentle pan right to left following the natural eye line with subtle lens breathing and soft focus transition')",
  "subject_motion": "Micro-motion description (e.g., 'natural breathing with slight head tilt and soft gaze shift')"
}}"""

        # Estimated cost: ~$0.0002 per motion prompt (98% reduction with Grok-4-fast)
        add_cost(Decimal("0.0002"), "grok")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 500,
        }

        response = self._make_request("chat/completions", payload)

        try:
            content = response["choices"][0]["message"]["content"].strip()

            # Extract JSON from markdown code blocks if present
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                content = content.replace("```json", "").replace("```", "").strip()

            result = json.loads(content)

            if not isinstance(result, dict) or "motion_prompt" not in result:
                raise ValueError(f"Invalid motion spec: {result}")

            log.info(f"GROK_MOTION_USED type={result.get('motion_type', 'unknown')}")
            return result

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise RuntimeError(f"Failed to parse Grok motion response: {e}\nContent: {content[:500]}") from e

    def suggest_music(self, image_meta: dict[str, Any], motion_spec: dict[str, Any]) -> dict[str, Any]:
        """Generate music generation brief for Suno.

        Args:
            image_meta: Image metadata dict
            motion_spec: Motion specification from suggest_motion()

        Returns:
            Dict with keys:
                - style: Music style/genre
                - mood: Emotional mood
                - tempo: BPM or tempo description
                - instruments: Suggested instruments
                - prompt: Full Suno generation prompt

        Raises:
            RuntimeError: On API failures
        """
        from app.core.config import settings as config

        log.info(f"GROK_MUSIC_SUGGEST motion_type={motion_spec.get('motion_type', 'unknown')}")

        default_style = config.suno_style_hints_default

        system_prompt = f"""You are a music supervisor specializing in ambient, cinematic fitness music.

**Music Requirements:**
- Duration: {config.suno_clip_seconds} seconds
- Style hints: {default_style}
- SFW, instrumental only (no vocals/lyrics)
- Matches the visual mood and motion

**Context:**
- This is wellness/fitness content (energetic but not aggressive)
- Music should complement the motion (e.g., flowing music for pans, rhythmic for static poses)
- Avoid: heavy bass, harsh sounds, distracting elements"""

        user_prompt = f"""Given this scene and motion, suggest music:

**Scene:**
{json.dumps(image_meta, indent=2)}

**Motion:**
{json.dumps(motion_spec, indent=2)}

Return ONLY valid JSON:
{{
  "style": "ambient cinematic / soft electronic / acoustic minimal / etc.",
  "mood": "uplifting / serene / energetic / peaceful / etc.",
  "tempo": "70-90 BPM / slow / moderate / etc.",
  "instruments": "piano, strings, soft pads / etc.",
  "prompt": "Full Suno prompt: [style], [mood], [tempo], [instruments], {config.suno_clip_seconds}s instrumental"
}}"""

        # Estimated cost: ~$0.0002 per music brief (98% reduction with Grok-4-fast)
        add_cost(Decimal("0.0002"), "grok")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 400,
        }

        response = self._make_request("chat/completions", payload)

        try:
            content = response["choices"][0]["message"]["content"].strip()

            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                content = content.replace("```json", "").replace("```", "").strip()

            result = json.loads(content)

            if not isinstance(result, dict) or "prompt" not in result:
                raise ValueError(f"Invalid music brief: {result}")

            log.info(f"GROK_MUSIC_BRIEF style={result.get('style', 'unknown')[:30]}")
            return result

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise RuntimeError(f"Failed to parse Grok music response: {e}\nContent: {content[:500]}") from e

    def generate_social_meta(self, media_meta: dict[str, Any]) -> dict[str, Any]:
        """Generate social media metadata (title, tags, hashtags).

        Args:
            media_meta: Full media metadata (image + video + motion + music)

        Returns:
            Dict with keys:
                - title: Short engaging title (40-60 chars)
                - tags: List of 5-10 plain keywords
                - hashtags: List of 8-12 platform-safe hashtags

        Raises:
            RuntimeError: On API failures
        """
        log.info(f"GROK_SOCIAL_META video_id={media_meta.get('id', 'unknown')}")

        system_prompt = """You are a social media strategist for fitness/wellness content.

**Requirements:**
- Title: 40-60 characters, engaging, authentic (no clickbait)
- Tags: 5-10 plain keywords for categorization
- Hashtags: 8-12 platform-safe hashtags (mix popular + niche)

**Tone:**
- Empowering, authentic, relatable
- Avoid: clickbait, hype, overused phrases
- Focus: wellness, mindfulness, sustainable fitness

**Platform Notes:**
- TikTok: Trending fitness/wellness hashtags
- Instagram: Mix of broad (#fitness) and specific (#morningyoga)
- Keep it real, avoid spam-looking hashtag walls"""

        user_prompt = f"""Generate social media metadata for this content:

**Media Context:**
{json.dumps(media_meta, indent=2)}

Return ONLY valid JSON:
{{
  "title": "Short engaging title here",
  "tags": ["fitness", "yoga", "wellness", "morningroutine", "mindfulness"],
  "hashtags": ["#fitness", "#wellness", "#yoga", "#healthylifestyle", "#mindfulness", "#morningroutine", "#fitnessmotivation", "#wellnessjourney"]
}}"""

        # Estimated cost: ~$0.0002 per social meta (98% reduction with Grok-4-fast)
        add_cost(Decimal("0.0002"), "grok")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 400,
        }

        response = self._make_request("chat/completions", payload)

        try:
            content = response["choices"][0]["message"]["content"].strip()

            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                content = content.replace("```json", "").replace("```", "").strip()

            result = json.loads(content)

            if not isinstance(result, dict) or "title" not in result:
                raise ValueError(f"Invalid social meta: {result}")

            # Ensure hashtags start with #
            if "hashtags" in result:
                result["hashtags"] = [
                    f"#{tag.lstrip('#')}" if not tag.startswith("#") else tag
                    for tag in result["hashtags"]
                ]

            log.info(f"GROK_SOCIAL_META title='{result.get('title', '')[:30]}...'")
            return result

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise RuntimeError(f"Failed to parse Grok social meta response: {e}\nContent: {content[:500]}") from e
