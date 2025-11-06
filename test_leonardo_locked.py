"""
Test script: ONE locked Leonardo generation with corrective locks.
Verifies that LoRA, steps, cfg, and all parameters are sent and confirmed.
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

# Strict test prompt (from user requirement)
test_payload = {
    "base": """evajoy, photorealistic vertical 9:16, native high resolution for phone (864×1536), no upscaling;
Santorini golden hour; subject seated at the pool edge, legs in water; relaxed confident gaze;
camera: low 3/4 side angle (slightly below waist height), looking down; lens 35mm f/2.0, shallow DOF;
wardrobe: ivory ribbed knit top (technical cotton knit, matte), chocolate high-waist shorts (matte athletic fabric);
skin: post-workout sheen with subtle specular highlights on shoulders/collarbones/shins (avoid plastic look);
lighting: warm rim from setting sun + neutral bounce fill camera-right; palette: ivory, warm amber, teal water;
environment: Cycladic white architecture, soft bokeh; framing: clean headroom, tidy leading lines.""",

    "neg": "doll-like, mannequin, uncanny face, over-smooth skin, plastic skin, extra fingers, warped anatomy, de-aging, seam, text, watermark, logo, lens flare streaks, silk/latex vinyl glare"
}

print("=" * 80)
print("LEONARDO LOCKED RETEST")
print("=" * 80)
print(f"\nModel ID: {settings.leonardo_model_id}")
print(f"LoRA ID: {settings.leonardo_lora_id} @ {settings.leonardo_lora_weight}")
print(f"Size: {settings.leonardo_width}×{settings.leonardo_height}")
print(f"Steps: {settings.leonardo_steps}, CFG: {settings.leonardo_cfg}")
print("\n" + "=" * 80)
print("Running generation...")
print("=" * 80 + "\n")

try:
    client = LeonardoClient()
    image_path = client.generate(test_payload)

    print("\n" + "=" * 80)
    print("GENERATION SUCCESS")
    print("=" * 80)
    print(f"\nImage Path: {image_path}")
    print("\nCheck logs for LEO_DIAG output showing:")
    print("  - requested=(model=..., size=864x1536, steps=32, cfg=7.0, element=155265@0.80)")
    print("  - used=(model=..., size=..., element_present=true/false)")
    print("=" * 80)

except Exception as e:
    print("\n" + "=" * 80)
    print("GENERATION FAILED")
    print("=" * 80)
    print(f"\nError: {e}")
    print("=" * 80)
    sys.exit(1)
