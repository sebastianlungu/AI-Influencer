"""
Asset validators for manual upload workflow.

Validates image dimensions (864×1536) and video duration/aspect (6s, 9:16).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.core.config import settings
from app.core.logging import log


class ValidationError(Exception):
    """Raised when asset validation fails."""

    pass


def validate_image_dimensions(image_path: str | Path) -> None:
    """
    Validate image is exactly 864×1536.

    Args:
        image_path: Path to image file

    Raises:
        ValidationError: If dimensions don't match 864×1536
        RuntimeError: If image cannot be read
    """
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            width, height = img.size

            if width != settings.image_width or height != settings.image_height:
                raise ValidationError(
                    f"Image dimensions must be exactly {settings.image_width}×{settings.image_height}. "
                    f"Got {width}×{height}."
                )

            log.info(f"VALIDATE_IMAGE path={image_path} dimensions={width}×{height} PASS")

    except ValidationError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to read image {image_path}: {e}") from e


def validate_video_format(video_path: str | Path) -> None:
    """
    Validate video is exactly 6.0±0.05s and 9:16 aspect ratio.

    Args:
        video_path: Path to video file

    Raises:
        ValidationError: If duration or aspect ratio invalid
        RuntimeError: If video cannot be read or ffprobe fails
    """
    video_path = str(video_path)

    try:
        # Use ffprobe to get video metadata
        cmd = [
            settings.ffprobe_path,
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "json",
            video_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )

        metadata = json.loads(result.stdout)
        stream = metadata.get("streams", [{}])[0]

        # Extract dimensions and duration
        width = stream.get("width")
        height = stream.get("height")
        duration = float(stream.get("duration", 0))

        if not width or not height:
            raise ValidationError(f"Could not read video dimensions from {video_path}")

        # Validate aspect ratio (9:16)
        aspect = width / height
        expected_aspect = 9 / 16

        # Allow 1% tolerance for aspect ratio
        if abs(aspect - expected_aspect) > 0.01:
            raise ValidationError(
                f"Video aspect ratio must be 9:16 (0.5625). "
                f"Got {width}×{height} (aspect: {aspect:.4f})."
            )

        # Validate duration (6.0±0.05s)
        expected_duration = settings.video_must_be_seconds
        tolerance = 0.05

        if abs(duration - expected_duration) > tolerance:
            raise ValidationError(
                f"Video duration must be exactly {expected_duration}s (±{tolerance}s). "
                f"Got {duration:.3f}s."
            )

        log.info(
            f"VALIDATE_VIDEO path={video_path} "
            f"dimensions={width}×{height} duration={duration:.3f}s PASS"
        )

    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"ffprobe failed for {video_path}: {e.stderr}"
        ) from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"ffprobe timeout for {video_path}"
        ) from e
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Failed to parse ffprobe output for {video_path}: {e}"
        ) from e
    except ValidationError:
        raise
    except Exception as e:
        raise RuntimeError(
            f"Failed to validate video {video_path}: {e}"
        ) from e
