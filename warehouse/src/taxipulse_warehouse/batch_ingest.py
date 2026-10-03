"""Batch-loads NYC TLC trip Parquet files into the raw.trips Delta table -
the "load historical data" ingestion path, separate from the real-time
streaming path in pipeline/ (which writes pre-aggregated windows to
raw.zone_aggregates instead of individual trip records). staging/marts and
the forecasting model are built from this table, since the live streaming
demo alone doesn't carry enough historical volume for meaningful analysis.
"""

from __future__ import annotations

import argparse
import logging

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from taxipulse_warehouse.spark_session import build_spark_session

logger = logging.getLogger(__name__)

# TLC yellow/green trip files use slightly different column names for the
# same fields - same mapping idea as replayer/reader.py, re-expressed for
# Spark since this job reads potentially large files natively rather than
# through pandas.
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "vendor_id": ("VendorID",),
    "pickup_datetime": ("tpep_pickup_datetime", "lpep_pickup_datetime"),
    "dropoff_datetime": ("tpep_dropoff_datetime", "lpep_dropoff_datetime"),
    "pickup_location_id": ("PULocationID",),
    "dropoff_location_id": ("DOLocationID",),
    "passenger_count": ("passenger_count",),
    "trip_distance": ("trip_distance",),
    "fare_amount": ("fare_amount",),
    "tip_amount": ("tip_amount",),
    "total_amount": ("total_amount",),
    "payment_type": ("payment_type",),
}


DOUBLE_FIELDS = {"trip_distance", "fare_amount", "tip_amount", "total_amount"}
INT_FIELDS = {
    "vendor_id",
    "pickup_location_id",
    "dropoff_location_id",
    "passenger_count",
    "payment_type",
}


def _target_type(canonical: str) -> str:
    if canonical in DOUBLE_FIELDS:
        return "double"
    if canonical in INT_FIELDS:
        return "int"
    return "timestamp"  # pickup_datetime / dropoff_datetime


def normalize_columns(df: DataFrame) -> DataFrame:
    existing = set(df.columns)
    select_exprs = []
    for canonical, candidates in COLUMN_ALIASES.items():
        source = next((c for c in candidates if c in existing), None)
        if source is None:
            raise ValueError(f"could not find a source column for '{canonical}'")
        select_exprs.append(F.col(source).cast(_target_type(canonical)).alias(canonical))
    return df.select(*select_exprs)


def validate_trips(df: DataFrame) -> DataFrame:
    """Same business rules as common.trip_event.TripEvent.from_dict /
    pipeline.transforms.parsing: non-negative amounts, dropoff >= pickup.
    Optional fields default the same way too (passenger_count=1,
    payment_type=0, tip_amount=0.0)."""
    return df.withColumn(
        "passenger_count", F.coalesce(F.col("passenger_count"), F.lit(1))
    ).withColumn(
        "payment_type", F.coalesce(F.col("payment_type"), F.lit(0))
    ).withColumn(
        "tip_amount", F.coalesce(F.col("tip_amount"), F.lit(0.0))
    ).filter(
        F.col("pickup_datetime").isNotNull()
        & F.col("dropoff_datetime").isNotNull()
        & (F.col("dropoff_datetime") >= F.col("pickup_datetime"))
        & (F.col("trip_distance") >= 0)
        & (F.col("fare_amount") >= 0)
        & (F.col("total_amount") >= 0)
    )


# TLC source data has no natural unique trip identifier. A random UUID per
# row would make re-running batch ingestion on the same file non-idempotent
# (every retry/backfill would mint "new" trips). Hashing each row's own
# attributes - plus the source file path, so two genuinely different files
# can't collide - gives a stable ID: re-ingesting the same file produces the
# same trip_ids every time, so a downstream dedup by trip_id (see
# staging.py) correctly collapses re-runs. Known limitation: two distinct
# real trips from the same zone pair starting the same second with
# identical distance/fare would hash identically and collapse into one -
# accepted as rare enough to not warrant a heavier key.
TRIP_ID_KEY_COLUMNS = (
    "pickup_datetime",
    "dropoff_datetime",
    "pickup_location_id",
    "dropoff_location_id",
    "trip_distance",
    "fare_amount",
    "total_amount",
)


def with_deterministic_trip_id(df: DataFrame) -> DataFrame:
    key_expr = F.concat_ws(
        "||", F.input_file_name(), *[F.col(c).cast("string") for c in TRIP_ID_KEY_COLUMNS]
    )
    return df.withColumn("trip_id", F.sha2(key_expr, 256))


def ingest(spark: SparkSession, input_path: str) -> DataFrame:
    raw = spark.read.parquet(input_path)
    normalized = normalize_columns(raw)
    validated = validate_trips(normalized)
    return with_deterministic_trip_id(validated)


def run(input_path: str, output_path: str) -> None:
    spark = build_spark_session(app_name="taxipulse-warehouse-batch-ingest")
    trips = ingest(spark, input_path)
    trips.write.format("delta").mode("append").save(output_path)
    logger.info("ingested %d trips -> %s", trips.count(), output_path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_path", help="Path (or glob) to TLC Parquet file(s)")
    parser.add_argument("--output-path", default="warehouse_output/raw/trips")
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    run(args.input_path, args.output_path)
