import apache_beam as beam
from apache_beam.testing.test_pipeline import TestPipeline
from apache_beam.testing.util import assert_that, equal_to

from taxipulse_common.trip_event import TripEvent
from taxipulse_pipeline.transforms.dedup import deduplicate_by_trip_id


def make_event(trip_id: str) -> TripEvent:
    return TripEvent.from_dict(
        {
            "trip_id": trip_id,
            "vendor_id": 1,
            "pickup_datetime": "2024-01-01T08:00:00",
            "dropoff_datetime": "2024-01-01T08:10:00",
            "pickup_location_id": 100,
            "dropoff_location_id": 200,
            "passenger_count": 1,
            "trip_distance": 2.0,
            "fare_amount": 10.0,
            "tip_amount": 1.0,
            "total_amount": 11.0,
            "payment_type": 1,
        }
    )


def test_deduplicate_by_trip_id_drops_exact_duplicates():
    events = [make_event("a"), make_event("a"), make_event("b")]

    with TestPipeline() as p:
        result = deduplicate_by_trip_id(p | beam.Create(events))
        result_ids = result | beam.Map(lambda e: e.trip_id)

        assert_that(result_ids, equal_to(["a", "b"]))


def test_deduplicate_by_trip_id_keeps_distinct_events_from_different_trips():
    events = [make_event(str(i)) for i in range(10)]

    with TestPipeline() as p:
        result = deduplicate_by_trip_id(p | beam.Create(events))
        result_ids = result | beam.Map(lambda e: e.trip_id)

        assert_that(result_ids, equal_to([str(i) for i in range(10)]))


def test_deduplicate_by_trip_id_drops_many_duplicates_of_the_same_trip():
    events = [make_event("a")] * 5

    with TestPipeline() as p:
        result = deduplicate_by_trip_id(p | beam.Create(events))
        count = result | beam.combiners.Count.Globally()

        assert_that(count, equal_to([1]))
