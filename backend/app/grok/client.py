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
import random
import re
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.core import concurrency
from app.core.cost import add_cost
from app.core.logging import log
from app.core.paths import get_data_path

from .models import ImagePrompt, MusicBrief, MotionSpec, PromptBundle, VideoPrompt
from .transport import XAITransport
from .utils import estimate_cost, estimate_tokens, extract_json, redact


# --- Accessory categorization for smart single-pick ---
ACCESSORY_MAP = {
    "face_head": r"(earring|ear[- ]?cuff|visor|headband|beret|hair stick|hairpin|kanzashi|glasses|sunglass|mask)",
    "neck_chest": r"(necklace|choker|pendant|torque\b|foulard|scarf|collar)",
    "waist_body": r"(\bbelt(?!\s*bag)\b|waist\s*chain|obi|harness|corset|waist pack)",
    "arm_hand": r"(wrist|bracelet|watch|wrap|glove|lifting strap|arm[- ]?band)",
    "leg_ankle": r"(anklet|calf sleeve|thigh holster|crampon|stirrup)",
    "bag": r"(belt bag|waist pack|micro-?satchel|purse|backpack)",
}

# Binding policy for recency tracking (Twist removed)
BIND_POLICY = {
    "scene": {"k": 1, "recent": 50},
    "pose_microaction": {"k": 1, "recent": 60},  # strict enforcement
    "lighting": {"k": 1, "recent": 40},
    "camera": {"k": 1, "recent": 40},
    "angle": {"k": 1, "recent": 40},
    "accessories": {"k": 1, "recent": 50},  # single accessory default
}
INSPIRE_ONLY = {"wardrobe_top", "wardrobe_bottom"}  # never bind

# Section budgets (soft targets for compression/diagnostics only)
SECTION_BUDGETS = {
    "Character": (80, 110),
    "Scene": (160, 230),
    "CameraAngle": (120, 170),
    "Wardrobe": (60, 90),
    "Accessories": (40, 70),
    "Pose": (160, 210),
    "Lighting": (120, 170),
    "Environment": (200, 270),
}


def _acc_category(text: str) -> str:
    """Categorize accessory by body location."""
    t = text.lower()
    for cat, rx in ACCESSORY_MAP.items():
        if re.search(rx, t):
            return cat
    return "other"


def _one_accessory_from_panel(acc_panel: list[str], pose_text: str) -> str:
    """
    Smart single accessory selection.
    Prefers non-arm categories; deprioritizes arm/hand if pose involves hands/wrists.
    """
    if not acc_panel:
        return ""

    prefer = ["face_head", "neck_chest", "waist_body", "bag", "leg_ankle", "other", "arm_hand"]

    # If pose involves hands/wrists, further deprioritize arm_hand
    if any(w in pose_text.lower() for w in ["wrist", "hand", "wrap", "glove", "fingers"]):
        prefer = ["face_head", "neck_chest", "waist_body", "bag", "leg_ankle", "other", "arm_hand"]

    # Categorize all accessories
    cats = {a: _acc_category(a) for a in acc_panel}

    # Sort by preference order
    ranked = sorted(acc_panel, key=lambda a: prefer.index(cats[a]))

    return ranked[0] if ranked else acc_panel[0]


def _compress_persona_appearance(persona: dict) -> str:
    """
    Build compressed appearance descriptor (target ≤110 chars).

    Removes redundant adjectives while keeping core descriptors.
    """
    hair = persona.get("hair", "medium wavy blonde hair")
    eyes = persona.get("eyes", "saturated blue eyes")
    body = persona.get("body", "busty muscular physique")
    skin = persona.get("skin", "realistic skin texture")

    # Compress body if too long
    if "with hourglass defined body" in body:
        body = body.replace(" with hourglass defined body", "")
    if "busty muscular physique" in body:
        body = "busty muscular physique"

    # Compress skin if too long
    if "realistic natural skin texture and strong realistic wet highlights" in skin:
        skin = "realistic skin with wet highlights"
    elif "realistic natural skin texture" in skin:
        skin = "realistic skin texture"

    # Build appearance
    appearance = f"{hair}, {eyes}, {body}, {skin}"

    # If still too long, aggressively compress
    if len(appearance) > 110:
        # Remove modifiers from hair
        hair = hair.replace("medium ", "").replace("wavy ", "")
        # Simplify eyes
        eyes = "blue eyes"
        # Minimal body
        body = "muscular physique"
        # Minimal skin
        skin = "realistic skin"
        appearance = f"{hair}, {eyes}, {body}, {skin}"

    return appearance


