"""PySpark schema for the TripEvent wire format - kept in sync by hand with
common/src/taxipulse_common/trip_event.py. The two can't literally share
code: one is a pure-Python dataclass used by the replayer (no Spark
dependency), the other is a Spark StructType used only by the pipeline."""

from __future__ import annotations

from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

TRIP_EVENT_SCHEMA = StructType(
    [
        StructField("trip_id", StringType()),
        StructField("vendor_id", IntegerType()),
        StructField("pickup_datetime", TimestampType()),
        StructField("dropoff_datetime", TimestampType()),
        StructField("pickup_location_id", IntegerType()),
        StructField("dropoff_location_id", IntegerType()),
        StructField("passenger_count", IntegerType()),
        StructField("trip_distance", DoubleType()),
        StructField("fare_amount", DoubleType()),
        StructField("tip_amount", DoubleType()),
        StructField("total_amount", DoubleType()),
        StructField("payment_type", IntegerType()),
        StructField("publish_time", StringType()),
    ]
)
