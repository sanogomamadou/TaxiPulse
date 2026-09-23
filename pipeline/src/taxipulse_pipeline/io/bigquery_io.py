"""BigQuery write side of the pipeline. Only exercised once the pipeline is
actually deployed to GCP (Phase 2) - local/dev runs use the text sink in
main.py instead, so Phase 1 never touches billable resources."""

from __future__ import annotations

import apache_beam as beam
from apache_beam.io.gcp.bigquery import BigQueryDisposition, WriteToBigQuery

ZONE_AGGREGATES_SCHEMA = {
    "fields": [
        {"name": "pickup_location_id", "type": "INTEGER", "mode": "REQUIRED"},
        {"name": "window_start", "type": "TIMESTAMP", "mode": "REQUIRED"},
        {"name": "window_end", "type": "TIMESTAMP", "mode": "REQUIRED"},
        {"name": "trip_count", "type": "INTEGER", "mode": "REQUIRED"},
        {"name": "total_revenue", "type": "FLOAT", "mode": "REQUIRED"},
        {"name": "avg_duration_seconds", "type": "FLOAT", "mode": "REQUIRED"},
        {"name": "avg_speed_mph", "type": "FLOAT", "mode": "REQUIRED"},
        {"name": "historical_avg_trip_count", "type": "FLOAT", "mode": "NULLABLE"},
        {"name": "spike_ratio", "type": "FLOAT", "mode": "NULLABLE"},
        {"name": "is_spike", "type": "BOOLEAN", "mode": "REQUIRED"},
    ]
}

DEAD_LETTER_SCHEMA = {
    "fields": [
        {"name": "raw_payload", "type": "STRING", "mode": "REQUIRED"},
        {"name": "error_message", "type": "STRING", "mode": "REQUIRED"},
        {"name": "processing_time", "type": "TIMESTAMP", "mode": "REQUIRED"},
    ]
}


def write_zone_aggregates_to_bigquery(records: beam.PCollection, table: str) -> None:
    records | "WriteZoneAggregatesToBigQuery" >> WriteToBigQuery(
        table=table,
        schema=ZONE_AGGREGATES_SCHEMA,
        create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
        write_disposition=BigQueryDisposition.WRITE_APPEND,
        method=WriteToBigQuery.Method.STREAMING_INSERTS,
    )


def write_dead_letters_to_bigquery(records: beam.PCollection, table: str) -> None:
    records | "WriteDeadLettersToBigQuery" >> WriteToBigQuery(
        table=table,
        schema=DEAD_LETTER_SCHEMA,
        create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
        write_disposition=BigQueryDisposition.WRITE_APPEND,
        method=WriteToBigQuery.Method.STREAMING_INSERTS,
    )
