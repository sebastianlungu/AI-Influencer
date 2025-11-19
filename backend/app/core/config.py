"""Prompt Lab configuration (LLM + data paths only)."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Project root directory (parent of backend/)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()

# Load .env file into environment variables
env_path = PROJECT_ROOT / ".env"
load_dotenv(env_path)


class Settings(BaseSettings):
    """Prompt Lab configuration with fail-loud validation."""

    # LLM Provider Selection
    llm_provider: str = Field(default="grok", env="LLM_PROVIDER")

    # Grok (xAI) - Default LLM Provider
    grok_api_key: str | None = Field(default=None, env="GROK_API_KEY")
    grok_model: str = Field(default="grok-beta", env="GROK_MODEL")
    grok_timeout_s: int = Field(default=30, env="GROK_TIMEOUT_S")

    # Cost tracking (Prompt Lab manual workflow)
    max_cost_per_run: float = Field(default=10.0, env="MAX_COST_PER_RUN")

    # Future LLM Providers (stubs for later implementation)
    # gemini_api_key: str | None = Field(default=None, env="GEMINI_API_KEY")
    # gemini_model: str = Field(default="gemini-pro", env="GEMINI_MODEL")
    # gpt_api_key: str | None = Field(default=None, env="OPENAI_API_KEY")
    # gpt_model: str = Field(default="gpt-4", env="GPT_MODEL")

    # Prompt Lab Data Paths (resolved relative to project root)
    persona_file: str = Field(default=str(PROJECT_ROOT / "app" / "data" / "persona.json"), env="PERSONA_FILE")
    variety_file: str = Field(default=str(PROJECT_ROOT / "app" / "data" / "variety_bank.json"), env="VARIETY_FILE")
    prompts_out_dir: str = Field(default=str(PROJECT_ROOT / "app" / "data" / "prompts"), env="PROMPTS_OUT_DIR")

    class Config:
        env_file = "../.env"  # Look in parent directory (project root)
        extra = "ignore"


settings = Settings()
