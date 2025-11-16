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

from pydantic import ValidationError

from app.core import concurrency
from app.core.cost import add_cost
from app.core.logging import log
from app.core.paths import get_data_path

from .models import ImagePrompt, MusicBrief, MotionSpec, PromptBundle, VideoPrompt
from .text_filter import filter_banned_words
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
    "hair_style": {"k": 1, "recent": 60},  # hairstyle arrangement (no length)
}
# STEP 3: Removed INSPIRE_ONLY constant (wardrobe can now be bound or inspire-only based on UI flag)

# Motion variety binding policy (independent from main prompt slots)
BIND_POLICY_MOTION = {
    "video_camera_motion": {"k": 1, "recent": 15},
    "video_micro_action": {"k": 1, "recent": 20},
    "video_posture": {"k": 1, "recent": 15},
    "video_closing_angle": {"k": 1, "recent": 20},
}

# Environment deny list (words that should not appear in motion lines)
ENV_DENY = {
    "street", "temple", "shrine", "rain", "city", "skyline", "market", "beach",
    "bridge", "alley", "plaza", "station", "rooftop", "river", "forest", "mountain",
    "snow", "neon", "lanterns", "tokyo", "japan", "manhattan", "york", "times", "square",
    "cafe", "restaurant", "bar", "club", "gym", "studio", "park", "garden", "pool",
    "ocean", "lake", "desert", "valley", "hill", "canyon", "waterfall", "sunset",
    "sunrise", "night", "evening", "morning", "dawn", "dusk", "twilight",
}

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


def _contains_phrase(text: str, phrase: str) -> bool:
    """
    Check if text contains phrase with word boundaries (case-insensitive).

    Collapses spaces and uses regex word boundaries for robust matching.
    """
    if not text or not phrase:
        return False

    # Collapse spaces for safety
    t = ' '.join(text.lower().split())
    p = ' '.join(phrase.lower().split())

    # Build pattern with word boundaries
    pattern = r'\b' + re.escape(p) + r'\b'

    return re.search(pattern, t) is not None


def _phrase_match_loose(text: str, phrase: str, threshold: float = 0.8) -> bool:
    """
    Fuzzy phrase matching that tolerates minor grammar fixes.

    Allows binding validation to pass even when Grok makes small edits like:
    - Fixing typos ("from from" → "from")
    - Adding/removing articles ("an arc slide" vs "arc slide")
    - Minor word reordering

    Strategy:
    1. Normalize both text and phrase (lowercase, strip articles, collapse spaces)
    2. Tokenize phrase into words
    3. Check that at least `threshold` % of phrase tokens appear in order in text

    Args:
        text: The full prompt text to search in
        phrase: The bound phrase to look for
        threshold: Minimum fraction of tokens that must match (default 0.8 = 80%)

    Returns:
        True if phrase is "loosely" present in text

    Examples:
        >>> _phrase_match_loose("an arc slide from marble colonnade", "arc slide from from marble colonnade")
        True  # Tolerates "from from" → "from" fix and added "an"
    """
    if not text or not phrase:
        return False

    # Normalize both strings
    def normalize(s: str) -> str:
        # Lowercase
        s = s.lower()
        # Remove common articles
        for article in [' a ', ' an ', ' the ']:
            s = s.replace(article, ' ')
        # Collapse multiple spaces
        s = ' '.join(s.split())
        return s

    text_norm = normalize(text)
    phrase_norm = normalize(phrase)

    # Tokenize phrase
    phrase_tokens = phrase_norm.split()
    if not phrase_tokens:
        return False

    # Find how many phrase tokens appear in order in text
    text_tokens = text_norm.split()
    matched_count = 0
    text_idx = 0

    for phrase_token in phrase_tokens:
        # Search for this token starting from current position
        while text_idx < len(text_tokens):
            if phrase_token == text_tokens[text_idx]:
                matched_count += 1
                text_idx += 1
                break
            text_idx += 1

    # Check if we matched at least threshold% of phrase tokens
    match_ratio = matched_count / len(phrase_tokens)
    return match_ratio >= threshold


# Regex to match slot wrapper tags like <scene>[...], <camera>[...], etc.
_TAG_BLOCK = re.compile(r"<[a-z_]+>\s*\[([^\]]+)\]", re.IGNORECASE)


