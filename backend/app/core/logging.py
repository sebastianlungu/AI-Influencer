from __future__ import annotations

import logging
import os

# Ensure logs directory exists
os.makedirs("app/data", exist_ok=True)

# Configure structured logging
logging.basicConfig(
    filename="app/data/logs.txt",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

log = logging.getLogger("ai-influencer")
