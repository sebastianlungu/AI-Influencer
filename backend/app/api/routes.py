from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Body, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.agents import edit, gen_video, indexer, qa_safety, qa_style, video_prompting
from app.grok import GrokClient
from app.clients.provider_selector import prompting_client
from app.clients.suno import SunoClient
from app.coordinator.orchestrator import generate_images_cycle
from app.core.config import settings
from app.core.logging import log, truncate_log_file
from app.core.paths import get_data_path
from app.core.scheduler import run_posting_cycle
from app.core.motion_dedup import (
    clear_motion_history,
    get_previous_prompts,
    store_motion_prompt,
)
from app.core.storage import find_json_item, read_json, update_json_item
from app.core.video_queue import (
    enqueue_video_generation,
    get_and_mark_next_job,
    get_queue_status,
    mark_complete,
    mark_failed,
    remove_job,
)

router = APIRouter()

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)


# Request/Response Models
class ImageRatingRequest(BaseModel):
    """Request body for rating an image."""

    rating: str  # "dislike" | "like"


class VideoRatingRequest(BaseModel):
    """Request body for rating a video."""

    rating: str  # "dislike" | "like"


@router.post("/cycle/generate")
@limiter.limit("5/minute")
def cycle_generate(request: Request, n: int | None = None) -> dict:
    """Triggers an image generation cycle.

    Generates images and indexes them to images.json with status=pending_review.
    User then reviews images in UI before video generation.

    Rate limited to 5 requests per minute per client.

    Args:
        request: FastAPI request object (for rate limiting)
        n: Number of images to generate (defaults to COORDINATOR_BATCH_SIZE)

    Returns:
        Dict with ok status and list of generated image metadata

    Raises:
        RuntimeError: If ALLOW_LIVE=false or API keys missing
        RuntimeError: If budget exceeded
        HTTPException: 429 if rate limit exceeded
    """
    batch_size = n if n is not None else settings.batch_size
    items = generate_images_cycle(batch_size)
    return {"ok": True, "items": items}


# ============================================================================
# Scheduler Control Endpoints
# ============================================================================


@router.post("/scheduler/run-once")
@limiter.limit("5/minute")
def scheduler_run_once(request: Request) -> dict:
    """Manually trigger one posting cycle (live).

    Posts one approved video to the configured platform.
    Generates social metadata if missing.
    Updates video status to "posted".

    This is the ONLY way to post videos (no manual post buttons).

    Rate limited to 5 requests per minute per client.

    Args:
        request: FastAPI request object (for rate limiting)

    Returns:
        Dict with cycle results:
        {
            "ok": True/False,
            "posted": 0 or 1,
            "video_id": str or None,
            "platform": str or None,
            "post_id": str or None,
            "skipped_window": True/False,
            "error": str or None,
        }

    Raises:
        RuntimeError: If ALLOW_LIVE=false or platform credentials missing
        HTTPException: 429 if rate limit exceeded
    """
    log.info("SCHEDULER_MANUAL_RUN_ONCE")
    result = run_posting_cycle()
    return result


