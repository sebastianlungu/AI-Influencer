from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration with fail-loud validation."""

    allow_live: bool = Field(default=False, env="ALLOW_LIVE")
    enable_scheduler: bool = Field(default=False, env="ENABLE_SCHEDULER")
    batch_size: int = Field(default=3, env="COORDINATOR_BATCH_SIZE")
    max_parallel: int = Field(default=3, env="COORDINATOR_MAX_PARALLEL")
    max_cost_per_run: float = Field(default=0.75, env="MAX_COST_PER_RUN")
    gen_seconds: int = Field(default=8, env="GEN_DEFAULT_SECONDS")
    gen_fps: int = Field(default=12, env="GEN_DEFAULT_FPS")

    leonardo_api_key: str | None = None
    pika_api_key: str | None = None
    shotstack_api_key: str | None = None
    tiktok_client_key: str | None = None
    tiktok_client_secret: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def assert_live_keys() -> None:
    """Validates that ALLOW_LIVE is true before making paid API calls."""
    if not settings.allow_live:
        raise RuntimeError(
            "ALLOW_LIVE=false. Enable explicitly to permit paid API calls."
        )
