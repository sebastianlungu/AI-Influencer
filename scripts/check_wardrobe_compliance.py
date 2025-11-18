#!/usr/bin/env python3
"""Check wardrobe compliance metrics."""

import json
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).parent.parent
VARIETY_BANK_PATH = BASE_DIR / "app" / "data" / "variety_bank.json"

with VARIETY_BANK_PATH.open("r", encoding="utf-8") as f:
    data = json.load(f)

wardrobe = data["wardrobe"]
lengths = [len(item["text"]) for item in wardrobe]

print("=" * 60)
print("WARDROBE COMPLIANCE CHECK")
print("=" * 60)
print(f"\nTotal items: {len(lengths)}")
print(f"Min length: {min(lengths)} chars")
print(f"Max length: {max(lengths)} chars")
print(f"Avg length: {sum(lengths)/len(lengths):.1f} chars")

print("\n Character count distribution:")
dist = Counter(lengths)
for length in sorted(dist.keys())[:10]:
    print(f"  {length} chars: {dist[length]} items")
print("  ...")
for length in sorted(dist.keys())[-10:]:
    print(f"  {length} chars: {dist[length]} items")

violations = [item["text"] for item in wardrobe if len(item["text"]) < 55 or len(item["text"]) > 90]
print(f"\nCharacter violations (< 55 or > 90): {len(violations)}")

if violations:
    print("\nViolation examples:")
    for v in violations[:5]:
        print(f"  - {len(v)} chars: {v}")

print("\n" + "=" * 60)
print(f"COMPLIANCE: {'PASS' if len(violations) == 0 else 'FAIL'}")
print("=" * 60)
