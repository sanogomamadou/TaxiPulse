"""Deduplicates trip events by trip_id using per-key state, so at-least-once
delivery duplicates (Pub/Sub redelivery, publisher retries, or the
replayer's own chaos injection) are not double-counted downstream.

A stateful DoFn is used instead of a stateless `Distinct` so that state is
bounded: each key's "seen" marker expires after DEDUP_STATE_TTL_SECONDS,
rather than accumulating forever for an unbounded stream.
"""

from __future__ import annotations

import apache_beam as beam
from apache_beam.coders import BooleanCoder
from apache_beam.transforms.timeutil import TimeDomain
from apache_beam.transforms.userstate import BagStateSpec, TimerSpec, on_timer
from apache_beam.utils.timestamp import Duration

from taxipulse_common.trip_event import TripEvent

# How long we remember a trip_id has been seen. Must comfortably exceed the
# maximum delay the replayer's chaos injection (or real Pub/Sub redelivery)
# can introduce between a message and its duplicate, or a duplicate could
# slip through once state has expired.
DEDUP_STATE_TTL_SECONDS = 600


class DeduplicateByTripId(beam.DoFn):
    SEEN = BagStateSpec("seen", BooleanCoder())
    EXPIRY_TIMER = TimerSpec("expiry", TimeDomain.WATERMARK)

    def process(
        self,
        element: tuple[str, TripEvent],
        seen=beam.DoFn.StateParam(SEEN),  # noqa: B008 - Beam's required pattern for state injection
        expiry_timer=beam.DoFn.TimerParam(EXPIRY_TIMER),  # noqa: B008
        timestamp=beam.DoFn.TimestampParam,
    ):
        _, event = element
        if not any(seen.read()):  # not a duplicate
            seen.add(True)
            expiry_timer.set(timestamp + Duration(seconds=DEDUP_STATE_TTL_SECONDS))
            yield event

    @on_timer(EXPIRY_TIMER)
    def expire(self, seen=beam.DoFn.StateParam(SEEN)):  # noqa: B008
        seen.clear()


def deduplicate_by_trip_id(events: beam.PCollection) -> beam.PCollection:
    return (
        events
        # An explicit output type hint gives the stateful DoFn below a
        # deterministic key coder (str) instead of the default
        # pickle-based one, which Beam otherwise warns about.
        | "KeyByTripId" >> beam.Map(lambda e: (e.trip_id, e)).with_output_types(tuple[str, TripEvent])
        | "DedupByTripId" >> beam.ParDo(DeduplicateByTripId())
    )
