from __future__ import annotations

import logging
import os

from app.core.paths import get_data_path

# Ensure logs directory exists
DATA_DIR = get_data_path()
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Log rotation settings
MAX_LOG_LINES = 10000
TRUNCATE_THRESHOLD = 15000  # Truncate when exceeding this many lines


def truncate_log_file() -> None:
    """Truncate log file to last MAX_LOG_LINES if it exceeds TRUNCATE_THRESHOLD.

    This prevents unbounded log file growth. Called on startup and periodically.
    """
    log_path = get_data_path("logs.txt")

    if not log_path.exists():
        return

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if len(lines) > TRUNCATE_THRESHOLD:
            # Keep only the last MAX_LOG_LINES
            truncated_lines = lines[-MAX_LOG_LINES:]

            # Write back atomically
            temp_path = log_path.with_suffix(".txt.tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                f.writelines(truncated_lines)

            # Replace original file
            temp_path.replace(log_path)

            print(f"LOG_ROTATION: Truncated {len(lines)} lines to {len(truncated_lines)} lines")
    except Exception as e:
        print(f"LOG_ROTATION_ERROR: Failed to truncate log file: {e}")


# Truncate logs on startup if needed
truncate_log_file()

# Configure structured logging
logging.basicConfig(
    filename=str(get_data_path("logs.txt")),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

log = logging.getLogger("ai-influencer")
