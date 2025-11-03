from __future__ import annotations

import os
from pathlib import Path

from app.clients.ffmpeg_mux import FFmpegMuxClient
from app.core.logging import log


def polish(video: str, payload: dict) -> str:
    """Ensures video is exactly 6 seconds and properly formatted.

    IMPORTANT: Music is NOT added during video generation. Music is added later
    via the Music Review workflow (after video is liked by user).

    This function just ensures:
    - Video is exactly 6 seconds
    - Video is properly formatted for QA and review

    Args:
        video: Path to input MP4 (from Veo 3)
        payload: Variation dict (unused, kept for compatibility)

    Returns:
        Path to polished MP4 file (trimmed to 6s, no audio)

    Raises:
        RuntimeError: If ffmpeg processing fails
    """
    log.info(f"EDIT_POLISH START video={Path(video).name}")

    # Generate output path
    video_path = Path(video)
    output_dir = video_path.parent
    output_path = output_dir / f"{video_path.stem}_polished.mp4"

    # Use ffmpeg to trim to exactly 6 seconds (silent)
    ffmpeg = FFmpegMuxClient()
    result_path = ffmpeg.mux(
        video_in=video,
        audio_in=None,  # No music during initial generation
        out_path=str(output_path),
        seconds=6,
    )

    log.info(f"EDIT_POLISH SUCCESS output={Path(result_path).name}")
    return result_path


def mux_with_audio(video: str, audio: str, output_path: str) -> str:
    """Mux video with audio track (used in Music Review workflow).

    This is called separately via music endpoints after video is liked.

    Args:
        video: Path to input video MP4
        audio: Path to audio file (from Suno)
        output_path: Path for final output

    Returns:
        Path to final muxed video

    Raises:
        RuntimeError: If ffmpeg muxing fails
    """
    log.info(f"EDIT_MUX_AUDIO START video={Path(video).name} audio={Path(audio).name}")

    ffmpeg = FFmpegMuxClient()
    result_path = ffmpeg.mux(
        video_in=video,
        audio_in=audio,
        out_path=output_path,
        seconds=6,
    )

    log.info(f"EDIT_MUX_AUDIO SUCCESS output={Path(result_path).name}")
    return result_path
