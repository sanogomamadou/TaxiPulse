"""Publishes TripEvent objects to an Azure Event Hub, transparently
targeting either a real Event Hubs namespace or a local emulator (both are
reached the same way: a connection string)."""

from __future__ import annotations

import logging

from azure.eventhub import EventData, EventHubProducerClient
from azure.eventhub.exceptions import EventHubError

from taxipulse_common.trip_event import TripEvent

from .config import ReplayerConfig

logger = logging.getLogger(__name__)


def build_publisher_client(config: ReplayerConfig) -> EventHubProducerClient:
    return EventHubProducerClient.from_connection_string(
        conn_str=config.eventhub_connection_string,
        eventhub_name=config.eventhub_name,
    )


class TripEventPublisher:
    """Thin wrapper around the Event Hubs producer client for publishing
    TripEvents as JSON, with the trip_id attached as an application
    property for observability."""

    def __init__(self, client: EventHubProducerClient) -> None:
        self._client = client

    def publish(self, event: TripEvent) -> None:
        event_data = EventData(event.to_json())
        event_data.properties = {"trip_id": event.trip_id}
        try:
            batch = self._client.create_batch()
            batch.add(event_data)
            self._client.send_batch(batch)
        except EventHubError:
            logger.exception("failed to publish trip_id=%s", event.trip_id)
            raise

    def close(self) -> None:
        self._client.close()
