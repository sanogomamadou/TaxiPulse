import json

from taxipulse_pipeline.transforms.parsing import parse_with_dead_letter

VALID_PAYLOAD = {
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


def test_parse_with_dead_letter_routes_valid_message_to_main_output(spark):
    df = spark.createDataFrame([(json.dumps(VALID_PAYLOAD),)], ["body"])

    valid, dead_letters = parse_with_dead_letter(df)

    valid_rows = valid.collect()
    assert len(valid_rows) == 1
    assert valid_rows[0]["trip_id"] == "abc-123"
    assert dead_letters.count() == 0


def test_parse_with_dead_letter_routes_malformed_json_to_dead_letter(spark):
    df = spark.createDataFrame([("not valid json",)], ["body"])

    valid, dead_letters = parse_with_dead_letter(df)

    assert valid.count() == 0
    dead_rows = dead_letters.collect()
    assert len(dead_rows) == 1
    assert dead_rows[0]["raw_payload"] == "not valid json"


def test_parse_with_dead_letter_routes_missing_required_field_to_dead_letter(spark):
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "trip_id"}
    df = spark.createDataFrame([(json.dumps(payload),)], ["body"])

    valid, dead_letters = parse_with_dead_letter(df)

    assert valid.count() == 0
    assert dead_letters.count() == 1


def test_parse_with_dead_letter_routes_negative_fare_to_dead_letter(spark):
    payload = {**VALID_PAYLOAD, "fare_amount": -5.0}
    df = spark.createDataFrame([(json.dumps(payload),)], ["body"])

    valid, dead_letters = parse_with_dead_letter(df)

    assert valid.count() == 0
    assert dead_letters.count() == 1


def test_parse_with_dead_letter_routes_dropoff_before_pickup_to_dead_letter(spark):
    payload = {**VALID_PAYLOAD, "dropoff_datetime": "2024-01-01T07:00:00"}
    df = spark.createDataFrame([(json.dumps(payload),)], ["body"])

    valid, dead_letters = parse_with_dead_letter(df)

    assert valid.count() == 0
    assert dead_letters.count() == 1


def test_parse_with_dead_letter_defaults_optional_fields(spark):
    payload = {
        k: v for k, v in VALID_PAYLOAD.items() if k not in ("passenger_count", "tip_amount")
    }
    df = spark.createDataFrame([(json.dumps(payload),)], ["body"])

    valid, _ = parse_with_dead_letter(df)

    row = valid.collect()[0]
    assert row["passenger_count"] == 1
    assert row["tip_amount"] == 0.0


def test_parse_with_dead_letter_handles_mixed_batch(spark):
    rows = [(json.dumps(VALID_PAYLOAD),), ("not valid json",)]
    df = spark.createDataFrame(rows, ["body"])

    valid, dead_letters = parse_with_dead_letter(df)

    assert valid.count() == 1
    assert dead_letters.count() == 1