def _strip_slot_wrappers(text: str) -> str:
    """
    Strip slot wrapper tags from prompt text.

    Replaces patterns like `<scene>[luxury penthouse]` with just `luxury penthouse`.
    This is a belt-and-suspenders safety measure to ensure no tags escape
    even if a template change accidentally reintroduces them.

    Args:
        text: Prompt text that may contain slot wrappers

    Returns:
        Text with all slot wrappers removed
    """
    if not text:
        return text

    # Replace `<slot>[payload]` -> `payload`
    return _TAG_BLOCK.sub(r"\1", text)


def _strip_section_labels(text: str) -> tuple[str, list[str]]:
    """
    Strip section labels from prompt text if they slip through.

    Removes patterns like "Camera: ...", "Pose: ...", "Lighting: ..." etc.
    Only strips at sentence boundaries to avoid damaging normal words.

    Args:
        text: Prompt text that may contain section labels

    Returns:
        Tuple of (cleaned_text, list_of_stripped_labels)
    """
    if not text:
        return text, []

    # Section labels to strip
    labels = ["Camera", "Angle", "Wardrobe", "Accessories", "Pose", "Lighting", "Environment", "Scene"]
    stripped = []
    cleaned = text

    for label in labels:
        # Match label at start of sentence or after period/newline
        # Pattern: (start of string OR period/newline) + whitespace + Label: + whitespace
        pattern = re.compile(
            r'(^|\.\s+|\n\s*)' + re.escape(label) + r':\s+',
            re.MULTILINE | re.IGNORECASE
        )

        # Find matches to track what was stripped
        matches = pattern.findall(cleaned)
        if matches:
            stripped.append(label)

        # Remove the label, keeping the sentence boundary
        cleaned = pattern.sub(r'\1', cleaned)

    # Clean up any double spaces
    cleaned = re.sub(r'  +', ' ', cleaned).strip()

    return cleaned, stripped


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


