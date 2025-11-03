from __future__ import annotations

import os
import subprocess
from pathlib import Path

from app.core.config import settings
from app.core.logging import log


class FFmpegMuxClient:
    """ffmpeg client for audio/video muxing.

    Replaces Shotstack for local audio/video composition.
    Ensures exact 6-second duration output.
    """

    def __init__(self):
        """Initialize ffmpeg mux client.

        Raises:
            RuntimeError: If ffmpeg or ffprobe not found
        """
        self.ffmpeg_path = settings.ffmpeg_path
        self.ffprobe_path = settings.ffprobe_path

        # Validate ffmpeg availability
        try:
            subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                check=True,
                timeout=5,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(
                f"ffmpeg not found at '{self.ffmpeg_path}'. "
                f"Install ffmpeg or set FFMPEG_PATH in .env"
            ) from e

        # Validate ffprobe availability
        try:
            subprocess.run(
                [self.ffprobe_path, "-version"],
                capture_output=True,
                check=True,
                timeout=5,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(
                f"ffprobe not found at '{self.ffprobe_path}'. "
                f"Install ffmpeg (includes ffprobe) or set FFPROBE_PATH in .env"
            ) from e

        log.info("FFmpegMuxClient initialized")

    def mux(
        self,
        video_in: str,
        audio_in: str | None,
        out_path: str,
        seconds: int = 6,
    ) -> str:
        """Mux video and audio, trim to exact duration.

        Args:
            video_in: Path to input video file
            audio_in: Path to input audio file (None for silent)
            out_path: Path to output video file
            seconds: Target duration in seconds (default 6)

        Returns:
            Path to muxed video file

        Raises:
            FileNotFoundError: If input video doesn't exist
            RuntimeError: If ffmpeg command fails
        """
        # Validate input video exists
        if not os.path.exists(video_in):
            raise FileNotFoundError(f"Input video not found: {video_in}")

        # Validate audio if provided
        if audio_in and not os.path.exists(audio_in):
            raise FileNotFoundError(f"Input audio not found: {audio_in}")

        # Ensure output directory exists
        out_dir = Path(out_path).parent
        out_dir.mkdir(parents=True, exist_ok=True)

        log.info(
            f"FFMPEG_MUX START video={Path(video_in).name} "
            f"audio={Path(audio_in).name if audio_in else 'none'} "
            f"duration={seconds}s"
        )

        # Build ffmpeg command
        if audio_in:
            # Mux video + audio, trim both to exact duration
            cmd = [
                self.ffmpeg_path,
                "-y",  # Overwrite output file
                "-i", video_in,
                "-i", audio_in,
                "-t", str(seconds),  # Trim to exact duration
                "-c:v", "copy",  # Copy video codec (no re-encode)
                "-c:a", "aac",  # Encode audio to AAC
                "-b:a", "128k",  # Audio bitrate
                "-shortest",  # Use shortest stream duration
                "-map", "0:v:0",  # Map video from first input
                "-map", "1:a:0",  # Map audio from second input
                out_path,
            ]
        else:
            # Silent video: copy video stream, trim to exact duration
            cmd = [
                self.ffmpeg_path,
                "-y",  # Overwrite output file
                "-i", video_in,
                "-t", str(seconds),  # Trim to exact duration
                "-c:v", "copy",  # Copy video codec (no re-encode)
                "-an",  # No audio
                out_path,
            ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=120,  # 2 minute timeout
            )

            # Validate output file exists
            if not os.path.exists(out_path):
                raise RuntimeError(f"ffmpeg did not create output file: {out_path}")

            # Verify duration using ffprobe
            actual_duration = self._get_duration(out_path)
            if actual_duration is None:
                log.warning(f"Could not verify duration of {out_path}")
            elif abs(actual_duration - seconds) > 0.5:  # Allow 0.5s tolerance
                log.warning(
                    f"Output duration {actual_duration:.2f}s != target {seconds}s "
                    f"(tolerance 0.5s)"
                )

            log.info(f"FFMPEG_MUX SUCCESS output={Path(out_path).name} duration={actual_duration:.2f}s")
            return out_path

        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"ffmpeg timeout after 120s") from e
        except subprocess.CalledProcessError as e:
            stderr = e.stderr if e.stderr else ""
            raise RuntimeError(
                f"ffmpeg failed with exit code {e.returncode}: {stderr[:500]}"
            ) from e

    def _get_duration(self, video_path: str) -> float | None:
        """Get video duration in seconds using ffprobe.

        Args:
            video_path: Path to video file

        Returns:
            Duration in seconds, or None if failed
        """
        cmd = [
            self.ffprobe_path,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )

            duration_str = result.stdout.strip()
            return float(duration_str)

        except (subprocess.CalledProcessError, ValueError, subprocess.TimeoutExpired):
            return None
