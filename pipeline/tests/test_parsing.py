import apache_beam as beam
from apache_beam.testing.test_pipeline import TestPipeline
from apache_beam.testing.util import assert_that, equal_to

from taxipulse_common.trip_event import TripEvent
from taxipulse_pipeline.transforms.parsing import parse_with_dead_letter

VALID_EVENT = TripEvent.from_dict(
    {
        "trip_id": "abc-123",
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
VALID_MESSAGE = VALID_EVENT.to_json().encode("utf-8")
INVALID_JSON_MESSAGE = b"not valid json"
INVALID_SCHEMA_MESSAGE = b'{"trip_id": "missing-fields"}'


def test_parse_with_dead_letter_routes_valid_message_to_main_output():
    with TestPipeline() as p:
        raw = p | beam.Create([VALID_MESSAGE])
        valid, dead_letter = parse_with_dead_letter(raw)

        valid_ids = valid | "ExtractIds" >> beam.Map(lambda e: e.trip_id)
        assert_that(valid_ids, equal_to(["abc-123"]), label="valid_ids")
        assert_that(dead_letter, equal_to([]), label="no_dead_letters")


def test_parse_with_dead_letter_routes_malformed_json_to_dead_letter():
    with TestPipeline() as p:
        raw = p | beam.Create([INVALID_JSON_MESSAGE])
        valid, dead_letter = parse_with_dead_letter(raw)

        assert_that(valid, equal_to([]), label="no_valid_events")
        dead_letter_messages = dead_letter | "ExtractRaw" >> beam.Map(lambda pair: pair[0])
        assert_that(dead_letter_messages, equal_to([INVALID_JSON_MESSAGE]), label="dead_letter_raw")


def test_parse_with_dead_letter_routes_schema_violation_to_dead_letter():
    with TestPipeline() as p:
        raw = p | beam.Create([INVALID_SCHEMA_MESSAGE])
        valid, dead_letter = parse_with_dead_letter(raw)

        assert_that(valid, equal_to([]), label="no_valid_events")
        error_messages = dead_letter | "ExtractError" >> beam.Map(lambda pair: pair[1])

        def has_missing_fields_error(actual):
            (msg,) = list(actual)
            assert "missing required fields" in msg

        assert_that(error_messages, has_missing_fields_error, label="dead_letter_error")


def test_parse_with_dead_letter_handles_mixed_batch():
    with TestPipeline() as p:
        raw = p | beam.Create([VALID_MESSAGE, INVALID_JSON_MESSAGE])
        valid, dead_letter = parse_with_dead_letter(raw)

        valid_count = valid | "CountValid" >> beam.combiners.Count.Globally()
        dead_letter_count = dead_letter | "CountDead" >> beam.combiners.Count.Globally()

        assert_that(valid_count, equal_to([1]), label="valid_count")
        assert_that(dead_letter_count, equal_to([1]), label="dead_letter_count")
