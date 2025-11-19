#!/usr/bin/env python3
"""
Process wardrobe generation outputs from parallel Claude agents.

Combines, deduplicates, validates, and audits 3,000 athletic wardrobe items.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "app" / "data"
WARDROBE_DIR = DATA_DIR / "wardrobe"
AUDITS_DIR = DATA_DIR / "audits"
VARIETY_BANK_PATH = DATA_DIR / "variety_bank.json"

# Policy: banned terms (SFW enforcement)
BANNED_KEYWORDS = [
    "lingerie", "bra cup", "underwire", "lace", "garter", "thong",
    "see-through", "sheer bra", "pasties", "nipple", "nude",
    "transparent nipple", "boudoir", "fetish", "erotic", "NSFW"
]

# Deduplication threshold
SIMILARITY_THRESHOLD = 0.82

# Target count
TARGET_COUNT = 3000


# =============================================================================
# UTILITIES
# =============================================================================

def normalize_text(text: str) -> str:
    """Normalize text for deduplication: lowercase, collapse spaces, strip."""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s-]', '', text)
    return text.strip()


def semantic_similarity(text1: str, text2: str) -> float:
    """Calculate semantic similarity using sequence matching."""
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    return SequenceMatcher(None, norm1, norm2).ratio()


def validate_char_length(text: str) -> bool:
    """Validate character count is within 55-90."""
    return 55 <= len(text) <= 90


def has_banned_terms(text: str) -> str | None:
    """Check for banned terms. Returns term if found, None otherwise."""
    text_lower = text.lower()
    for term in BANNED_KEYWORDS:
        if term in text_lower:
            return term
    return None


def extract_color(text: str) -> str | None:
    """Extract color from text (simple heuristic)."""
    colors = [
        "orchid", "caramel", "electric-blue", "graphite", "jade", "teal",
        "charcoal", "ivory", "pearl", "midnight", "coral", "onyx", "amber",
        "opal", "polar silver", "cobalt", "chalk", "sandstone", "moss", "rust",
        "plum", "sage", "ink", "bone", "storm", "obsidian", "forest", "navy",
        "burgundy", "slate", "lilac", "indigo", "bronze", "copper", "crimson",
        "violet", "emerald", "sapphire", "ruby", "magenta", "tangerine", "lime",
        "peach", "lavender", "rose", "mint", "berry", "honey", "cream", "gold",
        "silver", "black", "white", "grey", "gray", "blue", "green", "red",
        "pink", "purple", "orange", "yellow", "brown"
    ]

    text_lower = text.lower()
    for color in colors:
        if color in text_lower:
            return color
    return "neutral"


def extract_archetype(text: str) -> str:
    """Extract garment archetype (heuristic)."""
    text_lower = text.lower()

    # Fitness
    if any(w in text_lower for w in ["crop", "bra", "sports bra"]):
        return "crop_bra"
    if "legging" in text_lower or "tight" in text_lower:
        return "leggings"
    if "short" in text_lower and any(w in text_lower for w in ["bike", "compression", "biker"]):
        return "shorts"
    if "unitard" in text_lower or "bodysuit" in text_lower:
        return "unitard"
    if "tank" in text_lower or "singlet" in text_lower:
        return "tank"

    # Streetfit
    if "jacket" in text_lower:
        return "jacket"
    if "hoodie" in text_lower or "sweatshirt" in text_lower:
        return "hoodie"
    if "jogger" in text_lower or ("pant" in text_lower and "track" in text_lower):
        return "joggers"

    # Bikini
    if "bikini" in text_lower or "swim" in text_lower:
        return "swim"

    return "other"


def calculate_shannon_entropy(items: list[dict[str, Any]]) -> float:
    """Calculate Shannon entropy over text tokens."""
    words: list[str] = []
    for item in items:
        tokens = normalize_text(item["text"]).split()
        words.extend([t for t in tokens if len(t) > 3])

    if not words:
        return 0.0

    total = len(words)
    counts = Counter(words)
    entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
    return round(entropy, 2)


# =============================================================================
# DEDUPLICATION
# =============================================================================

def deduplicate_items(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """
    Deduplicate items using exact + semantic matching.

    Returns:
        (deduplicated_items, {"exact": [...], "semantic": [...]})
    """
    seen_exact: set[str] = set()
    seen_semantic: list[str] = []
    deduplicated: list[dict[str, Any]] = []
    duplicates = {"exact": [], "semantic": []}

    for item in items:
        text = item["text"]
        norm = normalize_text(text)

        # Exact duplicate check
        if norm in seen_exact:
            if len(duplicates["exact"]) < 20:
                duplicates["exact"].append(text)
            continue

        # Semantic duplicate check
        is_duplicate = False
        for seen_text in seen_semantic:
            if semantic_similarity(text, seen_text) >= SIMILARITY_THRESHOLD:
                is_duplicate = True
                if len(duplicates["semantic"]) < 20:
                    duplicates["semantic"].append(f"{text} H {seen_text}")
                break

        if not is_duplicate:
            seen_exact.add(norm)
            seen_semantic.append(text)
            deduplicated.append(item)

    return deduplicated, duplicates


# =============================================================================
# VALIDATION
# =============================================================================

def validate_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Validate items for SFW policy, char limits, diversity.

    Returns validation report.
    """
    report = {
        "total_items": len(items),
        "char_length_violations": [],
        "policy_violations": [],
        "valid_items": [],
        "diversity": {
            "colors": Counter(),
            "archetypes": Counter(),
        }
    }

    for item in items:
        text = item["text"]

        # Check character length
        if not validate_char_length(text):
            if len(report["char_length_violations"]) < 10:
                report["char_length_violations"].append(f"{text} ({len(text)} chars)")
            continue

        # Check for banned terms
        banned_term = has_banned_terms(text)
        if banned_term:
            if len(report["policy_violations"]) < 10:
                report["policy_violations"].append(f"{text} (contains: {banned_term})")
            continue

        # Valid item
        report["valid_items"].append(item)

        # Track diversity
        color = extract_color(text)
        archetype = extract_archetype(text)
        report["diversity"]["colors"][color] += 1
        report["diversity"]["archetypes"][archetype] += 1

    return report


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def main() -> None:
    """Main processing coordinator."""
    print("=" * 80)
    print("WARDROBE PROCESSING - CLAUDE PARALLEL AGENTS")
    print("=" * 80)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Load all agent outputs (including extras and bonus)
    agent_files = [
        "fitness_1.json", "fitness_2.json", "fitness_3.json", "fitness_4.json", "fitness_extra.json",
        "streetfit_1.json", "streetfit_2.json", "streetfit_3.json", "streetfit_4.json",
        "bikini_1.json", "bikini_2.json", "bikini_3.json", "bikini_4.json",
        "bonus_1.json", "bonus_2.json", "bonus_3.json", "bonus_4.json"
    ]

    print("\n[STEP 1] Loading agent outputs...")
    all_items: list[dict[str, Any]] = []

    for filename in agent_files:
        filepath = WARDROBE_DIR / filename
        if not filepath.exists():
            print(f"   Missing: {filename}")
            continue

        with filepath.open("r", encoding="utf-8") as f:
            items = json.load(f)
            all_items.extend(items)
            print(f"   {filename}: {len(items)} items")

    print(f"\nTotal raw items: {len(all_items)}")

    # Deduplication
    print("\n[STEP 2] Applying deduplication (threshold: {:.0%})...".format(SIMILARITY_THRESHOLD))
    deduped_items, duplicates = deduplicate_items(all_items)

    print(f"  • Exact duplicates removed: {len(duplicates['exact'])}")
    print(f"  • Semantic duplicates removed: {len(duplicates['semantic'])}")
    print(f"  • After deduplication: {len(deduped_items)} items")

    # Validation
    print("\n[STEP 3] Validating items (SFW, char limits, diversity)...")
    validation_report = validate_items(deduped_items)

    print(f"  • Character violations: {len(validation_report['char_length_violations'])}")
    print(f"  • Policy violations: {len(validation_report['policy_violations'])}")
    print(f"  • Valid items: {len(validation_report['valid_items'])}")

    # Take first 3000 valid items
    final_items = validation_report['valid_items'][:TARGET_COUNT]

    print(f"\n[STEP 4] Final wardrobe count: {len(final_items)}")

    # Save wardrobe.json
    wardrobe_path = WARDROBE_DIR / "wardrobe.json"
    with wardrobe_path.open("w", encoding="utf-8") as f:
        json.dump(final_items, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"   Saved to: {wardrobe_path}")

    # Calculate diversity metrics
    print("\n[STEP 5] Calculating diversity metrics...")

    color_counts = validation_report['diversity']['colors'].most_common()
    archetype_counts = validation_report['diversity']['archetypes'].most_common()

    total = len(final_items)
    max_color_pct = (color_counts[0][1] / total * 100) if color_counts else 0
    max_archetype_pct = (archetype_counts[0][1] / total * 100) if archetype_counts else 0

    colors_entropy = calculate_shannon_entropy(final_items)

    print(f"  • Color diversity: {len(color_counts)} unique colors")
    print(f"  • Max color %: {max_color_pct:.1f}% ({color_counts[0][0] if color_counts else 'N/A'})")
    print(f"  • Archetype diversity: {len(archetype_counts)} types")
    print(f"  • Max archetype %: {max_archetype_pct:.1f}% ({archetype_counts[0][0] if archetype_counts else 'N/A'})")
    print(f"  • Shannon entropy: {colors_entropy} bits")

    # Generate audit
    audit = {
        "timestamp": timestamp,
        "counts": {
            "wardrobe": len(final_items)
        },
        "diversity": {
            "colors": {
                "entropy_bits": colors_entropy,
                "hist": dict(color_counts[:30])
            },
            "archetypes": {
                "hist": dict(archetype_counts)
            }
        },
        "dedupe": {
            "raw_in": len(all_items),
            "removed": len(all_items) - len(deduped_items),
            "examples": duplicates["exact"][:5] + duplicates["semantic"][:5]
        },
        "policy_rejections": {
            "count": len(validation_report["policy_violations"]),
            "examples": validation_report["policy_violations"][:5]
        },
        "char_violations": {
            "count": len(validation_report["char_length_violations"]),
            "examples": validation_report["char_length_violations"][:5]
        }
    }

    # Save audit
    audit_path = AUDITS_DIR / f"wardrobe_audit_{timestamp}.json"
    AUDITS_DIR.mkdir(parents=True, exist_ok=True)

    with audit_path.open("w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"   Audit saved to: {audit_path}")

    # Update variety_bank.json
    print("\n[STEP 6] Updating variety_bank.json...")

    with VARIETY_BANK_PATH.open("r", encoding="utf-8") as f:
        variety_bank = json.load(f)

    # Replace wardrobe slot
    variety_bank["wardrobe"] = final_items

    with VARIETY_BANK_PATH.open("w", encoding="utf-8") as f:
        json.dump(variety_bank, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"   Updated variety_bank.json with {len(final_items)} wardrobe items")

    # Summary
    print("\n" + "=" * 80)
    print("PROCESSING COMPLETE")
    print("=" * 80)
    print(f"Final wardrobe count: {len(final_items)}")
    print(f"Color entropy: {colors_entropy} bits (target: e3.0)")
    print(f"Max color %: {max_color_pct:.1f}% (target: <15%)")
    print(f"Max archetype %: {max_archetype_pct:.1f}% (target: <15%)")
    print(f"Policy violations: {audit['policy_rejections']['count']} (target: 0)")
    print(f"\nFiles created:")
    print(f"  • {wardrobe_path}")
    print(f"  • {audit_path}")
    print(f"  • {VARIETY_BANK_PATH} (updated)")
    print("=" * 80)


if __name__ == "__main__":
    main()