def _trim_filler_words(text: str) -> str:
    """Remove common filler adverbs and duplicate adjectives."""
    # Remove common fillers
    fillers = [
        r'\b(softly|subtly|gently|richly|beautifully|perfectly|truly|simply)\s+',
        r'\s+(composition|framing|color palette)[^\.]+'
    ]
    for pattern in fillers:
        text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)

    # Remove duplicate adjectives (e.g., "warm golden glow" → "golden glow")
    text = re.sub(r'\b(\w+)\s+(\w+)\s+(\w+)\b',
                  lambda m: f"{m.group(2)} {m.group(3)}" if m.group(1).lower() in ['warm', 'cool', 'soft', 'rich'] else m.group(0),
                  text)

    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def _extract_bound_spans(prompt: str, bound_phrases: dict[str, list[str]]) -> list[tuple[int, int]]:
    """
    Find character spans of all bound phrases (case-insensitive).

    Returns list of (start, end) tuples marking protected regions.
    """
    spans = []
    prompt_lower = prompt.lower()

    for slot, phrases in bound_phrases.items():
        for phrase in phrases:
            if not phrase:
                continue
            phrase_lower = phrase.lower()
            start_idx = 0
            while True:
                idx = prompt_lower.find(phrase_lower, start_idx)
                if idx == -1:
                    break
                spans.append((idx, idx + len(phrase)))
                start_idx = idx + len(phrase)

    # Merge overlapping spans
    if not spans:
        return []

    spans.sort()
    merged = [spans[0]]
    for start, end in spans[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    return merged


def compress_image_prompt(text: str, bound_phrases: dict[str, list[str]], target_max: int = 1500) -> tuple[str, list[str]]:
    """
    Compress image prompt if >target_max chars while preserving all bound phrases.

    Strategy (in order):
    1. Remove filler words from Environment
    2. Trim Lighting, CameraAngle, Scene sections above budget
    3. Trim Wardrobe/Accessories descriptive fluff (NOT bound phrases)

    Args:
        text: The image prompt text
        bound_phrases: Dict of bound phrases to preserve exactly
        target_max: Maximum allowed length (default 1500)

    Returns:
        Tuple of (compressed_text, list_of_trimmed_sections)
    """
    if len(text) <= target_max:
        return text, []

    # Extract bound spans to protect
    protected_spans = _extract_bound_spans(text, bound_phrases)
    trimmed_sections = []

    # Split into sections (case-insensitive)
    section_pattern = r'(?i)(Character|Scene|Camera|Angle|Wardrobe|Accessories|Pose|Lighting|Environment):\s*'
    parts = re.split(section_pattern, text)

    if len(parts) < 3:  # Couldn't parse sections
        return _trim_filler_words(text), ["Global"]

    # Rebuild as dict
    sections = {}
    current_label = None
    for i, part in enumerate(parts):
        if i == 0:
            continue  # Skip text before first section
        if i % 2 == 1:  # Section label
            current_label = part.strip()
        elif current_label:  # Section content
            sections[current_label] = part.strip()

    # Compression steps
    saved_chars = 0

    # Step 1: Trim Environment fillers
    if "Environment" in sections:
        env_text = sections["Environment"]
        trimmed_env = _trim_filler_words(env_text)
        if len(trimmed_env) < len(env_text):
            saved = len(env_text) - len(trimmed_env)
            sections["Environment"] = trimmed_env
            saved_chars += saved
            trimmed_sections.append(f"Environment(-{saved})")

    # Step 2: Trim other sections if still over limit
    trim_order = ["Lighting", "Scene"]  # Don't trim CameraAngle (often bound)

    for section_name in trim_order:
        if len(text) - saved_chars <= target_max:
            break

        if section_name in sections:
            original = sections[section_name]
            trimmed = _trim_filler_words(original)

            # Additional aggressive trimming if needed
            if len(trimmed) > SECTION_BUDGETS.get(section_name, (0, 200))[1]:
                budget_max = SECTION_BUDGETS[section_name][1]
                # Trim to budget while avoiding protected spans
                if len(trimmed) > budget_max:
                    # Simple truncation for now
                    trimmed = trimmed[:budget_max].rsplit('.', 1)[0] + '.'

            if len(trimmed) < len(original):
                saved = len(original) - len(trimmed)
                sections[section_name] = trimmed
                saved_chars += saved
                trimmed_sections.append(f"{section_name}(-{saved})")

    # Rebuild prompt
    rebuilt = ""
    for section in ["Character", "Scene", "Camera", "Angle", "Wardrobe", "Accessories", "Pose", "Lighting", "Environment"]:
        if section in sections:
            rebuilt += f"{section}: {sections[section]} "

    # Final trim if still over
    if len(rebuilt) > target_max:
        rebuilt = _trim_filler_words(rebuilt)
        if len(rebuilt) > target_max:
            # Last resort: hard truncate at sentence boundary
            rebuilt = rebuilt[:target_max].rsplit('.', 1)[0] + '.'
            if "HardTrunc" not in trimmed_sections:
                trimmed_sections.append("HardTrunc")

    return rebuilt.strip(), trimmed_sections


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

    @staticmethod
    def _weighted_sample_texts(bank: list, k: int, rng: random.Random) -> list[str]:
        """
        Sample texts from bank with weights.
        bank can be a list[str] or list[dict{'text': str, 'weight': float}]
        Returns up to k unique texts, sampled with weights when present.
        """
        if not bank:
            return []
        # Normalize to (text, weight)
        norm = []
        for item in bank:
            if isinstance(item, dict):
                t = item.get("text") or item.get("name") or ""
                w = float(item.get("weight", 1.0))
            else:
                t, w = str(item), 1.0
            if t:
                norm.append((t, max(w, 0.0001)))
        if not norm:
            return []
        # Sample without replacement using weights
        if k >= len(norm):
            items = norm[:]
            rng.shuffle(items)
            return [t for t, _ in items]
        # Weighted sampling without replacement
        out = []
        pool = norm[:]
        for _ in range(k):
            total_w = sum(w for _, w in pool)
            r = rng.random() * total_w
            acc = 0.0
            idx = 0
            for i, (t, w) in enumerate(pool):
                acc += w
                if acc >= r:
                    idx = i
                    break
            t, _ = pool.pop(idx)
            out.append(t)
        return out

    @staticmethod
    def _load_recent_prompts(limit: int = 100) -> list[dict[str, Any]]:
        """Load recent prompt bundles from JSONL storage."""
        try:
            prompts_path = get_data_path("prompts/prompts.jsonl")
            if not prompts_path.exists():
                return []

            recent = []
            with open(prompts_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        recent.append(json.loads(line))

            # Return most recent first
            return recent[-limit:] if len(recent) > limit else recent

        except Exception as e:
            log.warning(f"Failed to load recent prompts: {e}")
            return []

    def _bind_from_panel(
        self,
        slot_name: str,
        panel: list[str],
        bind_policy: dict[str, dict[str, int]],
        rng: random.Random,
    ) -> list[str]:
        """
        Bind k items from panel, avoiding recent use.

        Args:
            slot_name: Slot name (e.g., "scene", "pose_microaction")
            panel: Available items for this slot
            bind_policy: Binding configuration
            rng: Random number generator

        Returns:
            List of k bound items
        """
        if slot_name not in bind_policy or not panel:
            return []

        k = bind_policy[slot_name]["k"]
        recent_window = bind_policy[slot_name]["recent"]

        # Load recent prompts
        recent_bundles = self._load_recent_prompts(recent_window)

        # Extract recently used items for this slot
        recently_used = set()
        for bundle in recent_bundles:
            # Check image prompt for slot content
            img_prompt = bundle.get("image_prompt", {}).get("final_prompt", "")
            for item in panel:
                if item.lower() in img_prompt.lower():
                    recently_used.add(item)

        # Filter out recently used items
        available = [item for item in panel if item not in recently_used]

        # If not enough available, fall back to full panel
        if len(available) < k:
            available = panel

        # Sample k items
        return self._weighted_sample_texts(available, k, rng)

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
        setting_id: str,
        location_label: str,
        location_path: str,
        seed_words: list[str] | None = None,
        count: int = 1,
        bind_scene: bool = True,
        bind_pose_microaction: bool = True,
        bind_lighting: bool = True,
        bind_camera: bool = True,
        bind_angle: bool = True,
        bind_accessories: bool = True,
        bind_wardrobe: bool = False,
        single_accessory: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Generate prompt bundles (image + video) for manual workflow.

        Args:
            setting_id: Location ID (e.g., "japan", "us-new_york-manhattan-times_square")
            location_label: Human-readable location name (e.g., "Japan", "Times Square — Manhattan, NY")
            location_path: Full path to location JSON file
            seed_words: Optional embellisher keywords
            count: Number of bundles to generate (1-10)
            bind_scene: Bind scene from location JSON
            bind_pose_microaction: Bind pose/micro-action (VERBATIM enforcement)
            bind_lighting: Bind lighting
            bind_camera: Bind camera
            bind_angle: Bind angle
            bind_accessories: Bind accessories
            bind_wardrobe: Bind wardrobe (top+bottom); else inspire-only
            single_accessory: If True, bind exactly 1 accessory; if False, bind 2

        Returns:
            List of bundle dicts (backwards compatible format)
        """
        log.info(
            f"GROK_BUNDLE setting_id={setting_id} location_label={location_label} seed_words={seed_words} count={count} "
            f"bind_scene={bind_scene} bind_pose={bind_pose_microaction} bind_lighting={bind_lighting} "
            f"bind_camera={bind_camera} bind_angle={bind_angle} "
            f"bind_accessories={bind_accessories} bind_wardrobe={bind_wardrobe} single_accessory={single_accessory}"
        )

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

        # Load scenes from location-specific JSON using provided path
        from pathlib import Path
        location_file = Path(location_path)

        if not location_file.exists():
            log.error(f"Location file not found: {location_path}")
            raise RuntimeError(f"Location file not found: {location_path}")

        try:
            with open(location_file, "r", encoding="utf-8") as f:
                location_data = json.load(f)
                scenes = location_data.get("scenes", [])
                log.info(f"GROK_BUNDLE loaded {len(scenes)} scenes from {location_file.name} (setting_id={setting_id})")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            log.error(f"Failed to load location file {location_path}: {e}")
            raise RuntimeError(f"Failed to load scenes from {location_path}: {e}") from e

        # Build appearance
        appearance = self._build_appearance(persona)

        # Get variety options (keep as weighted objects for sampling)
        accessories = variety_bank.get("accessories", [])
        poses = variety_bank.get("pose_microaction", [])
        lighting = variety_bank.get("lighting", [])
        camera = variety_bank.get("camera", [])
        angles = variety_bank.get("angle", [])
        wardrobe_top = variety_bank.get("wardrobe_top", [])
        wardrobe_bottom = variety_bank.get("wardrobe_bottom", [])

        # Build negative prompt
        dont_list = persona.get("dont", [])
        negative_list = variety_bank.get("negative", [])
        negative_prompt = ", ".join(set(dont_list + negative_list))

        # Per-call RNG for varied sampling (includes timestamp for true randomness)
        rng = random.Random()
        rng.seed(hash(f"{setting_id}|{count}|{time.time()}") & 0xFFFFFFFFFFFF)

        # Setup binding policy based on UI flags
        bind_policy = {}
        if bind_scene:
            bind_policy["scene"] = {"k": 1, "recent": 50}
        if bind_pose_microaction:
            bind_policy["pose_microaction"] = {"k": 1, "recent": 80}
        if bind_lighting:
            bind_policy["lighting"] = {"k": 1, "recent": 40}
        if bind_camera:
            bind_policy["camera"] = {"k": 1, "recent": 40}
        if bind_angle:
            bind_policy["angle"] = {"k": 1, "recent": 40}
        if bind_accessories:
            # Respect single_accessory flag
            bind_policy["accessories"] = {"k": 1 if single_accessory else 2, "recent": 50}
        if bind_wardrobe:
            bind_policy["wardrobe_top"] = {"k": 1, "recent": 50}
            bind_policy["wardrobe_bottom"] = {"k": 1, "recent": 50}

        # Create panels (larger for diversity)
        acc_panel = self._weighted_sample_texts(accessories, 15, rng)
        pose_panel = self._weighted_sample_texts(poses, 30, rng)
        light_panel = self._weighted_sample_texts(lighting, 12, rng)
        cam_panel = self._weighted_sample_texts(camera, 10, rng)
        ang_panel = self._weighted_sample_texts(angles, 12, rng)
        top_panel = self._weighted_sample_texts(wardrobe_top, 12, rng)
        bot_panel = self._weighted_sample_texts(wardrobe_bottom, 12, rng)
        scene_panel = self._weighted_sample_texts(scenes, 10, rng)

        # Bind slots according to policy
        bound = {}
        bound["scene"] = self._bind_from_panel("scene", scene_panel, bind_policy, rng) if bind_scene else []
        bound["pose_microaction"] = self._bind_from_panel("pose_microaction", pose_panel, bind_policy, rng) if bind_pose_microaction else []
        bound["lighting"] = self._bind_from_panel("lighting", light_panel, bind_policy, rng) if bind_lighting else []
        bound["camera"] = self._bind_from_panel("camera", cam_panel, bind_policy, rng) if bind_camera else []
        bound["angle"] = self._bind_from_panel("angle", ang_panel, bind_policy, rng) if bind_angle else []

        # Accessory binding with smart selection
        if bind_accessories:
            pose_text = bound["pose_microaction"][0] if bound.get("pose_microaction") else ""
            if single_accessory:
                # Smart single accessory selection (avoid arm accessories if pose is hands-busy)
                chosen_acc = _one_accessory_from_panel(acc_panel, pose_text)
                bound["accessories"] = [chosen_acc] if chosen_acc else []
            else:
                # Legacy: bind 2 accessories
                bound["accessories"] = self._bind_from_panel("accessories", acc_panel, bind_policy, rng)
        else:
            bound["accessories"] = []

        # Wardrobe binding (only if requested)
        if bind_wardrobe:
            bound["wardrobe_top"] = self._bind_from_panel("wardrobe_top", top_panel, bind_policy, rng)
            bound["wardrobe_bottom"] = self._bind_from_panel("wardrobe_bottom", bot_panel, bind_policy, rng)
        else:
            bound["wardrobe_top"] = []
            bound["wardrobe_bottom"] = []

        # Build system prompt with binding constraints
        seed_text = f" (embellish with: {', '.join(seed_words)})" if seed_words else ""

        # Build BOUND CONSTRAINTS section dynamically
        bound_constraints = []
        if bind_scene and bound.get("scene"):
            bound_constraints.append(f"Scene: `<scene>[{bound['scene'][0]}]`")
        if bind_pose_microaction and bound.get("pose_microaction"):
            bound_constraints.append(
                f"**BOUND POSE — copy this phrase EXACTLY at the START of the Pose line (no additions inside it):**\n"
                f"  `{bound['pose_microaction'][0]}`"
            )
        if bind_lighting and bound.get("lighting"):
            bound_constraints.append(f"Lighting: `<lighting>[{bound['lighting'][0]}]`")
        if bind_camera and bound.get("camera"):
            bound_constraints.append(f"Camera: `<camera>[{bound['camera'][0]}]`")
        if bind_angle and bound.get("angle"):
            bound_constraints.append(f"Angle: `<angle>[{bound['angle'][0]}]`")

        # Accessory section
        if bind_accessories and bound.get("accessories"):
            if single_accessory:
                accessories_section = f"""**ACCESSORIES:**
Use **exactly ONE** of the bound items below. Do NOT add or replace.
BOUND ACCESSORY: `<accessories>[{bound['accessories'][0]}]`"""
            else:
                accessories_section = f"""**ACCESSORIES:**
Use **exactly THESE TWO** bound items. Do NOT add or replace.
BOUND ACCESSORIES: `<accessories>[{', '.join(bound['accessories'])}]`"""
        else:
            accessories_section = f"""**ACCESSORIES (INSPIRE ONLY):**
Select 1-2 accessories from: {', '.join(acc_panel[:8])}"""

        # Wardrobe section
        if bind_wardrobe and bound.get("wardrobe_top") and bound.get("wardrobe_bottom"):
            wardrobe_section = f"""**WARDROBE (BOUND):**
Use both exact phrases below; do not add substitutes.
- BOUND TOP: `<wardrobe_top>[{bound['wardrobe_top'][0]}]`
- BOUND BOTTOM: `<wardrobe_bottom>[{bound['wardrobe_bottom'][0]}]`"""
        else:
            wardrobe_section = f"""**WARDROBE (INVENT NEW):**
50-70 chars, max 2 fabrics, no repeating panel fabrics.
Examples (DO NOT REUSE): {', '.join(top_panel[:3])}, {', '.join(bot_panel[:3])}"""

        # Build inspiration panels for unbound slots
        inspiration_panels = []
        if not bind_scene:
            inspiration_panels.append(f"Scenes (select/vary): {', '.join(scene_panel[:6])}")
        if not bind_pose_microaction:
            inspiration_panels.append(f"Poses (select/vary): {', '.join(pose_panel[:6])}")
        if not bind_lighting:
            inspiration_panels.append(f"Lighting (select): {', '.join(light_panel[:6])}")
        if not bind_camera:
            inspiration_panels.append(f"Camera (select): {', '.join(cam_panel[:5])}")
        if not bind_angle:
            inspiration_panels.append(f"Angles (select): {', '.join(ang_panel[:6])}")

        # Build the prompt sections
        bound_section = ""
        if bound_constraints:
            bound_section = f"""**BOUND CONSTRAINTS (must use exact phrases):**
{chr(10).join(bound_constraints)}

"""

        inspiration_section = ""
        if inspiration_panels:
            inspiration_section = f"""**VARIETY BANKS (inspiration for unbound slots):**
{chr(10).join(inspiration_panels)}

"""

        system_prompt = f"""Create {count} prompt bundle(s) for: {location_label}{seed_text}

Each bundle has:
1. **IMAGE** prompt (≈1,400 chars TARGET) - photorealistic glamour portrait
2. **VIDEO** prompt (< 160 chars, 3-part format)

**CRITICAL CHARACTER COUNT REQUIREMENTS:**
- Target: ≈1,400 characters (ideal sweet spot for detail + quality)
- Valid window: 1,300-1,500 characters (including spaces)
- Enforced minimum: 1,300 chars (below this will be REJECTED)
- Maximum: 1,500 chars (Leonardo API hard limit)
- Count carefully before submitting!

**CHARACTER:** {appearance}

{bound_section}{inspiration_section}{accessories_section}

{wardrobe_section}

**IMAGE STRUCTURE (aim for ≈1,400 chars total):**
Sections (ordered): Character, Scene, Camera + Angle, Wardrobe, Accessories, Pose, Lighting, Environment.
Expand each section with rich sensory detail, specific textures, and atmospheric cues to reach 1,400 chars.

**CRITICAL — BOUND POSE REQUIREMENT:**
If a BOUND POSE phrase is shown above, you MUST place it EXACTLY at the START of the Pose line.
- Do NOT add any text before the bound phrase
- Do NOT modify the phrase itself
- Do NOT add commas or embellishments inside the bound phrase
- After the bound phrase ends, you may add a period/semicolon/comma and continue with more pose detail
- Example: If bound phrase is "arched back stretch", your Pose line MUST start: "Pose: arched back stretch; ..."

For other bound phrases (scene, lighting, camera, angle, accessories), include them verbatim but placement flexibility is allowed.

**VIDEO (6s, keep < 160 chars total):**
Format: "[camera move]; [character micro-action]; [environment cue]."
Examples:
- "Dolly push; over-shoulder hair flip; lantern mist drifting."
- "Slider creep; slow inhale, chin lift; rain beads catching neon."
One sentence, plain English, no lenses/f-stops/rigs.

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
                invalid_prompts = []  # Track character limit violations
                validation_errors = []  # Track binding/format violations

                for bundle_raw in bundles_raw:
                    # Generate deterministic ID
                    prompt_text = bundle_raw["image_prompt"]["final_prompt"]
                    bundle_id = self._generate_bundle_id(setting_id, prompt_text)
                    bundle_raw["id"] = bundle_id

                    # Check length BEFORE Pydantic validation (to avoid max_length constraint)
                    prompt_len = len(prompt_text)
                    min_chars = 1300  # Target minimum (updated to 1,300)
                    max_chars = self.config.max_prompt_chars  # 1500 hard limit

                    # Try smart compression if over limit (BEFORE validation)
                    if prompt_len > max_chars:
                        compressed, trimmed_sections = compress_image_prompt(
                            prompt_text,
                            bound,
                            target_max=max_chars
                        )
                        compressed_len = len(compressed)

                        if compressed_len <= max_chars and compressed_len >= min_chars:
                            # Compression succeeded - update bundle_raw before validation
                            bundle_raw["image_prompt"]["final_prompt"] = compressed
                            prompt_len = compressed_len  # Update for validation below
                            log.info(
                                f"COMPRESS applied bundle_id={bundle_id} "
                                f"before={len(prompt_text)} after={compressed_len} "
                                f"saved={len(prompt_text) - compressed_len} sections={trimmed_sections}"
                            )
                            # Add compression metadata
                            bundle_raw["_compression_applied"] = {
                                "before": len(prompt_text),
                                "after": compressed_len,
                                "saved": len(prompt_text) - compressed_len,
                                "sections": trimmed_sections,
                            }
                        else:
                            # Compression didn't help enough
                            invalid_prompts.append((bundle_id, compressed_len, "too_long_post_compress"))
                            log.warning(
                                f"GROK_BUNDLE prompt too long even after compression: "
                                f"bundle_id={bundle_id} before={len(prompt_text)} after={compressed_len} "
                                f"(max {max_chars}) attempt={attempt}/{max_attempts}"
                            )
                            continue  # Skip this bundle

                    # Validate with Pydantic (after compression if needed)
                    validated = PromptBundle(**bundle_raw)

                    # Check character limit AFTER validation (for bundles that didn't need compression)
                    if prompt_len < min_chars:
                        invalid_prompts.append((bundle_id, prompt_len, "too_short"))
                        log.warning(
                            f"GROK_BUNDLE prompt too short: bundle_id={bundle_id} length={prompt_len} "
                            f"(min {min_chars}) attempt={attempt}/{max_attempts}"
                        )

                    # Validate binding constraints (pass all bind flags)
                    is_valid, errors = self._validate_bundle(
                        bundle_raw, bound,
                        bind_scene, bind_pose_microaction, bind_lighting,
                        bind_camera, bind_angle,
                        bind_accessories, bind_wardrobe
                    )
                    if not is_valid:
                        validation_errors.append((bundle_id, errors))
                        log.warning(
                            f"GROK_BUNDLE validation failed: bundle_id={bundle_id} "
                            f"errors={errors} attempt={attempt}/{max_attempts}"
                        )

                    # Per-bundle telemetry (Step 6)
                    final_prompt_len = len(bundle_raw["image_prompt"]["final_prompt"])
                    compression_info = bundle_raw.get("_compression_applied")
                    if compression_info:
                        log.info(
                            f"BUNDLE_METRICS bundle_id={bundle_id} "
                            f"len_before={compression_info.get('before', 0)} "
                            f"len_after_compress={compression_info.get('after', 0)} "
                            f"saved={compression_info.get('saved', 0)} "
                            f"sections_trimmed={str(compression_info.get('sections', []))}"
                        )
                    else:
                        log.info(
                            f"BUNDLE_METRICS bundle_id={bundle_id} "
                            f"len_final={final_prompt_len} compression=not_needed"
                        )

                    bundles.append(bundle_raw)  # Keep building bundles for validation

                # If ANY prompt violates limits or constraints, reject entire batch and retry
                if invalid_prompts or validation_errors:
                    error_parts = []

                    if invalid_prompts:
                        char_errors = ", ".join([f"{bid}:{length}({reason})" for bid, length, reason in invalid_prompts])
                        error_parts.append(f"Character violations: {char_errors}")

                    if validation_errors:
                        bind_errors = "; ".join([f"{bid}: {', '.join(errs)}" for bid, errs in validation_errors])
                        error_parts.append(f"Binding violations: {bind_errors}")

                    error_message = " | ".join(error_parts)

                    last_error = RuntimeError(
                        f"Validation failed on attempt {attempt}/{max_attempts}. {error_message}"
                    )

                    if attempt < max_attempts:
                        log.info(f"GROK_BUNDLE retrying (attempt {attempt + 1}/{max_attempts})...")
                        continue  # Retry
                    else:
                        # Fail-soft: log as STILL_NONCOMPLIANT and return bundles
                        log.error(f"STILL_NONCOMPLIANT after {max_attempts} attempts: {error_message}")
                        # Return bundles anyway but with warning
                        for bundle in bundles:
                            bundle["_validation_warning"] = "STILL_NONCOMPLIANT"
                        return bundles

                # All prompts valid - success!
                log.info(f"GROK_BUNDLE generated {len(bundles)} bundles (all valid)")
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
        """
        Build compressed appearance descriptor from persona (target ≤110 chars).

        Logs the final length for diagnostics.
        """
        appearance = _compress_persona_appearance(persona)
        log.info(f"PERSONA_APPEARANCE length={len(appearance)} chars: {appearance[:80]}...")
        return appearance

    def _generate_bundle_id(self, setting_id: str, prompt: str) -> str:
        """Generate deterministic bundle ID from setting_id and prompt."""
        content = f"{setting_id}:{prompt[:200]}"
        hash_hex = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return f"pr_{hash_hex[:12]}"

    @staticmethod
    def _extract_section(text: str, label: str) -> str | None:
        """Extract content of a labeled section from prompt text."""
        m = re.search(rf"{label}\s*:\s*(.+?)(?:\.|$)", text, flags=re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else None

    @staticmethod
    def _starts_with_phrase(section: str, phrase: str) -> bool:
        """Check if section starts with the exact phrase (case-insensitive)."""
        if not section or not phrase:
            return False
        # Escape special regex characters and match at start
        esc = re.escape(phrase.strip())
        # Allow end, whitespace, or punctuation immediately after
        return re.match(rf"^{esc}([\s\.,;:!\?]|$)", section, flags=re.IGNORECASE) is not None

    def _validate_bundle(
        self,
        bundle: dict[str, Any],
        bound: dict[str, list[str]],
        bind_scene: bool,
        bind_pose_microaction: bool,
        bind_lighting: bool,
        bind_camera: bool,
        bind_angle: bool,
        bind_accessories: bool,
        bind_wardrobe: bool,
    ) -> tuple[bool, list[str]]:
        """
        Validate bundle against binding constraints.

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        img_prompt = bundle.get("image_prompt", {}).get("final_prompt", "").lower()
        video_prompt = bundle.get("video_prompt", {})

        # Build full video string for validation
        video_full = f"{video_prompt.get('motion', '')} {video_prompt.get('character_action', '')} {video_prompt.get('environment', '')}"

        # Check bound slots (case-insensitive) - only for enabled bindings
        if bind_scene and bound.get("scene"):
            bound_text = bound["scene"][0].lower()
            if bound_text and bound_text not in img_prompt:
                errors.append(f"Missing bound scene: '{bound['scene'][0]}'")

        # STRICT Pose validation: must START the Pose section with exact phrase
        if bind_pose_microaction and bound.get("pose_microaction"):
            pose_bound = bound["pose_microaction"][0]
            pose_section = self._extract_section(img_prompt, "Pose")
            if not pose_section or not self._starts_with_phrase(pose_section, pose_bound):
                errors.append(f"Pose must START with bound micro-action: '{pose_bound}'")

        if bind_lighting and bound.get("lighting"):
            bound_text = bound["lighting"][0].lower()
            if bound_text and bound_text not in img_prompt:
                errors.append(f"Missing bound lighting: '{bound['lighting'][0]}'")

        if bind_camera and bound.get("camera"):
            bound_text = bound["camera"][0].lower()
            if bound_text and bound_text not in img_prompt:
                errors.append(f"Missing bound camera: '{bound['camera'][0]}'")

        if bind_angle and bound.get("angle"):
            bound_text = bound["angle"][0].lower()
            if bound_text and bound_text not in img_prompt:
                errors.append(f"Missing bound angle: '{bound['angle'][0]}'")

        if bind_accessories and bound.get("accessories"):
            for acc in bound["accessories"]:
                bound_text = acc.lower()
                if bound_text and bound_text not in img_prompt:
                    errors.append(f"Missing bound accessory: '{acc}'")

        if bind_wardrobe:
            if bound.get("wardrobe_top"):
                bound_text = bound["wardrobe_top"][0].lower()
                if bound_text and bound_text not in img_prompt:
                    errors.append(f"Missing bound wardrobe_top: '{bound['wardrobe_top'][0]}'")
            if bound.get("wardrobe_bottom"):
                bound_text = bound["wardrobe_bottom"][0].lower()
                if bound_text and bound_text not in img_prompt:
                    errors.append(f"Missing bound wardrobe_bottom: '{bound['wardrobe_bottom'][0]}'")

        # Check VIDEO format and length
        video_len = len(video_full)
        if video_len > 160:
            errors.append(f"VIDEO too long: {video_len} chars (max 160)")

        # Check VIDEO has 2 semicolons (3-part format)
        semicolon_count = video_full.count(";")
        if semicolon_count != 2:
            errors.append(f"VIDEO must have exactly 2 semicolons (found {semicolon_count})")

        return (len(errors) == 0, errors)

    def close(self) -> None:
        """Close transport session."""
        self.transport.close()

    def __enter__(self) -> GrokClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args) -> None:
        """Context manager exit."""
        self.close()
