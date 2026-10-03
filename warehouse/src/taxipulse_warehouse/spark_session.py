"""Shared Spark session builder for warehouse jobs (batch ingestion, staging,
marts, quality checks, forecasting). No Kafka package needed here - unlike
pipeline/, these are batch jobs over Delta tables, not streaming."""

from __future__ import annotations

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession


def build_spark_session(
    app_name: str = "taxipulse-warehouse", shuffle_partitions: int = 8
) -> SparkSession:
    # See pipeline/src/taxipulse_pipeline/main.py's build_spark_session for
    # why shuffle_partitions is lowered from Spark's 200 default.
    builder = (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog"
        )
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
    )
    return configure_spark_with_delta_pip(builder).getOrCreate()
