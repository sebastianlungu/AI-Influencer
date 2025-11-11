"""Prompt Lab configuration (LLM + data paths only)."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load .env file into environment variables
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)


class Settings(BaseSettings):
    """Prompt Lab configuration with fail-loud validation."""

    # LLM Provider Selection
    llm_provider: str = Field(default="grok", env="LLM_PROVIDER")

    # Grok (xAI) - Default LLM Provider
    grok_api_key: str | None = Field(default=None, env="GROK_API_KEY")
    grok_model: str = Field(default="grok-beta", env="GROK_MODEL")
    grok_timeout_s: int = Field(default=30, env="GROK_TIMEOUT_S")

    # Future LLM Providers (stubs for later implementation)
    # gemini_api_key: str | None = Field(default=None, env="GEMINI_API_KEY")
    # gemini_model: str = Field(default="gemini-pro", env="GEMINI_MODEL")
    # gpt_api_key: str | None = Field(default=None, env="OPENAI_API_KEY")
    # gpt_model: str = Field(default="gpt-4", env="GPT_MODEL")

    # Prompt Lab Data Paths
    persona_file: str = Field(default="app/data/persona.json", env="PERSONA_FILE")
    variety_file: str = Field(default="app/data/variety_bank.json", env="VARIETY_FILE")
    prompts_out_dir: str = Field(default="app/data/prompts", env="PROMPTS_OUT_DIR")

    class Config:
        env_file = "../.env"  # Look in parent directory (project root)
        extra = "ignore"


settings = Settings()