@router.post("/scheduler/dry-run")
@limiter.limit("10/minute")
def scheduler_dry_run(request: Request) -> dict:
    """Preview what would be posted without actually posting (dry-run).

    Shows which video would be posted next, with generated social metadata preview.
    Does NOT actually post to any platform.
    Does NOT update video status.

    Rate limited to 10 requests per minute per client.

    Args:
        request: FastAPI request object (for rate limiting)

    Returns:
        Dict with preview data:
        {
            "ok": True,
            "would_post": True/False,
            "video_id": str or None,
            "platform": str,
            "social_meta": dict or None,
            "within_window": True/False,
            "next_run": str (ISO timestamp of next scheduled run),
        }
    """
    log.info("SCHEDULER_DRY_RUN")

    # Check posting window
    from app.core.scheduler import _in_posting_window

    within_window = _in_posting_window()

    # Find approved videos
    videos = read_json("app/data/videos.json")
    approved_videos = [v for v in videos if v.get("status") == "approved"]

    if not approved_videos:
        return {
            "ok": True,
            "would_post": False,
            "video_id": None,
            "platform": settings.default_posting_platform,
            "within_window": within_window,
            "message": "No approved videos ready for posting",
        }

    # Take first approved video
    video = approved_videos[0]
    video_id = video["id"]

    # Generate social meta preview if missing
    social_meta = video.get("social")
    if not social_meta:
        try:
            # Get image metadata for context
            image_id = video.get("image_id")
            image = find_json_item("app/data/images.json", image_id) if image_id else None

            media_meta = {
                "video_id": video_id,
                "motion_prompt": video.get("video_meta", {}).get("motion_prompt", ""),
                "image_meta": image.get("meta", {}) if image else {},
            }

            # Generate social meta via Grok (preview only, not stored)
            grok = prompting_client()
            social_meta = grok.generate_social_meta(media_meta)
        except Exception as e:
            log.warning(f"DRY_RUN social meta generation failed: {e}")
            social_meta = {
                "title": "Fitness Inspiration",
                "tags": ["fitness", "workout", "motivation"],
                "hashtags": ["#fitness", "#workout", "#motivation"],
            }

    # Calculate next scheduled run time
    next_run = None
    if settings.enable_scheduler:
        from app.core.scheduler import scheduler
        if scheduler:
            jobs = scheduler.get_jobs()
            if jobs:
                next_run = jobs[0].next_run_time.isoformat() if jobs[0].next_run_time else None

    return {
        "ok": True,
        "would_post": within_window,
        "video_id": video_id,
        "platform": settings.default_posting_platform,
        "social_meta": social_meta,
        "within_window": within_window,
        "posting_window": settings.posting_window_local,
        "next_scheduled_run": next_run,
        "queue_size": len(approved_videos),
    }


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
    """Generate prompt bundles (image + video prompts) for manual generation workflow.

    Returns N prompt bundles, each containing:
    - Unique ID (for file naming)
    - Image prompt (with dimensions 864×1536)
    - Video prompt (with 6s duration)

    Rate limited to 10 requests per minute per client.

    Args:
        request: FastAPI request object (for rate limiting)
        body: Prompt bundle request with setting, seed_words, count

    Returns:
        Dict with:
        {
            "ok": True,
            "bundles": [
                {
                    "id": "pr_abc123...",
                    "image_prompt": {...},
                    "video_prompt": {...}
                },
                ...
            ]
        }

    Raises:
        HTTPException: 400 if count invalid or invalid body, 500 if generation fails
        RuntimeError: If ALLOW_LIVE=false or Grok API key missing
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
        # Generate bundles via Grok
        grok = prompting_client()
        bundles = grok.generate_prompt_bundle(
            setting=body.setting,
            seed_words=body.seed_words,
            count=body.count
        )

        # Store each bundle to prompts.jsonl
        from app.core.prompt_storage import append_prompt_bundle

        for bundle in bundles:
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
                    "video_prompt": {...}
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


@router.post("/assets/upload")
@limiter.limit("20/minute")
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),
    asset_type: str = Form(...),
    prompt_id: str = Form(...),
) -> dict:
    """Upload manually generated image or video asset.

    Validates dimensions/duration and indexes to images.json or videos.json.

    Rate limited to 20 uploads per minute per client.

    Args:
        request: FastAPI request object (for rate limiting)
        file: Uploaded file (image or video)
        asset_type: "image" or "video"
        prompt_id: Prompt bundle ID (pr_...) to associate with this asset

    Returns:
        Dict with:
        {
            "ok": True,
            "asset_id": "img_abc123" or "vid_abc123",
            "type": "image" or "video",
            "path": "app/data/manual/images/img_abc123.png",
            "prompt_id": "pr_...",
            "status": "pending_review"
        }

    Raises:
        HTTPException: 400 if validation fails, 500 on storage errors
    """
    import shutil
    import uuid
    from datetime import datetime, timezone

    from app.agents.validators import ValidationError, validate_image_dimensions, validate_video_format
    from app.core.storage import append_json_line

    # Validate asset_type
    if asset_type not in ["image", "video"]:
        raise HTTPException(
            status_code=400,
            detail='asset_type must be "image" or "video"'
        )

    # Verify prompt_id exists
    try:
        from app.core.prompt_storage import find_prompt_bundle

        prompt_bundle = find_prompt_bundle(settings.prompts_out_dir, prompt_id)
        if not prompt_bundle:
            raise HTTPException(
                status_code=400,
                detail=f"Prompt bundle {prompt_id} not found"
            )
    except Exception as e:
        log.error(f"PROMPT_LOOKUP_FAILED prompt_id={prompt_id}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid prompt_id: {e}")

    # Determine file extension and destination directory
    file_ext = Path(file.filename or "file").suffix.lower()
    if asset_type == "image":
        if file_ext not in [".png", ".jpg", ".jpeg"]:
            raise HTTPException(
                status_code=400,
                detail="Image must be PNG or JPEG"
            )
        dest_dir = Path(settings.manual_images_dir)
        asset_id = f"img_{uuid.uuid4().hex[:12]}"
        final_path = dest_dir / f"{asset_id}{file_ext}"
        index_file = "app/data/images.json"
    else:  # video
        if file_ext not in [".mp4", ".mov"]:
            raise HTTPException(
                status_code=400,
                detail="Video must be MP4 or MOV"
            )
        dest_dir = Path(settings.manual_videos_dir)
        asset_id = f"vid_{uuid.uuid4().hex[:12]}"
        final_path = dest_dir / f"{asset_id}{file_ext}"
        index_file = "app/data/videos.json"

    # Ensure destination directory exists
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded file to temp location first
    temp_path = dest_dir / f"temp_{uuid.uuid4().hex[:8]}{file_ext}"
    try:
        with temp_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        log.error(f"UPLOAD_SAVE_FAILED: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Validate asset
    try:
        if asset_type == "image":
            validate_image_dimensions(temp_path)
        else:  # video
            validate_video_format(temp_path)
    except ValidationError as e:
        # Delete temp file
        temp_path.unlink(missing_ok=True)
        log.warning(f"UPLOAD_VALIDATION_FAILED type={asset_type} prompt_id={prompt_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Delete temp file
        temp_path.unlink(missing_ok=True)
        log.error(f"UPLOAD_VALIDATION_ERROR type={asset_type}: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {e}")

    # Move to final location
    try:
        shutil.move(str(temp_path), str(final_path))
    except Exception as e:
        temp_path.unlink(missing_ok=True)
        log.error(f"UPLOAD_MOVE_FAILED: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to move file: {e}")

    # Index to JSON
    try:
        timestamp = datetime.now(timezone.utc).isoformat()

        if asset_type == "image":
            entry = {
                "id": asset_id,
                "status": "pending_review",
                "image_path": str(final_path),
                "created_at": timestamp,
                "prompt_id": prompt_id,
                "source": "manual_upload",
            }
        else:  # video
            entry = {
                "id": asset_id,
                "status": "pending_review",
                "video_path": str(final_path),
                "created_at": timestamp,
                "prompt_id": prompt_id,
                "source": "manual_upload",
                "video_meta": {
                    "duration_s": 6,  # Validated to be exactly 6s
                },
            }

        append_json_line(index_file, entry)

        log.info(
            f"ASSET_UPLOADED type={asset_type} id={asset_id} "
            f"prompt_id={prompt_id} path={final_path}"
        )

        return {
            "ok": True,
            "asset_id": asset_id,
            "type": asset_type,
            "path": str(final_path),
            "prompt_id": prompt_id,
            "status": "pending_review",
        }

    except Exception as e:
        # Clean up file on index failure
        final_path.unlink(missing_ok=True)
        log.error(f"ASSET_INDEX_FAILED type={asset_type} id={asset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to index asset: {e}")


# ============================================================================
# Image Rating Endpoints
# ============================================================================


@router.get("/images/pending")
def get_pending_image() -> dict:
    """Get next image pending review.

    Returns first image with status="pending_review" sorted by created_at.

    Returns:
        Dict with image metadata or {"ok": False, "message": "no pending images"}
    """
    images = read_json("app/data/images.json")

    # Filter pending images
    pending = [img for img in images if img.get("status") == "pending_review"]

    if not pending:
        return {"ok": False, "message": "no pending images"}

    # Return oldest pending image
    pending.sort(key=lambda x: x.get("created_at", ""))
    return {"ok": True, "image": pending[0]}


@router.put("/images/{image_id}/rate")
@limiter.limit("60/minute")
async def rate_image(
    request: Request,
    image_id: str
) -> dict:
    """Rate an image (dislike/like).

    - dislike: status → "deleted", file moved to deleted/
    - like: status → "liked" (ready for review/preview)

    Args:
        request: FastAPI request object (for rate limiting + body parsing)
        image_id: Image ID to rate

    Returns:
        Updated image metadata

    Raises:
        HTTPException: 400 if invalid rating or body, 404 if image not found
    """
    # Parse body manually to work around slowapi/FastAPI integration issue
    try:
        body_bytes = await request.body()
        import json
        body_dict = json.loads(body_bytes)
        body = ImageRatingRequest(**body_dict)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request body: {str(e)}"
        )

    valid_ratings = ["dislike", "like"]
    if body.rating not in valid_ratings:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid rating. Must be one of: {', '.join(valid_ratings)}",
        )

    # Find image
    image = find_json_item("app/data/images.json", image_id)
    if not image:
        raise HTTPException(status_code=404, detail=f"Image {image_id} not found")

    # Determine new status based on rating
    status_map = {
        "dislike": "deleted",
        "like": "liked",
    }
    new_status = status_map[body.rating]

    # Update image metadata
    updates = {
        "rating": body.rating,
        "status": new_status,
        "rated_at": datetime.now(timezone.utc).isoformat(),
    }

    updated = update_json_item("app/data/images.json", image_id, updates)
    log.info(f"Image rated: {image_id} → rating={body.rating}, status={new_status}")

    # Move file if deleted
    if body.rating == "dislike":
        import shutil

        # Use pathlib for cross-platform path handling
        src_path = Path(image["image_path"])
        deleted_dir = Path("app/data/deleted/images")
        deleted_dir.mkdir(parents=True, exist_ok=True)
        dst_path = deleted_dir / src_path.name

        if src_path.exists():
            shutil.move(str(src_path), str(dst_path))
            # Normalize path for JSON storage (forward slashes)
            dst_normalized = str(dst_path).replace("\\", "/")
            log.info(f"Image deleted: moved {src_path} → {dst_path}")
            # Update path in record
            update_json_item("app/data/images.json", image_id, {"image_path": dst_normalized})
        else:
            log.warning(f"Image file not found for deletion: {src_path}")

    return {"ok": True, "image": updated}


@router.get("/images/liked")
def get_liked_images() -> dict:
    """Get all liked images.

    Returns:
        List of images with status="liked"
    """
    images = read_json("app/data/images.json")
    liked = [img for img in images if img.get("status") == "liked"]
    liked.sort(key=lambda x: x.get("rated_at", ""), reverse=True)
    return {"ok": True, "images": liked}


# ============================================================================
# Video Rating Endpoints
# ============================================================================


@router.get("/videos/pending")
def get_pending_video() -> dict:
    """Get next video pending review.

    Returns first video with status="pending_review" sorted by created_at.

    Returns:
        Dict with video metadata or {"ok": False, "message": "no pending videos"}
    """
    videos = read_json("app/data/videos.json")

    # Filter pending videos
    pending = [vid for vid in videos if vid.get("status") == "pending_review"]

    if not pending:
        return {"ok": False, "message": "no pending videos"}

    # Return oldest pending video
    pending.sort(key=lambda x: x.get("created_at", ""))
    return {"ok": True, "video": pending[0]}


@router.put("/videos/{video_id}/rate")
@limiter.limit("60/minute")
async def rate_video(request: Request, video_id: str) -> dict:
    """Rate a video (dislike/like).

    - dislike: status → "deleted", file moved to deleted/ (will regenerate with different motion)
    - like: status → "liked", caption auto-generated via Grok (ready for music workflow)

    Args:
        request: FastAPI request object (for rate limiting + body parsing)
        video_id: Video ID to rate

    Returns:
        Updated video metadata (includes caption if liked)

    Raises:
        HTTPException: 400 if invalid rating or body, 404 if video not found
    """
    # Parse body manually to work around slowapi/FastAPI integration issue
    try:
        body_bytes = await request.body()
        import json
        body_dict = json.loads(body_bytes)
        body = VideoRatingRequest(**body_dict)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request body: {str(e)}"
        )

    valid_ratings = ["dislike", "like"]
    if body.rating not in valid_ratings:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid rating. Must be one of: {', '.join(valid_ratings)}",
        )

    # Find video
    video = find_json_item("app/data/videos.json", video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    # Determine new status based on rating
    status_map = {
        "dislike": "deleted",
        "like": "liked",  # Triggers caption generation, ready for music workflow
    }
    new_status = status_map[body.rating]

    # Base updates
    updates = {
        "rating": body.rating,
        "status": new_status,
        "rated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Generate caption when liked
    caption = None
    if body.rating == "like":
        try:
            log.info(f"VIDEO_LIKED video_id={video_id}, generating caption...")

            # Get image metadata for context (if available)
            image_id = video.get("image_id")
            image_meta = {}
            if image_id:
                image = find_json_item("app/data/images.json", image_id)
                if image:
                    image_meta = image.get("meta", {})

            # Build video metadata for caption generation
            video_meta = {
                "id": video_id,
                "image_meta": image_meta,
                "motion_prompt": video.get("video_meta", {}).get("motion_prompt", ""),
                "duration_s": video.get("video_meta", {}).get("duration_s", 6),
            }

            # Generate caption via Grok
            grok = prompting_client()
            caption = grok.generate_quick_caption(video_meta)

            # Add caption to updates
            updates["caption"] = caption

            log.info(f"VIDEO_CAPTION_GENERATED video_id={video_id} caption='{caption[:50]}...'")

        except Exception as e:
            log.error(f"VIDEO_CAPTION_FAILED video_id={video_id}: {e}")
            # Continue without caption - don't block the rating
            updates["caption_error"] = str(e)

    updated = update_json_item("app/data/videos.json", video_id, updates)

    # Move file if deleted
    if body.rating == "dislike":
        import shutil

        # Use pathlib for cross-platform path handling
        src_path = Path(video["video_path"])
        deleted_dir = Path("app/data/deleted/videos")
        deleted_dir.mkdir(parents=True, exist_ok=True)
        dst_path = deleted_dir / src_path.name

        if src_path.exists():
            shutil.move(str(src_path), str(dst_path))
            # Normalize path for JSON storage (forward slashes)
            dst_normalized = str(dst_path).replace("\\", "/")
            log.info(f"Video deleted: moved {src_path} → {dst_path}")
            # Update path in record
            update_json_item("app/data/videos.json", video_id, {"video_path": dst_normalized})
            # Clean up motion history for this video
            clear_motion_history(video_id)
        else:
            log.warning(f"Video file not found for deletion: {src_path}")

    return {"ok": True, "video": updated}


@router.post("/videos/{video_id}/regenerate")
@limiter.limit("10/minute")
def regenerate_video(request: Request, video_id: str) -> dict:
    """Regenerate a disliked video with a different motion prompt.

    Re-runs video generation pipeline with a NEW motion prompt.
    Avoids previously used motion prompts for variety.

    Args:
        request: FastAPI request object (for rate limiting)
        video_id: Video ID to regenerate

    Returns:
        Dict with regeneration result

    Raises:
        HTTPException: 404 if video not found, 400 if not deleted
    """
    # Find video
    video = find_json_item("app/data/videos.json", video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    if video.get("status") != "deleted":
        raise HTTPException(
            status_code=400,
            detail=f"Video must be deleted/disliked before regeneration. Current status: {video.get('status')}",
        )

    image_id = video.get("image_id")
    if not image_id:
        raise HTTPException(
            status_code=500, detail="Video missing image_id reference"
        )

    try:
        # Load image metadata
        image = find_json_item("app/data/images.json", image_id)
        if not image:
            raise ValueError(f"Source image not found: {image_id}")

        # Get previous motion prompts from motion dedup store (per-video tracking)
        previous_prompts = get_previous_prompts(video_id)

        regeneration_count = len(previous_prompts)

        log.info(
            f"VIDEO REGENERATION START: video_id={video_id}, attempt={regeneration_count + 1}, "
            f"avoiding {len(previous_prompts)} previous motion prompts"
        )

        # Generate NEW motion prompt (avoiding previous)
        image_meta = image.get("meta", {})
        motion_payload = video_prompting.generate_veo_prompt(
            image_path=image["image_path"],
            image_meta=image_meta,
            duration_s=6,  # Enforce 6s duration
            previous_prompts=previous_prompts,
            regeneration_count=regeneration_count + 1,
        )

        new_motion_prompt = motion_payload.get("variation", "")
        log.info(f"New motion prompt: {new_motion_prompt}")

        # Store new motion prompt in dedup store
        store_motion_prompt(video_id, new_motion_prompt)

        # Build video generation payload
        video_payload = {
            "id": video_id,  # Keep same video ID
            "seed": image["prompt"]["seed"],
            "duration_s": motion_payload["duration_s"],
        }

        # Re-run video pipeline
        video_path = gen_video.from_image(image["image_path"], video_payload)
        log.info(f"Video regenerated: {video_path}")

        edited_path = edit.polish(video_path, video_payload)
        log.info(f"Video edited: {edited_path}")

        qa_style.ensure(edited_path, video_payload)
        qa_safety.ensure(edited_path, video_payload)
        log.info(f"QA passed: {video_id}")

        # Update video record with new motion and increment count
        # Normalize path for JSON storage (forward slashes)
        video_path_normalized = Path(edited_path).as_posix()

        updates = {
            "video_path": video_path_normalized,
            "status": "pending_review",  # Back to review
            "rating": None,  # Clear previous rating
            "rated_at": None,
            "video_meta": {
                "motion_prompt": new_motion_prompt,
                "duration_s": motion_payload["duration_s"],
                "regeneration_count": regeneration_count,
                "previous_motion_prompts": previous_prompts,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        updated = update_json_item("app/data/videos.json", video_id, updates)
        log.info(
            f"VIDEO REGENERATION SUCCESS: video_id={video_id}, "
            f"regeneration_count={regeneration_count}, new_motion_prompt={new_motion_prompt[:100]}..."
        )

        return {
            "ok": True,
            "message": "Video regenerated with new motion",
            "video_id": video_id,
            "regeneration_count": regeneration_count,
            "new_motion_prompt": new_motion_prompt,
        }

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log.error(
            f"VIDEO REGENERATION FAILED: video_id={video_id}, error={error_msg}",
            exc_info=True
        )

        raise HTTPException(
            status_code=500,
            detail=f"Video regeneration failed: {error_msg}",
        )


# ============================================================================
# Music Review Workflow (Post-Like)
# ============================================================================


@router.post("/videos/{video_id}/music/suggest")
@limiter.limit("20/minute")
def suggest_music_for_video(request: Request, video_id: str) -> dict:
    """Generate music brief for a liked video using Grok.

    Called after user likes a video to get music suggestions.

    Args:
        request: FastAPI request object (for rate limiting)
        video_id: Video ID to generate music for

    Returns:
        Dict with music brief from Grok

    Raises:
        HTTPException: 404 if video not found, 400 if not liked
    """
    # Find video
    video = find_json_item("app/data/videos.json", video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    if video.get("status") != "liked":
        raise HTTPException(
            status_code=400,
            detail=f"Video must be liked before music suggestion. Current status: {video.get('status')}",
        )

    try:
        # Get image metadata for context
        image_id = video.get("image_id")
        image = find_json_item("app/data/images.json", image_id) if image_id else None
        image_meta = image.get("meta", {}) if image else {}

        # Get motion spec from video metadata
        video_meta = video.get("video_meta", {})
        motion_spec = {
            "motion_type": "unknown",  # Grok can infer from prompt
            "motion_prompt": video_meta.get("motion_prompt", ""),
        }

        log.info(f"MUSIC_SUGGEST_START video_id={video_id}")

        # Call Grok to suggest music
        grok = prompting_client()
        music_brief = grok.suggest_music(
            image_meta=image_meta,
            motion_spec=motion_spec,
        )

        # Store music brief in video metadata
        if "music" not in video_meta:
            video_meta["music"] = {}

        video_meta["music"]["brief"] = music_brief.get("prompt", "")
        video_meta["music"]["style"] = music_brief.get("style", "")
        video_meta["music"]["mood"] = music_brief.get("mood", "")
        video_meta["music"]["music_status"] = "suggested"

        update_json_item("app/data/videos.json", video_id, {"video_meta": video_meta})

        log.info(f"MUSIC_SUGGEST_SUCCESS video_id={video_id} style={music_brief.get('style', '')[:30]}")

        return {
            "ok": True,
            "video_id": video_id,
            "music_brief": music_brief,
        }

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log.error(f"MUSIC_SUGGEST_FAILED video_id={video_id} error={error_msg}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Music suggestion failed: {error_msg}",
        )


@router.post("/videos/{video_id}/music/generate")
@limiter.limit("10/minute")
def generate_music_for_video(request: Request, video_id: str) -> dict:
    """Generate music audio file using Suno.

    Called after user approves Grok's music suggestion.

    Args:
        request: FastAPI request object (for rate limiting)
        video_id: Video ID to generate music for

    Returns:
        Dict with generated audio path

    Raises:
        HTTPException: 404 if video not found, 400 if music not suggested
    """
    # Find video
    video = find_json_item("app/data/videos.json", video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    video_meta = video.get("video_meta", {})
    music = video_meta.get("music", {})

    if not music.get("brief"):
        raise HTTPException(
            status_code=400,
            detail="Music brief not found. Call /music/suggest first.",
        )

    try:
        log.info(f"MUSIC_GENERATE_START video_id={video_id}")

        # Initialize Suno client
        if not settings.allow_live:
            raise RuntimeError("ALLOW_LIVE=false. Set ALLOW_LIVE=true to enable Suno API calls.")
        if not settings.suno_api_key:
            raise RuntimeError("SUNO_API_KEY is required")

        suno = SunoClient(
            api_key=settings.suno_api_key,
            model=settings.suno_model,
        )

        # Generate music audio
        music_brief = {
            "prompt": music.get("brief", ""),
            "style": music.get("style", ""),
            "mood": music.get("mood", ""),
        }

        audio_path = suno.generate_clip(
            music_brief=music_brief,
            seconds=6,
        )

        # Store audio path in video metadata
        music["audio_path"] = str(Path(audio_path).as_posix())
        music["music_status"] = "generated"

        update_json_item("app/data/videos.json", video_id, {"video_meta": video_meta})

        log.info(f"MUSIC_GENERATE_SUCCESS video_id={video_id} audio={Path(audio_path).name}")

        return {
            "ok": True,
            "video_id": video_id,
            "audio_path": audio_path,
        }

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log.error(f"MUSIC_GENERATE_FAILED video_id={video_id} error={error_msg}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Music generation failed: {error_msg}",
        )


@router.post("/videos/{video_id}/music/mux")
@limiter.limit("20/minute")
def mux_video_with_music(request: Request, video_id: str) -> dict:
    """Mux video with generated music using ffmpeg.

    Called after Suno generates audio to create final video with music.

    Args:
        request: FastAPI request object (for rate limiting)
        video_id: Video ID to mux

    Returns:
        Dict with final video path

    Raises:
        HTTPException: 404 if video not found, 400 if audio not generated
    """
    # Find video
    video = find_json_item("app/data/videos.json", video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    video_meta = video.get("video_meta", {})
    music = video_meta.get("music", {})

    if not music.get("audio_path"):
        raise HTTPException(
            status_code=400,
            detail="Audio not found. Call /music/generate first.",
        )

    try:
        log.info(f"MUSIC_MUX_START video_id={video_id}")

        video_path = video.get("video_path")
        audio_path = music.get("audio_path")

        # Generate output path for final video with music
        video_path_obj = Path(video_path)
        final_path = video_path_obj.parent / f"{video_path_obj.stem}_with_music.mp4"

        # Mux video with audio
        muxed_path = edit.mux_with_audio(
            video=video_path,
            audio=audio_path,
            output_path=str(final_path),
        )

        # Update video record with final path
        updates = {
            "video_path": str(Path(muxed_path).as_posix()),
            "status": "pending_review_music",  # Ready for music rating
        }

        music["music_status"] = "muxed"
        video_meta["music"] = music
        updates["video_meta"] = video_meta

        update_json_item("app/data/videos.json", video_id, updates)

        log.info(f"MUSIC_MUX_SUCCESS video_id={video_id} final={Path(muxed_path).name}")

        return {
            "ok": True,
            "video_id": video_id,
            "final_path": muxed_path,
        }

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log.error(f"MUSIC_MUX_FAILED video_id={video_id} error={error_msg}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Music muxing failed: {error_msg}",
        )


class MusicRatingRequest(BaseModel):
    """Request body for rating music."""

    rating: str  # "approve" | "regenerate" | "skip"


@router.put("/videos/{video_id}/music/rate")
@limiter.limit("30/minute")
async def rate_video_music(request: Request, video_id: str) -> dict:
    """Rate the music for a video (approve, regenerate, or skip).

    Args:
        request: FastAPI request object (for rate limiting + body parsing)
        video_id: Video ID

    Returns:
        Dict with updated status

    Raises:
        HTTPException: 404 if video not found, 400 if invalid status or body
    """
    # Parse body manually to work around slowapi/FastAPI integration issue
    try:
        body_bytes = await request.body()
        import json
        body_dict = json.loads(body_bytes)
        body = MusicRatingRequest(**body_dict)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request body: {str(e)}"
        )

    # Find video
    video = find_json_item("app/data/videos.json", video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    if body.rating not in ("approve", "regenerate", "skip"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid rating: {body.rating}. Must be 'approve', 'regenerate', or 'skip'.",
        )

    try:
        video_meta = video.get("video_meta", {})

        if body.rating == "approve":
            # Music approved, video ready for posting
            if "music" in video_meta:
                video_meta["music"]["music_status"] = "approved"

            updates = {
                "status": "approved",  # Ready for scheduler to post
                "video_meta": video_meta,
            }

            update_json_item("app/data/videos.json", video_id, updates)

            log.info(f"MUSIC_APPROVED video_id={video_id}")

            return {
                "ok": True,
                "video_id": video_id,
                "status": "approved",
                "message": "Music approved, video ready for posting",
            }

        elif body.rating == "regenerate":
            # Regenerate music with different brief
            if "music" in video_meta:
                # Store current brief in previous_briefs for dedup
                current_brief = video_meta["music"].get("brief", "")
                if "previous_briefs" not in video_meta["music"]:
                    video_meta["music"]["previous_briefs"] = []
                if current_brief:
                    video_meta["music"]["previous_briefs"].append(current_brief)

                video_meta["music"]["music_status"] = "regenerate"

            updates = {
                "status": "liked",  # Back to liked, ready for new music suggestion
                "video_meta": video_meta,
            }

            update_json_item("app/data/videos.json", video_id, updates)

            log.info(f"MUSIC_REGENERATE video_id={video_id}")

            return {
                "ok": True,
                "video_id": video_id,
                "status": "liked",
                "message": "Music regeneration requested",
            }

        else:  # skip
            # Skip music, post video without music
            if "music" in video_meta:
                video_meta["music"]["music_status"] = "skipped"

            updates = {
                "status": "approved",  # Ready for posting (without music)
                "video_meta": video_meta,
            }

            update_json_item("app/data/videos.json", video_id, updates)

            log.info(f"MUSIC_SKIPPED video_id={video_id}")

            return {
                "ok": True,
                "video_id": video_id,
                "status": "approved",
                "message": "Music skipped, video ready for posting",
            }

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log.error(f"MUSIC_RATE_FAILED video_id={video_id} error={error_msg}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Music rating failed: {error_msg}",
        )


@router.get("/videos/approved")
def get_approved_videos() -> dict:
    """Get all approved videos (ready for posting).

    Returns:
        List of videos with status="approved"
    """
    videos = read_json("app/data/videos.json")
    approved = [vid for vid in videos if vid.get("status") == "approved"]
    approved.sort(key=lambda x: x.get("rated_at", ""), reverse=True)
    return {"ok": True, "videos": approved}


# ============================================================================
# Video Generation Queue
# ============================================================================


@router.get("/videos/queue/status")
def get_video_queue_status() -> dict:
    """Get video generation queue status.

    Returns:
        Queue statistics: pending, processing, failed counts and current job
    """
    status = get_queue_status()
    return {"ok": True, **status}


@router.post("/videos/process-queue")
@limiter.limit("10/minute")
def process_video_queue(request: Request) -> dict:
    """Process next video in generation queue (FIFO).

    Processes ONE video from queue:
    1. Get next pending job
    2. Load image metadata
    3. Generate motion prompt
    4. Run video pipeline (gen_video → edit → QA → index)
    5. Mark complete or failed

    Rate limited to prevent overwhelming Veo API.

    Args:
        request: FastAPI request object (for rate limiting)

    Returns:
        Dict with processing result or empty if no jobs

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    # ATOMIC: Get next job and mark as processing (race-condition safe)
    job = get_and_mark_next_job()

    if not job:
        log.info("QUEUE PROCESSOR: No pending jobs in queue")
        return {"ok": True, "message": "Queue is empty", "processed": False}

    image_id = job["image_id"]
    queued_at = job.get("queued_at", "unknown")
    log.info(
        f"QUEUE PROCESSOR START: Processing video for image_id={image_id}, "
        f"queued_at={queued_at}"
    )

    try:

        # Load image metadata
        image = find_json_item("app/data/images.json", image_id)
        if not image:
            raise ValueError(f"Image metadata not found in images.json: {image_id}")

        # VALIDATION: Check image was not deleted after queueing
        if image.get("status") == "deleted":
            raise ValueError(
                f"Image was deleted after being queued (cascade delete race condition): {image_id}"
            )

        # VALIDATION: Check image file exists on disk
        image_path = image.get("image_path")
        if not image_path:
            raise ValueError(f"Image record missing image_path field: {image_id}")

        if not os.path.exists(image_path):
            raise FileNotFoundError(
                f"Image file not found on disk: {image_path} (image_id: {image_id}). "
                f"File may have been deleted or moved."
            )

        log.info(
            f"Video queue validation passed for {image_id}: "
            f"status={image.get('status')}, path={image_path}"
        )

        # Generate motion prompt from image metadata
        # Load previous prompts from motion dedup store (using image_id since first video uses same ID)
        previous_prompts = get_previous_prompts(image_id)
        regeneration_count = len(previous_prompts)

        image_meta = image.get("meta", {})
        motion_payload = video_prompting.generate_veo_prompt(
            image_path=image["image_path"],
            image_meta=image_meta,
            duration_s=6,  # Enforce 6s duration
            previous_prompts=previous_prompts,
            regeneration_count=regeneration_count,
        )

        motion_prompt = motion_payload.get("variation", "")
        log.info(f"Generated motion prompt for {image_id}: {motion_prompt}")

        # Build video generation payload
        video_payload = {
            "id": image_id,  # Use same ID for first video
            "seed": image["prompt"]["seed"],
            "duration_s": motion_payload["duration_s"],
        }

        # Generate video from image
        video_path = gen_video.from_image(image["image_path"], video_payload)
        log.info(f"Video generated: {video_path}")

        # Edit video (no music added during generation)
        edited_path = edit.polish(video_path, video_payload)
        log.info(f"Video edited: {edited_path}")

        # QA gates
        qa_style.ensure(edited_path, video_payload)
        log.info(f"QA style passed: {image_id}")

        qa_safety.ensure(edited_path, video_payload)
        log.info(f"QA safety passed: {image_id}")

        # Index to videos.json
        video_meta = indexer.index(edited_path, video_payload, image_id, motion_prompt)
        log.info(f"Video indexed: {image_id}")

        # Store motion prompt in dedup store (using video_id from indexer)
        video_id = video_meta.get("id", image_id)
        store_motion_prompt(video_id, motion_prompt)

        # Mark job complete
        mark_complete(image_id)
        log.info(
            f"QUEUE PROCESSOR SUCCESS: Video generated for {image_id} → video_id={video_meta['id']}, "
            f"path={edited_path}"
        )

        return {
            "ok": True,
            "message": "Video generated successfully",
            "processed": True,
            "image_id": image_id,
            "video_id": video_meta["id"],
        }

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log.error(
            f"QUEUE PROCESSOR FAILED: Video generation failed for {image_id}. "
            f"Error: {error_msg}",
            exc_info=True
        )

        # Mark job as failed (keeps in queue for manual retry)
        mark_failed(image_id, error_msg)

        return {
            "ok": False,
            "message": f"Video generation failed: {error_msg}",
            "processed": True,
            "image_id": image_id,
            "error": error_msg,
        }


