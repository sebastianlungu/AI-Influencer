from __future__ import annotations

import pytest

from app.coordinator.orchestrator import generate_images_cycle


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
