from datetime import datetime

from taxipulse_warehouse.staging import add_trip_metrics, build_stg_trips

TRIP_SCHEMA = (
    "trip_id STRING, vendor_id INT, pickup_datetime TIMESTAMP, dropoff_datetime TIMESTAMP, "
    "pickup_location_id INT, dropoff_location_id INT, passenger_count INT, "
    "trip_distance DOUBLE, fare_amount DOUBLE, tip_amount DOUBLE, total_amount DOUBLE, "
    "payment_type INT"
)


def make_trip(trip_id="a", pickup_offset_min=0, duration_min=10, trip_distance=2.0):
    pickup = datetime(2024, 1, 1, 8, pickup_offset_min, 0)
    dropoff = datetime(2024, 1, 1, 8, pickup_offset_min + duration_min, 0)
    return (trip_id, 1, pickup, dropoff, 100, 200, 1, trip_distance, 10.0, 1.0, 11.0, 1)


def test_add_trip_metrics_computes_duration_and_speed(spark):
    df = spark.createDataFrame([make_trip(duration_min=10, trip_distance=2.0)], TRIP_SCHEMA)

    result = add_trip_metrics(df).collect()[0]

    assert result["duration_seconds"] == 600.0
    assert result["speed_mph"] == 12.0  # 2 miles in 10 min = 12 mph


def test_build_stg_trips_deduplicates_by_trip_id(spark):
    df = spark.createDataFrame([make_trip("a"), make_trip("a"), make_trip("b")], TRIP_SCHEMA)

    result = build_stg_trips(df)

    assert result.count() == 2
    assert {row["trip_id"] for row in result.collect()} == {"a", "b"}
