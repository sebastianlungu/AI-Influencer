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

    # Manual workflow directories
    prompts_out_dir: str = Field(default="app/data/prompts", env="PROMPTS_OUT_DIR")
    persona_file: str = Field(default="app/data/persona.json", env="PERSONA_FILE")
    variety_file: str = Field(default="app/data/variety_bank.json", env="VARIETY_FILE")
    manual_images_dir: str = Field(default="app/data/manual/images", env="MANUAL_IMAGES_DIR")
    manual_videos_dir: str = Field(default="app/data/manual/videos", env="MANUAL_VIDEOS_DIR")

    # Enforced formats
    image_width: int = Field(default=864, env="IMAGE_WIDTH")
    image_height: int = Field(default=1536, env="IMAGE_HEIGHT")
    video_must_be_seconds: int = Field(default=6, env="VIDEO_MUST_BE_SECONDS")
    video_aspect: str = Field(default="9:16", env="VIDEO_ASPECT")

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
    grok_model: str = Field(default="grok-4-fast-reasoning", env="GROK_MODEL")
    grok_timeout_s: int = Field(default=30, env="GROK_TIMEOUT_S")

    # Suno (Music Generation)
    suno_api_key: str | None = Field(default=None, env="SUNO_API_KEY")
    suno_model: str = Field(default="chirp-v3", env="SUNO_MODEL")
    suno_clip_seconds: int = Field(default=6, env="SUNO_CLIP_SECONDS")
    suno_style_hints_default: str = Field(default="ambient cinematic fitness", env="SUNO_STYLE_HINTS_DEFAULT")

    # Leonardo (Image Generation) - LOCKED TO VISION XL + EVA JOY LORA
    leonardo_api_key: str | None = Field(default=None, env="LEONARDO_API_KEY")
    # REQUIRED: Vision XL model ID (fails at startup if missing)
    leonardo_model_id: str = Field(env="LEONARDO_MODEL_ID")
    # Eva Joy LoRA Element (LOCKED)
    leonardo_lora_id: int = Field(default=155265, env="LEONARDO_LORA_ID")
    leonardo_lora_weight: float = Field(default=0.80, env="LEONARDO_LORA_WEIGHT")
    # Native 9:16 High-Res (NO UPSCALING) - Max 1536px height per Leonardo API limits
    leonardo_width: int = Field(default=864, env="LEONARDO_WIDTH")
    leonardo_height: int = Field(default=1536, env="LEONARDO_HEIGHT")
    # Alchemy V2 (REQUIRED for Vision XL + custom Elements)
    leonardo_use_alchemy: bool = Field(default=True, env="LEONARDO_USE_ALCHEMY")
    leonardo_preset_style: str = Field(default="DYNAMIC", env="LEONARDO_PRESET_STYLE")
    # Generation Quality (legacy parameters - may not work with Alchemy)
    leonardo_cfg: float = Field(default=7.0, env="LEONARDO_CFG")
    leonardo_steps: int = Field(default=32, env="LEONARDO_STEPS")
    leonardo_use_legacy_params: bool = Field(default=False, env="LEONARDO_USE_LEGACY_PARAMS")
    # Guards (fail-loud)
    leonardo_require_compatible_base: bool = Field(default=True, env="LEONARDO_REQUIRE_COMPATIBLE_BASE")
    leonardo_forbid_fallbacks: bool = Field(default=True, env="LEONARDO_FORBID_FALLBACKS")
    # Legacy (deprecated - for backward compatibility)
    leonardo_element_id: str | None = Field(default="155265", env="LEONARDO_ELEMENT_ID")
    leonardo_element_trigger: str | None = Field(default=None, env="LEONARDO_ELEMENT_TRIGGER")
    leonardo_element_weight: float = Field(default=0.80, env="LEONARDO_ELEMENT_WEIGHT")

    # Prompt guardrails (length only, no SFW redrafting)
    prompt_max_len: int = Field(default=1500, env="PROMPT_MAX_LEN")
    negative_max_len: int = Field(default=400, env="NEGATIVE_MAX_LEN")
    prompt_allow_rewrite: bool = Field(default=False, env="PROMPT_ALLOW_REWRITE")
    rewrite_max_attempts: int = Field(default=0, env="REWRITE_MAX_ATTEMPTS")

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
    scheduler_cron_exact: str = Field(
        default="0 0,6,12,18 * * *",  # Every 6 hours: 00:00, 06:00, 12:00, 18:00
        env="SCHEDULER_CRON_EXACT",
    )
    default_posting_platform: str = Field(default="tiktok", env="DEFAULT_POSTING_PLATFORM")
    # Platform posting order and delays
    post_order: str = Field(
        default="instagram,tiktok",  # Comma-separated list, Instagram first
        env="POST_ORDER",
    )
    post_delay_minutes_tiktok: int = Field(
        default=90,  # Wait 90 minutes after Instagram before posting to TikTok
        env="POST_DELAY_MINUTES_TIKTOK",
    )

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
