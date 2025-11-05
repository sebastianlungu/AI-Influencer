"""Image processing utilities for multi-aspect export.

Provides subject detection and smart cropping for generating consistent
4:5 exports from 9:16 masters while preserving subject composition.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np
from PIL import Image

from app.core.logging import log


def detect_subject_box(image_path: str) -> dict[str, int] | None:
    """Detect primary subject (face/person) bounding box.

    Detection pipeline:
    1. Try face detection (Haar cascade)
    2. Fallback to center region if no detection

    Args:
        image_path: Path to image file

    Returns:
        Dict with keys: x, y, width, height (pixel coords) or None if no detection
    """
    if not os.path.exists(image_path):
        log.error(f"image_utils: file not found: {image_path}")
        return None

    try:
        # Load image with OpenCV
        img = cv2.imread(image_path)
        if img is None:
            log.warning(f"image_utils: could not load image: {image_path}")
            return None

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Try face detection with Haar cascade
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(int(w * 0.05), int(h * 0.05)),  # At least 5% of image
        )

        if len(faces) > 0:
            # Use largest face
            largest_face = max(faces, key=lambda f: f[2] * f[3])  # area = width * height
            x, y, fw, fh = largest_face

            # Expand bounding box to include body (assume 3x face height for full subject)
            expanded_h = fh * 3
            expanded_y = max(0, y - int(fh * 0.5))  # Start above face
            expanded_h = min(expanded_h, h - expanded_y)  # Don't exceed image bounds

            # Center horizontally on face with some margin
            margin = int(fw * 0.3)
            expanded_x = max(0, x - margin)
            expanded_w = min(fw + 2 * margin, w - expanded_x)

            log.info(
                f"image_utils: face detected at ({x},{y}) size={fw}x{fh}, "
                f"expanded to ({expanded_x},{expanded_y}) size={expanded_w}x{expanded_h}"
            )

            return {
                "x": int(expanded_x),
                "y": int(expanded_y),
                "width": int(expanded_w),
                "height": int(expanded_h),
            }

        # No face detected - fallback to center region
        log.info("image_utils: no face detected, using center region")
        return None

    except Exception as e:
        log.error(f"image_utils: detection failed: {e}")
        return None


def calculate_crop_window(
    master_w: int,
    master_h: int,
    target_w: int,
    target_h: int,
    subject_box: dict[str, int] | None = None,
) -> Tuple[int, int, bool, str | None]:
    """Calculate optimal crop window for 4:5 export from 9:16 master.

    Attempts to center on subject while ensuring head/feet are not cropped.
    Applies nudging up to ±8% of height if subject risks being cut.

    Args:
        master_w: Master image width (1440)
        master_h: Master image height (2560)
        target_w: Target crop width (1080)
        target_h: Target crop height (1350)
        subject_box: Optional subject bounding box from detect_subject_box()

    Returns:
        Tuple of (crop_x, crop_y, composition_warning, warning_reason)
            - crop_x, crop_y: Top-left corner of crop window
            - composition_warning: True if subject may still be cut
            - warning_reason: Human-readable explanation or None
    """
    # Default to center crop
    crop_x = (master_w - target_w) // 2
    crop_y = (master_h - target_h) // 2

    if subject_box is None:
        log.info("image_utils: using center crop (no subject detection)")
        return crop_x, crop_y, False, None

    # Calculate subject center
    subject_center_x = subject_box["x"] + subject_box["width"] // 2
    subject_center_y = subject_box["y"] + subject_box["height"] // 2

    # Try to center crop on subject
    crop_x = max(0, min(master_w - target_w, subject_center_x - target_w // 2))
    crop_y = max(0, min(master_h - target_h, subject_center_y - target_h // 2))

    # Check if subject extends beyond crop window
    subject_top = subject_box["y"]
    subject_bottom = subject_box["y"] + subject_box["height"]
    crop_bottom = crop_y + target_h

    # Calculate margins
    top_margin = subject_top - crop_y
    bottom_margin = crop_bottom - subject_bottom

    # Required margins (10% headroom, 8% footroom)
    required_top_margin = int(target_h * 0.10)
    required_bottom_margin = int(target_h * 0.08)

    # Maximum nudge distance (±8% of master height)
    max_nudge = int(master_h * 0.08)

    warning = False
    reason = None

    # Nudge down if head is too close to top
    if top_margin < required_top_margin:
        nudge_down = required_top_margin - top_margin
        if nudge_down <= max_nudge and crop_y + nudge_down + target_h <= master_h:
            crop_y += nudge_down
            log.info(f"image_utils: nudged down {nudge_down}px to preserve headroom")
        else:
            warning = True
            reason = "Subject head near top edge, may be cropped"
            log.warning(f"image_utils: {reason}")

    # Nudge up if feet are too close to bottom
    elif bottom_margin < required_bottom_margin:
        nudge_up = required_bottom_margin - bottom_margin
        if nudge_up <= max_nudge and crop_y - nudge_up >= 0:
            crop_y -= nudge_up
            log.info(f"image_utils: nudged up {nudge_up}px to preserve footroom")
        else:
            warning = True
            reason = "Subject feet near bottom edge, may be cropped"
            log.warning(f"image_utils: {reason}")

    log.info(
        f"image_utils: crop window calculated at ({crop_x},{crop_y}), "
        f"margins: top={subject_top - crop_y}px, bottom={crop_bottom - subject_bottom}px"
    )

    return crop_x, crop_y, warning, reason


def apply_crop(
    master_path: str,
    crop_x: int,
    crop_y: int,
    target_w: int,
    target_h: int,
    output_path: str,
) -> str:
    """Apply crop to master image and save result.

    Args:
        master_path: Path to master image (1440×2560)
        crop_x: Crop window top-left X coordinate
        crop_y: Crop window top-left Y coordinate
        target_w: Target width (1080)
        target_h: Target height (1350)
        output_path: Path to save cropped image

    Returns:
        Path to saved cropped image

    Raises:
        FileNotFoundError: If master_path doesn't exist
        RuntimeError: If crop operation fails
    """
    if not os.path.exists(master_path):
        raise FileNotFoundError(f"Master image not found: {master_path}")

    try:
        with Image.open(master_path) as img:
            # Validate crop bounds
            if crop_x < 0 or crop_y < 0:
                raise ValueError(f"Invalid crop origin: ({crop_x},{crop_y})")
            if crop_x + target_w > img.width or crop_y + target_h > img.height:
                raise ValueError(
                    f"Crop window ({crop_x},{crop_y},{target_w},{target_h}) "
                    f"exceeds image bounds ({img.width}x{img.height})"
                )

            # Crop
            cropped = img.crop((crop_x, crop_y, crop_x + target_w, crop_y + target_h))

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Save with high quality
            cropped.save(output_path, quality=92, optimize=True)

            log.info(
                f"image_utils: cropped {master_path} -> {output_path} "
                f"size={cropped.width}x{cropped.height}"
            )

            return output_path

    except Exception as e:
        log.error(f"image_utils: crop failed: {e}")
        raise RuntimeError(f"Failed to crop image: {e}") from e


def downscale_image(
    source_path: str, target_w: int, target_h: int, output_path: str
) -> str:
    """Downscale image to target resolution while maintaining aspect ratio.

    Args:
        source_path: Path to source image
        target_w: Target width
        target_h: Target height
        output_path: Path to save downscaled image

    Returns:
        Path to saved downscaled image

    Raises:
        FileNotFoundError: If source_path doesn't exist
        RuntimeError: If downscale operation fails
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source image not found: {source_path}")

    try:
        with Image.open(source_path) as img:
            # Use Lanczos for high-quality downscaling
            downscaled = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Save with high quality
            downscaled.save(output_path, quality=92, optimize=True)

            log.info(
                f"image_utils: downscaled {source_path} "
                f"from {img.width}x{img.height} to {target_w}x{target_h} -> {output_path}"
            )

            return output_path

    except Exception as e:
        log.error(f"image_utils: downscale failed: {e}")
        raise RuntimeError(f"Failed to downscale image: {e}") from e


