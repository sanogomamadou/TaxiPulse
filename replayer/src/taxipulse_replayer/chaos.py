"""Optional chaos injection used to test the pipeline's robustness:
duplicate delivery and delayed/out-of-order arrival."""

from __future__ import annotations

import random
from collections.abc import Iterator

from taxipulse_common.trip_event import TripEvent


def inject_duplicates(
    events: Iterator[TripEvent],
    ratio: float,
    rng: random.Random | None = None,
) -> Iterator[TripEvent]:
    """Re-emit a fraction of events right after their first emission,
    simulating at-least-once delivery duplicates (e.g. a publisher retry
    after an ack timeout)."""
    if not 0 <= ratio <= 1:
        raise ValueError("ratio must be between 0 and 1")
    rng = rng or random.Random()
    for event in events:
        yield event
        if rng.random() < ratio:
            yield event


def inject_late_events(
    events: Iterator[TripEvent],
    ratio: float,
    max_hold: int = 5,
    rng: random.Random | None = None,
) -> Iterator[TripEvent]:
    """Hold back a fraction of events and release each of them a few
    positions after their chronological slot, simulating events that arrive
    after the pipeline's watermark has already advanced past their event
    time.

    `max_hold` bounds how many events accumulate in the holdback buffer
    before the oldest one is forced out, so late events are eventually
    released even in a long low-traffic stretch.
    """
    if not 0 <= ratio <= 1:
        raise ValueError("ratio must be between 0 and 1")
    rng = rng or random.Random()
    held: list[TripEvent] = []

    for event in events:
        if rng.random() < ratio:
            held.append(event)
        else:
            yield event

        if len(held) >= max_hold:
            yield held.pop(0)

    yield from held
