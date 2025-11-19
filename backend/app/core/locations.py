"""Location discovery and caching service.

Scans app/data/locations/ for scene banks and provides location metadata.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

from app.core.logging import log
from app.core.paths import get_data_path


class LocationRecord(TypedDict):
    """Metadata for a single location."""

    id: str  # Unique flattened slug (e.g., "japan", "us-new_york-manhattan-times_square")
    label: str  # Display name (e.g., "Japan", "Times Square — Manhattan, NY")
    group: str  # Grouping for UI (e.g., "Global", "USA / New York")
    path: str  # Full file path
    count: int  # Number of scenes in file


class LocationCache:
    """In-memory cache for location discovery."""

    def __init__(self) -> None:
        self._locations: list[LocationRecord] = []
        self._id_map: dict[str, LocationRecord] = {}
        self._loaded = False

    def get_all(self, refresh: bool = False) -> list[LocationRecord]:
        """Get all locations, loading from disk if needed.

        Args:
            refresh: Force rescan of filesystem

        Returns:
            Sorted list of location records
        """
        if not self._loaded or refresh:
            self._scan()
        return self._locations

    def get_by_id(self, location_id: str, refresh: bool = False) -> LocationRecord | None:
        """Get location by ID.

        Args:
            location_id: Location slug
            refresh: Force rescan if not found

        Returns:
            Location record or None if not found
        """
        if not self._loaded or refresh:
            self._scan()
        return self._id_map.get(location_id)

    def _scan(self) -> None:
        """Scan filesystem for location JSON files."""
        locations_root = Path(get_data_path("locations"))

        if not locations_root.exists():
            log.warning(f"LOCATIONS_DIR_MISSING path={locations_root}")
            self._locations = []
            self._id_map = {}
            self._loaded = True
            return

        records: list[LocationRecord] = []

        # Recursively find all .json files
        for json_file in locations_root.rglob("*.json"):
            try:
                # Build location ID (flattened with hyphens)
                relative = json_file.relative_to(locations_root)
                # Use as_posix() to get consistent forward slashes, then replace with hyphens
                location_id = relative.with_suffix("").as_posix().replace("/", "-")

                # Load file to get scene count
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        scene_count = len(data.get("scenes", []))
                except Exception:
                    scene_count = 0

                # Build label and group
                label, group = self._build_labels(relative)

                record: LocationRecord = {
                    "id": location_id,
                    "label": label,
                    "group": group,
                    "path": str(json_file),
                    "count": scene_count,
                }

                records.append(record)

            except Exception as e:
                log.warning(f"LOCATION_SCAN_FAILED file={json_file}: {e}")
                continue

        # Sort by group, then label
        records.sort(key=lambda r: (r["group"], r["label"]))

        self._locations = records
        self._id_map = {r["id"]: r for r in records}
        self._loaded = True

        log.info(f"LOCATIONS_SCANNED count={len(records)}")

    def _build_labels(self, relative_path: Path) -> tuple[str, str]:
        """Build human-readable label and group from file path.

        Args:
            relative_path: Path relative to locations root

        Returns:
            Tuple of (label, group)

        Examples:
            japan.json → ("Japan", "Global")
            us/new_york/manhattan/times_square.json → ("Times Square — Manhattan, NY", "USA / New York")
            us/california/los_angeles/venice_beach.json → ("Venice Beach — Los Angeles, CA", "USA / California")
        """
        parts = relative_path.with_suffix("").parts

        # Flat file (e.g., japan.json)
        if len(parts) == 1:
            return (self._titlecase(parts[0]), "Global")

        # US nested path: us/<state>/<city>/.../<name>.json
        if parts[0].lower() == "us" and len(parts) >= 4:
            state = parts[1]
            city = parts[2]
            name = parts[-1]

            state_title = self._titlecase(state)
            state_abbr = self._get_state_abbr(state)
            city_title = self._titlecase(city)
            name_title = self._titlecase(name)

            label = f"{name_title} — {city_title}, {state_abbr or state_title}"
            group = f"USA / {state_title}"

            return (label, group)

        # Generic nested file (non-US)
        location_name = self._titlecase(parts[-1])
        parent_name = self._titlecase(parts[-2])

        label = f"{location_name} — {parent_name}"
        group = parent_name

        return (label, group)

    def _titlecase(self, text: str) -> str:
        """Convert snake_case or kebab-case to Title Case."""
        return text.replace("_", " ").replace("-", " ").title()

    def _get_state_abbr(self, name: str) -> str | None:
        """Get state abbreviation if applicable."""
        state_map = {
            "new_york": "NY",
            "california": "CA",
            "florida": "FL",
            "texas": "TX",
            "illinois": "IL",
            "pennsylvania": "PA",
            "ohio": "OH",
            "georgia": "GA",
            "north_carolina": "NC",
            "michigan": "MI",
            # Add more as needed
        }
        return state_map.get(name.lower().replace(" ", "_"))


# Global cache instance
_cache = LocationCache()


def get_all_locations(refresh: bool = False) -> list[LocationRecord]:
    """Get all available locations.

    Args:
        refresh: Force filesystem rescan

    Returns:
        List of location records
    """
    return _cache.get_all(refresh=refresh)


def get_location_by_id(location_id: str, refresh: bool = False) -> LocationRecord | None:
    """Get location by ID.

    Args:
        location_id: Location slug
        refresh: Force rescan if not found

    Returns:
        Location record or None
    """
    return _cache.get_by_id(location_id, refresh=refresh)
