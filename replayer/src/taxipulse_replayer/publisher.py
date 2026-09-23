"""Publishes TripEvent objects to a Pub/Sub topic, transparently targeting
either real GCP Pub/Sub or a local emulator."""

from __future__ import annotations

import logging
import os

from google.api_core.exceptions import GoogleAPIError
from google.cloud import pubsub_v1

from taxipulse_common.trip_event import TripEvent

from .config import ReplayerConfig

logger = logging.getLogger(__name__)


def build_publisher_client(config: ReplayerConfig) -> pubsub_v1.PublisherClient:
    if config.emulator_host:
        # google-cloud-pubsub reads PUBSUB_EMULATOR_HOST from the environment
        # and automatically switches to an insecure, unauthenticated channel
        # pointed at that host - no credentials needed against the emulator.
        os.environ["PUBSUB_EMULATOR_HOST"] = config.emulator_host
    return pubsub_v1.PublisherClient()


class TripEventPublisher:
    """Thin wrapper around the Pub/Sub client for publishing TripEvents as
    JSON, with the trip_id attached as a message attribute for observability
    (e.g. filtering/inspecting messages in the emulator or console)."""

    def __init__(self, client: pubsub_v1.PublisherClient, project_id: str, topic: str) -> None:
        self._client = client
        self._topic_path = client.topic_path(project_id, topic)

    def publish(self, event: TripEvent, timeout: float = 30.0) -> str:
        data = event.to_json().encode("utf-8")
        future = self._client.publish(self._topic_path, data=data, trip_id=event.trip_id)
        try:
            return future.result(timeout=timeout)
        except GoogleAPIError:
            logger.exception("failed to publish trip_id=%s", event.trip_id)
            raise