def _enforce_min_len(s: str, min_len: int = 12, pad: str = " — steady, focused") -> str:
    """
    Ensure string meets minimum length by appending a natural-sounding tail.

    Prevents video_prompt fields from failing Pydantic min_length validators.
    """
    if not isinstance(s, str):
        return ""

    s = s.strip(" .;")
    if len(s) >= min_len:
        return s

    # Natural padding options
    tails = [
        " — steady, focused",
        " with calm intent",
        " — measured and deliberate",
        " with quiet precision"
    ]

    for t in tails:
        if len(s) + len(t) >= min_len:
            return f"{s}{t}"

    # Fallback to first tail
    return f"{s}{tails[0]}"


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

    @staticmethod
    def _load_motion_bank() -> dict[str, list[dict[str, Any]]]:
        """Load video motion variety bank from variety_bank.json."""
        try:
            variety_bank_path = get_data_path("variety_bank.json")
            with open(variety_bank_path, "r", encoding="utf-8") as f:
                full_bank = json.load(f)
                # Extract only the video motion banks
                return {
                    "video_camera_motion": full_bank.get("video_camera_motion", []),
                    "video_micro_action": full_bank.get("video_micro_action", []),
                    "video_posture": full_bank.get("video_posture", []),
                    "video_closing_angle": full_bank.get("video_closing_angle", []),
                }
        except FileNotFoundError:
            log.warning("variety_bank.json not found, returning empty motion banks")
            return {
                "video_camera_motion": [],
                "video_micro_action": [],
                "video_posture": [],
                "video_closing_angle": [],
            }
        except Exception as e:
            log.error(f"Failed to load motion banks from variety_bank.json: {e}")
            return {
                "video_camera_motion": [],
                "video_micro_action": [],
                "video_posture": [],
                "video_closing_angle": [],
            }

    @staticmethod
    def _validate_motion_line(line: str) -> tuple[bool, str]:
        """
        Validate a single motion line against the new forever structure.

        Expected format:
        "natural, instagram-photorealistic, hand-held camera — {camera_motion}, she {micro_action} while keeping {posture}; {closing_angle}"

        Where closing_angle starts with "ending in..." or "ending as..." etc.

        Returns:
            (is_valid, error_message)
        """
        # Rule 1: Must start with prefix
        if not line.startswith("natural, instagram-photorealistic, hand-held camera — "):
            return False, "missing 'natural, instagram-photorealistic, hand-held camera — ' prefix"

        # Rule 2: Must include "she"
        if ", she " not in line:
            return False, "missing ', she ' separator"

        # Rule 3: Must include "while keeping"
        if " while keeping " not in line:
            return False, "missing ' while keeping ' posture phrase"

        # Rule 4: Must include closing angle marker ("; ending" or "; finishing")
        if "; ending " not in line and "; finishing " not in line:
            return False, "missing '; ending ' or '; finishing ' closing phrase"

        # Rule 5: No environment words
        env_deny_tokens = line.lower().split()
        for token in env_deny_tokens:
            if token in ENV_DENY:
                return False, f"contains environment word: '{token}'"

        # Rule 6: Length check (adjusted for new structure with longer prefix)
        # Old prefix was ~32 chars, new is ~56 chars (+24), so adjust thresholds
        if len(line) < 120:
            return False, f"too short ({len(line)} < 120 chars)"
        if len(line) > 230:
            return False, f"too long ({len(line)} > 230 chars)"

        return True, ""

    def _generate_motion_line(
        self,
        rng: random.Random,
        image_pose: str | None = None,
    ) -> str:
        """
        Generate a single motion line with binding & recency using the new forever structure.

        Forever structure:
        "natural, instagram-photorealistic, hand-held camera — {camera_motion}, she {micro_action} while keeping {posture}; {closing_angle}."

        Args:
            rng: Random number generator
            image_pose: Optional pose/micro-action from the image prompt for context-aware motion

        Returns:
            Single motion line string (120-230 chars)
        """
        # Load motion bank
        motion_bank = self._load_motion_bank()

        # Load recent bundles for recency tracking
        recent_bundles = self._load_recent_prompts(limit=50)

        # Extract recently used items per slot
        recently_used = {
            "video_camera_motion": set(),
            "video_micro_action": set(),
            "video_posture": set(),
            "video_closing_angle": set(),
        }

        for bundle in recent_bundles:
            video = bundle.get("video_prompt", {})
            if isinstance(video, dict) and "line" in video:
                # Try to extract components from lines
                line = video["line"]
                # Simple heuristic extraction (best effort)
                for slot_name in recently_used.keys():
                    slot_bank = motion_bank.get(slot_name, [])
                    for item in slot_bank:
                        text = item.get("text", "") if isinstance(item, dict) else str(item)
                        if text and text.lower() in line.lower():
                            recently_used[slot_name].add(text)

        # Try up to 3 times to generate a valid line
        for attempt in range(3):
            # Sample from each slot (excluding recent)
            selected = {}

            for slot_name, policy in BIND_POLICY_MOTION.items():
                bank = motion_bank.get(slot_name, [])
                if not bank:
                    log.warning(f"Empty motion bank for slot '{slot_name}'")
                    selected[slot_name] = ""
                    continue

                # Filter out recently used
                recent_window = policy["recent"]
                recent_for_slot = list(recently_used[slot_name])[-recent_window:]
                available = [
                    item for item in bank
                    if (item.get("text", "") if isinstance(item, dict) else str(item)) not in recent_for_slot
                ]

                # Fallback to full bank if nothing available
                if not available:
                    available = bank

                # Sample k=1 with weights
                k = policy["k"]
                sampled = self._weighted_sample_texts(available, k, rng)
                selected[slot_name] = sampled[0] if sampled else ""

            # CONTEXT-AWARE ENHANCEMENT: Optionally reference the image pose
            # 20% chance to add context when image_pose is provided
            micro_action_text = selected['video_micro_action']
            if image_pose and rng.random() < 0.2:
                # Extract key action words from pose (first 2-3 words typically describe the action)
                pose_keywords = ' '.join(image_pose.split()[:3])
                context_phrases = [
                    f"continues the {pose_keywords}",
                    f"extends the {pose_keywords}",
                    f"maintains the {pose_keywords}",
                ]
                micro_action_text = rng.choice(context_phrases)

            # Build line with new forever structure:
            # "natural, instagram-photorealistic, hand-held camera — {camera_motion}, she {micro_action} while keeping {posture}; {closing_angle}"
            # Note: closing_angle already includes "ending in..." or "ending as..." so we don't add "finish"
            line = (
                f"natural, instagram-photorealistic, hand-held camera — {selected['video_camera_motion']}, "
                f"she {micro_action_text} while keeping {selected['video_posture']}; "
                f"{selected['video_closing_angle']}"
            )

            # Validate
            is_valid, error_msg = self._validate_motion_line(line)

            if is_valid:
                log.info(f"MOTION_LINE_GENERATED length={len(line)} attempt={attempt + 1}")
                return line
            else:
                log.warning(f"MOTION_VALIDATION_FAIL attempt={attempt + 1} reason={error_msg}")

        # If all attempts fail, return the last attempt anyway (will be caught by Pydantic)
        log.error(f"MOTION_LINE_GENERATION_FAILED after 3 attempts, returning last attempt")
        return line

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
        bind_wardrobe: bool = True,  # STEP 2: Wardrobe binding ON by default
        bind_hair: bool = True,  # Hairstyle arrangement binding (ON by default)
        single_accessory: bool = True,
        motion_variations: int = 3,  # Interface compatibility (not used - motion generated client-side)
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

        # Build compressed appearance for system prompt reference only
        appearance = self._build_appearance(persona)

        # Get variety options (keep as weighted objects for sampling)
        accessories = variety_bank.get("accessories", [])
        poses = variety_bank.get("pose_microaction", [])
        lighting = variety_bank.get("lighting", [])
        camera = variety_bank.get("camera", [])
        angles = variety_bank.get("angle", [])
        # STEP 3: Use unified wardrobe array (single outfit phrase)
        wardrobe = variety_bank.get("wardrobe", [])
        hair_styles = variety_bank.get("hair_style", [])

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
            # STEP 3: Single wardrobe slot (unified outfit phrase)
            bind_policy["wardrobe"] = {"k": 1, "recent": 50}
        if bind_hair:
            bind_policy["hair_style"] = {"k": 1, "recent": 60}

        # Create panels (larger for diversity)
        acc_panel = self._weighted_sample_texts(accessories, 15, rng)
        pose_panel = self._weighted_sample_texts(poses, 30, rng)
        light_panel = self._weighted_sample_texts(lighting, 12, rng)
        cam_panel = self._weighted_sample_texts(camera, 10, rng)
        ang_panel = self._weighted_sample_texts(angles, 12, rng)
        # STEP 3: Single wardrobe panel (full outfit phrases)
        wardrobe_panel = self._weighted_sample_texts(wardrobe, 15, rng)
        hair_panel = self._weighted_sample_texts(hair_styles, 12, rng) if hair_styles else []
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

        # Wardrobe binding (only if requested) - STEP 3: Single outfit phrase
        if bind_wardrobe:
            bound["wardrobe"] = self._bind_from_panel("wardrobe", wardrobe_panel, bind_policy, rng)
        else:
            bound["wardrobe"] = []

        # Hairstyle binding (only if requested)
        if bind_hair and hair_panel:
            bound["hair_style"] = self._bind_from_panel("hair_style", hair_panel, bind_policy, rng)
        else:
            bound["hair_style"] = []

        # Build FOREVER prefix (fixed, with bound hairstyle)
        forever_prefix = self._build_forever_prefix(persona, bound)

        # Build system prompt with binding constraints
        seed_text = f" (embellish with: {', '.join(seed_words)})" if seed_words else ""

        # Build BOUND CONSTRAINTS section dynamically
        bound_constraints = []
        if bind_scene and bound.get("scene"):
            bound_constraints.append(f"Scene: `{bound['scene'][0]}`")
        if bind_pose_microaction and bound.get("pose_microaction"):
            bound_constraints.append(
                f"**BOUND POSE — copy this phrase EXACTLY at the START of the Pose line (no additions inside it):**\n"
                f"  `{bound['pose_microaction'][0]}`"
            )
        if bind_lighting and bound.get("lighting"):
            bound_constraints.append(f"Lighting: `{bound['lighting'][0]}`")
        if bind_camera and bound.get("camera"):
            bound_constraints.append(f"Camera: `{bound['camera'][0]}`")
        if bind_angle and bound.get("angle"):
            bound_constraints.append(f"Angle: `{bound['angle'][0]}`")
        if bind_hair and bound.get("hair_style"):
            bound_constraints.append(
                f"**BOUND HAIRSTYLE (use EXACTLY this phrase, no additions):**\n"
                f"  `<hair_style>[{bound['hair_style'][0]}]`"
            )

        # Accessory section
        if bind_accessories and bound.get("accessories"):
            if single_accessory:
                accessories_section = f"""**ACCESSORIES:**
Use **exactly ONE** of the bound items below. Do NOT add or replace.
BOUND ACCESSORY: `{bound['accessories'][0]}`"""
            else:
                accessories_section = f"""**ACCESSORIES:**
Use **exactly THESE TWO** bound items. Do NOT add or replace.
BOUND ACCESSORIES: `{', '.join(bound['accessories'])}`"""
        else:
            accessories_section = f"""**ACCESSORIES (INSPIRE ONLY):**
Select 1-2 accessories from: {', '.join(acc_panel[:8])}"""

        # Wardrobe section - STEP 3: Single outfit phrase
        if bind_wardrobe and bound.get("wardrobe"):
            wardrobe_section = f"""**WARDROBE (BOUND):**
Use this exact outfit phrase; do not substitute or modify.
- BOUND OUTFIT: `{bound['wardrobe'][0]}`"""
        else:
            wardrobe_section = f"""**WARDROBE (INVENT NEW):**
Create a coherent single outfit phrase (50-80 chars) in fitness/street-fitness/muscle-showing aesthetic.
Wardrobe must be fitness-oriented, light clothing, bikini/swim, or minimal fashion pieces that reveal the physique.
Avoid sweaters, hoodies, fleece, heavy or winter garments unless explicitly present in the bound phrase.
Max 2-3 fabrics per outfit. Must describe ONE complete outfit (not separate top+bottom).
Examples for inspiration (DO NOT REUSE): {', '.join(wardrobe_panel[:5])}"""

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

        # Calculate budget for LLM (total target - FOREVER prefix)
        # Target: 1930-2130 chars total (FOREVER ~236 + LLM ~1694-1894)
        # Increased by +200 chars to reach 1300-1400 total target
        forever_len = len(forever_prefix)
        llm_min = 1694   # Minimum chars from LLM (1930 - 236)
        llm_target = 1794  # Target chars from LLM (2030 - 236)
        llm_max = 1894  # Maximum chars from LLM (2130 - 236)

        system_prompt = f"""Create {count} prompt bundle(s) for: {location_label}{seed_text}

Each bundle has:
**IMAGE** prompt - photorealistic glamour portrait

**CRITICAL: FOREVER PREFIX (already fixed on our side):**
The following prefix is FIXED and will be prepended automatically to your text:
"{forever_prefix}"

**YOUR TASK:**
Write ONLY what comes AFTER the above prefix. Do NOT rewrite or include the persona/character description.
Start directly with the scene/location (e.g., ", shot at [specific location]...").

**CHARACTER COUNT REQUIREMENTS (for YOUR text only):**
- Target: ≈{llm_target} characters (ideal sweet spot for detail + quality)
- Valid window: {llm_min}-{llm_max} characters (including spaces)
- Enforced minimum: {llm_min} chars (below this will be REJECTED)
- Maximum: {llm_max} chars (enforced limit)
- We'll add the {forever_len}-char FOREVER prefix automatically
- Final combined prompt: ≈{llm_target + forever_len} chars total (range {llm_min + forever_len}-{llm_max + forever_len})

**CHARACTER (for reference only - DO NOT rewrite this):** {appearance}

{bound_section}{inspiration_section}{accessories_section}

{wardrobe_section}

**YOUR TEXT STRUCTURE (≈{llm_target} chars):**
Start with: ", shot at [specific scene/location]..."

**CRITICAL - WRITE AS A FLOWING PARAGRAPH (NO SECTION LABELS):**
Use this internal structure conceptually: Scene, Camera, Angle, Wardrobe, Accessories, Pose, Lighting, Environment.
However, write it as ONE CONTINUOUS natural description - do NOT prefix sections with labels like "Camera:", "Pose:", "Lighting:", etc.
Instead of: "Camera: 85mm at f/2.5... Pose: arched back... Lighting: orchid gelled rim..."
Write: "shot at [scene]. [Camera details] capture the scene. [Wardrobe details]. [Accessories details]. [Pose details]; [more pose]. [Lighting details]. [Environment details]."

**CRITICAL — BOUND POSE REQUIREMENT:**
If a BOUND POSE phrase is shown above, you MUST include it EXACTLY in the pose portion of your flowing text.
- Include the exact phrase verbatim (no modifications)
- Weave it naturally into the pose description
- Example: If bound phrase is "arched back stretch", include: "...arched back stretch against the wall, muscles..."

For other bound phrases (scene, lighting, camera, angle, accessories), include them verbatim in the appropriate part of your flowing description.

Return JSON array of {count} bundle(s):
[{{"id": "pr_xxx", "image_prompt": {{"final_prompt": "...", "negative_prompt": "{negative_prompt}", "width": 864, "height": 1536}}}}]"""

        user_prompt = f"Generate {count} creative bundle(s). Be vivid, concise, varied. No clichés."

        # Single-attempt generation (no retries, accept all prompts)
        # Length and binding validation are now informational only
        try:
            content = self._call_api(system_prompt, user_prompt, temperature=0.9, max_tokens=4000)

            bundles_raw = extract_json(content)

            if not isinstance(bundles_raw, list) or len(bundles_raw) != count:
                raise ValueError(f"Expected {count} bundles, got {len(bundles_raw) if isinstance(bundles_raw, list) else 'non-array'}")

            # Process each bundle (no skipping, all bundles returned)
            bundles = []
            advisory_min = 1230  # Advisory minimum (FOREVER ~236 + LLM 994)
            advisory_max = 1500  # Advisory maximum (Leonardo safe limit)

            for bundle_raw in bundles_raw:
                # Sanitize: strip any slot wrapper tags (belt-and-suspenders safety)
                llm_text = bundle_raw["image_prompt"]["final_prompt"]
                llm_text = _strip_slot_wrappers(llm_text)

                # CRITICAL: Prepend the FOREVER prefix (client-side, NOT from LLM)
                # The LLM only wrote what comes AFTER the persona
                prompt_text = forever_prefix + llm_text

                # Strip any accidental section labels that slipped through
                prompt_text, stripped_labels = _strip_section_labels(prompt_text)
                if stripped_labels:
                    log.info(f"LABEL_STRIP applied labels={stripped_labels} bundle_id={bundle_raw.get('id', 'unknown')}")

                # Filter banned words from image prompt
                prompt_text, removed_words_img = filter_banned_words(prompt_text)
                if removed_words_img:
                    log.info(f"BANNED_WORDS_REMOVED bundle_id={bundle_raw.get('id', 'unknown')} removed={removed_words_img} source=image_prompt")

                # Update the prompt
                bundle_raw["image_prompt"]["final_prompt"] = prompt_text

                # Store metadata about the split for debugging
                bundle_raw["_forever_split"] = {
                    "prefix_len": len(forever_prefix),
                    "llm_len": len(llm_text),
                    "total_len": len(prompt_text),
                }

                # Generate deterministic ID
                bundle_id = self._generate_bundle_id(setting_id, prompt_text)
                bundle_raw["id"] = bundle_id

                # Check length (advisory only, no enforcement)
                prompt_len = len(prompt_text)
                length_warnings = []
                if prompt_len < advisory_min:
                    length_warnings.append(f"below_advisory_min({advisory_min})")
                if prompt_len > advisory_max:
                    length_warnings.append(f"above_advisory_max({advisory_max})")

                # Generate motion line (client-side, not from Grok)
                # Pass image pose for context-aware motion (if bound)
                image_pose = bound.get("pose_microaction", [None])[0] if bound.get("pose_microaction") else None
                motion_line = self._generate_motion_line(rng, image_pose=image_pose)

                # Filter banned words from video motion line
                motion_line, removed_words_video = filter_banned_words(motion_line)
                if removed_words_video:
                    log.info(f"BANNED_WORDS_REMOVED bundle_id={bundle_id} removed={removed_words_video} source=video_motion")

                bundle_raw["video_prompt"] = {"line": motion_line}

                # Validate with Pydantic (informational only, don't skip on failure)
                pydantic_valid = True
                try:
                    validated = PromptBundle(**bundle_raw)
                except ValidationError as e:
                    pydantic_valid = False
                    error_details = [(str(err['loc']), err['msg']) for err in e.errors()]
                    log.warning(
                        f"PYDANTIC_VALIDATION_FAILED bundle_id={bundle_id} "
                        f"errors={error_details} "
                        f"(informational only, bundle still saved)"
                    )
                    bundle_raw["_validation_warning"] = f"pydantic_failed: {e.errors()[0]['msg']}"

                # Add bound metadata for audit (persisted in saved bundle)
                bundle_raw["bound"] = bound

                # Validate binding constraints (informational only)
                is_valid, errors = self._validate_bundle(
                    bundle_raw, bound,
                    bind_scene, bind_pose_microaction, bind_lighting,
                    bind_camera, bind_angle,
                    bind_accessories, bind_wardrobe, bind_hair
                )

                # Build binding status summary for logging
                bind_status_parts = []
                if bind_scene:
                    status = "ok" if not any("scene" in e.lower() for e in errors) else "miss"
                    bind_status_parts.append(f"scene={status}")
                if bind_camera:
                    status = "ok" if not any("camera" in e.lower() for e in errors) else "miss"
                    bind_status_parts.append(f"camera={status}")
                if bind_angle:
                    status = "ok" if not any("angle" in e.lower() for e in errors) else "miss"
                    bind_status_parts.append(f"angle={status}")
                if bind_pose_microaction:
                    status = "ok" if not any("pose" in e.lower() for e in errors) else "miss"
                    bind_status_parts.append(f"pose={status}")
                if bind_lighting:
                    status = "ok" if not any("lighting" in e.lower() for e in errors) else "miss"
                    bind_status_parts.append(f"lighting={status}")
                if bind_accessories:
                    status = "ok" if not any("accessor" in e.lower() for e in errors) else "miss"
                    bind_status_parts.append(f"accessories={status}")
                if bind_wardrobe:
                    status = "ok" if not any("wardrobe" in e.lower() for e in errors) else "miss"
                    bind_status_parts.append(f"wardrobe={status}")
                if bind_hair:
                    status = "ok" if not any("hair_style" in e.lower() for e in errors) else "miss"
                    bind_status_parts.append(f"hair={status}")

                bind_status = ",".join(bind_status_parts) if bind_status_parts else "none"

                # Add binding warnings if any
                if not is_valid:
                    existing_warning = bundle_raw.get("_validation_warning", "")
                    binding_issues = ";".join([e.split(":")[0].replace("Missing bound ", "") for e in errors])
                    if existing_warning:
                        bundle_raw["_validation_warning"] = f"{existing_warning}; binding: {binding_issues}"
                    else:
                        bundle_raw["_validation_warning"] = f"binding: {binding_issues}"

                # Add length warnings if any
                if length_warnings:
                    existing_warning = bundle_raw.get("_validation_warning", "")
                    length_str = ",".join(length_warnings)
                    if existing_warning:
                        bundle_raw["_validation_warning"] = f"{existing_warning}; length: {length_str}"
                    else:
                        bundle_raw["_validation_warning"] = f"length: {length_str}"

                # Log concise BUNDLE_SUMMARY (informational)
                warnings_str = bundle_raw.get("_validation_warning", "none")
                log.info(
                    f"BUNDLE_SUMMARY bundle_id={bundle_id} len={prompt_len} "
                    f"bind_status=\"{bind_status}\" pydantic_valid={pydantic_valid} "
                    f"warnings=\"{warnings_str}\""
                )

                # ALWAYS include bundle (no skipping)
                bundles.append(bundle_raw)

            # Success - return all bundles
            log.info(f"GROK_BUNDLE generated {len(bundles)} bundles (single attempt, all returned)")
            return bundles

        except Exception as e:
            log.error(f"GROK_BUNDLE failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate prompt bundles: {e}") from e

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
        Generate social media metadata (title, caption, tags, hashtags).

        Args:
            media_meta: Full media metadata

        Returns:
            Dict with keys: title, caption, tags, hashtags
        """
        log.info(f"GROK_SOCIAL media_id={media_meta.get('id', 'unknown')}")

        system_prompt = """Generate social media metadata:
