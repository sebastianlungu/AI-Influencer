"""Prompt Lab API routes (prompt generation + observability only)."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.clients.provider_selector import prompting_client
from app.core.config import settings
from app.core.logging import log, truncate_log_file
from app.core.paths import get_data_path

router = APIRouter()

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)


# ============================================================================
# Prompt Bundle Endpoints (Manual Workflow)
# ============================================================================


class PromptBundleRequest(BaseModel):
    """Request body for generating prompt bundles."""

    setting: str  # High-level setting (e.g., "Japan", "Santorini")
    seed_words: list[str] | None = None  # Optional embellisher keywords
    count: int = 1  # Number of bundles to generate (1-10)


@router.post("/prompts/bundle")
@limiter.limit("10/minute")
async def generate_prompt_bundle(request: Request) -> dict:
    """Generate prompt bundles (image + video + social prompts) for manual workflow.

    Returns N prompt bundles, each containing:
    - Unique ID (for file naming)
    - Image prompt (with dimensions 864×1536, 900-1100 char target)
    - Video motion prompt (6s duration)
    - Social metadata (title, tags, hashtags)

    Rate limited to 10 requests per minute per client.

    Args:
        request: FastAPI request object (for rate limiting)

    Returns:
        Dict with:
        {
            "ok": True,
            "bundles": [
                {
                    "id": "pr_abc123...",
                    "image_prompt": {...},
                    "video_prompt": {...},
                    "social_meta": {...}
                },
                ...
            ]
        }

    Raises:
        HTTPException: 400 if count invalid or invalid body, 500 if generation fails
        RuntimeError: If LLM API key missing
    """
    # Parse body manually to work around slowapi/FastAPI integration issue
    try:
        body_bytes = await request.body()
        import json
        body_dict = json.loads(body_bytes)
        body = PromptBundleRequest(**body_dict)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request body: {str(e)}"
        )

    # Validate count
    if not (1 <= body.count <= 10):
        raise HTTPException(
            status_code=400,
            detail="count must be between 1 and 10"
        )

    try:
        # Generate bundles via LLM (Grok by default)
        llm = prompting_client()
        bundles = llm.generate_prompt_bundle(
            setting=body.setting,
            seed_words=body.seed_words,
            count=body.count
        )

        # Store each bundle to prompts.jsonl
        from app.core.prompt_storage import append_prompt_bundle

        for bundle in bundles:
            # Add social metadata to bundle
            # Generate social meta for each bundle
            try:
                media_meta = {
                    "bundle_id": bundle["id"],
                    "setting": body.setting,
                    "image_prompt": bundle["image_prompt"]["final_prompt"][:200],
                    "video_motion": bundle["video_prompt"].get("motion", "")[:100],
                }
                social_meta = llm.generate_social_meta(media_meta)
                bundle["social_meta"] = social_meta
            except Exception as e:
                log.warning(f"SOCIAL_META_GENERATION_FAILED bundle_id={bundle['id']}: {e}")
                # Provide fallback social meta
                bundle["social_meta"] = {
                    "title": "Fitness Inspiration",
                    "tags": ["fitness", "workout", "motivation"],
                    "hashtags": ["#fitness", "#workout", "#motivation"],
                }

            append_prompt_bundle(
                prompts_dir=settings.prompts_out_dir,
                bundle=bundle,
                setting=body.setting,
                seed_words=body.seed_words
            )

        log.info(f"PROMPT_BUNDLE_CREATED count={len(bundles)} setting={body.setting}")

        return {"ok": True, "bundles": bundles}

    except Exception as e:
        log.error(f"PROMPT_BUNDLE_FAILED: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts")
@limiter.limit("30/minute")
def get_recent_prompts(request: Request, limit: int = 20) -> dict:
    """Get recent prompt bundles (newest first).

    Args:
        request: FastAPI request object (for rate limiting)
        limit: Max number of bundles to return (default 20, max 100)

    Returns:
        Dict with:
        {
            "ok": True,
            "prompts": [
                {
                    "id": "pr_abc123...",
                    "timestamp": "2025-11-07T12:34:56.789Z",
                    "setting": "Japan",
                    "seed_words": ["dojo", "dusk"],
                    "image_prompt": {...},
                    "video_prompt": {...},
                    "social_meta": {...}
                },
                ...
            ]
        }
    """
    # Cap limit to 100
    limit = min(limit, 100)

    try:
        from app.core.prompt_storage import read_recent_prompts

        prompts = read_recent_prompts(
            prompts_dir=settings.prompts_out_dir,
            limit=limit
        )

        return {"ok": True, "prompts": prompts}

    except Exception as e:
        log.error(f"READ_PROMPTS_FAILED: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Health & Observability
# ============================================================================


@router.get("/healthz")
def healthz() -> dict:
    """Health check endpoint with Prompt Lab readiness status.

    Returns:
        Dict with status and configuration (NO SECRETS)
    """
    # Check LLM provider availability
    llm_status = "key_missing"
    if settings.llm_provider == "grok":
        llm_status = "configured" if settings.grok_api_key else "key_missing"
    # Future: add gemini, gpt checks here

    # Check persona and variety bank files
    persona_path = Path(settings.persona_file)
    variety_path = Path(settings.variety_file)

    return {
        "ok": True,
        "mode": "prompt_lab",
        "llm": {
            "provider": settings.llm_provider,
            "model": settings.grok_model if settings.llm_provider == "grok" else "unknown",
            "status": llm_status,
        },
        "config_files": {
            "persona": "present" if persona_path.exists() else "missing",
            "variety_bank": "present" if variety_path.exists() else "missing",
        },
        "prompts_output": settings.prompts_out_dir,
    }


@router.get("/logs/tail")
@limiter.limit("60/minute")
def get_logs_tail(request: Request, lines: int = 100) -> dict:
    """Get last N lines from logs.txt for real-time log viewing.

    Args:
        request: FastAPI request object (for rate limiting)
        lines: Number of lines to return (default 100, max 10000)

    Returns:
        Dict with log lines array and metadata
    """
    # Truncate log file if needed (keeps last 10k lines)
    truncate_log_file()

    max_lines = min(lines, 10000)  # Cap at 10000 lines
    log_file = str(get_data_path("logs.txt"))

    if not os.path.exists(log_file):
        return {"ok": True, "logs": [], "message": "No logs yet"}

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            tail_lines = all_lines[-max_lines:] if len(all_lines) > max_lines else all_lines

        return {
            "ok": True,
            "logs": [line.rstrip('\n') for line in tail_lines],
            "total_lines": len(all_lines),
            "returned_lines": len(tail_lines)
        }
    except Exception as e:
        log.error(f"Failed to read logs: {e}")
        return {"ok": False, "error": str(e)}
