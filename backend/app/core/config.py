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
    gen_seconds: int = Field(default=8, env="GEN_DEFAULT_SECONDS")
    gen_fps: int = Field(default=12, env="GEN_DEFAULT_FPS")

    # Provider selection
    video_provider: str = Field(default="veo", env="VIDEO_PROVIDER")

    # GCP / Veo 3 configuration
    gcp_project_id: str | None = Field(default=None, env="GCP_PROJECT_ID")
    gcp_location: str = Field(default="us-central1", env="GCP_LOCATION")
    veo_model_id: str = Field(default="veo-3.0-generate-001", env="VEO_MODEL_ID")
    veo_aspect: str = Field(default="9:16", env="VEO_ASPECT")
    veo_duration_seconds: int = Field(default=8, env="VEO_DURATION_SECONDS")
    veo_num_results: int = Field(default=1, env="VEO_NUM_RESULTS")

    # Leonardo (Image Generation)
    leonardo_api_key: str | None = Field(default=None, env="LEONARDO_API_KEY")
    leonardo_model_id: str | None = Field(default=None, env="LEONARDO_MODEL_ID")

    # Shotstack (Video Editing)
    shotstack_api_key: str | None = Field(default=None, env="SHOTSTACK_API_KEY")
    shotstack_region: str = Field(default="us", env="SHOTSTACK_REGION")
    soundtrack_url: str | None = Field(default=None, env="SOUNDTRACK_URL")
    output_resolution: str = Field(default="HD", env="OUTPUT_RESOLUTION")

    # Pika Labs (alternative video provider)
    pika_api_key: str | None = Field(default=None, env="PIKA_API_KEY")

    # TikTok API
    tiktok_client_key: str | None = Field(default=None, env="TIKTOK_CLIENT_KEY")
    tiktok_client_secret: str | None = Field(default=None, env="TIKTOK_CLIENT_SECRET")

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