@router.post("/scheduler/run-once")
@limiter.limit("5/minute")
def scheduler_run_once(request: Request) -> dict:
    """Run posting cycle once immediately (live execution).

    Posts one approved video to configured platform if within posting window.
    Requires ALLOW_LIVE=true to execute actual API calls.

    Rate limited to 5 requests per minute per client.

    Returns:
        Dict with posting results:
        {
            "ok": True/False,
            "posted": 0 or 1,
            "video_id": str or None,
            "platform": str or None,
            "post_id": str or None,
            "skipped_window": True/False,
            "error": str or None
        }
    """
    log.info("SCHEDULER_RUN_ONCE_TRIGGERED")

    # Check ALLOW_LIVE guard
    if not settings.allow_live:
        raise HTTPException(
            status_code=403,
            detail="Posting disabled: ALLOW_LIVE=false. Set ALLOW_LIVE=true to enable live posting."
        )

    # Execute posting cycle
    result = run_posting_cycle()

    return result


@router.post("/scheduler/dry-run")
@limiter.limit("20/minute")
def scheduler_dry_run(request: Request) -> dict:
    """Preview what would be posted without executing (dry run).

    Shows which video would be posted and its metadata without actually posting.
    Does not require ALLOW_LIVE=true (safe preview).

    Rate limited to 20 requests per minute per client.

    Returns:
        Dict with preview info:
        {
            "ok": True,
            "would_post": True/False,
            "video": dict or None,
            "platform": str,
            "window_active": True/False,
            "approved_count": int,
            "message": str
        }
    """
    log.info("SCHEDULER_DRY_RUN_TRIGGERED")

    # Import locally to access helper functions
    from app.core.scheduler import _in_posting_window

    # Check posting window
    window_active = _in_posting_window()

    # Count approved videos
    videos = read_json("app/data/videos.json")
    approved_videos = [v for v in videos if v.get("status") == "approved"]
    approved_count = len(approved_videos)

    if not approved_videos:
        return {
            "ok": True,
            "would_post": False,
            "video": None,
            "platform": settings.default_posting_platform,
            "window_active": window_active,
            "approved_count": 0,
            "message": "No approved videos available for posting"
        }

    # Get first approved video (what would be posted)
    next_video = approved_videos[0]

    # Determine if it would actually post
    would_post = window_active

    message = f"Would post video {next_video['id']} to {settings.default_posting_platform}"
    if not window_active:
        message += f" (currently outside posting window: {settings.posting_window_local})"

    return {
        "ok": True,
        "would_post": would_post,
        "video": {
            "id": next_video["id"],
            "video_path": next_video.get("video_path"),
            "created_at": next_video.get("created_at"),
            "status": next_video.get("status"),
            "has_social_meta": bool(next_video.get("social")),
        },
        "platform": settings.default_posting_platform,
        "window_active": window_active,
        "approved_count": approved_count,
        "message": message,
    }


