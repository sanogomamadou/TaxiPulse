"""Paces trip event emission to respect the trips' original chronology,
compressed by a configurable speed-up factor (e.g. 60 = 60x faster than the
real world)."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Iterator
from datetime import datetime

from taxipulse_common.trip_event import TripEvent

SleepFn = Callable[[float], None]


def pace_events(
    events: Iterable[TripEvent],
    speedup_factor: float,
    sleep_fn: SleepFn = time.sleep,
) -> Iterator[TripEvent]:
    """Yield events at a pace proportional to the delta between consecutive
    pickup times, divided by `speedup_factor`.

    The first event is yielded immediately. If pickup times go backwards
    (can happen after chaos-injected reordering) the wait is clamped to 0
    rather than raising.
    """
    if speedup_factor <= 0:
        raise ValueError("speedup_factor must be > 0")

    previous_pickup: datetime | None = None
    for event in events:
        pickup = datetime.fromisoformat(event.pickup_datetime)
        if previous_pickup is not None:
            real_delta_seconds = (pickup - previous_pickup).total_seconds()
            wait_seconds = max(real_delta_seconds, 0.0) / speedup_factor
            if wait_seconds > 0:
                sleep_fn(wait_seconds)
        previous_pickup = pickup
        yield event
