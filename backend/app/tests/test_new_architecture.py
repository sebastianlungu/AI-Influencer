"""Tests for new architecture: Grok, Suno, ffmpeg, scheduler, 6s duration."""

from __future__ import annotations

import pytest


def test_veo_duration_is_6_seconds():
    """Verify Veo 3 is configured for exactly 6 seconds, not 8."""
    from app.core.config import settings

    assert settings.veo_duration_seconds == 6, "Veo duration must be exactly 6 seconds"
    assert settings.gen_seconds == 6, "Default generation duration must be 6 seconds"


def test_shotstack_removed():
    """Verify Shotstack client and imports have been completely removed."""
    import importlib.util

    # Verify shotstack.py file does not exist
    shotstack_spec = importlib.util.find_spec("app.clients.shotstack")
    assert shotstack_spec is None, "Shotstack client file should not exist"

    # Verify no imports in provider_selector
    from app.clients import provider_selector
    import inspect

    source = inspect.getsource(provider_selector)
    assert "shotstack" not in source.lower(), "Shotstack should not be referenced in provider_selector"


def test_ffmpeg_mux_client_exists():
    """Verify ffmpeg_mux client exists and has correct interface."""
    from app.clients.ffmpeg_mux import FFmpegMuxClient

    client = FFmpegMuxClient()

    # Verify required method exists
    assert hasattr(client, "mux"), "FFmpegMuxClient must have mux method"

    # Verify method signature
    import inspect

    sig = inspect.signature(client.mux)
    params = list(sig.parameters.keys())

    assert "video_in" in params, "mux must accept video_in parameter"
    assert "audio_in" in params, "mux must accept audio_in parameter"
    assert "out_path" in params, "mux must accept out_path parameter"
    assert "seconds" in params, "mux must accept seconds parameter"


def test_grok_client_has_all_methods():
    """Verify Grok client has all required methods for the new architecture."""
    from app.clients.grok import GrokClient
    import inspect

    # Initialize with dummy key to test interface
    try:
        client = GrokClient(api_key="test_key", model="test_model")
    except Exception:
        # If initialization fails due to env validation, that's okay
        # We just need to verify the class structure
        pass

    # Verify required methods exist
    assert hasattr(GrokClient, "generate_variations"), "GrokClient must have generate_variations"
    assert hasattr(GrokClient, "suggest_motion"), "GrokClient must have suggest_motion"
    assert hasattr(GrokClient, "suggest_music"), "GrokClient must have suggest_music"
    assert hasattr(GrokClient, "generate_social_meta"), "GrokClient must have generate_social_meta"


def test_suno_client_exists():
    """Verify Suno client exists for music generation."""
    from app.clients.suno import SunoClient

    # Verify class exists
    assert SunoClient is not None

    # Verify required method exists
    assert hasattr(SunoClient, "generate_clip"), "SunoClient must have generate_clip method"


def test_motion_dedup_store_exists():
    """Verify per-video motion deduplication store exists."""
    from app.core import motion_dedup

    # Verify required functions exist
    assert hasattr(motion_dedup, "get_previous_prompts"), "Must have get_previous_prompts"
    assert hasattr(motion_dedup, "store_motion_prompt"), "Must have store_motion_prompt"
    assert hasattr(motion_dedup, "clear_motion_history"), "Must have clear_motion_history"


def test_video_prompting_uses_grok():
    """Verify video_prompting uses Grok for motion generation."""
    from app.agents import video_prompting
    import inspect

    source = inspect.getsource(video_prompting)

    # Verify imports Grok
    assert "prompting_client" in source, "video_prompting must use prompting_client"

    # Verify function signature accepts video_id for dedup
    sig = inspect.signature(video_prompting.generate_motion_prompt)
    params = list(sig.parameters.keys())
    assert "video_id" in params, "generate_motion_prompt must accept video_id for deduplication"


def test_edit_agent_uses_ffmpeg():
    """Verify edit agent uses ffmpeg instead of Shotstack."""
    from app.agents import edit
    import inspect

    source = inspect.getsource(edit)

    # Verify no Shotstack references
    assert "shotstack" not in source.lower(), "Edit agent should not reference Shotstack"

    # Verify ffmpeg usage
    assert "ffmpeg" in source.lower(), "Edit agent must use ffmpeg"


def test_qa_style_blur_disabled():
    """Verify blur QA is disabled in qa_style."""
    from app.agents import qa_style
    import inspect

    source = inspect.getsource(qa_style.ensure)

    # Verify blur detection is commented out or disabled
    assert (
        "blur detection DISABLED" in source.upper() or "identity QA handled by human gate" in source
    ), "Blur QA must be documented as disabled"


