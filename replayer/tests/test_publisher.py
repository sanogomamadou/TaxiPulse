import json
import os

from taxipulse_common.trip_event import TripEvent
from taxipulse_replayer.config import ReplayerConfig
from taxipulse_replayer.publisher import TripEventPublisher, build_publisher_client

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


class FakeFuture:
    def __init__(self, message_id: str) -> None:
        self._message_id = message_id

    def result(self, timeout: float | None = None) -> str:
        return self._message_id


class FakePublisherClient:
    """Stands in for google.cloud.pubsub_v1.PublisherClient so tests never
    hit the network or require an emulator."""

    def __init__(self) -> None:
        self.published: list[dict] = []

    def topic_path(self, project_id: str, topic: str) -> str:
        return f"projects/{project_id}/topics/{topic}"

    def publish(self, topic_path: str, data: bytes, **attributes: str) -> FakeFuture:
        self.published.append({"topic_path": topic_path, "data": data, "attributes": attributes})
        return FakeFuture(message_id=f"msg-{len(self.published)}")


def test_publish_sends_json_encoded_event_with_trip_id_attribute():
    client = FakePublisherClient()
    publisher = TripEventPublisher(client, project_id="taxipulse-mds", topic="taxi-trips")

    message_id = publisher.publish(SAMPLE_EVENT)

    assert message_id == "msg-1"
    assert len(client.published) == 1
    sent = client.published[0]
    assert sent["topic_path"] == "projects/taxipulse-mds/topics/taxi-trips"
    assert sent["attributes"] == {"trip_id": "abc-123"}
    assert json.loads(sent["data"])["trip_id"] == "abc-123"


def test_build_publisher_client_sets_emulator_host_env_var(monkeypatch):
    monkeypatch.delenv("PUBSUB_EMULATOR_HOST", raising=False)
    config = ReplayerConfig(
        project_id="taxipulse-mds",
        topic="taxi-trips",
        speedup_factor=60,
        inject_late_ratio=0.0,
        inject_duplicate_ratio=0.0,
        emulator_host="localhost:8085",
    )

    build_publisher_client(config)

    assert os.environ["PUBSUB_EMULATOR_HOST"] == "localhost:8085"
