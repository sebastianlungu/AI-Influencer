"""LLM provider selection for Prompt Lab (provider-agnostic).

Supports swapping between Grok, Gemini, GPT via LLM_PROVIDER env var.
Prompt Lab mode: only prompting_client() is available.
"""

from __future__ import annotations

from app.clients.llm_interface import LLMClient, GrokAdapter
from app.grok import GrokClient
from app.core.config import settings


def _guard_llm(provider: str, key: str | None) -> None:
    """Validates that LLM API key is present.

    Args:
        provider: Provider name (for error messages)
        key: API key value

    Raises:
        RuntimeError: If key is missing
    """
    if not key:
        raise RuntimeError(
            f"Prompt Lab mode requires {provider.upper()}_API_KEY. "
            f"Set {provider.upper()}_API_KEY in .env to enable prompt generation."
        )


def prompting_client() -> LLMClient:
    """Returns configured LLM client for prompt generation.

    Provider selection based on LLM_PROVIDER env var (default: grok).
    Returns LLMClient interface for provider-agnostic access.

    Supported providers:
    - grok: xAI Grok (default)
    - gemini: Google Gemini Pro (future)
    - gpt: OpenAI GPT-4 (future)

    Returns:
        LLMClient implementation for selected provider

    Raises:
        RuntimeError: If API key missing or provider unknown
    """
    provider = settings.llm_provider.lower()

    if provider == "grok":
        _guard_llm("grok", settings.grok_api_key)
        grok = GrokClient(
            api_key=settings.grok_api_key,
            model=settings.grok_model,
        )
        return GrokAdapter(grok)

    elif provider == "gemini":
        raise RuntimeError(
            "Gemini provider not yet implemented. "
            "Set LLM_PROVIDER=grok to use Grok (default)."
        )

    elif provider == "gpt":
        raise RuntimeError(
            "GPT provider not yet implemented. "
            "Set LLM_PROVIDER=grok to use Grok (default)."
        )

    else:
        raise RuntimeError(
            f"Unknown LLM provider: {provider}. "
            f"Supported providers: grok (default), gemini (future), gpt (future)."
        )