def smart_crop_4x5(master_path: str, output_path: str) -> Tuple[str, bool, str | None]:
    """Perform smart 4:5 crop from 9:16 master with subject detection.

    Detects subject, calculates optimal crop window with nudging to preserve
    head/feet, and applies crop to produce 1080×1350 feed-ready export.

    Args:
        master_path: Path to 9:16 master image (1440×2560)
        output_path: Path to save 4:5 cropped image (1080×1350)

    Returns:
        Tuple of (output_path, composition_warning, warning_reason)
            - output_path: Path to saved crop
            - composition_warning: True if subject may be cropped
            - warning_reason: Human-readable explanation or None

    Raises:
        FileNotFoundError: If master_path doesn't exist
        RuntimeError: If crop operation fails
    """
    # Constants for mobile-first targets
    MASTER_W, MASTER_H = 1440, 2560  # 9:16 master resolution
    TARGET_W, TARGET_H = 1080, 1350  # 4:5 feed resolution

    # Detect subject
    subject_box = detect_subject_box(master_path)

    # Calculate crop window
    crop_x, crop_y, warning, reason = calculate_crop_window(
        MASTER_W, MASTER_H, TARGET_W, TARGET_H, subject_box
    )

    # Apply crop
    result_path = apply_crop(master_path, crop_x, crop_y, TARGET_W, TARGET_H, output_path)

    return result_path, warning, reason
