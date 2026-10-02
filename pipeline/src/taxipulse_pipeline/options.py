"""CLI options for the TaxiPulse Spark pipeline."""

from __future__ import annotations

import argparse


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TaxiPulse streaming pipeline (PySpark)")
    parser.add_argument(
        "--bootstrap-servers",
        required=True,
        help="Event Hubs Kafka endpoint, e.g. localhost:9092 (emulator) or "
        "<namespace>.servicebus.windows.net:9093 (real Azure)",
    )
    parser.add_argument("--eventhub-name", default="taxi-trips")
    parser.add_argument(
        "--connection-string",
        default=None,
        help="Event Hubs namespace connection string. Omit for the local emulator "
        "(unauthenticated); required against real Azure Event Hubs.",
    )
    parser.add_argument(
        "--output-path",
        default="output/zone_aggregates",
        help="Delta table path for zone aggregates (local dir or abfss:// URL).",
    )
    parser.add_argument(
        "--dead-letter-path",
        default="output/dead_letters",
        help="Delta table path for dead-lettered messages.",
    )
    parser.add_argument(
        "--checkpoint-path",
        default="output/_checkpoints",
        help="Base path for Spark Structured Streaming checkpoints.",
    )
    parser.add_argument("--window-duration", default="5 minutes")
    parser.add_argument("--slide-duration", default="1 minute")
    parser.add_argument("--watermark-delay", default="2 minutes")
    parser.add_argument("--spike-ratio-threshold", type=float, default=1.5)
    parser.add_argument(
        "--historical-avg-path",
        default=None,
        help="Path to a local JSON file mapping zone_id -> historical average trip "
        "count per window, used as the spike-detection baseline. Until the "
        "Lakehouse marts/forecast baseline exists (Phase 3), omitting this means "
        "no zone is ever flagged as a spike.",
    )
    return parser.parse_args(argv)
