"""Loads the zone reference file (scripts/download_taxi_zones.py's output:
borough/zone name + centroid lat/lon per TLC zone) into the
staging.stg_taxi_zones Delta table."""

from __future__ import annotations

import argparse
import logging

from pyspark.sql import DataFrame, SparkSession

from taxipulse_warehouse.spark_session import build_spark_session

logger = logging.getLogger(__name__)


def load_zone_reference(spark: SparkSession, reference_path: str) -> DataFrame:
    """`reference_path` is the parquet file written by
    scripts/download_taxi_zones.py (local path or abfss:// URL once deployed)."""
    return spark.read.parquet(reference_path)


def write_stg_taxi_zones(df: DataFrame, output_path: str) -> None:
    df.write.format("delta").mode("overwrite").save(output_path)


def run(reference_path: str, output_path: str) -> None:
    spark = build_spark_session(app_name="taxipulse-warehouse-zones")
    df = load_zone_reference(spark, reference_path)
    write_stg_taxi_zones(df, output_path)
    logger.info("wrote %d zones -> %s", df.count(), output_path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-path", default="data/reference/taxi_zones.parquet")
    parser.add_argument("--output-path", default="warehouse_output/staging/stg_taxi_zones")
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    run(args.reference_path, args.output_path)
