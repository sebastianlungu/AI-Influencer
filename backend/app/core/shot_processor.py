"""Shot processor for single-generation multi-aspect export.

Orchestrates:
1. Leonardo generation at 1440×2560 (9:16 master)
2. Downscale to 1080×1920 (9:16 video source for Veo 3)
3. Smart crop to 1080×1350 (4:5 feed export for Instagram)

One generation → three derivatives → deterministic from seed.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

from app.core import image_utils
from app.core.logging import log
from app.core.paths import get_data_path


class ShotMeta:
    """Metadata for a processed shot with dual exports."""

    def __init__(
        self,
        shot_id: str,
        seed: int,
        master_9x16_path: str,
        video_9x16_path: str,
        feed_4x5_path: str,
        composition_warning: bool = False,
        composition_reason: str | None = None,
    ):
        self.shot_id = shot_id
        self.seed = seed
        self.master_9x16_path = master_9x16_path
        self.video_9x16_path = video_9x16_path
        self.feed_4x5_path = feed_4x5_path
        self.composition_warning = composition_warning
        self.composition_reason = composition_reason
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "shot_id": self.shot_id,
            "seed": self.seed,
            "exports": {
                "master_9x16": self.master_9x16_path,
                "video_9x16_1080x1920": self.video_9x16_path,
                "feed_4x5_1080x1350": self.feed_4x5_path,
            },
            "composition": {
                "warning": self.composition_warning,
                "reason": self.composition_reason,
            },
            "created_at": self.created_at,
        }


def create_shot_directory(shot_id: str) -> Path:
    """Create shot directory structure.

    Args:
        shot_id: Unique shot identifier

    Returns:
        Path to shot directory (app/data/shots/{shot_id}/)
    """
    data_dir = get_data_path()
    shot_dir = data_dir / "shots" / shot_id
    shot_dir.mkdir(parents=True, exist_ok=True)
    log.info(f"shot_processor: created shot directory: {shot_dir}")
    return shot_dir


def save_master(temp_path: str, shot_id: str, shot_dir: Path) -> str:
    """Move generated master image to shot directory.

    Args:
        temp_path: Temporary path from Leonardo client
        shot_id: Shot identifier
        shot_dir: Shot directory path

    Returns:
        Path to saved master image
    """
    master_filename = f"shot_{shot_id}_master_9x16.jpg"
    master_path = str(shot_dir / master_filename)

    # Move from temp to final location
    shutil.move(temp_path, master_path)
    log.info(f"shot_processor: saved master to {master_path}")

    return master_path


def downscale_for_video(master_path: str, shot_id: str, shot_dir: Path) -> str:
    """Downscale master to 1080×1920 for Veo 3 video generation.

    Args:
        master_path: Path to 1440×2560 master
        shot_id: Shot identifier
        shot_dir: Shot directory path

    Returns:
        Path to downscaled video source image
    """
    video_filename = f"shot_{shot_id}_video_9x16_1080x1920.jpg"
    video_path = str(shot_dir / video_filename)

    image_utils.downscale_image(master_path, 1080, 1920, video_path)

    log.info(f"shot_processor: created video source at {video_path}")
    return video_path


def smart_crop_feed(
    master_path: str, shot_id: str, shot_dir: Path
) -> Tuple[str, bool, str | None]:
    """Smart crop master to 1080×1350 (4:5) for Instagram feed.

    Uses subject detection to center crop intelligently.

    Args:
        master_path: Path to 1440×2560 master
        shot_id: Shot identifier
        shot_dir: Shot directory path

    Returns:
        Tuple of (feed_path, composition_warning, warning_reason)
    """
    feed_filename = f"shot_{shot_id}_feed_4x5_1080x1350.jpg"
    feed_path = str(shot_dir / feed_filename)

    crop_path, warning, reason = image_utils.smart_crop_4x5(master_path, feed_path)

    log.info(
        f"shot_processor: created feed export at {feed_path}, "
        f"warning={warning}, reason={reason or 'N/A'}"
    )

    return crop_path, warning, reason


def save_shot_exports(master_temp_path: str, shot_id: str) -> ShotMeta:
    """Save all shot exports from Leonardo master.

    Creates three derivatives:
    1. Master 9:16 @ 1440×2560 (moved from temp)
    2. Video 9:16 @ 1080×1920 (downscaled for Veo 3)
    3. Feed 4:5 @ 1080×1350 (smart cropped for Instagram)

    Args:
        master_temp_path: Temporary path to Leonardo-generated master
        shot_id: Shot identifier

    Returns:
        ShotMeta with all export paths and composition warnings

    Raises:
        RuntimeError: If export operations fail
    """
    try:
        # Create shot directory
        shot_dir = create_shot_directory(shot_id)

        # Save master
        master_path = save_master(master_temp_path, shot_id, shot_dir)

        # Create video source (downscale 9:16)
        video_path = downscale_for_video(master_path, shot_id, shot_dir)

        # Create feed export (smart crop 4:5)
        feed_path, comp_warning, comp_reason = smart_crop_feed(
            master_path, shot_id, shot_dir
        )

        # Create metadata object
        meta = ShotMeta(
            shot_id=shot_id,
            seed=0,  # Will be set by caller
            master_9x16_path=master_path,
            video_9x16_path=video_path,
            feed_4x5_path=feed_path,
            composition_warning=comp_warning,
            composition_reason=comp_reason,
        )

        # Save metadata JSON
        meta_path = shot_dir / "meta.json"
        with open(meta_path, "w") as f:
            json.dump(meta.to_dict(), f, indent=2)

        log.info(
            f"shot_processor: shot exports complete, "
            f"master={master_path}, video={video_path}, feed={feed_path}"
        )

        return meta

    except Exception as e:
        log.error(f"shot_processor: export failed for shot {shot_id}: {e}", exc_info=True)
        raise RuntimeError(f"Shot export failed: {e}") from e


def generate_shot(payload: dict, leonardo_client_fn) -> ShotMeta:
    """Generate shot with dual exports: one Leonardo generation → two aspect ratios.

    This is the main entry point for shot generation. It:
    1. Calls Leonardo to generate master at 1440×2560
    2. Creates downscaled 1080×1920 for video (Veo 3)
    3. Creates smart-cropped 1080×1350 for feed (Instagram 4:5)

    Args:
        payload: Variation payload with id, seed, base, neg, meta
        leonardo_client_fn: Function that returns configured Leonardo client

    Returns:
        ShotMeta with all export paths and composition data

    Raises:
        RuntimeError: If generation or export fails
    """
    shot_id = payload["id"]
    seed = payload.get("seed", 0)

    log.info(f"shot_processor: generating shot {shot_id} with seed={seed}")

    try:
        # Generate master via Leonardo (will be 1440×2560)
        from app.clients.provider_selector import image_client

        leonardo = image_client()
        master_temp_path = leonardo.generate(payload)

        log.info(f"shot_processor: Leonardo generated master for {shot_id}")

        # Create exports
        meta = save_shot_exports(master_temp_path, shot_id)

        # Set seed in metadata
        meta.seed = seed

        # Update metadata JSON with correct seed
        shot_dir = get_data_path() / "shots" / shot_id
        meta_path = shot_dir / "meta.json"
        with open(meta_path, "w") as f:
            json.dump(meta.to_dict(), f, indent=2)

        log.info(f"shot_processor: shot {shot_id} generation complete")

        return meta

    except Exception as e:
        log.error(
            f"shot_processor: generation failed for shot {shot_id}: {e}", exc_info=True
        )
        raise RuntimeError(f"Shot generation failed: {e}") from e
