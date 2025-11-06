#!/usr/bin/env python
"""Helper script to discover Leonardo custom elements (LoRAs).

Usage:
    uv run python scripts/discover_leonardo_elements.py

This script fetches your trained custom elements from Leonardo API
and displays their IDs, names, and trigger words for use in .env configuration.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path to import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.clients.leonardo import LeonardoClient


def main() -> None:
    """Fetch and display user's custom elements."""
    print("Discovering Leonardo Custom Elements...\n")

    try:
        client = LeonardoClient()
        elements = client.get_user_elements()

        if not elements:
            print("No custom elements found for this account.")
            print("Train an element at https://leonardo.ai/models-and-training\n")
            return

        print(f"Found {len(elements)} custom element(s):\n")
        print("-" * 80)

        for i, elem in enumerate(elements, 1):
            print(f"\n#{i} Element:")
            print(f"   Name:         {elem['name']}")
            print(f"   ID:           {elem['id']}")
            print(f"   Trigger Word: {elem['trigger_word']}")
            if elem['description']:
                print(f"   Description:  {elem['description']}")

        print("\n" + "-" * 80)
        print("\nTo use an element, add these to your .env file:")
        print(f"\n   LEONARDO_ELEMENT_ID={elements[0]['id']}")
        print(f"   LEONARDO_ELEMENT_TRIGGER={elements[0]['trigger_word']}")
        print("   LEONARDO_ELEMENT_WEIGHT=1.0")
        print()

    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
