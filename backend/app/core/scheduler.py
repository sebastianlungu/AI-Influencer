"""Background scheduler for automated posting to social platforms.

Runs on a configurable cron schedule (default: every 20 minutes).
Posts videos with status="approved" to TikTok or Instagram.
"""

from __future__ import annotations

import time
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone as pytz_timezone

from app.clients.grok import GrokClient
from app.clients.instagram import InstagramClient
from app.clients.provider_selector import prompting_client
from app.clients.tiktok import TikTokClient
from app.core.config import settings
from app.core.logging import log
from app.core.storage import find_json_item, read_json, update_json_item

scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    """Start background scheduler if ENABLE_SCHEDULER=true.

    Schedules posting jobs with cron trigger based on SCHEDULER_CRON_MINUTES.
    Respects posting window configured in POSTING_WINDOW_LOCAL.
    """
    global scheduler
    if not settings.enable_scheduler:
        log.info("SCHEDULER_DISABLED (ENABLE_SCHEDULER=false)")
        return

    # Parse cron minutes
    cron_minutes = settings.scheduler_cron_minutes  # e.g., "*/20" for every 20 mins

    scheduler = BackgroundScheduler(timezone=settings.scheduler_timezone)

    # Create cron trigger (runs at specified minute intervals)
    trigger = CronTrigger(minute=cron_minutes, timezone=settings.scheduler_timezone)

    scheduler.add_job(
        lambda: _safe_posting_cycle(),
        trigger=trigger,
        id="posting_cycle",
        coalesce=True,
        max_instances=1,
    )

    scheduler.start()
    log.info(
        f"SCHEDULER_STARTED cron={cron_minutes} timezone={settings.scheduler_timezone} "
        f"window={settings.posting_window_local} platform={settings.default_posting_platform}"
    )


def _safe_posting_cycle() -> None:
    """Safe wrapper for posting cycle with exception handling."""
    try:
        run_posting_cycle()
    except Exception as e:
        log.error(
            f"SCHEDULER_POSTING_FAILED: {type(e).__name__}: {e}",
            exc_info=True
        )


def run_posting_cycle() -> dict:
    """Execute one posting cycle.

    Selects ONE video with status="approved", generates social meta if missing,
    posts to configured platform, updates status to "posted".

    Returns:
        Dict with cycle results:
        {
            "ok": True/False,
            "posted": 0 or 1,
            "skipped_window": True/False,
            "video_id": str or None,
            "platform": str or None,
            "error": str or None,
        }
    """
    log.info("SCHEDULER_CYCLE_START")

    # Check if we're within posting window
    if not _in_posting_window():
        log.info(
            f"SCHEDULER_SKIPPED_WINDOW current_time outside {settings.posting_window_local} "
            f"(timezone: {settings.scheduler_timezone})"
        )
        return {"ok": True, "posted": 0, "skipped_window": True}

    # Find one approved video
    videos = read_json("app/data/videos.json")
    approved_videos = [v for v in videos if v.get("status") == "approved"]

    if not approved_videos:
        log.info("SCHEDULER_NO_APPROVED_VIDEOS no videos ready for posting")
        return {"ok": True, "posted": 0, "video_id": None}

    # Take first approved video
    video = approved_videos[0]
    video_id = video["id"]

    try:
        # Generate social meta if missing
        if not video.get("social"):
            log.info(f"SCHEDULER_GENERATE_SOCIAL_META video_id={video_id}")
            video = _generate_social_meta(video)

        # Determine platform
        platform = settings.default_posting_platform.lower()

        # Post to platform
        log.info(f"SCHEDULER_POSTING video_id={video_id} platform={platform}")

        if platform == "tiktok":
            post_id = _post_to_tiktok(video)
        elif platform == "instagram":
            post_id = _post_to_instagram(video)
        else:
            raise ValueError(f"Unknown platform: {platform}")

        # Update video status to posted
        updates = {
            "status": "posted",
            "posted_at": datetime.utcnow().isoformat() + "Z",
            "posted_platform": platform,
            "posted_id": post_id,
        }
        update_json_item("app/data/videos.json", video_id, updates)

        log.info(
            f"SCHEDULER_POST_SUCCESS video_id={video_id} platform={platform} post_id={post_id}"
        )

        return {
            "ok": True,
            "posted": 1,
            "video_id": video_id,
            "platform": platform,
            "post_id": post_id,
        }

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log.error(
            f"SCHEDULER_POST_FAILED video_id={video_id} error={error_msg}",
            exc_info=True
        )

        # Mark video as failed (keeps approved status for manual retry)
        update_json_item("app/data/videos.json", video_id, {"posting_error": error_msg})

        return {
            "ok": False,
            "posted": 0,
            "video_id": video_id,
            "error": error_msg,
        }


