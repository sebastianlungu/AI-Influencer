"""Clean wardrobe bank to be fitness/muscle-focused."""

import json
from pathlib import Path

# Bad keywords that indicate covering too much / not fitness-oriented
BAD_KEYWORDS = [
    'oversized hoodie', 'fleece pullover', 'utility hoodie',
    'parka', 'puffer', 'down jacket', 'winter coat',
    'platform sneakers', 'chunky sneakers', 'joggers',
    'poncho', 'cape', 'blanket', 'cardigan',
    'track pants', 'sweatpants', 'baggy',
    'wool coat', 'trench coat', 'peacoat',
    'chunky knit', 'turtleneck sweater',
    'tracksuit', 'windbreaker', 'technical shell',
    'bomber jacket', 'varsity jacket', 'reebok jacket',
    'adidas jacket', 'nike jacket', 'coach jacket',
    'rain jacket', 'shell jacket', 'windbreaker dress',
    'windproof bomber', 'nylon bomber', 'button-up shirt',
    'oversized fit', 'oversized shirt',
    'cargo pants', 'jogger suit', 'utility pants',
]

# Borderline acceptable - cropped hoodie is OK if paired with shorts/leggings
# But we'll keep these and let them through

def is_bad_entry(text: str) -> bool:
    """Check if wardrobe entry should be removed."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in BAD_KEYWORDS)

def clean_wardrobe_bank():
    """Clean the wardrobe bank."""
    bank_path = Path("app/data/variety_bank.json")

    print("Loading variety bank...")
    with open(bank_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    original_count = len(data.get('wardrobe', []))
    print(f"Original wardrobe entries: {original_count}")

    # Filter out bad entries
    wardrobe = data.get('wardrobe', [])
    cleaned = []
    removed = []

    for entry in wardrobe:
        text = entry.get('text', '')
        if is_bad_entry(text):
            removed.append(text)
        else:
            cleaned.append(entry)

    print(f"\nRemoved {len(removed)} entries:")
    print("Sample removed entries (first 10):")
    for i, text in enumerate(removed[:10], 1):
        print(f"  {i}. {text}")

    # Update data
    data['wardrobe'] = cleaned
    new_count = len(cleaned)

    print(f"\nNew wardrobe count: {new_count}")
    print(f"Removed: {original_count - new_count} entries")
    print(f"Retention rate: {new_count/original_count*100:.1f}%")

    # Save
    print("\nSaving cleaned bank...")
    with open(bank_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✅ Wardrobe bank cleaned!")

    # Sample some entries to verify
    import random
    random.seed(42)
    samples = random.sample(cleaned, min(15, len(cleaned)))
    print("\nSample remaining entries (random 15):")
    for i, entry in enumerate(samples, 1):
        print(f"  {i}. {entry['text']}")

if __name__ == '__main__':
    clean_wardrobe_bank()
