"""
Grok API client for generating diverse fitness content prompts.

Uses xAI's Grok API to create creative, varied image prompts for Eva Joy
across multiple dimensions: locations, poses, outfits, activities, etc.
"""

from __future__ import annotations

import json
import re  # Keep this import even though not used directly in this module
import time
from decimal import Decimal
from typing import Any

import httpx

from app.core import concurrency
from app.core.cost import add_cost
from app.core.logging import log
from app.core.variety_tracker import get_recent_location_strings


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

    def generate_prompt_bundle(
        self,
        setting: str,
        seed_words: list[str] | None = None,
        count: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Generate prompt bundles (image + video prompts) for manual generation workflow.

        Args:
            setting: High-level setting input (e.g., "Japan", "Santorini")
            seed_words: Optional embellisher keywords
            count: Number of prompt bundles to generate (1-10)

        Returns:
            List of dicts with keys:
                - id: Unique prompt bundle ID (pr_...)
                - image_prompt: Dict with final_prompt, negative_prompt, width, height
                - video_prompt: Dict with motion, character_action, environment, duration_seconds, notes

        Raises:
            RuntimeError: On API failures or invalid config files
        """
        from app.core.config import settings as config
        from app.core.paths import get_data_path

        # Load persona and variety bank
        try:
            persona_path = get_data_path("persona.json")
            variety_path = get_data_path("variety_bank.json")
            with open(persona_path, "r", encoding="utf-8") as f:
                persona = json.load(f)
            with open(variety_path, "r", encoding="utf-8") as f:
                variety_bank = json.load(f)
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Missing config file: {e.filename}. "
                f"Ensure persona.json and variety_bank.json exist."
            ) from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in config file: {e}") from e

        log.info(f"GROK_PROMPT_BUNDLE setting={setting} seed_words={seed_words} count={count}")

        # Build system prompt
        try:
            import traceback
            log.info("DEBUG: About to build system prompt")
            system_prompt = self._build_prompt_bundle_system(persona, variety_bank)
            log.info("DEBUG: System prompt built successfully")
        except Exception as e:
            tb = traceback.format_exc()
            log.error(f"ERROR building system prompt: {e}\n{tb}")
            raise

        # Build user prompt with dynamic appearance
        seed_text = f" (embellish with: {', '.join(seed_words)})" if seed_words else ""

        # Build appearance descriptor from persona.json (same as system prompt)
        appearance = (
            f"{persona.get('hair', 'medium wavy blonde hair')}, "
            f"{persona.get('eyes', 'saturated blue eyes')}, "
            f"{persona.get('body', 'busty muscular curvy physique with defined abs, legs, and arms')}, "
            f"{persona.get('skin', 'sun-kissed realistic glowing skin with high radiant complexion and natural wet highlights')}"
        )

        user_prompt = f"""Generate {count} prompt bundle(s) for setting: "{setting}"{seed_text}

Each bundle MUST include:
1. **Image Prompt**: Photorealistic glamour portrait with diverse attributes
2. **Video Prompt**: Paired 6-second motion prompt for the same scene

Return ONLY valid JSON array of {count} object(s). Example final_prompt format - THIS MUST BE YOUR TEMPLATE (1200-1450 characters, comprehensive):
{{
  "image_prompt": {{
    "final_prompt": "photorealistic vertical 9:16 image of a 28-years-old woman with {appearance}, captured in medium shot (waist up) at a luxury Tokyo penthouse rooftop infinity pool at dusk, city skyline glittering below, modern glass railings. Camera: 50mm f/2.0 from subtle high beauty angle. She wears orchid-purple strappy sports bra with criss-cross back detailing and matching high-cut micro thong-style workout shorts with sheer mesh side panels; accessories include delicate layered gold necklaces, diamond tennis bracelet on right wrist, rose-gold anklet. Pose: leaning forward with torso bent 30 degrees, right hand on pool edge, left hand running through windblown hair, shoulders angled diagonal, weight on left hip with right leg bent and heel lifted, sultry playful expression with half-smile and direct gaze. Post-workout skin with dewy moisture sheen and specular highlights on cheekbones, collarbones, shoulders, upper chest. Lighting: golden hour backlight creates warm rim glow on right side, soft bounce fill from left, city lights bokeh adds depth. Environment: crystalline pool water with ripples, Tokyo skyline with illuminated skyscrapers in soft focus, wispy sunset clouds. Colors: warm golden sunset with coral and amber mixing with cool steel-blue shadows and orchid purple wardrobe. Composition: subject on right third, minimal headroom, diagonal body line, 9:16 mobile framing",
    "negative_prompt": "[concatenated persona.dont + variety_bank.negative, deduped]",
    "width": 864,
    "height": 1536
  }},
  "video_prompt": {{
    "motion": "gentle push-in with subtle tilt",
    "character_action": "sultry glance shifting from pool to camera, fingers running through hair",
    "environment": "infinity pool ripples catching golden hour light, Tokyo skyline bokeh",
    "duration_seconds": 6,
    "notes": "emphasize confident allure and luxury setting ambience"
  }}
}}

MANDATORY REQUIREMENTS - EVERY PROMPT MUST INCLUDE ALL OF THESE:

1. **OPENING FORMAT** (use appearance descriptor):
   "photorealistic vertical 9:16 image of a 28-years-old woman with {appearance}, captured in [SHOT TYPE] at [COMBINED SETTING + SCENE]"

   Where appearance = {appearance}

2. **SHOT TYPE** (rotate for variety - MUST specify one):
   - Close-up portrait: face and shoulders only, emphasis on expression
   - Medium shot: waist up, showing pose and wardrobe
   - 3/4 body: thighs up, full outfit visible
   - Full body: head to toe, environment context

3. **SETTING + SCENE COMBINATION** (REQUIRED - two-part system):
   - **SETTING**: Choose broad geographic location (Japan, Greece, Indonesia, United States, etc.)
   - **SCENE**: Choose or create specific detailed environment with atmosphere and visual details
   - **COMBINE**: Merge setting with scene, adding city/region specificity

   Examples:
   • "Japan" + "luxury penthouse rooftop infinity pool at dusk" → "at a luxury Tokyo penthouse rooftop infinity pool at dusk, city skyline glittering below, modern glass railings"
   • "Greece" + "whitewashed cliffside terrace overlooking turquoise sea" → "at a whitewashed Santorini cliffside terrace overlooking turquoise Aegean sea, blue-domed chapel in soft-focus background"
   • "Indonesia" + "beachfront villa deck" → "at a sun-drenched Bali beachfront villa deck with teak flooring, infinity pool merging with ocean horizon, tropical palms swaying"

4. **CAMERA TECHNICAL** (REQUIRED):
   - Specific lens: 35mm / 50mm / 85mm
   - Aperture: f/1.8 / f/2.0 / f/2.8
   - Angle: low angle hero / high beauty angle / Dutch tilt / eye-level intimate / side profile
   - Include technical composition notes

5. **WARDROBE** (REQUIRED - comprehensive description):
   - Base garment with "micro" prefix: micro-crop / micro-shorts / micro-bra / barely-there bikini
   - Color and fabric details: "champagne satin" / "sheer mesh" / "metallic rose-gold"
   - Fit and revealing details: "underboob cutout" / "plunging neckline" / "side cutouts" / "thong-cut"
   - Must describe completely, not just name the item

6. **ACCESSORIES** (REQUIRED - select 2-3):
   - Choose from: minimalist gold studs, delicate layered necklaces, rose-gold chain anklet, thin diamond tennis bracelet, oversized sunglasses, dainty belly chain, gold hoop earrings, gemstone body jewelry, silk hair ribbon, pearl drop earrings, stack of thin bangles, leather wrap bracelet

7. **POSE & BODY MECHANICS** (REQUIRED - ultra-detailed):
   - Specific body position: leaning forward / kneeling / lying on side / standing
   - Body mechanics: torso angle, weight distribution, limb placement (be precise: "torso bent at 30 degrees, right elbow on knee")
   - Micro-action: hair flip / adjusting strap / stretching / over-shoulder glance
   - Expression: sultry / playful / confident / intense
   - Gaze direction: to camera / away / over shoulder / downward

8. **SKIN REALISM** (REQUIRED):
   - "realistic wet skin with strong specular highlights across cheekbones, collarbones, shoulders" OR
   - "post-workout dewy moisture sheen" OR
   - "tan oil sheen with golden glow"
   - Must mention specific body areas catching light

9. **LIGHTING SETUP** (REQUIRED - multi-source with directions):
   - Primary source: golden hour backlight / window key from left / studio beauty light
   - Secondary source: bounce fill / rim light / environmental ambient
   - Direction and effect: "creates warm rim glow along right side", "separates subject from background"
   - Must describe 3-4 light sources with spatial details

10. **ENVIRONMENT DETAILS** (REQUIRED - 3-4 specific elements):
    - NOT generic ("beautiful beach") but specific ("crystalline infinity pool water with gentle ripples")
    - Include foreground, midground, background elements
    - Tie to setting expansion

11. **COLOR PALETTE** (REQUIRED):
    - Overall color scheme from variety bank: "warm golden sunset with coral accents" / "cool steel-blue ambient with bronze highlights"
    - How it ties together: wardrobe + lighting + environment

12. **COMPOSITION & FRAMING** (REQUIRED):
    - Rule of thirds positioning
    - Headroom/negative space
    - Diagonal lines or visual flow
    - Social-media vertical framing notes
    - Safe zones for 9:16 mobile viewing

**TARGET LENGTH**: 300-500 words per final_prompt - be comprehensive and holistic

**VARIETY**: Rotate ALL elements across multiple generations - shot types, settings, wardrobes, poses, lighting, angles

**FORBIDDEN**: "NATIVE 9:16", resolution text, "evajoy", LoRA names, identity triggers"""

        # Estimated cost: ~$0.001 per bundle (smaller than full variation gen)
        estimated_cost = Decimal("0.001") * Decimal(count)
        add_cost(estimated_cost, "grok")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.9,  # High creativity for diversity
            "max_tokens": 3000,
        }

        response = self._make_request("chat/completions", payload)

        try:
            content = response["choices"][0]["message"]["content"].strip()

            # Extract JSON from markdown code blocks
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                content = content.replace("```json", "").replace("```", "").strip()

            bundles = json.loads(content)

            if not isinstance(bundles, list):
                raise ValueError("Response is not a JSON array")

            # Validate and enrich each bundle
            enriched = []
            for i, bundle in enumerate(bundles):
                if not isinstance(bundle, dict):
                    log.warning(f"Bundle {i} is not a dict, skipping")
                    continue

                if "image_prompt" not in bundle or "video_prompt" not in bundle:
                    log.warning(f"Bundle {i} missing image_prompt or video_prompt, skipping")
                    continue

                # Validate dimensions
                img = bundle["image_prompt"]
                if img.get("width") != 864 or img.get("height") != 1536:
                    raise ValueError(f"Bundle {i} has invalid dimensions: {img.get('width')}×{img.get('height')}")

                # Clean up final_prompt: remove resolution prefix and identity triggers
                if "final_prompt" in img:
                    prompt = img["final_prompt"]

                    # Remove "NATIVE 9:16 (864×1536); " prefix (simple string removal)
                    if prompt.startswith("NATIVE "):
                        # Find the first semicolon and remove everything before it
                        semicolon_idx = prompt.find(";")
                        if semicolon_idx != -1:
                            prompt = prompt[semicolon_idx + 1:].strip()

                    # Remove "evajoy, " and "evajoy " occurrences (case insensitive)
                    prompt = prompt.replace("evajoy, ", "").replace("evajoy ", "").replace("Evajoy, ", "").replace("Evajoy ", "")

                    # Remove "photorealistic vertical 9:16" prefix if present
                    if prompt.lower().startswith("photorealistic vertical 9:16"):
                        # Find the first semicolon and remove everything before it
                        semicolon_idx = prompt.find(";")
                        if semicolon_idx != -1:
                            prompt = prompt[semicolon_idx + 1:].strip()

                    img["final_prompt"] = prompt.strip()

                # Validate video duration
                vid = bundle["video_prompt"]
                if vid.get("duration_seconds") != 6:
                    raise ValueError(f"Bundle {i} has invalid duration: {vid.get('duration_seconds')}s")

                # Generate unique ID
                import hashlib
                bundle_hash = hashlib.sha256(
                    (setting + str(seed_words) + str(i) + str(time.time())).encode()
                ).hexdigest()[:12]
                bundle["id"] = f"pr_{bundle_hash}"

                enriched.append(bundle)

            if len(enriched) == 0:
                raise ValueError("No valid bundles in Grok response")

            log.info(f"Successfully generated {len(enriched)} prompt bundle(s)")
            return enriched

        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Failed to parse Grok prompt bundle response as JSON: {e}\n"
                f"Response content: {content[:500]}..."
            ) from e
        except (KeyError, ValueError) as e:
            raise RuntimeError(f"Invalid prompt bundle structure: {e}") from e

    def _build_prompt_bundle_system(
        self, persona: dict[str, Any], variety_bank: dict[str, Any]
    ) -> str:
        """Build system prompt for prompt bundle generation."""
        # Generic appearance descriptors (user provides reference images separately)
        appearance = (
            f"{persona.get('hair', 'medium wavy blonde hair')}, "
            f"{persona.get('eyes', 'saturated blue eyes')}, "
            f"{persona.get('body', 'busty muscular curvy physique with defined abs, legs, and arms')}, "
            f"{persona.get('skin', 'sun-kissed realistic glowing skin with high radiant complexion and natural wet highlights')}"
        )

        # Get FULL lists from variety banks (not just examples)
        settings_list = variety_bank.get("setting", [])
        scene_list = variety_bank.get("scene", [])
        wardrobe_list = variety_bank.get("wardrobe", [])
        accessories_list = variety_bank.get("accessories", [])
        lighting_list = variety_bank.get("lighting", [])
        camera_list = variety_bank.get("camera", [])
        angle_list = variety_bank.get("angle", [])
        pose_list = variety_bank.get("pose_microaction", [])
        color_palette_list = variety_bank.get("color_palette", [])

        # Load recent posted locations for variety enforcement
        recent_locations = get_recent_location_strings("app/data/recent_posted_combinations.json", limit=20)

        return f"""You are an elite prompt engineer creating comprehensive, ultra-detailed prompts for high-end editorial/Instagram glamour photography AI generation.

**CRITICAL MISSION**: Generate prompts of 1200-1450 characters (approximately 200-240 words) that are COMPLETE, HOLISTIC, and use ALL mandatory categories below. Every prompt must be comprehensive like a professional editorial photography brief.

**CHARACTER LIMIT**: Leonardo API has a strict 1500 character maximum. Target 1200-1450 characters for safety margin.

═══════════════════════════════════════════════════════════════════

**MANDATORY STRUCTURE (every prompt MUST include ALL 12 components):**

1. **OPENING FORMAT** (use appearance descriptor):
   "photorealistic vertical 9:16 image of a 28-years-old woman with {appearance}, captured in [SHOT TYPE] at [EXPANDED SPECIFIC LOCATION]"

   Where appearance = {appearance}

2. **SHOT TYPE** (REQUIRED - rotate for variety):
   • Close-up portrait (face/shoulders only)
   • Medium shot (waist up)
   • 3/4 body (thighs up)
   • Full body (head to toe)

3. **SETTING + SCENE** (REQUIRED - two-part location system):

   **SETTING** (broad geographic location):
   Available: {', '.join(settings_list)}
   Examples: Japan, United States, Greece, Indonesia, France

   **SCENE** (specific detailed environment with atmosphere):
   Available scenes: {', '.join(scene_list[:3])}...

   YOU MUST COMBINE: Pick one SETTING (country/region) + one SCENE (detailed environment)
   Example combinations:
   • Setting: "Japan" + Scene: "luxury penthouse rooftop infinity pool at dusk, city skyline glittering below"
     → "at a luxury Tokyo penthouse rooftop infinity pool at dusk, city skyline glittering below, modern glass railings"
   • Setting: "Greece" + Scene: "whitewashed cliffside terrace overlooking turquoise sea"
     → "at a whitewashed Santorini cliffside terrace overlooking turquoise Aegean sea, blue-domed chapel in background"
   • Setting: "Indonesia" + Scene: "sun-drenched beachfront villa deck with teak flooring"
     → "at a sun-drenched Bali beachfront villa deck with teak flooring, infinity pool merging with ocean horizon"

   OR create NEW scenes inspired by the examples in the same glamorous/luxury style

4. **CAMERA TECHNICAL** (REQUIRED - be specific):
   Lens options: {', '.join(camera_list)}
   Angle options: {', '.join(angle_list[:6])}

   Include: exact lens + aperture + angle description + spatial positioning

5. **WARDROBE** (REQUIRED - comprehensive, not brief):
   Available options: {', '.join(wardrobe_list[:10])}...

   YOU MUST DESCRIBE: base garment + color + fabric type + fit details + revealing elements (underboob/cutouts/transparency/thong-cut/etc.)
   Use "micro" prefix: micro-crop, micro-shorts, micro-bra, barely-there bikini

6. **ACCESSORIES** (REQUIRED - select 2-3):
   Options: {', '.join(accessories_list)}

   Specify which accessories and where worn (e.g., "rose-gold chain anklet on right ankle")

7. **POSE & BODY MECHANICS** (REQUIRED - ultra-detailed):
   Pose options: {', '.join(pose_list[:8])}...

   YOU MUST INCLUDE:
   • Specific body position (kneeling/leaning/standing/etc.)
   • Body mechanics with precision ("torso bent 30 degrees forward, weight on left leg")
   • Limb placement (where each arm/leg is positioned)
   • Micro-action (hair flip, adjusting strap, stretching, glancing)
   • Expression (sultry/playful/confident/intense)
   • Gaze direction (to camera/away/over shoulder/downward)

8. **SKIN REALISM** (REQUIRED):
   Options:
   • "realistic wet skin with strong specular highlights across cheekbones, collarbones, shoulders"
   • "post-workout dewy moisture sheen with natural glow"
   • "tan oil sheen with golden highlights"

   Must specify which body areas catch light

9. **LIGHTING SETUP** (REQUIRED - multi-source with spatial details):
   Lighting options: {', '.join(lighting_list)}

   YOU MUST DESCRIBE 3-4 LIGHT SOURCES:
   • Primary source with direction ("golden hour backlight from right creates warm rim glow")
   • Secondary fill ("soft bounce fill from left maintains facial detail")
   • Accent/rim lights ("rim light separates subject from background")
   • Environmental ambient ("city lights bokeh in background")

10. **ENVIRONMENT DETAILS** (REQUIRED - 3-4 specific elements):
    NOT generic ("beautiful beach") but SPECIFIC ("crystalline infinity pool water with gentle ripples")
    Include: foreground element + midground element + background element + atmospheric detail

11. **COLOR PALETTE** (REQUIRED - overall scene cohesion):
    Options: {', '.join(color_palette_list)}

    Describe how colors tie together: wardrobe + lighting + environment creating cohesive aesthetic

12. **COMPOSITION & FRAMING** (REQUIRED):
    Must include:
    • Rule of thirds positioning (subject placement)
    • Headroom/negative space
    • Diagonal lines or visual flow
    • Social-media vertical framing for 9:16
    • Safe zones for mobile viewing

═══════════════════════════════════════════════════════════════════

**⚠️ VARIETY ENFORCEMENT & ANTI-CLICHÉ CREATIVITY RULES ⚠️**

**RECENTLY POSTED LOCATIONS (DO NOT REPEAT):**
{self._format_recent_locations(recent_locations)}

**CREATIVITY MANDATE:**
❌ AVOID OBVIOUS TOURIST CLICHÉS:
   • Paris → Eiffel Tower backgrounds
   • Japan → Temple with cherry blossoms
   • Greece → White buildings with blue domes (Santorini postcard shots)
   • Dubai → Burj Khalifa prominent in frame
   • USA → Statue of Liberty, Golden Gate Bridge
   • Indonesia → Rice terraces
   • Maldives → Overwater bungalow deck

✅ INSTEAD, USE CREATIVE UNEXPECTED LOCATIONS:
   • Paris → Industrial-chic converted loft with exposed brick, Seine-view through steel-frame windows
   • Japan → Minimalist concrete zen garden with single maple tree, modern rock formations
   • Greece → Secluded coastal cave pool with natural rock formations, turquoise water reflections
   • Dubai → Ultra-modern sky lounge with geometric light installations, city panorama
   • USA → Desert modernist glass house at golden hour, Joshua trees silhouetted
   • Indonesia → Private villa jungle deck with infinity pool disappearing into rainforest canopy
   • Maldives → Sandbank sunset setup with silk daybed, crystalline shallow waters

**LOCATION SELECTION STRATEGY:**
1. Choose SETTING (country/region) from the variety bank
2. Either pick a SCENE from the bank OR create a NEW creative scene inspired by the bank's style
3. Check: Does this specific location appear in "Recently Posted" above?
   - YES → REJECT and choose completely different combination
   - NO → Proceed with creative expansion
4. Avoid tourist landmarks/postcard views - seek hidden gems, architectural surprises, unexpected angles
5. Add city/region specificity (Tokyo not just Japan, Santorini not just Greece)

═══════════════════════════════════════════════════════════════════

**QUALITY STANDARDS:**

✅ TARGET LENGTH: 1200-1450 characters per final_prompt (max 1500 for Leonardo API)
✅ VARIETY: Rotate ALL elements across generations (never repeat exact combinations)
✅ SPECIFICITY: Use precise measurements, directions, technical terms
✅ HOLISTIC: Every prompt should paint a complete, vivid, realistic scene
✅ EDITORIAL QUALITY: Write like a professional photography director's brief
✅ CONCISE BUT COMPLETE: Be descriptive but economical with words - every word counts toward the 1500 char limit

❌ FORBIDDEN: Generic descriptions, placeholders, "NATIVE 9:16", resolution text, "evajoy", LoRA names, identity triggers, unnecessary filler words

═══════════════════════════════════════════════════════════════════

**YOUR TASK**: Create prompts that are SO comprehensive and detailed that an artist could visualize the exact scene without seeing the image. Use ALL 12 mandatory components in EVERY prompt. Target 1200-1450 characters (max 1500). Be creative, specific, and holistic.

Output ONLY structured JSON matching the schema."""

    def _format_recent_locations(self, locations: list[str]) -> str:
        """Format recent posted locations for display in system prompt."""
        if not locations:
            return "   None yet - first generation! You have full creative freedom."

        formatted = []
        for i, loc in enumerate(locations, 1):
            formatted.append(f"   {i}. {loc}")

        return "\n".join(formatted)

    def generate_quick_caption(self, video_meta: dict[str, Any]) -> str:
        """
        Generate quick caption for video (1-2 sentences + 5-10 hashtags).

        Args:
            video_meta: Video metadata dict (image_meta, motion, music, etc.)

        Returns:
            Caption string with hashtags (e.g., "Morning flow vibes 🌅 #fitness #yoga ...")

        Raises:
            RuntimeError: On API failures
        """
        log.info(f"GROK_QUICK_CAPTION video_id={video_meta.get('id', 'unknown')}")

        system_prompt = """You are a social media caption writer for authentic fitness/wellness content.

**Requirements:**
- 1-2 short sentences (engaging, authentic, no clickbait)
- 5-10 hashtags appended (mix popular + niche)
- Tone: empowering, relatable, aspirational
- Avoid: hype, overused phrases, spam-looking hashtag walls

**Format:**
[1-2 sentence hook]. [Optional second sentence]. #hashtag1 #hashtag2 #hashtag3 ..."""

        user_prompt = f"""Generate a quick caption for this video:

**Video Context:**
{json.dumps(video_meta, indent=2)}

Return ONLY the caption text (1-2 sentences + 5-10 hashtags). NO JSON, just plain text."""

        # Estimated cost: ~$0.0001 per caption (very small)
        add_cost(Decimal("0.0001"), "grok")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 200,
        }

        response = self._make_request("chat/completions", payload)

        try:
            content = response["choices"][0]["message"]["content"].strip()

            # Remove any markdown formatting if present
            content = content.replace("```", "").strip()

            log.info(f"GROK_QUICK_CAPTION generated: '{content[:50]}...'")
            return content

        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Failed to extract caption from Grok response: {e}") from e

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
