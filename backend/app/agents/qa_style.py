from __future__ import annotations

import cv2


def ensure(video_path: str, payload: dict) -> None:
    """Validates video quality using blur detection.

    Args:
        video_path: Path to MP4 file
        payload: Variation dict (for logging)

    Raises:
        RuntimeError: If video is unreadable
        ValueError: If video is too blurry (Laplacian variance < 60)
    """
    cap = cv2.VideoCapture(video_path)
    ok, frame = cap.read()
    cap.release()

    if not ok:
        raise RuntimeError(f"Unreadable video: {video_path}")

    # Blur detection using Laplacian variance
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    val = cv2.Laplacian(gray, cv2.CV_64F).var()

    if val < 60:
        raise ValueError(
            f"Video too blurry (Laplacian variance={val:.2f} < 60): {video_path}"
        )
