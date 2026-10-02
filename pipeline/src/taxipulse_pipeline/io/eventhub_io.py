"""Reads trip events from Azure Event Hubs via its Kafka-compatible
endpoint, using Spark's own spark-sql-kafka connector.

Deliberately NOT using the dedicated `azure-eventhubs-spark` connector:
Event Hubs exposes a fully Kafka-protocol-compatible endpoint, and
spark-sql-kafka-0-10 is Apache Spark's own first-party connector, released
and version-matched alongside Spark itself - the dedicated Event Hubs
connector has historically lagged behind new Spark major versions. Same
approach works against the local emulator (plaintext, port 9092) and real
Azure Event Hubs (SASL_SSL with the namespace connection string as the
password) - only the auth options differ.
"""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession


def read_trip_events_from_eventhub(
    spark: SparkSession,
    bootstrap_servers: str,
    eventhub_name: str,
    connection_string: str | None = None,
) -> DataFrame:
    reader = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap_servers)
        .option("subscribe", eventhub_name)
        .option("startingOffsets", "latest")
    )

    if connection_string:
        jaas_config = (
            "org.apache.kafka.common.security.plain.PlainLoginModule required "
            f'username="$ConnectionString" password="{connection_string}";'
        )
        reader = (
            reader.option("kafka.sasl.mechanism", "PLAIN")
            .option("kafka.security.protocol", "SASL_SSL")
            .option("kafka.sasl.jaas.config", jaas_config)
        )
    else:
        # Local emulator: unauthenticated, plaintext.
        reader = reader.option("kafka.security.protocol", "PLAINTEXT")

    return reader.load().selectExpr("CAST(value AS STRING) AS body")
