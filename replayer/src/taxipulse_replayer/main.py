"""CLI entry point for the replayer: reads a TLC sample, replays it in
chronological order (sped up, and optionally with chaos injection), and
publishes each trip as an event to Pub/Sub.

Example:
    python -m taxipulse_replayer.main data/sample/yellow_tripdata_2024-01_sample.parquet \
        --speedup 600 --duplicate-ratio 0.02 --late-ratio 0.05
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .chaos import inject_duplicates, inject_late_events
from .config import ReplayerConfig
from .publisher import TripEventPublisher, build_publisher_client
from .reader import iter_trip_events, load_trips
from .scheduler import pace_events

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample_path", type=Path, help="Path to a TLC sample Parquet file")
    parser.add_argument("--speedup", type=float, default=None, help="Override REPLAYER_SPEEDUP_FACTOR")
    parser.add_argument("--late-ratio", type=float, default=None, help="Override REPLAYER_INJECT_LATE_RATIO")
    parser.add_argument(
        "--duplicate-ratio", type=float, default=None, help="Override REPLAYER_INJECT_DUPLICATE_RATIO"
    )
    parser.add_argument("--limit", type=int, default=None, help="Only replay the first N trips")
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    config = ReplayerConfig.from_env()
    speedup = args.speedup if args.speedup is not None else config.speedup_factor
    late_ratio = args.late_ratio if args.late_ratio is not None else config.inject_late_ratio
    duplicate_ratio = (
        args.duplicate_ratio if args.duplicate_ratio is not None else config.inject_duplicate_ratio
    )

    df = load_trips(args.sample_path)
    if args.limit:
        df = df.head(args.limit)
    logger.info("loaded %d trips from %s", len(df), args.sample_path)

    events = iter_trip_events(df)
    events = inject_late_events(events, late_ratio)
    events = pace_events(events, speedup)
    events = inject_duplicates(events, duplicate_ratio)

    client = build_publisher_client(config)
    publisher = TripEventPublisher(client, config.project_id, config.topic)

    published = 0
    for event in events:
        publisher.publish(event)
        published += 1
        if published % 100 == 0:
            logger.info("published %d trips", published)

    logger.info("done: published %d trips to topic '%s'", published, config.topic)
    return published


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
