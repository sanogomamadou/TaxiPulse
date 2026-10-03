"""Data quality checks for the warehouse layers - deliberately lightweight
(no Great Expectations or similar framework): row-count sanity, null rates
on required columns, value-range checks, and referential integrity against
the zone dimension. Enough to catch real regressions without pulling in a
whole DQ framework for a project this size."""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from taxipulse_warehouse.spark_session import build_spark_session

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QualityCheckResult:
    name: str
    passed: bool
    detail: str


def check_not_empty(df: DataFrame, name: str) -> QualityCheckResult:
    count = df.count()
    return QualityCheckResult(name, count > 0, f"{count} rows")


def check_no_nulls(df: DataFrame, columns: list[str], name: str) -> QualityCheckResult:
    row = df.select(
        [F.sum(F.col(c).isNull().cast("int")).alias(c) for c in columns]
    ).collect()[0]
    offending = {c: n for c, n in row.asDict().items() if n}
    return QualityCheckResult(name, not offending, str(offending) if offending else "no nulls")


def check_non_negative(df: DataFrame, columns: list[str], name: str) -> QualityCheckResult:
    condition = None
    for c in columns:
        clause = F.col(c) < 0
        condition = clause if condition is None else (condition | clause)
    bad_count = df.filter(condition).count()
    return QualityCheckResult(name, bad_count == 0, f"{bad_count} rows with a negative value")


def check_zone_referential_integrity(
    zone_demand: DataFrame, stg_taxi_zones: DataFrame, name: str
) -> QualityCheckResult:
    known_zones = stg_taxi_zones.select("location_id")
    orphaned = zone_demand.join(
        known_zones, zone_demand.pickup_location_id == known_zones.location_id, how="left_anti"
    )
    bad_count = orphaned.count()
    return QualityCheckResult(
        name, bad_count == 0, f"{bad_count} zone_demand rows with an unknown pickup_location_id"
    )


def run_quality_checks(
    stg_trips: DataFrame, stg_taxi_zones: DataFrame, zone_demand_hourly: DataFrame
) -> list[QualityCheckResult]:
    return [
        check_not_empty(stg_trips, "stg_trips_not_empty"),
        check_not_empty(zone_demand_hourly, "zone_demand_hourly_not_empty"),
        check_no_nulls(
            stg_trips,
            ["pickup_datetime", "dropoff_datetime", "pickup_location_id"],
            "stg_trips_required_fields_not_null",
        ),
        check_non_negative(
            stg_trips,
            ["trip_distance", "fare_amount", "total_amount"],
            "stg_trips_amounts_non_negative",
        ),
        check_zone_referential_integrity(
            zone_demand_hourly, stg_taxi_zones, "zone_demand_hourly_zone_referential_integrity"
        ),
    ]


def run(stg_trips_path: str, stg_taxi_zones_path: str, zone_demand_hourly_path: str) -> bool:
    spark = build_spark_session(app_name="taxipulse-warehouse-quality")
    stg_trips = spark.read.format("delta").load(stg_trips_path)
    stg_taxi_zones = spark.read.format("delta").load(stg_taxi_zones_path)
    zone_demand_hourly = spark.read.format("delta").load(zone_demand_hourly_path)

    results = run_quality_checks(stg_trips, stg_taxi_zones, zone_demand_hourly)
    all_passed = True
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        logger.info("[%s] %s: %s", status, result.name, result.detail)
        all_passed = all_passed and result.passed
    return all_passed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stg-trips-path", default="warehouse_output/staging/stg_trips")
    parser.add_argument(
        "--stg-taxi-zones-path", default="warehouse_output/staging/stg_taxi_zones"
    )
    parser.add_argument(
        "--zone-demand-hourly-path", default="warehouse_output/marts/zone_demand_hourly"
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    passed = run(args.stg_trips_path, args.stg_taxi_zones_path, args.zone_demand_hourly_path)
    sys.exit(0 if passed else 1)
