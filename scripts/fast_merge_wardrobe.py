#!/usr/bin/env python3
"""
Fast merge: combine existing validated wardrobe with new bonus items.
Skips deduplication for speed.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "app" / "data"
WARDROBE_DIR = DATA_DIR / "wardrobe"
VARIETY_BANK_PATH = DATA_DIR / "variety_bank.json"

# SFW policy
BANNED_KEYWORDS = [
    "lingerie", "bra cup", "underwire", "lace", "garter", "thong",
    "see-through", "sheer bra", "pasties", "nipple", "nude",
    "transparent nipple", "boudoir", "fetish", "erotic", "NSFW"
]

TARGET_COUNT = 3000


def has_banned_terms(text: str) -> str | None:
    """Check for banned terms."""
    text_lower = text.lower()
    for term in BANNED_KEYWORDS:
        if term in text_lower:
            return term
    return None


def validate_char_length(text: str) -> bool:
    """Validate character count is within 55-90."""
    return 55 <= len(text) <= 90


def main() -> None:
    print("=" * 80)
    print("FAST WARDROBE MERGE")
    print("=" * 80)

    # Load existing validated wardrobe
    print("\n[1/5] Loading existing validated wardrobe...")
    existing_wardrobe_path = WARDROBE_DIR / "wardrobe.json"

    if existing_wardrobe_path.exists():
        with existing_wardrobe_path.open("r", encoding="utf-8") as f:
            existing_items = json.load(f)
        print(f"  Loaded {len(existing_items)} existing validated items")
    else:
        existing_items = []
        print("  No existing wardrobe found, starting fresh")

    # Load and validate bonus files
    print("\n[2/5] Loading and validating bonus files...")
    bonus_files = ["bonus_1.json", "bonus_2.json", "bonus_3.json", "bonus_4.json", "final_batch.json"]
    bonus_items = []
    policy_violations = 0
    char_violations = 0

    for filename in bonus_files:
        filepath = WARDROBE_DIR / filename
        if not filepath.exists():
            print(f"  SKIP Missing: {filename}")
            continue

        with filepath.open("r", encoding="utf-8") as f:
            items = json.load(f)

        # Validate each item
        valid_count = 0
        for item in items:
            text = item["text"]

            # Character length check
            if not validate_char_length(text):
                char_violations += 1
                continue

            # SFW policy check
            if has_banned_terms(text):
                policy_violations += 1
                continue

            bonus_items.append(item)
            valid_count += 1

        print(f"  OK {filename}: {valid_count}/{len(items)} valid")

    print(f"\n  Total bonus items validated: {len(bonus_items)}")
    print(f"  Policy violations: {policy_violations}")
    print(f"  Character violations: {char_violations}")

    # Merge
    print("\n[3/5] Merging wardrobes...")
    all_items = existing_items + bonus_items
    print(f"  Combined total: {len(all_items)} items")

    # Take first 3000
    final_items = all_items[:TARGET_COUNT]
    print(f"\n[4/5] Taking first {TARGET_COUNT} items: {len(final_items)}")

    # Save wardrobe.json
    with existing_wardrobe_path.open("w", encoding="utf-8") as f:
        json.dump(final_items, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  Saved to: {existing_wardrobe_path}")

    # Update variety_bank.json
    print("\n[5/5] Updating variety_bank.json...")
    with VARIETY_BANK_PATH.open("r", encoding="utf-8") as f:
        variety_bank = json.load(f)

    variety_bank["wardrobe"] = final_items

    with VARIETY_BANK_PATH.open("w", encoding="utf-8") as f:
        json.dump(variety_bank, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  Updated variety_bank.json with {len(final_items)} items")

    print("\n" + "=" * 80)
    print("MERGE COMPLETE")
    print("=" * 80)
    print(f"Final wardrobe count: {len(final_items)}")
    print(f"  Existing validated: {len(existing_items)}")
    print(f"  New bonus added: {len(bonus_items)}")
    print("=" * 80)


if __name__ == "__main__":
    main()