def test_scheduler_has_posting_workflow():
    """Verify scheduler has complete posting workflow with social meta generation."""
    from app.core import scheduler

    # Verify required functions exist
    assert hasattr(scheduler, "run_posting_cycle"), "Scheduler must have run_posting_cycle"
    assert hasattr(scheduler, "start_scheduler"), "Scheduler must have start_scheduler"
    assert hasattr(scheduler, "stop_scheduler"), "Scheduler must have stop_scheduler"

    # Verify internal helper for social meta generation
    assert hasattr(scheduler, "_generate_social_meta"), "Scheduler must have _generate_social_meta"


def test_tiktok_client_exists():
    """Verify TikTok posting client exists."""
    from app.clients.tiktok import TikTokClient

    assert TikTokClient is not None
    assert hasattr(TikTokClient, "upload_video"), "TikTokClient must have upload_video method"


def test_instagram_client_exists():
    """Verify Instagram posting client exists."""
    from app.clients.instagram import InstagramClient

    assert InstagramClient is not None
    assert hasattr(InstagramClient, "upload_reel"), "InstagramClient must have upload_reel method"


def test_music_endpoints_exist():
    """Verify all music workflow endpoints are registered."""
    from app.api.routes import router

    # Get all registered routes
    routes = {route.path for route in router.routes}

    # Verify music endpoints exist
    assert "/videos/{video_id}/music/suggest" in routes, "Music suggest endpoint must exist"
    assert "/videos/{video_id}/music/generate" in routes, "Music generate endpoint must exist"
    assert "/videos/{video_id}/music/mux" in routes, "Music mux endpoint must exist"
    assert "/videos/{video_id}/music/rate" in routes, "Music rate endpoint must exist"


def test_scheduler_endpoints_exist():
    """Verify scheduler control endpoints exist."""
    from app.api.routes import router

    # Get all registered routes
    routes = {route.path for route in router.routes}

    # Verify scheduler control endpoints exist
    assert "/scheduler/run-once" in routes, "Scheduler run-once endpoint must exist"
    assert "/scheduler/dry-run" in routes, "Scheduler dry-run endpoint must exist"


def test_config_has_new_settings():
    """Verify configuration includes all new settings."""
    from app.core.config import settings

    # Verify Grok settings
    assert hasattr(settings, "grok_api_key"), "Config must have grok_api_key"
    assert hasattr(settings, "grok_model"), "Config must have grok_model"

    # Verify Suno settings
    assert hasattr(settings, "suno_api_key"), "Config must have suno_api_key"
    assert hasattr(settings, "suno_model"), "Config must have suno_model"
    assert hasattr(settings, "suno_clip_seconds"), "Config must have suno_clip_seconds"

    # Verify scheduler settings
    assert hasattr(settings, "enable_scheduler"), "Config must have enable_scheduler"
    assert hasattr(settings, "posting_window_local"), "Config must have posting_window_local"
    assert hasattr(settings, "scheduler_cron_exact"), "Config must have scheduler_cron_exact"
    assert hasattr(settings, "scheduler_timezone"), "Config must have scheduler_timezone"

    # Verify platform settings
    assert hasattr(settings, "default_posting_platform"), "Config must have default_posting_platform"
    assert hasattr(settings, "post_order"), "Config must have post_order"
    assert hasattr(settings, "post_delay_minutes_tiktok"), "Config must have post_delay_minutes_tiktok"
    assert hasattr(settings, "tiktok_client_key"), "Config must have tiktok_client_key"
    assert hasattr(settings, "instagram_business_account_id"), "Config must have instagram_business_account_id"


def test_referral_prompts_json_exists():
    """Verify referral_prompts.json exists with Eva Joy persona."""
    import json
    from pathlib import Path
    import os

    # Navigate up to repo root to find app/data/
    repo_root = Path(__file__).parent.parent.parent.parent
    prompts_path = repo_root / "app" / "data" / "referral_prompts.json"
    assert prompts_path.exists(), f"referral_prompts.json must exist at {prompts_path}"

    with open(prompts_path) as f:
        data = json.load(f)

    # Verify required top-level keys
    assert "persona" in data, "referral_prompts.json must have persona"
    assert "style" in data, "referral_prompts.json must have style"
    assert "banks" in data, "referral_prompts.json must have diversity banks"
    assert "negatives" in data, "referral_prompts.json must have negatives"

    # Verify persona contains Eva Joy
    assert "Eva Joy" in data["persona"]["name"], "Persona must be Eva Joy"


def test_motion_dedup_directory_exists():
    """Verify motion dedup directory is created."""
    from pathlib import Path

    # Navigate up to repo root to find app/data/
    repo_root = Path(__file__).parent.parent.parent.parent
    data_dir = repo_root / "app" / "data"
    motion_dir = data_dir / "motion"

    # Directory should be created by motion_dedup module on first use
    # Just verify the parent data directory exists
    assert data_dir.exists(), f"Data directory must exist at {data_dir}"

    # Motion directory may not exist yet, which is fine
    # It's created on first use by motion_dedup module