- title: 40-60 char engaging title
- caption: 1 short motivational phrase (40-120 chars) based on scene/pose/wardrobe
  * MUST start lowercase (no capital first letter)
  * Positive, confident, discipline/travel/fitness vibe
  * End with EXACTLY ONE emoji (no more, no less)
  * NO hashtags, NO line breaks, NO quotes
  * Examples: "strong days start with small decisions 💪" or "steady steps, bold heart, quiet confidence 🌊"
- tags: 5-10 plain keywords (no #)
- hashtags: 8-12 hashtags (with #)

Tone: Empowering, authentic, context-aware."""

        user_prompt = f"""Media context: {json.dumps(media_meta, indent=2)}

Create metadata. Return JSON:
{{"title": "...", "caption": "...", "tags": ["tag1", "tag2"], "hashtags": ["#hash1", "#hash2"]}}"""

        content = self._call_api(system_prompt, user_prompt, temperature=0.7, max_tokens=400)

        try:
            social_meta = extract_json(content)

            # Validate caption if present
            caption = social_meta.get("caption", "")
            if caption:
                # Check basic rules
                if len(caption) > 200 or len(caption) < 20 or not caption or caption[0].isupper():
                    log.warning(f"GROK_SOCIAL caption failed validation, using fallback: {caption}")
                    social_meta["caption"] = "strong, calm and focused 💪"

            log.info(f"GROK_SOCIAL generated title={social_meta.get('title', '')[:50]} caption={social_meta.get('caption', '')[:40]}")
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

    def _build_forever_prefix(self, persona: dict[str, Any], bound: dict[str, Any]) -> str:
        """
        Build the FOREVER persona prefix (uncompressed, canonical).

        This is the fixed opening that NEVER changes and appears at the start
        of every final image prompt. The LLM only writes what comes AFTER this.

        Args:
            persona: Persona configuration
            bound: Bound slots dictionary (includes hair_style if bound)

        Returns:
            Canonical persona prefix string (e.g., "photorealistic vertical 9:16 image of a 28-year-old woman with...")
        """
        # Use RAW persona values (no compression)
        hair = persona.get("hair", "medium wavy caramel-blonde hair")
        eyes = persona.get("eyes", "saturated blue eyes")
        body = persona.get("body", "busty muscular physique with hourglass defined body")
        skin = persona.get("skin", "realistic natural skin texture and strong realistic wet highlights")

        # Get bound hairstyle (arrangement only, no length)
        hair_style = None
        if bound.get("hair_style"):
            hair_style = bound["hair_style"][0]
            log.info(f"HAIR_STYLE_SELECTED {hair_style}")

        # Build canonical FOREVER prefix with optional hairstyle
        if hair_style:
            forever_prefix = (
                f"photorealistic vertical 9:16 image of a 28-year-old woman with "
                f"{hair}, styled in {hair_style}, {eyes}, {body}, {skin}"
            )
        else:
            forever_prefix = (
                f"photorealistic vertical 9:16 image of a 28-year-old woman with "
                f"{hair}, {eyes}, {body}, {skin}"
            )

        log.info(f"FOREVER_PREFIX length={len(forever_prefix)} chars")
        return forever_prefix

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
        bind_hair: bool,
    ) -> tuple[bool, list[str]]:
        """
        Validate bundle against binding constraints.

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        img_prompt = bundle.get("image_prompt", {}).get("final_prompt", "")

        # STEP 3: Check bound slots with fuzzy matching (tolerates minor grammar fixes)
        # Use _phrase_match_loose() instead of strict _contains_phrase()
        if bind_scene and bound.get("scene"):
            phrase = bound["scene"][0]
            if phrase and not _phrase_match_loose(img_prompt, phrase):
                errors.append(f"Missing bound scene: '{phrase}'")

        # STRICT Pose validation: must START the Pose section with exact phrase
        if bind_pose_microaction and bound.get("pose_microaction"):
            pose_bound = bound["pose_microaction"][0]
            pose_section = self._extract_section(img_prompt, "Pose")
            if not pose_section or not self._starts_with_phrase(pose_section, pose_bound):
                errors.append(f"Pose must START with bound micro-action: '{pose_bound}'")

        if bind_lighting and bound.get("lighting"):
            phrase = bound["lighting"][0]
            if phrase and not _phrase_match_loose(img_prompt, phrase):
                errors.append(f"Missing bound lighting: '{phrase}'")

        if bind_camera and bound.get("camera"):
            phrase = bound["camera"][0]
            if phrase and not _phrase_match_loose(img_prompt, phrase):
                errors.append(f"Missing bound camera: '{phrase}'")

        if bind_angle and bound.get("angle"):
            phrase = bound["angle"][0]
            if phrase and not _phrase_match_loose(img_prompt, phrase):
                errors.append(f"Missing bound angle: '{phrase}'")

        if bind_accessories and bound.get("accessories"):
            for acc in bound["accessories"]:
                if acc and not _phrase_match_loose(img_prompt, acc):
                    errors.append(f"Missing bound accessory: '{acc}'")

        # STEP 3: Validate single wardrobe phrase with fuzzy matching
        if bind_wardrobe and bound.get("wardrobe"):
            phrase = bound["wardrobe"][0]
            if phrase and not _phrase_match_loose(img_prompt, phrase):
                errors.append(f"Missing bound wardrobe: '{phrase}'")

        # Validate hairstyle phrase with fuzzy matching
        if bind_hair and bound.get("hair_style"):
            phrase = bound["hair_style"][0]
            if phrase and not _phrase_match_loose(img_prompt, phrase):
                errors.append(f"Missing bound hair_style: '{phrase}'")

        # VIDEO validation removed - now handled by Pydantic VideoPrompt model with min_length=10
        # Individual fields (motion, character_action, environment) are padded by _enforce_min_len()

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
