"""Parses raw Event Hubs message bodies into validated trip event rows,
routing invalid payloads to a dead-letter DataFrame instead of failing the
job. Mirrors the validation rules in
common/src/taxipulse_common/trip_event.py's TripEvent.from_dict (required
fields, dropoff >= pickup, non-negative amounts) - re-expressed as Spark
column expressions instead of Python since this runs over a DataFrame,
possibly a streaming one."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from taxipulse_pipeline.schema import TRIP_EVENT_SCHEMA

REQUIRED_FIELDS = (
    "trip_id",
    "vendor_id",
    "pickup_datetime",
    "dropoff_datetime",
    "pickup_location_id",
    "dropoff_location_id",
    "trip_distance",
    "fare_amount",
    "total_amount",
)

# Defaults applied to optional fields once a row is valid (same defaults as
# TripEvent.from_dict: passenger_count=1, payment_type=0, tip_amount=0.0).
OPTIONAL_FIELD_DEFAULTS = {"passenger_count": 1, "payment_type": 0, "tip_amount": 0.0}


def parse_with_dead_letter(df: DataFrame, body_col: str = "body") -> tuple[DataFrame, DataFrame]:
    """`df` must have a string column named `body_col` holding the raw JSON
    payload. Returns (valid_events, dead_letters)."""
    parsed = df.withColumn("event", F.from_json(F.col(body_col), TRIP_EVENT_SCHEMA))

    required_not_null = F.lit(True)
    for field in REQUIRED_FIELDS:
        required_not_null = required_not_null & F.col(f"event.{field}").isNotNull()

    is_valid = (
        parsed["event"].isNotNull()
        & required_not_null
        & (F.col("event.dropoff_datetime") >= F.col("event.pickup_datetime"))
        & (F.col("event.trip_distance") >= 0)
        & (F.col("event.fare_amount") >= 0)
        & (F.col("event.total_amount") >= 0)
    )

    valid_events = parsed.filter(is_valid).select("event.*").fillna(OPTIONAL_FIELD_DEFAULTS)

    dead_letters = parsed.filter(~is_valid).select(
        F.col(body_col).alias("raw_payload"),
        F.lit("schema or business-rule validation failed").alias("error_message"),
        F.current_timestamp().alias("processing_time"),
    )

    return valid_events, dead_letters
