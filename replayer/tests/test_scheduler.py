import pytest

from taxipulse_common.trip_event import TripEvent
from taxipulse_replayer.scheduler import pace_events


def make_event(trip_id: str, pickup_iso: str) -> TripEvent:
    return TripEvent.from_dict(
        {
            "trip_id": trip_id,
            "vendor_id": 1,
            "pickup_datetime": pickup_iso,
            "dropoff_datetime": pickup_iso,
            "pickup_location_id": 1,
            "dropoff_location_id": 2,
            "passenger_count": 1,
            "trip_distance": 1.0,
            "fare_amount": 5.0,
            "tip_amount": 0.0,
            "total_amount": 5.0,
            "payment_type": 1,
        }
    )


def test_pace_events_first_event_has_no_wait():
    events = [make_event("a", "2024-01-01T08:00:00")]
    sleeps: list[float] = []

    result = list(pace_events(events, speedup_factor=1, sleep_fn=sleeps.append))

    assert [e.trip_id for e in result] == ["a"]
    assert sleeps == []


def test_pace_events_waits_scaled_delta_between_events():
    events = [
        make_event("a", "2024-01-01T08:00:00"),
        make_event("b", "2024-01-01T08:01:00"),  # 60s later
    ]
    sleeps: list[float] = []

    list(pace_events(events, speedup_factor=60, sleep_fn=sleeps.append))

    assert sleeps == [1.0]  # 60s / speedup 60 = 1s


def test_pace_events_clamps_negative_delta_to_zero_wait():
    events = [
        make_event("a", "2024-01-01T08:01:00"),
        make_event("b", "2024-01-01T08:00:00"),  # earlier than "a"
    ]
    sleeps: list[float] = []

    list(pace_events(events, speedup_factor=1, sleep_fn=sleeps.append))

    assert sleeps == []


def test_pace_events_preserves_event_order_and_count():
    events = [
        make_event("a", "2024-01-01T08:00:00"),
        make_event("b", "2024-01-01T08:00:30"),
        make_event("c", "2024-01-01T08:01:00"),
    ]

    result = list(pace_events(events, speedup_factor=600, sleep_fn=lambda _: None))

    assert [e.trip_id for e in result] == ["a", "b", "c"]


def test_pace_events_rejects_non_positive_speedup():
    with pytest.raises(ValueError, match="speedup_factor"):
        list(pace_events([], speedup_factor=0, sleep_fn=lambda _: None))
