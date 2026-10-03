from datetime import datetime

from taxipulse_warehouse.marts import aggregate_zone_demand, enrich_with_zone_dimension

TRIP_SCHEMA = (
    "trip_id STRING, pickup_datetime TIMESTAMP, pickup_location_id INT, "
    "trip_distance DOUBLE, total_amount DOUBLE, duration_seconds DOUBLE, speed_mph DOUBLE"
)
ZONE_SCHEMA = (
    "location_id INT, borough STRING, zone_name STRING, service_zone STRING, "
    "centroid_lat DOUBLE, centroid_lon DOUBLE"
)


def make_trip(trip_id, pickup, zone=100, total_amount=11.0, duration_seconds=600.0, speed_mph=12.0):
    return (trip_id, pickup, zone, 2.0, total_amount, duration_seconds, speed_mph)


def test_aggregate_zone_demand_groups_by_hour_and_zone(spark):
    rows = [
        make_trip("a", datetime(2024, 1, 1, 8, 5), zone=100, total_amount=10.0),
        make_trip("b", datetime(2024, 1, 1, 8, 45), zone=100, total_amount=20.0),
        make_trip("c", datetime(2024, 1, 1, 9, 5), zone=100, total_amount=15.0),
        make_trip("d", datetime(2024, 1, 1, 8, 5), zone=200, total_amount=5.0),
    ]
    df = spark.createDataFrame(rows, TRIP_SCHEMA)

    result = {
        (row["pickup_location_id"], str(row["period_start"])): row
        for row in aggregate_zone_demand(df, "hour").collect()
    }

    hour8_zone100 = result[(100, "2024-01-01 08:00:00")]
    assert hour8_zone100["trip_count"] == 2
    assert hour8_zone100["total_revenue"] == 30.0

    hour9_zone100 = result[(100, "2024-01-01 09:00:00")]
    assert hour9_zone100["trip_count"] == 1

    hour8_zone200 = result[(200, "2024-01-01 08:00:00")]
    assert hour8_zone200["trip_count"] == 1


def test_enrich_with_zone_dimension_joins_borough_and_centroid(spark):
    demand = spark.createDataFrame(
        [(100, 5, 50.0, 300.0, 12.0)],
        "pickup_location_id INT, trip_count INT, total_revenue DOUBLE, avg_duration_seconds DOUBLE, avg_speed_mph DOUBLE",
    )
    zones = spark.createDataFrame(
        [(100, "Manhattan", "Midtown", "Yellow Zone", 40.75, -73.98)], ZONE_SCHEMA
    )

    result = enrich_with_zone_dimension(demand, zones).collect()[0]

    assert result["borough"] == "Manhattan"
    assert result["zone_name"] == "Midtown"
    assert result["centroid_lat"] == 40.75


def test_enrich_with_zone_dimension_handles_unknown_zone(spark):
    demand = spark.createDataFrame(
        [(999, 5, 50.0, 300.0, 12.0)],
        "pickup_location_id INT, trip_count INT, total_revenue DOUBLE, avg_duration_seconds DOUBLE, avg_speed_mph DOUBLE",
    )
    zones = spark.createDataFrame([], ZONE_SCHEMA)

    result = enrich_with_zone_dimension(demand, zones).collect()[0]

    assert result["borough"] is None
