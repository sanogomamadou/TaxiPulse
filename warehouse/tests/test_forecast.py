from datetime import datetime, timedelta

from taxipulse_warehouse.forecast import select_top_zones, train_and_forecast

HOURLY_SCHEMA = (
    "period_start TIMESTAMP, pickup_location_id INT, trip_count INT, "
    "total_revenue DOUBLE, avg_duration_seconds DOUBLE, avg_speed_mph DOUBLE"
)


def make_hourly_rows(zone: int, hours: int, base_count: int):
    start = datetime(2024, 1, 1, 0, 0, 0)
    return [
        (start + timedelta(hours=i), zone, base_count + (i % 5), 100.0, 600.0, 12.0)
        for i in range(hours)
    ]


def test_select_top_zones_orders_by_total_trip_count(spark):
    rows = make_hourly_rows(100, 10, 50) + make_hourly_rows(200, 10, 5)
    df = spark.createDataFrame(rows, HOURLY_SCHEMA)

    result = select_top_zones(df, top_n=1)

    assert result == [100]


def test_train_and_forecast_produces_expected_schema_and_horizon(spark):
    rows = make_hourly_rows(100, 40, 20)
    df = spark.createDataFrame(rows, HOURLY_SCHEMA)

    result = train_and_forecast(
        df, top_n_zones=1, forecast_hours=5, holdout_hours=5
    ).collect()

    assert len(result) == 5
    assert all(row["pickup_location_id"] == "100" for row in result)
    assert all(row["predicted_trip_count"] >= 0 for row in result)
    assert all(row["mae"] is not None for row in result)
