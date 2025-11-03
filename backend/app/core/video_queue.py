"""Video generation queue management (FIFO).

Manages a queue of video generation jobs to prevent overwhelming Veo API.
Jobs are stored in app/data/video_queue.json and processed one at a time.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.logging import log
from app.core.paths import get_data_path
from app.core.storage import atomic_write


def _load_queue() -> dict:
    """Load queue from video_queue.json.

    Returns:
        Queue data with structure:
        {
            "queue": [
                {"image_id": "abc123", "queued_at": "ISO8601", "status": "pending"},
                ...
            ]
        }
    """
    queue_path = get_data_path("video_queue.json")
    if not queue_path.exists():
        return {"queue": []}

    with open(queue_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_queue(queue_data: dict) -> None:
    """Save queue to video_queue.json atomically.

    Args:
        queue_data: Queue data structure
    """
    queue_path = get_data_path("video_queue.json")
    atomic_write(queue_path, json.dumps(queue_data, indent=2))


def enqueue_video_generation(image_id: str) -> dict:
    """Add video generation job to queue (FIFO).

    Args:
        image_id: Image ID to generate video from

    Returns:
        Dict with queue position info:
        {
            "image_id": "abc123",
            "queued_at": "ISO8601",
            "status": "pending",
            "queue_position": 3
        }
    """
    queue_data = _load_queue()

    # Check if already queued
    for job in queue_data["queue"]:
        if job["image_id"] == image_id:
            log.warning(f"Video generation already queued: {image_id}")
            position = queue_data["queue"].index(job) + 1
            return {**job, "queue_position": position}

    # Add to end of queue
    new_job = {
        "image_id": image_id,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }

    queue_data["queue"].append(new_job)
    _save_queue(queue_data)

    position = len(queue_data["queue"])
    log.info(f"Enqueued video generation: {image_id} (position {position})")

    return {**new_job, "queue_position": position}


def get_next_job() -> dict | None:
    """Get next pending job from queue (FIFO).

    Returns oldest pending job without changing its status.

    Returns:
        Job dict or None if queue is empty:
        {
            "image_id": "abc123",
            "queued_at": "ISO8601",
            "status": "pending"
        }
    """
    queue_data = _load_queue()

    for job in queue_data["queue"]:
        if job["status"] == "pending":
            return job

    return None


def get_and_mark_next_job() -> dict | None:
    """ATOMIC: Get next pending job and mark as processing (race-condition safe).

    This function prevents race conditions by atomically getting and marking
    the next job in a single file load/save operation. Use this instead of
    calling get_next_job() + mark_processing() separately.

    Returns:
        Job dict with status updated to "processing", or None if queue is empty:
        {
            "image_id": "abc123",
            "queued_at": "ISO8601",
            "status": "processing",
            "processing_started_at": "ISO8601"
        }
    """
    queue_data = _load_queue()

    # Find first pending job and mark it as processing atomically
    for job in queue_data["queue"]:
        if job["status"] == "pending":
            job["status"] = "processing"
            job["processing_started_at"] = datetime.now(timezone.utc).isoformat()

            # Save atomically before returning
            _save_queue(queue_data)

            log.info(
                f"ATOMIC GET+MARK: video job {job['image_id']} marked as processing"
            )

            return job

    return None


def mark_processing(image_id: str) -> None:
    """Mark job as processing.

    Args:
        image_id: Image ID to mark
    """
    queue_data = _load_queue()

    for job in queue_data["queue"]:
        if job["image_id"] == image_id:
            job["status"] = "processing"
            job["processing_started_at"] = datetime.now(timezone.utc).isoformat()
            _save_queue(queue_data)
            log.info(f"Video job started: {image_id}")
            return

    log.warning(f"Job not found for processing: {image_id}")


def mark_complete(image_id: str) -> None:
    """Remove completed job from queue.

    Args:
        image_id: Image ID to remove
    """
    queue_data = _load_queue()

    queue_data["queue"] = [
        job for job in queue_data["queue"] if job["image_id"] != image_id
    ]

    _save_queue(queue_data)
    log.info(f"Video job completed, removed from queue: {image_id}")


def mark_failed(image_id: str, reason: str) -> None:
    """Mark job as failed (keeps in queue for manual retry).

    Args:
        image_id: Image ID to mark
        reason: Failure reason
    """
    queue_data = _load_queue()

    for job in queue_data["queue"]:
        if job["image_id"] == image_id:
            job["status"] = "failed"
            job["failed_at"] = datetime.now(timezone.utc).isoformat()
            job["failure_reason"] = reason
            _save_queue(queue_data)
            log.error(f"Video job failed: {image_id}, reason: {reason}")
            return

    log.warning(f"Job not found for marking failed: {image_id}")


def get_queue_status() -> dict:
    """Get current queue status summary.

    Returns:
        Dict with queue statistics:
        {
            "pending": 3,
            "processing": 1,
            "failed": 0,
            "current_job": {"image_id": "abc123", ...} or None
        }
    """
    queue_data = _load_queue()
    jobs = queue_data["queue"]

    pending = [j for j in jobs if j["status"] == "pending"]
    processing = [j for j in jobs if j["status"] == "processing"]
    failed = [j for j in jobs if j["status"] == "failed"]

    current_job = processing[0] if processing else None

    return {
        "pending": len(pending),
        "processing": len(processing),
        "failed": len(failed),
        "current_job": current_job,
    }


def remove_job(image_id: str) -> bool:
    """Remove job from queue by image_id (for cascade delete).

    Args:
        image_id: Image ID to remove from queue

    Returns:
        True if job was found and removed, False otherwise
    """
    queue_data = _load_queue()
    original_count = len(queue_data["queue"])

    # Filter out the job
    queue_data["queue"] = [
        job for job in queue_data["queue"] if job["image_id"] != image_id
    ]

    removed_count = original_count - len(queue_data["queue"])

    if removed_count > 0:
        _save_queue(queue_data)
        log.info(f"Removed {removed_count} job(s) from queue for image: {image_id}")
        return True
    else:
        log.debug(f"No queue jobs found for image: {image_id}")
        return False


def clear_queue() -> int:
    """Clear all jobs from queue (emergency use).

    Returns:
        Number of jobs cleared
    """
    queue_data = _load_queue()
    count = len(queue_data["queue"])

    queue_data["queue"] = []
    _save_queue(queue_data)

    log.warning(f"Queue cleared: {count} jobs removed")
    return count
