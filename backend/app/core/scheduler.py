from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.logging import log

scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    """Starts the background scheduler if ENABLE_SCHEDULER=true.

    Schedules hourly generation cycles with job coalescing to prevent overlaps.
    """
    global scheduler
    if not settings.enable_scheduler:
        log.info("scheduler_disabled (ENABLE_SCHEDULER=false)")
        return

    # Import here to avoid circular dependency
    from app.coordinator.orchestrator import run_cycle

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: _safe_cycle(),
        "interval",
        hours=1,
        id="hourly_gen",
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()
    log.info("scheduler_started (hourly_gen)")


def _safe_cycle() -> None:
    """Wraps run_cycle with exception handling for scheduler."""
    from app.coordinator.orchestrator import run_cycle

    try:
        run_cycle(settings.batch_size)
    except Exception as e:
        log.error(f"scheduler_cycle_fail: {type(e).__name__}: {e}", exc_info=True)


def stop_scheduler() -> None:
    """Stops the background scheduler if running."""
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        scheduler = None
        log.info("scheduler_stopped")
