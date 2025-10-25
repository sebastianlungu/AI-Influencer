from __future__ import annotations

import threading
from decimal import Decimal, ROUND_HALF_UP

from app.core.config import settings
from app.core.logging import log

_cost_lock = threading.Lock()
_current_run_cost = Decimal("0")


def reset_cycle() -> None:
    """Resets the current cycle cost to zero (call at start of each cycle)."""
    global _current_run_cost
    with _cost_lock:
        _current_run_cost = Decimal("0")
        log.info("cost_reset")


def add_cost(amount: Decimal, service: str) -> None:
    """Tracks cost and raises if budget exceeded.

    IMPORTANT: Check budget BEFORE making the API call, not after.

    Args:
        amount: Cost to add in USD (Decimal for precision)
        service: Name of the service (for logging)

    Raises:
        RuntimeError: If adding this cost would exceed MAX_COST_PER_RUN
    """
    global _current_run_cost
    with _cost_lock:
        new_total = (_current_run_cost + amount).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

        # Fail BEFORE making the call if it would exceed budget
        if new_total > settings.max_cost_per_run:
            raise RuntimeError(
                f"Budget exceeded: ${new_total} > ${settings.max_cost_per_run} "
                f"(attempted to add ${amount} for {service})"
            )

        _current_run_cost = new_total
        log.info(f"cost_add service={service} amount={amount} total={_current_run_cost}")


def get_current_cost() -> Decimal:
    """Returns the current run cost as Decimal."""
    with _cost_lock:
        return _current_run_cost
