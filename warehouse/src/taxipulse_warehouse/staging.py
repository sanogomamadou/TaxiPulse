"""Staging layer: deduplicated raw.trips with derived per-trip metrics
(duration_seconds, speed_mph)."""

from __future__ import annotations

import argparse
import logging

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from taxipulse_warehouse.spark_session import build_spark_session

logger = logging.getLogger(__name__)


def add_trip_metrics(df: DataFrame) -> DataFrame:
    """Same logic as pipeline.transforms.windowing.add_trip_metrics,
    duplicated rather than imported - warehouse/ and pipeline/ are separate
    deployable components, same hand-kept-in-sync pattern as
    common/trip_event.py vs pipeline/schema.py."""
    duration_seconds = F.greatest(
        F.unix_timestamp("dropoff_datetime") - F.unix_timestamp("pickup_datetime"), F.lit(0)
    ).cast("double")
    return df.withColumn("duration_seconds", duration_seconds).withColumn(
        "speed_mph",
        F.when(
            F.col("duration_seconds") > 0,
            F.col("trip_distance") / (F.col("duration_seconds") / 3600),
        ).otherwise(F.lit(0.0)),
    )


def build_stg_trips(raw_trips: DataFrame) -> DataFrame:
    # trip_id is deterministic (see batch_ingest.with_deterministic_trip_id),
    # so this also makes re-running the whole staging job idempotent.
    deduped = raw_trips.dropDuplicates(["trip_id"])
    return add_trip_metrics(deduped)


def run(input_path: str, output_path: str) -> None:
    spark = build_spark_session(app_name="taxipulse-warehouse-staging")
    raw_trips = spark.read.format("delta").load(input_path)
    stg_trips = build_stg_trips(raw_trips)
    stg_trips.write.format("delta").mode("overwrite").save(output_path)
    logger.info("staged %d trips -> %s", stg_trips.count(), output_path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-path", default="warehouse_output/raw/trips")
    parser.add_argument("--output-path", default="warehouse_output/staging/stg_trips")
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    run(args.input_path, args.output_path)
