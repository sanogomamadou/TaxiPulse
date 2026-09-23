"""Event-time assignment and sliding-window per-zone aggregation, with the
watermark / allowed-lateness / trigger configuration used to reconcile
out-of-order and late-arriving trip events."""

from __future__ import annotations

from datetime import UTC, datetime

import apache_beam as beam
from apache_beam import window
from apache_beam.transforms.trigger import (
    AccumulationMode,
    AfterCount,
    AfterProcessingTime,
    AfterWatermark,
)

from taxipulse_common.trip_event import TripEvent

DEFAULT_WINDOW_SIZE_SECONDS = 300  # 5-minute sliding window
DEFAULT_WINDOW_PERIOD_SECONDS = 60  # slides every minute
DEFAULT_ALLOWED_LATENESS_SECONDS = 120  # accept late data up to 2 minutes after the watermark


def event_timestamp_seconds(event: TripEvent) -> float:
    """The event's pickup time as a Unix timestamp - this is what drives the
    pipeline's watermark, not Pub/Sub publish time. TLC timestamps have no
    timezone info; we treat them as UTC, a documented simplification (see
    CLAUDE.md)."""
    pickup = datetime.fromisoformat(event.pickup_datetime)
    if pickup.tzinfo is None:
        pickup = pickup.replace(tzinfo=UTC)
    return pickup.timestamp()


class AssignEventTimestamp(beam.DoFn):
    """Reassigns each element's pipeline timestamp to its pickup time,
    instead of Pub/Sub's default publish-time-based timestamp."""

    def process(self, element: TripEvent):
        yield window.TimestampedValue(element, event_timestamp_seconds(element))


class ZoneAggregate(beam.CombineFn):
    """Accumulates trip count, revenue, and running sums for
    duration/speed, so per-zone averages can be derived on extraction."""

    def create_accumulator(self):
        return {
            "trip_count": 0,
            "total_revenue": 0.0,
            "total_duration_seconds": 0.0,
            "total_speed_mph": 0.0,
        }

    def add_input(self, accumulator, element: TripEvent):
        duration_seconds = max(
            (
                datetime.fromisoformat(element.dropoff_datetime)
                - datetime.fromisoformat(element.pickup_datetime)
            ).total_seconds(),
            0.0,
        )
        speed_mph = element.trip_distance / (duration_seconds / 3600) if duration_seconds > 0 else 0.0

        accumulator["trip_count"] += 1
        accumulator["total_revenue"] += element.total_amount
        accumulator["total_duration_seconds"] += duration_seconds
        accumulator["total_speed_mph"] += speed_mph
        return accumulator

    def merge_accumulators(self, accumulators):
        merged = self.create_accumulator()
        for acc in accumulators:
            merged["trip_count"] += acc["trip_count"]
            merged["total_revenue"] += acc["total_revenue"]
            merged["total_duration_seconds"] += acc["total_duration_seconds"]
            merged["total_speed_mph"] += acc["total_speed_mph"]
        return merged

    def extract_output(self, accumulator):
        count = accumulator["trip_count"]
        return {
            "trip_count": count,
            "total_revenue": round(accumulator["total_revenue"], 2),
            "avg_duration_seconds": (
                round(accumulator["total_duration_seconds"] / count, 1) if count else 0.0
            ),
            "avg_speed_mph": round(accumulator["total_speed_mph"] / count, 1) if count else 0.0,
        }


def window_and_aggregate_by_zone(
    events: beam.PCollection,
    window_size_seconds: int = DEFAULT_WINDOW_SIZE_SECONDS,
    window_period_seconds: int = DEFAULT_WINDOW_PERIOD_SECONDS,
    allowed_lateness_seconds: int = DEFAULT_ALLOWED_LATENESS_SECONDS,
) -> beam.PCollection:
    """Sliding-window aggregation of trip events by pickup zone.

    Windows overlap (size > period). The AfterWatermark trigger fires once
    the watermark passes the window's end, fires early every 30s of
    processing time while data is still arriving, and - with an explicit
    `late=AfterCount(1)` - fires again immediately on every late element
    that shows up within `allowed_lateness_seconds` of the watermark
    (accumulating, not discarding, so each late firing includes everything
    seen so far). Beam requires the late trigger to be spelled out
    explicitly here: leaving it implicit is treated as an unsafe trigger
    that risks silently dropping data.
    """
    keyed = events | "KeyByPickupZone" >> beam.Map(lambda e: (e.pickup_location_id, e))

    windowed = keyed | "SlidingWindow" >> beam.WindowInto(
        window.SlidingWindows(window_size_seconds, window_period_seconds),
        trigger=AfterWatermark(early=AfterProcessingTime(30), late=AfterCount(1)),
        accumulation_mode=AccumulationMode.ACCUMULATING,
        allowed_lateness=allowed_lateness_seconds,
    )

    return windowed | "AggregateByZone" >> beam.CombinePerKey(ZoneAggregate())


class AddWindowBounds(beam.DoFn):
    """Adds the enclosing window's [start, end) as ISO timestamps to each
    keyed aggregate, so the sink can write them out without needing access
    to Beam's window object."""

    def process(self, element, window=beam.DoFn.WindowParam):
        zone_id, aggregate = element
        yield (
            zone_id,
            {
                **aggregate,
                "window_start": window.start.to_utc_datetime().isoformat(),
                "window_end": window.end.to_utc_datetime().isoformat(),
            },
        )
