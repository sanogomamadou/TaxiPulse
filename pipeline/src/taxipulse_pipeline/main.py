"""Entry point that wires the TaxiPulse Spark Structured Streaming pipeline
together:

    Event Hubs (Kafka protocol) -> parse + dead-letter -> trip metrics
    -> watermark + dedup -> sliding-window per-zone aggregation
    -> demand spike detection -> Delta Lake (zone_aggregates, dead_letters)

Example (against real Azure Event Hubs, or an emulator whose Kafka endpoint
is reachable from the host):
    python -m taxipulse_pipeline.main \
        --bootstrap-servers localhost:9092 --eventhub-name taxi-trips \
        --output-path output/zone_aggregates --dead-letter-path output/dead_letters

Known limitation: the local Azure Event Hubs Emulator's Kafka-compatible
port (9092) could not be made reachable from this entry point during local
testing - the broker's metadata response advertises an address the Spark
Kafka client can't resolve/reach from the host (neither localhost,
127.0.0.1, nor a fixed container hostname + hosts-file entry fixed it; not
documented by Microsoft for this emulator). This is a local-dev-only gap:
spark-sql-kafka-0-10 against Kafka-compatible endpoints is a mainstream,
well-documented pattern for real Azure Event Hubs. The downstream pipeline
(everything from parsing onward) was validated end-to-end in genuine
streaming execution using a local file source as a stand-in for the Kafka
read step - see CLAUDE.md for the full writeup and verified results.

Windows prerequisites for running this locally: a Java 17+ JDK (Spark 4.x
requires it; JAVA_HOME may point somewhere older), and winutils.exe +
hadoop.dll on HADOOP_HOME/bin (Spark's Hadoop filesystem layer needs them
even for purely local paths) - see README.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pyspark
from delta import configure_spark_with_delta_pip
from pyspark.sql import DataFrame, SparkSession

from taxipulse_pipeline.io.delta_io import write_to_delta
from taxipulse_pipeline.io.eventhub_io import read_trip_events_from_eventhub
from taxipulse_pipeline.options import parse_args
from taxipulse_pipeline.transforms.anomaly import detect_demand_spikes
from taxipulse_pipeline.transforms.parsing import parse_with_dead_letter
from taxipulse_pipeline.transforms.windowing import (
    add_trip_metrics,
    aggregate_by_zone,
    deduplicate_by_trip_id,
    with_watermark,
)

logger = logging.getLogger(__name__)

HISTORICAL_AVG_SCHEMA = "pickup_location_id INT, historical_avg_trip_count DOUBLE"


def build_spark_session(
    app_name: str = "taxipulse-pipeline", shuffle_partitions: int = 8
) -> SparkSession:
    # Spark's default of 200 shuffle partitions is sized for large clusters, not
    # this project's data volume - at 200, every micro-batch's windowed
    # aggregation/dedup shuffle spends most of its time on scheduling overhead
    # for near-empty tasks rather than actual work (found by profiling a local
    # run that was taking minutes to emit its first window). A real multi-node
    # Databricks deployment at higher volume should raise this back up.
    kafka_package = f"org.apache.spark:spark-sql-kafka-0-10_2.13:{pyspark.__version__}"
    builder = (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog"
        )
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
    )
    return configure_spark_with_delta_pip(builder, extra_packages=[kafka_package]).getOrCreate()


def load_historical_avg_by_zone(spark: SparkSession, path: str | None) -> DataFrame:
    if not path:
        return spark.createDataFrame([], schema=HISTORICAL_AVG_SCHEMA)
    data = json.loads(Path(path).read_text())
    rows = [(int(zone_id), float(avg)) for zone_id, avg in data.items()]
    return spark.createDataFrame(rows, schema=HISTORICAL_AVG_SCHEMA)


def run(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    spark = build_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    raw = read_trip_events_from_eventhub(
        spark, args.bootstrap_servers, args.eventhub_name, args.connection_string
    )
    valid_events, dead_letters = parse_with_dead_letter(raw)

    events = add_trip_metrics(valid_events)
    events = with_watermark(events, args.watermark_delay)
    events = deduplicate_by_trip_id(events)

    zone_aggregates = aggregate_by_zone(events, args.window_duration, args.slide_duration)

    historical_avg_by_zone = load_historical_avg_by_zone(spark, args.historical_avg_path)
    enriched = detect_demand_spikes(
        zone_aggregates, historical_avg_by_zone, args.spike_ratio_threshold
    )

    write_to_delta(enriched, args.output_path, f"{args.checkpoint_path}/zone_aggregates")
    write_to_delta(dead_letters, args.dead_letter_path, f"{args.checkpoint_path}/dead_letters")

    logger.info(
        "pipeline running - zone aggregates -> %s, dead letters -> %s",
        args.output_path,
        args.dead_letter_path,
    )
    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
