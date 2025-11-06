"""
P0 Test: Single Leonardo generation with exact spec.
- Native 9:16 (864×1536)
- LoRA 155265@0.80 (FAIL LOUD if not applied)
- Caramel-blonde hair (NOT brunette)
"""
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.clients.leonardo import LeonardoClient
from app.core.config import settings

# Verify ALLOW_LIVE
if not settings.allow_live:
    print("ERROR: ALLOW_LIVE=false. Set ALLOW_LIVE=true in .env to run test.")
    sys.exit(1)

# EXACT PROMPT SPEC (caramel-blonde, NOT brunette)
test_payload = {
    "base": """evajoy, photorealistic vertical 9:16 (native 864×1536, no upscaling);
medium-length wavy caramel-blonde hair; striking blue eyes; athletic, curvy, muscular fitness model with defined abs and toned arms; natural daylight; clean composition with soft warm rim light and neutral bounce fill; realistic skin with subtle post-workout sheen (no plastic look); single clear scene; 35mm lens at f/2.0; shallow depth of field; editorial sport aesthetic with clean headroom and strong leading lines.
Stadium tunnel cooling zone; low 3/4 side angle; ponytail adjustment gesture.""",

    "neg": "doll-like, uncanny face, plastic skin, over-smooth, extra fingers, warped limbs, de-aging artifacts, text, watermark, logo, lens flare streaks, latex/super-gloss fabrics"
}

print("=" * 80)
print("LEONARDO P0 TEST: Native 9:16 + LoRA 155265 (FAIL LOUD)")
print("=" * 80)
print(f"\nModel ID: {settings.leonardo_model_id}")
print(f"LoRA: {settings.leonardo_lora_id}@{settings.leonardo_lora_weight}")
print(f"Size: {settings.leonardo_width}×{settings.leonardo_height}")
print(f"Steps: {settings.leonardo_steps}, CFG: {settings.leonardo_cfg}")
print(f"FORBID_FALLBACKS: {settings.leonardo_forbid_fallbacks}")
print("\n" + "=" * 80)
print("Generating...")
print("=" * 80 + "\n")

try:
    client = LeonardoClient()
    image_path = client.generate(test_payload)

    print("\n" + "=" * 80)
    print("SUCCESS")
    print("=" * 80)
    print(f"\nImage Path: {image_path}")
    print(f"\nPrompt (first 160 chars): {test_payload['base'][:160]}")
    print("\nCheck logs for LEO_DIAG line showing:")
    print("  requested=(model=... size=864x1536 steps=32 cfg=7.0 lora=155265@0.80)")
    print("  applied=(lora_present=true/false) gen_id=... path=...")
    print("=" * 80)

except Exception as e:
    print("\n" + "=" * 80)
    print("FAILED (FAIL-LOUD WORKED)")
    print("=" * 80)
    print(f"\nError: {e}")
    print("\nThis is EXPECTED if Leonardo ignores LoRA (FORBID_FALLBACKS=true)")
    print("=" * 80)
    sys.exit(1)
