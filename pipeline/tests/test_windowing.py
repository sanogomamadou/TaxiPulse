from datetime import UTC, datetime, timedelta

import apache_beam as beam
from apache_beam import window
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
from apache_beam.testing.test_pipeline import TestPipeline
from apache_beam.testing.test_stream import TestStream
from apache_beam.testing.util import assert_that, equal_to

from taxipulse_common.trip_event import TripEvent
from taxipulse_pipeline.transforms.windowing import (
    AssignEventTimestamp,
    ZoneAggregate,
    event_timestamp_seconds,
    window_and_aggregate_by_zone,
)

EPOCH = datetime(2024, 1, 1, tzinfo=UTC)


def make_event(
    trip_id: str,
    pickup_offset_seconds: float = 0,
    duration_seconds: float = 600,
    zone: int = 100,
    trip_distance: float = 2.0,
    total_amount: float = 10.0,
) -> TripEvent:
    pickup = EPOCH + timedelta(seconds=pickup_offset_seconds)
    dropoff = pickup + timedelta(seconds=duration_seconds)
    return TripEvent.from_dict(
        {
            "trip_id": trip_id,
            "vendor_id": 1,
            "pickup_datetime": pickup.isoformat(),
            "dropoff_datetime": dropoff.isoformat(),
            "pickup_location_id": zone,
            "dropoff_location_id": zone + 1,
            "passenger_count": 1,
            "trip_distance": trip_distance,
            "fare_amount": total_amount,
            "tip_amount": 0.0,
            "total_amount": total_amount,
            "payment_type": 1,
        }
    )


# --- Pure functions / CombineFn, no Beam pipeline needed ---


def test_event_timestamp_seconds_matches_pickup_time():
    event = make_event("a", pickup_offset_seconds=3600)
    assert event_timestamp_seconds(event) == EPOCH.timestamp() + 3600


def test_zone_aggregate_computes_count_revenue_duration_and_speed():
    combine_fn = ZoneAggregate()
    acc = combine_fn.create_accumulator()
    # 2 miles in 600s (10 min) => 12 mph
    acc = combine_fn.add_input(acc, make_event("a", duration_seconds=600, trip_distance=2.0, total_amount=10.0))
    # 3 miles in 900s (15 min) => 12 mph
    acc = combine_fn.add_input(acc, make_event("b", duration_seconds=900, trip_distance=3.0, total_amount=20.0))

    result = combine_fn.extract_output(acc)

    assert result["trip_count"] == 2
    assert result["total_revenue"] == 30.0
    assert result["avg_duration_seconds"] == 750.0
    assert result["avg_speed_mph"] == 12.0


def test_zone_aggregate_merge_accumulators():
    combine_fn = ZoneAggregate()
    acc1 = combine_fn.add_input(combine_fn.create_accumulator(), make_event("a"))
    acc2 = combine_fn.add_input(combine_fn.create_accumulator(), make_event("b"))

    merged = combine_fn.merge_accumulators([acc1, acc2])

    assert merged["trip_count"] == 2


def test_zone_aggregate_extract_output_handles_empty_accumulator():
    combine_fn = ZoneAggregate()
    result = combine_fn.extract_output(combine_fn.create_accumulator())
    assert result == {
        "trip_count": 0,
        "total_revenue": 0.0,
        "avg_duration_seconds": 0.0,
        "avg_speed_mph": 0.0,
    }


# --- AssignEventTimestamp DoFn ---


def collect_with_timestamp(element, timestamp=beam.DoFn.TimestampParam):
    return (element.trip_id, timestamp)


def test_assign_event_timestamp_sets_pipeline_timestamp_to_pickup_time():
    event = make_event("a", pickup_offset_seconds=120)
    expected_ts = window.TimestampedValue(event, event_timestamp_seconds(event)).timestamp

    with TestPipeline() as p:
        result = (
            p
            | beam.Create([event])
            | beam.ParDo(AssignEventTimestamp())
            | beam.Map(collect_with_timestamp)
        )
        assert_that(result, equal_to([("a", expected_ts)]))


# --- Sliding window aggregation with a TestPipeline (no lateness) ---


def test_window_and_aggregate_by_zone_groups_by_zone_within_window():
    events = [
        make_event("a", zone=100),
        make_event("b", zone=100),
        make_event("c", zone=200),
    ]

    with TestPipeline() as p:
        timestamped = (
            p
            | beam.Create(events)
            | beam.Map(lambda e: window.TimestampedValue(e, event_timestamp_seconds(e)))
        )
        aggregated = window_and_aggregate_by_zone(
            timestamped, window_size_seconds=60, window_period_seconds=60, allowed_lateness_seconds=0
        )
        counts = aggregated | beam.Map(lambda kv: (kv[0], kv[1]["trip_count"]))

        assert_that(counts, equal_to([(100, 2), (200, 1)]))


# --- Late data handling with TestStream: the heart of the brief's ---
# "watermarks, allowed lateness, triggers" requirement.


def test_late_event_within_allowed_lateness_is_included_but_beyond_is_dropped():
    zone = 100
    on_time_a = make_event("a", zone=zone)
    on_time_b = make_event("b", zone=zone)
    late_but_allowed = make_event("late", zone=zone)
    too_late = make_event("too-late", zone=zone)

    test_stream = (
        TestStream()
        .advance_watermark_to(0)
        .add_elements(
            [
                window.TimestampedValue(on_time_a, 10),
                window.TimestampedValue(on_time_b, 20),
            ]
        )
        .advance_watermark_to(61)  # passes the [0, 60) window's end -> on-time firing
        .add_elements([window.TimestampedValue(late_but_allowed, 15)])  # late, but within allowed_lateness
        .advance_watermark_to(200)  # passes window_end(60) + allowed_lateness(120) -> window is GC'd
        .add_elements([window.TimestampedValue(too_late, 12)])  # arrives after GC -> dropped
        .advance_watermark_to_infinity()
    )

    options = PipelineOptions()
    options.view_as(StandardOptions).streaming = True

    with TestPipeline(options=options) as p:
        events = p | test_stream
        aggregated = window_and_aggregate_by_zone(
            events, window_size_seconds=60, window_period_seconds=60, allowed_lateness_seconds=120
        )
        counts = aggregated | beam.Map(lambda kv: kv[1]["trip_count"])

        def check_panes(actual):
            actual = list(actual)
            assert actual, "expected at least one pane to fire"
            assert 2 in actual, f"expected an on-time pane with trip_count=2, got {actual}"
            assert 3 in actual, f"expected a late-refire pane with trip_count=3, got {actual}"
            assert max(actual) == 3, f"too-late event must not be counted, got {actual}"

        assert_that(counts, check_panes)
