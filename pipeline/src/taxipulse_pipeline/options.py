"""Custom PipelineOptions for the TaxiPulse streaming pipeline."""

from __future__ import annotations

from apache_beam.options.pipeline_options import PipelineOptions


class TaxiPulseOptions(PipelineOptions):
    @classmethod
    def _add_argparse_args(cls, parser) -> None:
        parser.add_argument(
            "--input_subscription",
            required=True,
            help="Pub/Sub subscription to read trip events from, e.g. "
            "projects/<project>/subscriptions/taxi-trips-sub",
        )
        parser.add_argument(
            "--dead_letter_output",
            default=None,
            help="Path prefix (local dev) to write dead-lettered raw messages to. "
            "If omitted, invalid messages are only logged.",
        )
        parser.add_argument(
            "--output_sink",
            choices=["text", "bigquery"],
            default="text",
            help="Where to write zone aggregates: 'text' for local dev (DirectRunner), "
            "'bigquery' once deployed to GCP (Phase 2).",
        )
        parser.add_argument(
            "--output_path",
            default="output/zone_aggregates",
            help="Path prefix used when --output_sink=text.",
        )
        parser.add_argument(
            "--output_table",
            default=None,
            help="BigQuery table (project:dataset.table) used when --output_sink=bigquery.",
        )
        parser.add_argument("--window_size_seconds", type=int, default=300)
        parser.add_argument("--window_period_seconds", type=int, default=60)
        parser.add_argument("--allowed_lateness_seconds", type=int, default=120)
        parser.add_argument(
            "--spike_ratio_threshold",
            type=float,
            default=1.5,
            help="A zone's trip_count / historical_avg_trip_count ratio at or above "
            "this value is flagged as a demand spike.",
        )
        parser.add_argument(
            "--historical_avg_path",
            default=None,
            help="Path to a local JSON file mapping zone_id -> historical average trip "
            "count per window, used as the spike-detection baseline. Until the "
            "BigQuery marts/BQML baseline exists (Phase 3), omitting this means no "
            "zone is ever flagged as a spike.",
        )
