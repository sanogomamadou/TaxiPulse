"""Entry point that wires the TaxiPulse streaming pipeline together:

    Pub/Sub -> parse + dead-letter -> assign event timestamps -> dedup
    -> sliding-window per-zone aggregation -> demand spike detection
    -> BigQuery (or a local text sink for DirectRunner dev runs)

Example (local dev, against the Pub/Sub emulator, DirectRunner):
    python -m taxipulse_pipeline.main \
        --input_subscription projects/taxipulse-mds/subscriptions/taxi-trips-sub \
        --output_sink text --output_path output/zone_aggregates \
        --runner DirectRunner --streaming

Known local-dev quirks (both verified harmless against the emulator, neither
affects the real BigQuery sink used once deployed to GCP in Phase 2):
  - The text sink's shard files only get moved out of `<path>/.temp*/` into
    their final location once the pipeline shuts down cleanly (Ctrl+C). This
    is a `fileio.WriteToFiles` + classic DirectRunner finalization quirk, not
    a data-correctness issue - the content of the (correctly windowed and
    triggered) panes is already fully written to the temp shard files.
  - The classic DirectRunner's Pub/Sub reader polls with a 30s blocking
    `pull()`; the local emulator raises DeadlineExceeded instead of
    returning an empty response when idle, so you'll see a periodic,
    self-recovering DeadlineExceeded traceback in the logs whenever there is
    no new data. Harmless.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import apache_beam as beam
from apache_beam import window
from apache_beam.io import fileio

from taxipulse_pipeline.io.pubsub_io import read_trip_events_from_pubsub
from taxipulse_pipeline.options import TaxiPulseOptions
from taxipulse_pipeline.transforms.anomaly import detect_demand_spikes
from taxipulse_pipeline.transforms.dedup import deduplicate_by_trip_id
from taxipulse_pipeline.transforms.parsing import parse_with_dead_letter
from taxipulse_pipeline.transforms.windowing import (
    AddWindowBounds,
    AssignEventTimestamp,
    window_and_aggregate_by_zone,
)

logger = logging.getLogger(__name__)


def load_historical_avg_by_zone(path: str | None) -> dict[int, float]:
    if not path:
        return {}
    data = json.loads(Path(path).read_text())
    return {int(zone_id): float(avg) for zone_id, avg in data.items()}


def build_pipeline(pipeline: beam.Pipeline, options: TaxiPulseOptions) -> None:
    opts = options.view_as(TaxiPulseOptions)

    raw_messages = read_trip_events_from_pubsub(pipeline, opts.input_subscription)
    valid_events, dead_letters = parse_with_dead_letter(raw_messages)

    timestamped = valid_events | "AssignEventTimestamp" >> beam.ParDo(AssignEventTimestamp())
    deduped = deduplicate_by_trip_id(timestamped)

    zone_aggregates = window_and_aggregate_by_zone(
        deduped,
        window_size_seconds=opts.window_size_seconds,
        window_period_seconds=opts.window_period_seconds,
        allowed_lateness_seconds=opts.allowed_lateness_seconds,
    )
    zone_aggregates = zone_aggregates | "AddWindowBounds" >> beam.ParDo(AddWindowBounds())

    historical_avg_by_zone = load_historical_avg_by_zone(opts.historical_avg_path)
    enriched = detect_demand_spikes(
        zone_aggregates,
        beam.pvalue.AsDict(
            pipeline | "HistoricalAvgSideInput" >> beam.Create(list(historical_avg_by_zone.items()))
        ),
        spike_ratio_threshold=opts.spike_ratio_threshold,
    )

    if opts.output_sink == "bigquery":
        from taxipulse_pipeline.io.bigquery_io import (
            write_dead_letters_to_bigquery,
            write_zone_aggregates_to_bigquery,
        )

        if not opts.output_table:
            raise ValueError("--output_table is required when --output_sink=bigquery")
        write_zone_aggregates_to_bigquery(enriched, opts.output_table)

        dead_letter_records = dead_letters | "FormatDeadLetters" >> beam.Map(
            lambda pair: {"raw_payload": pair[0].decode("utf-8", errors="replace"), "error_message": pair[1]}
        )
        if opts.dead_letter_output:
            write_dead_letters_to_bigquery(dead_letter_records, opts.dead_letter_output)
    else:
        # WriteToText is a batch-oriented sink: on an unbounded PCollection it
        # needs a periodic trigger to know when to flush a shard.
        # `zone_aggregates`/`enriched` already have one (the sliding-window
        # trigger from window_and_aggregate_by_zone), so fileio.WriteToFiles
        # can key off it directly.
        (
            enriched
            | "FormatAggregatesAsJson" >> beam.Map(json.dumps)
            | "WriteAggregatesToText"
            >> fileio.WriteToFiles(
                path=opts.output_path,
                sink=fileio.TextSink(),
                file_naming=fileio.destination_prefix_naming(suffix=".jsonl"),
            )
        )
        if opts.dead_letter_output:
            (
                dead_letters
                | "FormatDeadLettersAsJson"
                >> beam.Map(
                    lambda pair: json.dumps(
                        {"raw_payload": pair[0].decode("utf-8", errors="replace"), "error_message": pair[1]}
                    )
                )
                # dead_letters has no meaningful event-time windowing of its
                # own (it comes straight off the Pub/Sub read) - give it a
                # simple periodic window purely so the file sink has
                # something to trigger a flush on.
                | "WindowDeadLetters" >> beam.WindowInto(window.FixedWindows(60))
                | "WriteDeadLettersToText"
                >> fileio.WriteToFiles(
                    path=opts.dead_letter_output,
                    sink=fileio.TextSink(),
                    file_naming=fileio.destination_prefix_naming(suffix=".jsonl"),
                )
            )


def run(argv: list[str] | None = None) -> None:
    options = TaxiPulseOptions(argv)
    with beam.Pipeline(options=options) as pipeline:
        build_pipeline(pipeline, options)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