def _in_posting_window() -> bool:
    """Check if current time is within configured posting window.

    Returns:
        True if within window, False otherwise
    """
    try:
        # Parse posting window (e.g., "09:00-21:00")
        start_str, end_str = settings.posting_window_local.split("-")
        start_hour, start_min = map(int, start_str.split(":"))
        end_hour, end_min = map(int, end_str.split(":"))

        # Get current time in configured timezone
        tz = pytz_timezone(settings.scheduler_timezone)
        now = datetime.now(tz)
        current_minutes = now.hour * 60 + now.minute

        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min

        return start_minutes <= current_minutes <= end_minutes

    except Exception as e:
        log.warning(f"Failed to parse posting window, defaulting to ALLOW: {e}")
        return True  # Fail open


def _generate_social_meta(video: dict) -> dict:
    """Generate social metadata (title, tags, hashtags) using Grok.

    Args:
        video: Video record from videos.json

    Returns:
        Updated video record with social metadata
    """
    try:
        # Get image metadata for context
        image_id = video.get("image_id")
        image = find_json_item("app/data/images.json", image_id) if image_id else None

        media_meta = {
            "video_id": video["id"],
            "motion_prompt": video.get("video_meta", {}).get("motion_prompt", ""),
            "image_meta": image.get("meta", {}) if image else {},
        }

        # Generate social meta via Grok
        grok = prompting_client()
        social_meta = grok.generate_social_meta(media_meta)

        # Store in video record
        video["social"] = social_meta
        update_json_item("app/data/videos.json", video["id"], {"social": social_meta})

        log.info(
            f"GROK_SOCIAL_META_SUCCESS video_id={video['id']} "
            f"hashtags={len(social_meta.get('hashtags', []))}"
        )

        return video

    except Exception as e:
        log.error(f"GROK_SOCIAL_META_FAILED video_id={video['id']} error={str(e)}")
        # Use fallback metadata
        video["social"] = {
            "title": "Fitness Inspiration",
            "tags": ["fitness", "workout", "motivation"],
            "hashtags": ["#fitness", "#workout", "#motivation"],
        }
        return video


def _post_to_tiktok(video: dict) -> str:
    """Post video to TikTok.

    Args:
        video: Video record with social metadata

    Returns:
        TikTok post ID
    """
    if not settings.tiktok_client_key or not settings.tiktok_access_token:
        raise RuntimeError("TikTok credentials not configured (check TIKTOK_* env vars)")

    client = TikTokClient(
        client_key=settings.tiktok_client_key,
        client_secret=settings.tiktok_client_secret,
        access_token=settings.tiktok_access_token,
    )

    # Build caption from social metadata
    social = video.get("social", {})
    title = social.get("title", "")
    hashtags = " ".join(social.get("hashtags", []))
    caption = f"{title}\n\n{hashtags}".strip()

    # Upload video
    video_path = video["video_path"]
    post_id = client.upload_video(video_path=video_path, caption=caption)

    return post_id


def _post_to_instagram(video: dict) -> str:
    """Post video to Instagram Reels.

    Args:
        video: Video record with social metadata

    Returns:
        Instagram media ID
    """
    if not settings.instagram_business_account_id or not settings.fb_access_token:
        raise RuntimeError("Instagram credentials not configured (check INSTAGRAM_* / FB_* env vars)")

    client = InstagramClient(
        business_account_id=settings.instagram_business_account_id,
        access_token=settings.fb_access_token,
    )

    # Build caption from social metadata
    social = video.get("social", {})
    title = social.get("title", "")
    hashtags = " ".join(social.get("hashtags", []))
    caption = f"{title}\n\n{hashtags}".strip()

    # Upload reel
    video_path = video["video_path"]
    media_id = client.upload_reel(video_path=video_path, caption=caption)

    return media_id


def stop_scheduler() -> None:
    """Stop the background scheduler if running."""
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        scheduler = None
        log.info("SCHEDULER_STOPPED")
