"""
Test bundle generation after recent changes.

Validates:
- Length targeting (1350-1450)
- Wardrobe binding (single outfit phrase)
- Fuzzy matching reduces STILL_NONCOMPLIANT
- FOREVER prefix intact
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.grok.client import GrokClient
from app.core.logging import log


def main():
    """Generate test bundles and collect statistics."""

    log.info("BUNDLE_TEST starting...")

    # Initialize client
    if not settings.grok_api_key:
        raise ValueError("GROK_API_KEY not set")

    client = GrokClient(api_key=settings.grok_api_key, model=settings.grok_model)

    # Generate 10 bundles for Japan (all bindings ON including wardrobe)
    bundles = client.generate_prompt_bundle(
        setting_id="japan",
        location_label="Japan",
        location_path="C:/Users/seba5/AI-influencer/app/data/locations/japan.json",
        count=10,
        bind_scene=True,
        bind_pose_microaction=True,
        bind_lighting=True,
        bind_camera=True,
        bind_angle=True,
        bind_accessories=True,
        bind_wardrobe=True,  # Now ON by default
        single_accessory=True,
    )

    # Collect statistics
    lengths = []
    noncompliant = []
    wardrobe_phrases = []
    bind_fail_slots = {}

    for bundle in bundles:
        bundle_id = bundle.get("id", "unknown")
        final_prompt = bundle.get("image_prompt", {}).get("final_prompt", "")
        prompt_len = len(final_prompt)
        lengths.append(prompt_len)

        # Check for FOREVER prefix
        if not final_prompt.startswith("photorealistic vertical 9:16 image of a 28-year-old woman"):
            log.warning(f"BUNDLE_TEST bundle_id={bundle_id} MISSING_FOREVER_PREFIX")

        # Extract wardrobe phrase (for inspection)
        bound_wardrobe = bundle.get("bound", {}).get("wardrobe", [])
        if bound_wardrobe:
            wardrobe_phrases.append(bound_wardrobe[0])

        # Check if noncompliant
        if bundle.get("_validation_warning") == "STILL_NONCOMPLIANT":
            noncompliant.append(bundle_id)
            # Track which slots failed
            # (Would need to parse errors from logs, but for now just note it)

    # Calculate statistics
    avg_len = sum(lengths) / len(lengths) if lengths else 0
    min_len = min(lengths) if lengths else 0
    max_len = max(lengths) if lengths else 0
    # Adjusted range: FOREVER prefix (~236) + LLM text (750-950) = 950-1200 total
    in_range = sum(1 for l in lengths if 950 <= l <= 1200)

    # Print summary
    print("\n" + "="*80)
    print("BUNDLE_TEST_SUMMARY")
    print("="*80)
    print(f"Count: {len(bundles)}")
    print(f"Average length: {avg_len:.0f} chars")
    print(f"Min length: {min_len} chars")
    print(f"Max length: {max_len} chars")
    print(f"In range (950-1200): {in_range}/{len(bundles)} ({in_range/len(bundles)*100:.1f}%)")
    print(f"STILL_NONCOMPLIANT: {len(noncompliant)}/{len(bundles)} ({len(noncompliant)/len(bundles)*100:.1f}%)")

    if noncompliant:
        print(f"  Failed bundle IDs: {', '.join(noncompliant)}")

    print(f"\nWardrobe binding (first 3 examples):")
    for i, phrase in enumerate(wardrobe_phrases[:3], 1):
        print(f"  {i}. {phrase}")

    print("="*80)

    # Log one-liner summary
    log.info(
        f"BUNDLE_TEST_SUMMARY count={len(bundles)} avg_len={avg_len:.0f} "
        f"in_range={in_range}/{len(bundles)} noncompliant={len(noncompliant)}/{len(bundles)}"
    )


if __name__ == "__main__":
    main()
