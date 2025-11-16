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
from app.core.locations import get_all_locations, get_location_by_id
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

    setting_id: str  # Location ID from /api/locations (e.g., "japan", "us/new_york/manhattan/times_square")
    seed_words: list[str] | None = None  # Optional embellisher keywords
    count: int = 1  # Number of bundles to generate (1-10)

    # Per-slot binding toggles
    bind_scene: bool = True
    bind_pose_microaction: bool = True
    bind_lighting: bool = True
    bind_camera: bool = True
    bind_angle: bool = True
    bind_accessories: bool = True
    bind_wardrobe: bool = True  # STEP 2: Wardrobe binding ON by default

    single_accessory: bool = True  # If True, bind exactly 1 accessory; if False, bind 2


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

    # Validate setting_id
    location = get_location_by_id(body.setting_id)
    if not location:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid setting_id: '{body.setting_id}'. Please select from /api/locations."
        )

    try:
        # Generate bundles via LLM (Grok by default)
        llm = prompting_client()
        bundles = llm.generate_prompt_bundle(
            setting_id=body.setting_id,
            location_label=location["label"],
            location_path=location["path"],
            seed_words=body.seed_words,
            count=body.count,
            bind_scene=body.bind_scene,
            bind_pose_microaction=body.bind_pose_microaction,
            bind_lighting=body.bind_lighting,
            bind_camera=body.bind_camera,
            bind_angle=body.bind_angle,
            bind_accessories=body.bind_accessories,
            bind_wardrobe=body.bind_wardrobe,
            single_accessory=body.single_accessory,
        )

        # Store each bundle to prompts.jsonl
        from app.core.prompt_storage import append_prompt_bundle

        for bundle in bundles:
            # Add social metadata to bundle
            # Generate social meta for each bundle
            try:
                media_meta = {
                    "bundle_id": bundle["id"],
                    "setting": location["label"],
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
                setting=location["label"],
                seed_words=body.seed_words
            )

        log.info(f"PROMPT_BUNDLE_CREATED count={len(bundles)} setting_id={body.setting_id}")

        return {"ok": True, "bundles": bundles}

    except Exception as e:
        log.error(f"PROMPT_BUNDLE_FAILED: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts")
