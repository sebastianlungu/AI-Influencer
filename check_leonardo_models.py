import os
import httpx
import json

api_key = os.getenv("LEONARDO_API_KEY")
headers = {"Authorization": f"Bearer {api_key}"}

# Query platform models
resp = httpx.get("https://cloud.leonardo.ai/api/rest/v1/platformModels", headers=headers, timeout=15)
data = resp.json()

target_id = "aa77f04e-3eec-4034-9c07-d0f619684628"

print("=" * 80)
print("LEONARDO MODEL QUERY")
print("=" * 80)
print("\nAPI Response Keys:", list(data.keys()))
print("="  * 80)

# Check all model sources
all_models = []
if "custom_models" in data:
    all_models.extend([("custom", m) for m in data["custom_models"]])
for key in data.keys():
    if key not in ["custom_models"] and isinstance(data[key], list):
        all_models.extend([(key, m) for m in data[key] if isinstance(m, dict)])

for source, model in all_models:
    if (target_id in str(model.get("id", "")) or
        "Vision" in model.get("name", "") or
        "Nano" in model.get("name", "") or
        "Nana" in model.get("name", "") or
        "Banana" in model.get("name", "") or
        "Kino" in model.get("name", "")):
        print(f"\n[{source}] Model: {model.get('name')}")
        print(f"ID: {model.get('id')}")
        print(f"Description: {model.get('description', 'N/A')[:100]}")
        if model.get("id") == target_id:
            print("*** THIS IS THE CURRENT MODEL ***")

print("\n" + "=" * 80)
print("CHECKING FOR TARGET MODEL:", target_id)
found = False
for source, model in all_models:
    if model.get("id") == target_id:
        found = True
        print(f"FOUND in [{source}]: {model.get('name')}")
        print(f"Generated Image Resolution: {model.get('generated_image_resolution', 'N/A')}")
        print(f"Type: {model.get('type', 'N/A')}")
        break
if not found:
    print("NOT FOUND in any model list")

print("=" * 80)
