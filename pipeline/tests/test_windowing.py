from datetime import datetime, timedelta

from taxipulse_pipeline.transforms.windowing import add_trip_metrics, aggregate_by_zone

EPOCH = datetime(2024, 1, 1, 8, 0, 0)

SCHEMA = (
    "trip_id STRING, pickup_datetime TIMESTAMP, dropoff_datetime TIMESTAMP, "
    "pickup_location_id INT, trip_distance DOUBLE, total_amount DOUBLE"
)


def make_row(
    trip_id: str,
    pickup_offset_seconds: float = 0,
    duration_seconds: float = 600,
    zone: int = 100,
    trip_distance: float = 2.0,
    total_amount: float = 11.0,
):
    pickup = EPOCH + timedelta(seconds=pickup_offset_seconds)
    dropoff = pickup + timedelta(seconds=duration_seconds)
    return (trip_id, pickup, dropoff, zone, trip_distance, total_amount)


def test_add_trip_metrics_computes_duration_and_speed(spark):
    df = spark.createDataFrame([make_row("a", duration_seconds=600, trip_distance=2.0)], SCHEMA)

    result = add_trip_metrics(df).collect()[0]

    assert result["duration_seconds"] == 600.0
    assert result["speed_mph"] == 12.0  # 2 miles in 600s (10 min) = 12 mph


def test_add_trip_metrics_handles_zero_duration(spark):
    df = spark.createDataFrame([make_row("a", duration_seconds=0, trip_distance=2.0)], SCHEMA)

    result = add_trip_metrics(df).collect()[0]

    assert result["duration_seconds"] == 0.0
    assert result["speed_mph"] == 0.0


def test_aggregate_by_zone_groups_by_zone_and_computes_metrics(spark):
    rows = [
        make_row("a", pickup_offset_seconds=0, zone=100, total_amount=10.0, duration_seconds=600, trip_distance=2.0),
        make_row("b", pickup_offset_seconds=30, zone=100, total_amount=20.0, duration_seconds=900, trip_distance=3.0),
        make_row("c", pickup_offset_seconds=0, zone=200, total_amount=15.0, duration_seconds=300, trip_distance=1.0),
    ]
    df = add_trip_metrics(spark.createDataFrame(rows, SCHEMA))

    result = aggregate_by_zone(df, window_duration="60 minutes", slide_duration="60 minutes").collect()

    by_zone = {row["pickup_location_id"]: row for row in result}
    assert by_zone[100]["trip_count"] == 2
    assert by_zone[100]["total_revenue"] == 30.0
    assert by_zone[200]["trip_count"] == 1
    assert by_zone[200]["total_revenue"] == 15.0
