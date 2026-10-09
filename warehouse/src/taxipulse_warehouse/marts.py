"""Marts layer: per-zone demand rolled up from staging.stg_trips into
hourly/daily buckets, enriched with the zone dimension (borough, zone name,
centroid lat/lon) from staging.stg_taxi_zones. This is what the forecasting
model trains on and what the API (Phase 4) will eventually serve."""

from __future__ import annotations

import argparse
import logging

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from taxipulse_warehouse.spark_session import build_spark_session

logger = logging.getLogger(__name__)


def aggregate_zone_demand(stg_trips: DataFrame, bucket: str) -> DataFrame:
    """`bucket` is a Spark `date_trunc` unit, e.g. "hour" or "day"."""
    return stg_trips.groupBy(
        F.date_trunc(bucket, F.col("pickup_datetime")).alias("period_start"),
        F.col("pickup_location_id"),
    ).agg(
        F.count(F.lit(1)).alias("trip_count"),
        F.round(F.sum("total_amount"), 2).alias("total_revenue"),
        F.round(F.avg("duration_seconds"), 1).alias("avg_duration_seconds"),
        F.round(F.avg("speed_mph"), 1).alias("avg_speed_mph"),
    )


def enrich_with_zone_dimension(zone_demand: DataFrame, stg_taxi_zones: DataFrame) -> DataFrame:
    zones = stg_taxi_zones.select(
        F.col("location_id"),
        F.col("borough"),
        F.col("zone_name"),
        F.col("centroid_lat"),
        F.col("centroid_lon"),
    )
    return zone_demand.join(
        zones, zone_demand.pickup_location_id == zones.location_id, how="left"
    ).drop("location_id")


def build_zone_demand_mart(
    stg_trips: DataFrame, stg_taxi_zones: DataFrame, bucket: str
) -> DataFrame:
    return enrich_with_zone_dimension(aggregate_zone_demand(stg_trips, bucket), stg_taxi_zones)


def run(
    stg_trips_path: str, stg_taxi_zones_path: str, hourly_output_path: str, daily_output_path: str
) -> None:
    spark = build_spark_session(app_name="taxipulse-warehouse-marts")
    stg_trips = spark.read.format("delta").load(stg_trips_path)
    stg_taxi_zones = spark.read.format("delta").load(stg_taxi_zones_path)

    hourly = build_zone_demand_mart(stg_trips, stg_taxi_zones, "hour")
    hourly.write.format("delta").mode("overwrite").save(hourly_output_path)
    logger.info("wrote %d hourly rows -> %s", hourly.count(), hourly_output_path)

    daily = build_zone_demand_mart(stg_trips, stg_taxi_zones, "day")
    daily.write.format("delta").mode("overwrite").save(daily_output_path)
    logger.info("wrote %d daily rows -> %s", daily.count(), daily_output_path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stg-trips-path", default="warehouse_output/staging/stg_trips")
    parser.add_argument("--stg-taxi-zones-path", default="warehouse_output/staging/stg_taxi_zones")
    parser.add_argument("--hourly-output-path", default="warehouse_output/marts/zone_demand_hourly")
    parser.add_argument("--daily-output-path", default="warehouse_output/marts/zone_demand_daily")
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    run(
        args.stg_trips_path,
        args.stg_taxi_zones_path,
        args.hourly_output_path,
        args.daily_output_path,
    )
