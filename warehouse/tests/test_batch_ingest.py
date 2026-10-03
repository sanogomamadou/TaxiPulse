from datetime import datetime

import pytest

from taxipulse_warehouse.batch_ingest import (
    normalize_columns,
    validate_trips,
    with_deterministic_trip_id,
)

RAW_SCHEMA = (
    "VendorID INT, tpep_pickup_datetime TIMESTAMP, tpep_dropoff_datetime TIMESTAMP, "
    "passenger_count INT, trip_distance DOUBLE, PULocationID INT, DOLocationID INT, "
    "payment_type INT, fare_amount DOUBLE, tip_amount DOUBLE, total_amount DOUBLE"
)


def make_raw_row(
    vendor_id=1,
    pickup=datetime(2024, 1, 1, 8, 0, 0),
    dropoff=datetime(2024, 1, 1, 8, 10, 0),
    passenger_count=1,
    trip_distance=2.0,
    pu=100,
    do=200,
    payment_type=1,
    fare_amount=10.0,
    tip_amount=1.0,
    total_amount=11.0,
):
    return (
        vendor_id,
        pickup,
        dropoff,
        passenger_count,
        trip_distance,
        pu,
        do,
        payment_type,
        fare_amount,
        tip_amount,
        total_amount,
    )


def test_normalize_columns_renames_tlc_columns_to_canonical_names(spark):
    df = spark.createDataFrame([make_raw_row()], RAW_SCHEMA)

    result = normalize_columns(df)

    assert set(result.columns) == {
        "vendor_id",
        "pickup_datetime",
        "dropoff_datetime",
        "pickup_location_id",
        "dropoff_location_id",
        "passenger_count",
        "trip_distance",
        "fare_amount",
        "tip_amount",
        "total_amount",
        "payment_type",
    }
    row = result.collect()[0]
    assert row["pickup_location_id"] == 100
    assert row["dropoff_location_id"] == 200


def test_normalize_columns_raises_on_missing_source_column(spark):
    df = spark.createDataFrame([(1,)], "VendorID INT")

    with pytest.raises(ValueError, match="pickup_datetime"):
        normalize_columns(df)


def test_validate_trips_filters_negative_fare(spark):
    df = normalize_columns(spark.createDataFrame([make_raw_row(fare_amount=-5.0, total_amount=-5.0)], RAW_SCHEMA))

    result = validate_trips(df)

    assert result.count() == 0


def test_validate_trips_filters_dropoff_before_pickup(spark):
    df = normalize_columns(
        spark.createDataFrame(
            [
                make_raw_row(
                    pickup=datetime(2024, 1, 1, 8, 10, 0),
                    dropoff=datetime(2024, 1, 1, 8, 0, 0),
                )
            ],
            RAW_SCHEMA,
        )
    )

    result = validate_trips(df)

    assert result.count() == 0


def test_validate_trips_defaults_optional_fields(spark):
    df = spark.createDataFrame(
        [
            (
                1,
                datetime(2024, 1, 1, 8, 0, 0),
                datetime(2024, 1, 1, 8, 10, 0),
                None,
                2.0,
                100,
                200,
                None,
                10.0,
                None,
                11.0,
            )
        ],
        RAW_SCHEMA,
    )
    normalized = normalize_columns(df)

    result = validate_trips(normalized).collect()[0]

    assert result["passenger_count"] == 1
    assert result["payment_type"] == 0
    assert result["tip_amount"] == 0.0


def test_with_deterministic_trip_id_is_stable_across_runs(spark):
    df = validate_trips(normalize_columns(spark.createDataFrame([make_raw_row()], RAW_SCHEMA)))

    first_run = with_deterministic_trip_id(df).collect()[0]["trip_id"]
    second_run = with_deterministic_trip_id(df).collect()[0]["trip_id"]

    assert first_run == second_run


def test_with_deterministic_trip_id_differs_for_different_trips(spark):
    df = validate_trips(
        normalize_columns(
            spark.createDataFrame(
                [make_raw_row(pu=100), make_raw_row(pu=200)], RAW_SCHEMA
            )
        )
    )

    ids = [row["trip_id"] for row in with_deterministic_trip_id(df).collect()]

    assert ids[0] != ids[1]
