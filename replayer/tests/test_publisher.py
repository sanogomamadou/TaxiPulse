import json

from taxipulse_common.trip_event import TripEvent
from taxipulse_replayer.publisher import TripEventPublisher

SAMPLE_EVENT = TripEvent.from_dict(
    {
        "trip_id": "abc-123",
        "vendor_id": 1,
        "pickup_datetime": "2024-01-01T08:00:00",
        "dropoff_datetime": "2024-01-01T08:10:00",
        "pickup_location_id": 142,
        "dropoff_location_id": 236,
        "passenger_count": 1,
        "trip_distance": 2.5,
        "fare_amount": 12.0,
        "tip_amount": 2.0,
        "total_amount": 15.5,
        "payment_type": 1,
    }
)


class FakeBatch:
    """Stands in for azure.eventhub.EventDataBatch."""

    def __init__(self) -> None:
        self.events: list = []

    def add(self, event_data) -> None:
        self.events.append(event_data)


class FakeEventHubProducerClient:
    """Stands in for azure.eventhub.EventHubProducerClient so tests never
    hit the network or require an emulator."""

    def __init__(self) -> None:
        self.sent_batches: list[FakeBatch] = []
        self.closed = False

    def create_batch(self) -> FakeBatch:
        return FakeBatch()

    def send_batch(self, batch: FakeBatch) -> None:
        self.sent_batches.append(batch)

    def close(self) -> None:
        self.closed = True


def test_publish_sends_json_encoded_event_with_trip_id_property():
    client = FakeEventHubProducerClient()
    publisher = TripEventPublisher(client)

    publisher.publish(SAMPLE_EVENT)

    assert len(client.sent_batches) == 1
    (sent_event,) = client.sent_batches[0].events
    assert sent_event.properties == {"trip_id": "abc-123"}
    assert json.loads(sent_event.body_as_str())["trip_id"] == "abc-123"


def test_publish_multiple_events_sends_one_batch_each():
    client = FakeEventHubProducerClient()
    publisher = TripEventPublisher(client)

    publisher.publish(SAMPLE_EVENT)
    publisher.publish(SAMPLE_EVENT)

    assert len(client.sent_batches) == 2


def test_close_closes_the_underlying_client():
    client = FakeEventHubProducerClient()
    publisher = TripEventPublisher(client)

    publisher.close()

    assert client.closed is True
