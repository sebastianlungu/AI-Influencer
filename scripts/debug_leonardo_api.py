#!/usr/bin/env python
"""Debug script to see raw Leonardo API responses."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from backend.app.core.config import settings

BASE_URL = "https://cloud.leonardo.ai/api/rest/v1"

def main() -> None:
    """Fetch and display raw API responses."""
    api_key = settings.leonardo_api_key
    if not api_key:
        print("Error: LEONARDO_API_KEY not set in .env")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=30) as client:
        # Get user info
        print("Fetching user info from /me...\n")
        me_resp = client.get(f"{BASE_URL}/me", headers=headers)
        print(f"Status: {me_resp.status_code}")
        user_data = me_resp.json()
        print(f"Response:\n{json.dumps(user_data, indent=2)}\n")

        # Try to extract user ID
        user_id = user_data.get("user_details", [{}])[0].get("user", {}).get("id")
        print(f"Extracted user_id: {user_id}\n")

        if user_id:
            # Get elements
            print(f"Fetching elements from /elements/user/{user_id}...\n")
            elem_resp = client.get(f"{BASE_URL}/elements/user/{user_id}", headers=headers)
            print(f"Status: {elem_resp.status_code}")
            elem_data = elem_resp.json()
            print(f"Response:\n{json.dumps(elem_data, indent=2)}\n")

if __name__ == "__main__":
    main()
