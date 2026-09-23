"""Pub/Sub read side of the pipeline."""

from __future__ import annotations

import apache_beam as beam
from apache_beam.io import ReadFromPubSub


def read_trip_events_from_pubsub(pipeline: beam.Pipeline, subscription: str) -> beam.PCollection:
    """Reads raw message bytes from a Pub/Sub subscription. Timestamps are
    NOT taken from Pub/Sub publish time here - `AssignEventTimestamp`
    (transforms/windowing.py) reassigns them from each trip's pickup time
    right after parsing, since that is what the windowing logic must react
    to for the replayer's compressed timeline to make sense."""
    return pipeline | "ReadFromPubSub" >> ReadFromPubSub(subscription=subscription)
