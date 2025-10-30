from __future__ import annotations

from pathlib import Path

# Project root is 2 levels up from this file (backend/app/core/paths.py -> root)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Data directory at project root
DATA_DIR = PROJECT_ROOT / "app" / "data"


def get_data_path(filename: str = "") -> Path:
    """Get path to file in app/data directory.

    Args:
        filename: Optional filename to append to data directory path

    Returns:
        Path object pointing to app/data or app/data/filename
    """
    if filename:
        return DATA_DIR / filename
    return DATA_DIR
