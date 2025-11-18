"""Diagnostic script for prompt length analysis."""
import json
import statistics
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.grok.client import GrokClient


def main():
    """Generate 50 prompts and analyze lengths."""
    client = GrokClient(api_key=settings.grok_api_key, model=settings.grok_model)

    # Test configuration (all bindings ON as per UI default)
    location_id = "japan"
    location_label = "Japan"
    location_path = str(Path(__file__).parent / "app" / "data" / "locations" / "japan.json")

    results = []
    section_counts = {
        "Character": 0,
        "Scene": 0,
        "Camera": 0,
        "Angle": 0,
        "Wardrobe": 0,
        "Accessories": 0,
        "Pose": 0,
        "Lighting": 0,
        "Environment": 0,
    }

    print("Generating 50 prompts for diagnostic analysis...")
    print("Configuration: all bindings ON, single accessory")
    print("-" * 80)

    for i in range(50):
        try:
            bundles = client.generate_prompt_bundle(
                setting_id=location_id,
                location_label=location_label,
                location_path=location_path,
                seed_words=None,
                count=1,
                bind_scene=True,
                bind_pose_microaction=True,
                bind_lighting=True,
                bind_camera=True,
                bind_angle=True,
                bind_accessories=True,
                bind_wardrobe=False,  # Default is OFF (inspire-only)
                single_accessory=True,
            )

            if bundles:
                bundle = bundles[0]
                image_prompt = bundle["image_prompt"]["final_prompt"]
                length = len(image_prompt)
                results.append({
                    "id": bundle["id"],
                    "length": length,
                    "prompt": image_prompt,
                })

                # Count sections
                prompt_lower = image_prompt.lower()
                if "character:" in prompt_lower or "medium wavy" in prompt_lower:
                    section_counts["Character"] += 1
                if "scene:" in prompt_lower or "<scene>" in image_prompt:
                    section_counts["Scene"] += 1
                if "camera:" in prompt_lower or "<camera>" in image_prompt:
                    section_counts["Camera"] += 1
                if "angle:" in prompt_lower or "<angle>" in image_prompt:
                    section_counts["Angle"] += 1
                if "wardrobe:" in prompt_lower:
                    section_counts["Wardrobe"] += 1
                if "accessories:" in prompt_lower or "<accessories>" in image_prompt:
                    section_counts["Accessories"] += 1
                if "pose:" in prompt_lower:
                    section_counts["Pose"] += 1
                if "lighting:" in prompt_lower or "<lighting>" in image_prompt:
                    section_counts["Lighting"] += 1
                if "environment:" in prompt_lower:
                    section_counts["Environment"] += 1

                print(f"✓ {i+1}/50 | Length: {length} chars | ID: {bundle['id'][:16]}...")

        except Exception as e:
            print(f"✗ {i+1}/50 | Error: {e}")

    # Analyze results
    if results:
        lengths = [r["length"] for r in results]
        mean_len = statistics.mean(lengths)
        median_len = statistics.median(lengths)
        stdev_len = statistics.stdev(lengths) if len(lengths) > 1 else 0
        min_len = min(lengths)
        max_len = max(lengths)
        in_target = sum(1 for l in lengths if 1300 <= l <= 1450)
        pct_target = (in_target / len(lengths)) * 100 if lengths else 0

        # Save results
        output_path = Path(__file__).parent / "app" / "data" / "debug"
        output_path.mkdir(parents=True, exist_ok=True)

        with open(output_path / "length_probe.jsonl", "w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        # Print report
        print("\n" + "=" * 80)
        print("DIAGNOSTIC RESULTS")
        print("=" * 80)
        print(f"\nN:                {len(lengths)}")
        print(f"Mean:             {mean_len:.1f} chars")
        print(f"Median:           {median_len:.1f} chars")
        print(f"Std Dev:          {stdev_len:.1f}")
        print(f"Min:              {min_len}")
        print(f"Max:              {max_len}")
        print(f"% in [1300-1450]: {pct_target:.1f}%")

        print(f"\nSECTION PRESENCE (out of {len(results)}):")
        print("-" * 40)
        for section, count in section_counts.items():
            print(f"{section:15} {count}/{len(results)}")

        # Sample 3 prompts
        print(f"\nSAMPLE PROMPTS (first 3):")
        print("-" * 80)
        for i, r in enumerate(results[:3]):
            print(f"\n[Sample {i+1}] ID: {r['id']} | Length: {r['length']}")
            print(r['prompt'][:500] + "..." if len(r['prompt']) > 500 else r['prompt'])

        print(f"\nResults saved to: {output_path / 'length_probe.jsonl'}")
    else:
        print("\n✗ No successful generations")


if __name__ == "__main__":
    main()
