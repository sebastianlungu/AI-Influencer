from __future__ import annotations

import logging

from app.core.paths import get_data_path

# Ensure logs directory exists
DATA_DIR = get_data_path()
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Configure structured logging
logging.basicConfig(
    filename=str(get_data_path("logs.txt")),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

log = logging.getLogger("ai-influencer")
