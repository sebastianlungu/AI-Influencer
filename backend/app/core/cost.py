from __future__ import annotations

import threading

from app.core.config import settings
from app.core.logging import log

_cost_lock = threading.Lock()
_current_run_cost = 0.0


def reset_run_cost() -> None:
    """Resets the current run cost to zero (call at start of each cycle)."""
    global _current_run_cost
    with _cost_lock:
        _current_run_cost = 0.0
        log.info("cost_reset")


def add_cost(amount: float, service: str) -> None:
    """Tracks cost and raises if budget exceeded.

    Args:
        amount: Cost to add in USD
        service: Name of the service (for logging)

    Raises:
        RuntimeError: If total cost exceeds MAX_COST_PER_RUN
    """
    global _current_run_cost
    with _cost_lock:
        _current_run_cost += amount
        log.info(f"cost_add service={service} amount={amount:.4f} total={_current_run_cost:.4f}")

        if _current_run_cost > settings.max_cost_per_run:
            raise RuntimeError(
                f"Budget exceeded: ${_current_run_cost:.2f} > ${settings.max_cost_per_run:.2f}"
            )


def get_current_cost() -> float:
    """Returns the current run cost."""
    with _cost_lock:
        return _current_run_cost
