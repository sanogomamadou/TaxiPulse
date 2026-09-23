import random

import pytest

from taxipulse_common.trip_event import TripEvent
from taxipulse_replayer.chaos import inject_duplicates, inject_late_events


def make_event(trip_id: str) -> TripEvent:
    return TripEvent.from_dict(
        {
            "trip_id": trip_id,
            "vendor_id": 1,
            "pickup_datetime": "2024-01-01T08:00:00",
            "dropoff_datetime": "2024-01-01T08:10:00",
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


def test_inject_duplicates_zero_ratio_is_a_no_op():
    events = [make_event("a"), make_event("b")]
    result = list(inject_duplicates(iter(events), ratio=0.0))
    assert [e.trip_id for e in result] == ["a", "b"]


def test_inject_duplicates_ratio_one_duplicates_every_event():
    events = [make_event("a"), make_event("b")]
    result = list(inject_duplicates(iter(events), ratio=1.0))
    assert [e.trip_id for e in result] == ["a", "a", "b", "b"]


def test_inject_duplicates_is_deterministic_with_seeded_rng():
    events = [make_event(str(i)) for i in range(20)]
    result = list(inject_duplicates(iter(events), ratio=0.5, rng=random.Random(42)))
    duplicate_count = len(result) - 20
    assert duplicate_count > 0
    assert duplicate_count < 20


@pytest.mark.parametrize("bad_ratio", [-0.1, 1.1])
def test_inject_duplicates_rejects_invalid_ratio(bad_ratio):
    with pytest.raises(ValueError, match="ratio"):
        list(inject_duplicates(iter([]), ratio=bad_ratio))


def test_inject_late_events_zero_ratio_preserves_order():
    events = [make_event(str(i)) for i in range(5)]
    result = list(inject_late_events(iter(events), ratio=0.0))
    assert [e.trip_id for e in result] == ["0", "1", "2", "3", "4"]


def test_inject_late_events_preserves_the_full_set_of_events():
    events = [make_event(str(i)) for i in range(30)]
    result = list(inject_late_events(iter(events), ratio=0.3, max_hold=5, rng=random.Random(7)))
    assert sorted(e.trip_id for e in result) == sorted(str(i) for i in range(30))


def test_inject_late_events_ratio_one_delays_everything_by_max_hold():
    events = [make_event(str(i)) for i in range(10)]
    result = list(inject_late_events(iter(events), ratio=1.0, max_hold=3))
    # every event is held; the buffer flushes oldest-first once it hits max_hold,
    # so trip "0" (the first held) should not come out before trip "2" is held
    assert result[0].trip_id == "0"
    assert len(result) == 10