@router.get("/healthz")
def healthz() -> dict:
    """Health check endpoint with provider readiness status.

    Returns:
        Dict with status and provider configuration (NO SECRETS)
    """
    # Manual workflow: Leonardo and Veo are used externally by user
    # System only generates prompts via Grok, validates uploads, and posts via TikTok/Instagram

    # Check provider key availability (NOT the values!)
    providers = {
        "leonardo": "manual",  # User generates images externally
        "veo": "manual",  # User generates videos externally
        "grok": "configured" if settings.grok_api_key else "key_missing",
        "suno": "configured" if settings.suno_api_key else "key_missing",
        "tiktok": "configured"
        if (settings.tiktok_client_key and settings.tiktok_client_secret and settings.tiktok_access_token)
        else "key_missing",
        "instagram": "configured"
        if (settings.instagram_business_account_id and settings.fb_access_token)
        else "key_missing",
    }

    # Add Grok configuration info (no secrets)
    grok_config = {
        "model": settings.grok_model,
        "timeout_s": settings.grok_timeout_s,
    }

    # Add Suno configuration info (no secrets)
    suno_config = {
        "model": settings.suno_model,
        "clip_seconds": settings.suno_clip_seconds,
        "style_hints": settings.suno_style_hints_default,
    }

    # Add manual workflow configuration
    manual_config = {
        "prompts_out_dir": settings.prompts_out_dir,
        "manual_images_dir": settings.manual_images_dir,
        "manual_videos_dir": settings.manual_videos_dir,
        "enforced_image_dimensions": f"{settings.image_width}×{settings.image_height}",
        "enforced_video_duration": f"{settings.video_must_be_seconds}s",
        "enforced_video_aspect": settings.video_aspect,
    }

    # Add ffmpeg/QA configuration
    qa_config = {
        "blur_qa_enabled": False,  # Disabled as per requirements
        "container_qa_enabled": True,
        "ffmpeg_available": bool(settings.ffmpeg_path),
        "ffprobe_available": bool(settings.ffprobe_path),
    }

    return {
        "ok": True,
        "workflow": "manual",  # User generates assets externally
        "allow_live": settings.allow_live,
        "scheduler_enabled": settings.enable_scheduler,
        "providers": providers,
        "manual_config": manual_config,
        "grok_config": grok_config,
        "suno_config": suno_config,
        "qa_config": qa_config,
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

