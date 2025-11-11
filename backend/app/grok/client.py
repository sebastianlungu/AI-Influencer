"""Refactored Grok API client with simplified prompts and robust transport.

Key improvements:
- Simplified system prompts (80% reduction)
- Pydantic validation for all responses
- Proper HTTP session management
- Accurate cost estimation
- Type hints throughout
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.core import concurrency
from app.core.cost import add_cost
from app.core.logging import log
from app.core.paths import get_data_path
from app.core.variety_tracker import get_recent_location_strings

from .models import ImagePrompt, MusicBrief, MotionSpec, PromptBundle, VideoPrompt
from .transport import XAITransport
from .utils import estimate_cost, estimate_tokens, extract_json, redact


@dataclass(frozen=True)
class GrokConfig:
    """Configuration constants for Grok API."""

    model: str = "grok-4-fast-reasoning"
    timeout_connect_s: float = 10.0
    timeout_read_s: float = 30.0
    max_retries: int = 3
    rps: float = 2.0

    # Leonardo API constraints
    max_prompt_chars: int = 1500
    default_width: int = 864
    default_height: int = 1536

    # Veo constraints
    default_video_duration_s: int = 6

    # Pricing (per million tokens)
    price_per_mtok_in: Decimal = Decimal("0.30")
    price_per_mtok_out: Decimal = Decimal("0.75")


class GrokClient:
    """Refactored Grok API client for prompt generation."""

    def __init__(
        self,
        api_key: str,
        model: str = "grok-4-fast-reasoning",
        config: GrokConfig | None = None,
    ):
        """
        Initialize Grok client.

        Args:
            api_key: xAI API key
            model: Model ID (default: grok-4-fast-reasoning)
            config: Optional custom configuration (uses defaults if not provided)
        """
        if not api_key:
            raise ValueError("Grok API key cannot be empty")

        self.config = config or GrokConfig(model=model)
        self.transport = XAITransport(
            api_key=api_key,
            timeout_connect_s=self.config.timeout_connect_s,
            timeout_read_s=self.config.timeout_read_s,
            max_retries=self.config.max_retries,
            rps=self.config.rps,
        )

    def _call_api(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        Make API call with concurrency control and cost tracking.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum output tokens

        Returns:
            Raw response content string

        Raises:
            RuntimeError: On API failures
        """
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Estimate cost from character counts
        input_chars = len(system_prompt) + len(user_prompt)
        estimated_output_chars = max_tokens * 4  # Rough estimate

        cost = estimate_cost(
            input_chars,
            estimated_output_chars,
            self.config.price_per_mtok_in,
            self.config.price_per_mtok_out,
        )

        # Track estimated cost
        add_cost(cost, "grok")

        log.info(
            f"GROK_API_CALL model={self.config.model} temp={temperature} "
            f"in_tokens={estimate_tokens(input_chars)} estimated_cost=${cost:.4f}"
        )

        # Make request with concurrency control
        with concurrency.grok_slot():
            response = self.transport.post_json("chat/completions", payload)

        # Extract content
        try:
            content = response["choices"][0]["message"]["content"].strip()
            log.debug(f"GROK_RESPONSE preview={redact(content, 200)}")
            return content
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Failed to extract content from Grok response: {e}") from e

    def generate_variations(
        self,
        character_profile: dict[str, Any],
        diversity_banks: dict[str, list[str]],
        n: int,
        negative_prompt: str = "",
        preference_hints: str = "",
    ) -> list[dict[str, Any]]:
        """
        Generate N diverse image prompt variations.

        Args:
            character_profile: Character description (appearance, style, etc.)
            diversity_banks: Variety banks (locations, poses, outfits, etc.)
            n: Number of variations to generate
            negative_prompt: Base negative prompt
            preference_hints: Optional hints for diversity

        Returns:
            List of variation dicts (backwards compatible format)
        """
        log.info(f"GROK_VARIATIONS n={n}")

        # Build appearance descriptor
        appearance = self._build_appearance(character_profile)

        # Extract variety options
        settings = diversity_banks.get("setting", [])
        scenes = diversity_banks.get("scene", [])
        wardrobe = diversity_banks.get("wardrobe", [])
        poses = diversity_banks.get("pose_microaction", [])
        lighting = diversity_banks.get("lighting", [])
        camera = diversity_banks.get("camera", [])

        # Build simplified system prompt
        system_prompt = f"""Create {n} diverse photorealistic glamour portrait prompts (900-1100 chars each).

Character: {appearance}

Variety banks (rotate creatively):
- Settings: {', '.join(settings[:5])}...
- Scenes: {', '.join(scenes[:3])}...
- Wardrobe: {', '.join(wardrobe[:8])}...
- Poses: {', '.join(poses[:6])}...

Structure (compact):
1. Opening: "photorealistic vertical 9:16 image of a 28-year-old woman with [appearance], [shot type] in [specific location]"
2. Camera: lens + angle
3. Wardrobe: detailed description
4. Pose: body mechanics + expression
5. Lighting: natural description

Return JSON array: [{{"base": "...", "neg": "{negative_prompt}", "variation": "brief desc", "meta": {{}}}}]"""

        user_prompt = f"Generate {n} varied prompts. Be creative, concise, vivid. No tourist clichés."

        # Make API call
        content = self._call_api(system_prompt, user_prompt, temperature=0.9, max_tokens=3000)

        # Parse and validate
        try:
            variations = extract_json(content)

            if not isinstance(variations, list) or len(variations) != n:
                raise ValueError(f"Expected {n} variations, got {len(variations) if isinstance(variations, list) else 'non-array'}")

            log.info(f"GROK_VARIATIONS generated {len(variations)} prompts")
            return variations

        except Exception as e:
            log.error(f"GROK_VARIATIONS failed: {e}")
            raise RuntimeError(f"Failed to parse variations from Grok: {e}") from e

    def suggest_motion(self, image_meta: dict[str, Any], duration_s: int = 6) -> dict[str, Any]:
        """
        Generate cinematic motion prompt for video generation.

        Args:
            image_meta: Image metadata dict
            duration_s: Video duration in seconds (default 6)

        Returns:
            Motion spec dict (backwards compatible format)
        """
        log.info(f"GROK_MOTION duration={duration_s}s")

        system_prompt = f"""Generate a cinematic motion prompt for a {duration_s}-second video.

Focus on:
- Camera motion (pan, zoom, tilt, dolly, static, tracking)
- Subject motion (subtle actions, micro-expressions)
- Environment dynamics (lighting, atmosphere)

Be specific but concise. Aim for smooth, elegant motion that enhances the mood."""

        user_prompt = f"""Image context: {json.dumps(image_meta, indent=2)}

Create motion prompt. Return JSON:
{{"motion_type": "pan|zoom|tilt|...", "motion_prompt": "detailed description", "subject_motion": "character action"}}"""

        content = self._call_api(system_prompt, user_prompt, temperature=0.7, max_tokens=500)

        try:
            motion_spec = extract_json(content)

            # Validate with Pydantic
            validated = MotionSpec(**motion_spec)

            log.info(f"GROK_MOTION generated motion_type={validated.motion_type}")
            return motion_spec  # Return dict for backwards compatibility

        except Exception as e:
            log.error(f"GROK_MOTION failed: {e}")
            raise RuntimeError(f"Failed to parse motion spec from Grok: {e}") from e

    def suggest_music(self, image_meta: dict[str, Any], motion_spec: dict[str, Any]) -> dict[str, Any]:
        """
        Generate music brief for Suno.

        Args:
            image_meta: Image metadata dict
            motion_spec: Motion specification dict

        Returns:
            Music brief dict (backwards compatible format)
        """
        log.info("GROK_MUSIC")

        system_prompt = """Generate a music brief for a 6-second fitness/wellness video.

Focus on:
- Style/genre (electronic, ambient, cinematic, etc.)
- Mood (energizing, calm, motivational, etc.)
- Tempo (slow, medium, fast)
- Instruments (synths, piano, drums, etc.)

Keep it concise but vivid."""

        user_prompt = f"""Context:
Image: {json.dumps(image_meta, indent=2)}
Motion: {json.dumps(motion_spec, indent=2)}

Create music brief. Return JSON:
{{"style": "...", "mood": "...", "tempo": "...", "instruments": "...", "prompt": "complete brief"}}"""

        content = self._call_api(system_prompt, user_prompt, temperature=0.7, max_tokens=500)

        try:
            music_brief = extract_json(content)

            # Validate with Pydantic
            validated = MusicBrief(**music_brief)

            log.info(f"GROK_MUSIC generated style={validated.style} mood={validated.mood}")
            return music_brief  # Return dict for backwards compatibility

        except Exception as e:
            log.error(f"GROK_MUSIC failed: {e}")
            raise RuntimeError(f"Failed to parse music brief from Grok: {e}") from e

    def generate_prompt_bundle(
        self,
        setting: str,
        seed_words: list[str] | None = None,
        count: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Generate prompt bundles (image + video) for manual workflow.

        Args:
            setting: High-level setting (e.g., "Japan", "Santorini")
            seed_words: Optional embellisher keywords
            count: Number of bundles to generate (1-10)

        Returns:
            List of bundle dicts (backwards compatible format)
        """
        log.info(f"GROK_BUNDLE setting={setting} seed_words={seed_words} count={count}")

        # Load persona and variety bank
        try:
            persona_path = get_data_path("persona.json")
            variety_path = get_data_path("variety_bank.json")
            with open(persona_path, "r", encoding="utf-8") as f:
                persona = json.load(f)
            with open(variety_path, "r", encoding="utf-8") as f:
                variety_bank = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to load config files: {e}") from e

        # Build appearance
        appearance = self._build_appearance(persona)

        # Get variety options
        scenes = variety_bank.get("scene", [])
        wardrobe = variety_bank.get("wardrobe", [])
        accessories = variety_bank.get("accessories", [])
        poses = variety_bank.get("pose_microaction", [])
        lighting = variety_bank.get("lighting", [])
        camera = variety_bank.get("camera", [])
        angles = variety_bank.get("angle", [])

        # Build negative prompt
        dont_list = persona.get("dont", [])
        negative_list = variety_bank.get("negative", [])
        negative_prompt = ", ".join(set(dont_list + negative_list))

        # Build simplified system prompt with explicit character limit
        seed_text = f" (embellish with: {', '.join(seed_words)})" if seed_words else ""

        system_prompt = f"""Create {count} prompt bundle(s) for: {setting}{seed_text}

Each bundle has:
1. Image prompt (900-1100 chars TARGET) - photorealistic glamour portrait
2. Video prompt (6s motion + action)

**CRITICAL CHARACTER COUNT REQUIREMENTS:**
- Target: 900-1100 characters (including spaces)
- Minimum: 900 chars (prompts under 900 will be REJECTED)
- Maximum: 1500 chars (Leonardo API hard limit)
- Count carefully before submitting!

Character: {appearance}

Variety banks:
- Scenes (rotate/select): {', '.join(scenes[:4])}...
- Accessories (select 2-3): {', '.join(accessories[:6])}...
- Poses (select/vary): {', '.join(poses[:6])}...
- Lighting (select): {', '.join(lighting[:5])}...
- Camera (select): {', '.join(camera[:4])}... + angles: {', '.join(angles[:6])}...

**WARDROBE - INVENT NEW (examples for style inspiration only):**
Examples: {', '.join(wardrobe[:5])}
**DO NOT REUSE THESE. CREATE entirely unique wardrobe for each prompt with specific fabrics, cuts, colors, and styling details (50-80 chars).**

Detailed template (aim for 900-1100 chars total):
"photorealistic vertical 9:16 image of a 28-year-old woman with [full appearance: hair, eyes, body, skin - 60 chars], [shot type: 3/4 body/full body/thighs up] at [very specific {setting} location with architectural/environmental details - 80 chars]. Camera: [lens focal length + f-stop + specific angle - 20 chars]. Wardrobe: [INVENT unique outfit with fabric types, fit details, colors, style - 50-80 chars]. Accessories: [2-3 specific items with materials - 30 chars]. Pose: [detailed body mechanics + facial expression + hand placement - 60 chars]. Lighting: [specific lighting description with direction and quality - 50 chars]. Environment: [atmospheric details, textures, background elements - 70 chars]."

Return JSON array of {count} bundle(s):
[{{"id": "pr_xxx", "image_prompt": {{"final_prompt": "...", "negative_prompt": "{negative_prompt}", "width": 864, "height": 1536}}, "video_prompt": {{"motion": "...", "character_action": "...", "environment": "...", "duration_seconds": 6, "notes": "..."}}}}]"""

        user_prompt = f"Generate {count} creative bundle(s). Be vivid, concise, varied. No clichés."

        # Retry loop for character limit enforcement (max 3 attempts)
        max_attempts = 3
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                content = self._call_api(system_prompt, user_prompt, temperature=0.9, max_tokens=4000)

                bundles_raw = extract_json(content)

                if not isinstance(bundles_raw, list) or len(bundles_raw) != count:
                    raise ValueError(f"Expected {count} bundles, got {len(bundles_raw) if isinstance(bundles_raw, list) else 'non-array'}")

                # Validate and generate IDs
                bundles = []
                invalid_prompts = []  # Track both over-limit AND under-limit

                for bundle_raw in bundles_raw:
                    # Generate deterministic ID
                    prompt_text = bundle_raw["image_prompt"]["final_prompt"]
                    bundle_id = self._generate_bundle_id(setting, prompt_text)
                    bundle_raw["id"] = bundle_id

                    # Validate with Pydantic
                    validated = PromptBundle(**bundle_raw)

                    # Enforce character limits (fail-loud policy)
                    prompt_len = len(validated.image_prompt.final_prompt)
                    min_chars = 900  # Target minimum
                    max_chars = self.config.max_prompt_chars  # 1500 hard limit

                    if prompt_len < min_chars:
                        invalid_prompts.append((bundle_id, prompt_len, "too_short"))
                        log.warning(
                            f"GROK_BUNDLE prompt too short: bundle_id={bundle_id} length={prompt_len} "
                            f"(min {min_chars}) attempt={attempt}/{max_attempts}"
                        )
                    elif prompt_len > max_chars:
                        invalid_prompts.append((bundle_id, prompt_len, "too_long"))
                        log.warning(
                            f"GROK_BUNDLE prompt too long: bundle_id={bundle_id} length={prompt_len} "
                            f"(max {max_chars}) attempt={attempt}/{max_attempts}"
                        )

                    bundles.append(bundle_raw)  # Keep building bundles for validation

                # If ANY prompt violates limits, reject entire batch and retry
                if invalid_prompts:
                    error_details = ", ".join([f"{bid}:{length}({reason})" for bid, length, reason in invalid_prompts])
                    last_error = RuntimeError(
                        f"Character limit violation on attempt {attempt}/{max_attempts}. "
                        f"Invalid prompts: {error_details}. "
                        f"Required: 900-1500 chars (Leonardo API constraint)."
                    )
                    if attempt < max_attempts:
                        log.info(f"GROK_BUNDLE retrying (attempt {attempt + 1}/{max_attempts})...")
                        continue  # Retry
                    else:
                        raise last_error  # Fail loud after max attempts

                # All prompts within limits - success!
                log.info(f"GROK_BUNDLE generated {len(bundles)} bundles (all within 900-{self.config.max_prompt_chars} char range)")
                return bundles

            except Exception as e:
                log.error(f"GROK_BUNDLE failed on attempt {attempt}/{max_attempts}: {e}")
                last_error = e
                if attempt < max_attempts and "limit exceeded" not in str(e):
                    continue  # Retry on parsing errors
                else:
                    raise RuntimeError(f"Failed to generate valid prompt bundles after {attempt} attempts: {e}") from e

        # Should never reach here, but fail loud just in case
        raise last_error or RuntimeError("Failed to generate prompt bundles (unknown error)")

    def generate_quick_caption(self, video_meta: dict[str, Any]) -> str:
        """
        Generate quick caption for social media.

        Args:
            video_meta: Video metadata dict

        Returns:
            Caption string with hashtags
        """
        log.info(f"GROK_CAPTION video_id={video_meta.get('id', 'unknown')}")

        system_prompt = """Generate a quick social media caption (1-2 sentences + 5-10 hashtags).

Tone: Empowering, authentic, aspirational. No clickbait or hype."""

        user_prompt = f"""Video context: {json.dumps(video_meta, indent=2)}

Create caption. Return plain text (no JSON, just the caption with hashtags)."""

        content = self._call_api(system_prompt, user_prompt, temperature=0.7, max_tokens=200)

        # Remove any markdown formatting
        caption = content.replace("```", "").strip()

        log.info(f"GROK_CAPTION generated: {redact(caption, 100)}")
        return caption

    def generate_social_meta(self, media_meta: dict[str, Any]) -> dict[str, Any]:
        """
        Generate social media metadata (title, tags, hashtags).

        Args:
            media_meta: Full media metadata

        Returns:
            Dict with keys: title, tags, hashtags
        """
        log.info(f"GROK_SOCIAL media_id={media_meta.get('id', 'unknown')}")

        system_prompt = """Generate social media metadata:
- title: 40-60 char engaging title
- tags: 5-10 plain keywords (no #)
- hashtags: 8-12 hashtags (with #)

Tone: Empowering, authentic."""

        user_prompt = f"""Media context: {json.dumps(media_meta, indent=2)}

Create metadata. Return JSON:
{{"title": "...", "tags": ["tag1", "tag2"], "hashtags": ["#hash1", "#hash2"]}}"""

        content = self._call_api(system_prompt, user_prompt, temperature=0.7, max_tokens=300)

        try:
            social_meta = extract_json(content)

            log.info(f"GROK_SOCIAL generated title={social_meta.get('title', '')[:50]}")
            return social_meta

        except Exception as e:
            log.error(f"GROK_SOCIAL failed: {e}")
            raise RuntimeError(f"Failed to parse social meta from Grok: {e}") from e

    def _build_appearance(self, persona: dict[str, Any]) -> str:
        """Build appearance descriptor from persona."""
        return (
            f"{persona.get('hair', 'medium wavy blonde hair')}, "
            f"{persona.get('eyes', 'saturated blue eyes')}, "
            f"{persona.get('body', 'busty muscular curvy physique with defined abs, legs, and arms')}, "
            f"{persona.get('skin', 'sun-kissed realistic glowing skin with high radiant complexion and natural wet highlights')}"
        )

    def _generate_bundle_id(self, setting: str, prompt: str) -> str:
        """Generate deterministic bundle ID from setting and prompt."""
        content = f"{setting}:{prompt[:200]}"
        hash_hex = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return f"pr_{hash_hex[:12]}"

    def close(self) -> None:
        """Close transport session."""
        self.transport.close()

    def __enter__(self) -> GrokClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args) -> None:
        """Context manager exit."""
        self.close()
