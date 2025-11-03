from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load .env file into environment variables
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)


class Settings(BaseSettings):
    """Application configuration with fail-loud validation."""

    allow_live: bool = Field(default=False, env="ALLOW_LIVE")
    enable_scheduler: bool = Field(default=False, env="ENABLE_SCHEDULER")
    batch_size: int = Field(default=3, env="COORDINATOR_BATCH_SIZE")
    max_parallel: int = Field(default=3, env="COORDINATOR_MAX_PARALLEL")
    max_cost_per_run: Decimal = Field(default=Decimal("0.75"), env="MAX_COST_PER_RUN")
    gen_seconds: int = Field(default=6, env="GEN_DEFAULT_SECONDS")
    gen_fps: int = Field(default=12, env="GEN_DEFAULT_FPS")

    # Provider selection
    video_provider: str = Field(default="veo", env="VIDEO_PROVIDER")

    # GCP / Veo 3 configuration
    gcp_project_id: str | None = Field(default=None, env="GCP_PROJECT_ID")
    gcp_location: str = Field(default="us-central1", env="GCP_LOCATION")
    veo_model_id: str = Field(default="veo-3.0-generate-001", env="VEO_MODEL_ID")
    veo_aspect: str = Field(default="9:16", env="VEO_ASPECT")
    veo_duration_seconds: int = Field(default=6, env="VEO_DURATION_SECONDS")
    veo_num_results: int = Field(default=1, env="VEO_NUM_RESULTS")

    # Grok (xAI - Image Briefs, Motion, Music, Social Meta)
    grok_api_key: str | None = Field(default=None, env="GROK_API_KEY")
    grok_model: str = Field(default="grok-2-latest", env="GROK_MODEL")
    grok_timeout_s: int = Field(default=45, env="GROK_TIMEOUT_S")

    # Suno (Music Generation)
    suno_api_key: str | None = Field(default=None, env="SUNO_API_KEY")
    suno_model: str = Field(default="chirp-v3", env="SUNO_MODEL")
    suno_clip_seconds: int = Field(default=6, env="SUNO_CLIP_SECONDS")
    suno_style_hints_default: str = Field(default="ambient cinematic fitness", env="SUNO_STYLE_HINTS_DEFAULT")

    # Leonardo (Image Generation)
    leonardo_api_key: str | None = Field(default=None, env="LEONARDO_API_KEY")
    leonardo_model_id: str | None = Field(default=None, env="LEONARDO_MODEL_ID")

    # Local AV Tools
    ffmpeg_path: str = Field(default="ffmpeg", env="FFMPEG_PATH")
    ffprobe_path: str = Field(default="ffprobe", env="FFPROBE_PATH")

    # TikTok (Content Posting API)
    tiktok_client_key: str | None = Field(default=None, env="TIKTOK_CLIENT_KEY")
    tiktok_client_secret: str | None = Field(default=None, env="TIKTOK_CLIENT_SECRET")
    tiktok_access_token: str | None = Field(default=None, env="TIKTOK_ACCESS_TOKEN")

    # Instagram/Facebook (Graph API)
    instagram_business_account_id: str | None = Field(default=None, env="INSTAGRAM_BUSINESS_ACCOUNT_ID")
    facebook_page_id: str | None = Field(default=None, env="FACEBOOK_PAGE_ID")
    fb_app_id: str | None = Field(default=None, env="FB_APP_ID")
    fb_app_secret: str | None = Field(default=None, env="FB_APP_SECRET")
    fb_access_token: str | None = Field(default=None, env="FB_ACCESS_TOKEN")

    # Scheduler (Posting Only)
    posting_window_local: str = Field(default="09:00-21:00", env="POSTING_WINDOW_LOCAL")
    scheduler_timezone: str = Field(default="Europe/Paris", env="SCHEDULER_TIMEZONE")
    scheduler_cron_minutes: str = Field(default="*/20", env="SCHEDULER_CRON_MINUTES")
    default_posting_platform: str = Field(default="tiktok", env="DEFAULT_POSTING_PLATFORM")

    class Config:
        env_file = "../.env"  # Look in parent directory (project root)
        extra = "ignore"


settings = Settings()


def assert_live_keys() -> None:
    """Validates that ALLOW_LIVE is true before making paid API calls."""
    if not settings.allow_live:
        raise RuntimeError(
            "ALLOW_LIVE=false. Enable explicitly to permit paid API calls."
        )