@limiter.limit("30/minute")
def get_recent_prompts(
    request: Request,
    status: str = "all",  # all, used, unused
    search: str = "",
    page: int = 1,
    page_size: int = 20,
    sort: str = "-created_at",  # created_at, -created_at, location, -location
    fetch_all: str = "false",  # "true" to return all prompts (no pagination)
    order: str = "created_desc",  # created_desc, created_asc (fallback to sort if not provided)
) -> dict:
    """Get prompt bundles with pagination, search, and filtering.

    Args:
        request: FastAPI request object (for rate limiting)
        status: Filter by used status (all, used, unused)
        search: Search across id, location, seed_words
        page: Page number (1-indexed)
        page_size: Items per page (default 20, max 100)
        sort: Sort field (created_at, -created_at, location, -location)
        all: "true" to return all prompts without pagination
        order: Sort order (created_desc, created_asc); defaults to created_desc

    Returns:
        Dict with:
        {
            "ok": True,
            "items": [
                {
                    "id": "pr_abc123...",
                    "created_at": "2025-11-14T20:45:00Z",
                    "location": "Times Square — Manhattan, NY",
                    "seed_words": ["neon"],
                    "used": false,
                    "summary": "Medium wavy caramel-blonde hair...",
                    "media": {"w": 864, "h": 1536, "ar": "9:16"},
                    "has_negative": true
                },
                ...
            ],
            "page": 1,
            "page_size": 20,
            "total": 253
        }
    """
    # Parse fetch_all flag
    all_flag = fetch_all.lower() == "true"

    # Cap page_size to 100 (unless fetch_all=true)
    if not all_flag:
        page_size = min(page_size, 100)
        page = max(page, 1)

    try:
        from app.core.prompt_storage import read_all_prompts, load_prompt_states

        # Get all prompts (we'll filter and paginate in memory)
        all_prompts = read_all_prompts(prompts_dir=settings.prompts_out_dir)

        # Enrich with used state
        states = load_prompt_states(settings.prompts_out_dir)
        for prompt in all_prompts:
            prompt_id = prompt.get("id")
            if prompt_id and prompt_id in states:
                prompt["used"] = states[prompt_id].get("used", False)
            else:
                prompt["used"] = False

        # Filter by status
        if status == "used":
            all_prompts = [p for p in all_prompts if p.get("used")]
        elif status == "unused":
            all_prompts = [p for p in all_prompts if not p.get("used")]

        # Filter by search
        if search:
            search_lower = search.lower()
            filtered = []
            for p in all_prompts:
                if (
                    search_lower in p.get("id", "").lower()
                    or search_lower in p.get("setting", "").lower()
                    or any(search_lower in sw.lower() for sw in p.get("seed_words", []))
                    or search_lower in p.get("image_prompt", {}).get("final_prompt", "").lower()[:200]
                ):
                    filtered.append(p)
            all_prompts = filtered

        # Sort (prefer order param, fallback to sort for backwards compatibility)
        if order == "created_asc":
            all_prompts.sort(key=lambda p: p.get("timestamp", ""), reverse=False)
        elif order == "created_desc":
            all_prompts.sort(key=lambda p: p.get("timestamp", ""), reverse=True)
        else:
            # Fallback to legacy sort param
            reverse = sort.startswith("-")
            sort_field = sort.lstrip("-")
            if sort_field == "created_at":
                all_prompts.sort(key=lambda p: p.get("timestamp", ""), reverse=reverse)
            elif sort_field == "location":
                all_prompts.sort(key=lambda p: p.get("setting", ""), reverse=reverse)

        # Paginate (skip if fetch_all=true)
        total = len(all_prompts)
        if all_flag:
            # Return all items without pagination
            page_items = all_prompts
            page = 1
            page_size = total
        else:
            # Normal pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_items = all_prompts[start_idx:end_idx]

        # Create summary items (remove full prompts to save bandwidth)
        items = []
        for p in page_items:
            img_prompt = p.get("image_prompt", {}).get("final_prompt", "")
            items.append({
                "id": p.get("id"),
                "created_at": p.get("timestamp"),
                "location": p.get("setting"),
                "seed_words": p.get("seed_words", []),
                "used": p.get("used", False),
                "summary": img_prompt[:100] + "..." if len(img_prompt) > 100 else img_prompt,
                "media": {
                    "w": p.get("image_prompt", {}).get("width", 864),
                    "h": p.get("image_prompt", {}).get("height", 1536),
                    "ar": "9:16",  # Standard aspect ratio
                },
                "has_negative": bool(p.get("image_prompt", {}).get("negative_prompt")),
            })

        return {
            "ok": True,
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    except Exception as e:
        log.error(f"READ_PROMPTS_FAILED: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts/{bundle_id}")
@limiter.limit("60/minute")
def get_prompt_bundle(request: Request, bundle_id: str) -> dict:
    """Get full prompt bundle details by ID.

    Args:
        request: FastAPI request object (for rate limiting)
        bundle_id: Prompt bundle ID (pr_...)

    Returns:
        Dict with:
        {
            "ok": True,
            "bundle": {
                "id": "pr_606ffe047",
                "created_at": "2025-11-14T20:45:00Z",
                "location": "Times Square — Manhattan, NY",
                "seed_words": ["neon"],
                "used": false,
                "image_prompt": "…full text…",
                "video": {
                    "motion": "…",
                    "action": "…",
                    "environment": "…",
                    "duration": "6s",
                    "notes": "…"
                },
                "media": {
                    "dimensions": "864 × 1536",
                    "aspect": "9:16",
                    "format": "vertical"
                },
                "negative_prompt": "…"
            }
        }

    Raises:
        HTTPException: 404 if bundle not found, 500 on error
    """
    try:
        from app.core.prompt_storage import find_prompt_bundle, get_prompt_state

        # Find bundle
        bundle = find_prompt_bundle(settings.prompts_out_dir, bundle_id)
        if not bundle:
            raise HTTPException(
                status_code=404,
                detail=f"Prompt bundle not found: {bundle_id}"
            )

        # Get used state
        state = get_prompt_state(settings.prompts_out_dir, bundle_id)
        used = state.get("used", False) if state else False

        # Format response
        img = bundle.get("image_prompt", {})
        vid = bundle.get("video_prompt", {})

        # Handle both new single-line format and old multi-field format
        if "line" in vid:
            # New format: single motion line
            video_data = {"line": vid.get("line", "")}
        else:
            # Old format: fallback rendering - compose into single line
            motion = vid.get("motion", "")
            action = vid.get("character_action", "")
            environment = vid.get("environment", "")

            # Compose fallback line
            if motion or action:
                fallback_line = f"natural, realistic — handheld {motion}, she {action}; finish eye-level front."
            else:
                fallback_line = "natural, realistic — handheld push-in, she holds position; finish eye-level front."

            video_data = {"line": fallback_line}

        return {
            "ok": True,
            "bundle": {
                "id": bundle.get("id"),
                "created_at": bundle.get("timestamp"),
                "location": bundle.get("setting"),
                "seed_words": bundle.get("seed_words", []),
                "used": used,
                "image_prompt": img.get("final_prompt", ""),
                "video": video_data,
                "media": {
                    "dimensions": f"{img.get('width', 864)} × {img.get('height', 1536)}",
                    "aspect": "9:16",
                    "format": "vertical",
                },
                "negative_prompt": img.get("negative_prompt", ""),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"GET_PROMPT_BUNDLE_FAILED bundle_id={bundle_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PromptStateUpdate(BaseModel):
    """Request body for updating prompt state."""

    used: bool


@router.patch("/prompts/{bundle_id}/state")
@limiter.limit("60/minute")
async def update_prompt_state(request: Request, bundle_id: str) -> dict:
    """Update used state for a prompt bundle.

    Args:
        request: FastAPI request object (for rate limiting)
        bundle_id: Prompt bundle ID (pr_...)

    Returns:
        Dict with:
        {
            "ok": True,
            "bundle_id": "pr_abc123...",
            "used": true
        }

    Raises:
        HTTPException: 400 if invalid body, 404 if bundle not found, 500 on error
    """
    # Parse body
    try:
        body_bytes = await request.body()
        import json
        body_dict = json.loads(body_bytes)
        body = PromptStateUpdate(**body_dict)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request body: {str(e)}"
        )

    try:
        from app.core.prompt_storage import find_prompt_bundle, update_prompt_state as save_state

        # Verify bundle exists
        bundle = find_prompt_bundle(settings.prompts_out_dir, bundle_id)
        if not bundle:
            raise HTTPException(
                status_code=404,
                detail=f"Prompt bundle not found: {bundle_id}"
            )

        # Update state
        save_state(settings.prompts_out_dir, bundle_id, body.used)

        log.info(f"PROMPT_STATE_UPDATED bundle_id={bundle_id} used={body.used}")

        return {
            "ok": True,
            "bundle_id": bundle_id,
            "used": body.used
        }

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"PROMPT_STATE_UPDATE_FAILED bundle_id={bundle_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Locations Endpoint (Location Discovery)
# ============================================================================


@router.get("/locations")
@limiter.limit("60/minute")
def get_locations(request: Request, refresh: int = 0) -> dict:
    """Get all available locations for prompt generation.

    Scans app/data/locations/ for scene bank JSON files and returns metadata.
    Results are cached in memory; use ?refresh=1 to force rescan.

    Args:
        request: FastAPI request object (for rate limiting)
        refresh: Set to 1 to force filesystem rescan

    Returns:
        Dict with:
        {
            "ok": True,
            "locations": [
                {
                    "id": "japan",
                    "label": "Japan",
                    "group": "Global",
                    "path": "app/data/locations/japan.json",
                    "count": 1000
                },
                ...
            ]
        }

    Raises:
        HTTPException: 500 if scan fails
    """
    try:
        locations = get_all_locations(refresh=bool(refresh))
        return {"ok": True, "locations": locations}
    except Exception as e:
        log.error(f"LOCATIONS_SCAN_FAILED: {e}", exc_info=True)
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
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
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
