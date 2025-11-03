from __future__ import annotations

import pytest
from unittest.mock import patch

from app.coordinator.orchestrator import generate_images_cycle


def test_startup_fails_without_ffmpeg():
    """Verify application startup fails fast if ffmpeg is not found."""
    from app.main import _check_ffmpeg_presence

    # Mock subprocess to simulate ffmpeg not found
    with patch("app.main.subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("ffmpeg not found")

        with pytest.raises(RuntimeError, match="ffmpeg not found"):
            _check_ffmpeg_presence()


def test_startup_fails_without_ffprobe():
    """Verify application startup fails fast if ffprobe is not found."""
    from app.main import _check_ffmpeg_presence

    # Mock ffmpeg check to pass, ffprobe check to fail
    def mock_subprocess_run(cmd, *args, **kwargs):
        if "ffmpeg" in cmd[0]:
            return  # ffmpeg check passes
        elif "ffprobe" in cmd[0]:
            raise FileNotFoundError("ffprobe not found")

    with patch("app.main.subprocess.run", side_effect=mock_subprocess_run):
        with pytest.raises(RuntimeError, match="ffprobe not found"):
            _check_ffmpeg_presence()


def test_live_flag_required():
    """Validates that generate_images_cycle fails when ALLOW_LIVE=false.

    Since ALLOW_LIVE defaults to false in tests, attempting to run
    the image generation cycle should fail at the provider client level
    when trying to make actual API calls.
    """
    with pytest.raises(RuntimeError) as exc_info:
        generate_images_cycle(1)

    assert "ALLOW_LIVE=false" in str(exc_info.value)


def test_prompt_config_required():
    """Validates that prompting agent fails if prompt_config.json is missing."""
    import os
    import tempfile
    from app.agents import prompting

    # Temporarily rename the config file
    config_path = "app/data/prompt_config.json"
    if os.path.exists(config_path):
        backup_path = config_path + ".backup"
        os.rename(config_path, backup_path)

        try:
            with pytest.raises(FileNotFoundError):
                prompting.propose(1)
        finally:
            # Restore the config
            os.rename(backup_path, config_path)
