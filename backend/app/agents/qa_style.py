from __future__ import annotations

import json
import shutil
import subprocess

import cv2


def _ffprobe_validate(path: str) -> bool:
    """Validates video container format using FFprobe.

    Args:
        path: Path to video file

    Returns:
        True if valid video container with at least one video stream

    Raises:
        ValueError: If video container is invalid or corrupt
    """
    if not shutil.which("ffprobe"):
        # Development fallback: skip FFprobe validation if not installed
        return True

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            raise ValueError(f"FFprobe failed to read video: {path}")

        data = json.loads(result.stdout or "{}")
        streams = data.get("streams", [])

        # Must have at least one video stream
        has_video = any(s.get("codec_type") == "video" for s in streams)
        if not has_video:
            raise ValueError(f"No video streams found in: {path}")

        return True

    except subprocess.TimeoutExpired:
        raise ValueError(f"FFprobe timeout on: {path}")
    except json.JSONDecodeError:
        raise ValueError(f"FFprobe returned invalid JSON for: {path}")


def ensure(video_path: str, payload: dict) -> None:
    """Validates video quality using container validation and blur detection.

    Args:
        video_path: Path to MP4 file
        payload: Variation dict (for logging)

    Raises:
        RuntimeError: If video is unreadable
        ValueError: If video container is invalid or too blurry
    """
    # Step 1: Validate container format with FFprobe
    _ffprobe_validate(video_path)

    # Step 2: Validate readability with OpenCV
    cap = cv2.VideoCapture(video_path)
    ok, frame = cap.read()
    cap.release()

    if not ok:
        raise RuntimeError(f"Unreadable video (OpenCV failed): {video_path}")

    # Step 3: Blur detection using Laplacian variance
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    val = cv2.Laplacian(gray, cv2.CV_64F).var()

    if val < 60:
        raise ValueError(
            f"Video too blurry (Laplacian variance={val:.2f} < 60): {video_path}"
        )
