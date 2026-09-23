import json

import pytest

from taxipulse_common.trip_event import TripEvent, TripEventValidationError

VALID_PAYLOAD = {
    "trip_id": "abc-123",
    "vendor_id": 1,
    "pickup_datetime": "2024-01-01T08:00:00",
    "dropoff_datetime": "2024-01-01T08:15:00",
    "pickup_location_id": 142,
    "dropoff_location_id": 236,
    "passenger_count": 1,
    "trip_distance": 2.5,
    "fare_amount": 12.0,
    "tip_amount": 2.0,
    "total_amount": 15.5,
    "payment_type": 1,
}


def test_from_dict_valid_payload_round_trips_through_json():
    event = TripEvent.from_dict(VALID_PAYLOAD)
    assert event.trip_id == "abc-123"
    assert event.pickup_location_id == 142

    reparsed = TripEvent.from_json(event.to_json())
    assert reparsed.trip_id == event.trip_id
    assert reparsed.total_amount == event.total_amount


def test_from_json_invalid_json_raises():
    with pytest.raises(TripEventValidationError, match="invalid JSON"):
        TripEvent.from_json(b"not json")


@pytest.mark.parametrize("missing_field", ["trip_id", "pickup_datetime", "total_amount"])
def test_from_dict_missing_required_field_raises(missing_field):
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != missing_field}
    with pytest.raises(TripEventValidationError, match="missing required fields"):
        TripEvent.from_dict(payload)


def test_from_dict_dropoff_before_pickup_raises():
    payload = {**VALID_PAYLOAD, "dropoff_datetime": "2024-01-01T07:00:00"}
    with pytest.raises(TripEventValidationError, match="dropoff_datetime is before pickup_datetime"):
        TripEvent.from_dict(payload)


@pytest.mark.parametrize("field_name", ["trip_distance", "fare_amount", "total_amount"])
def test_from_dict_negative_amount_raises(field_name):
    payload = {**VALID_PAYLOAD, field_name: -1}
    with pytest.raises(TripEventValidationError, match="negative"):
        TripEvent.from_dict(payload)


def test_from_dict_invalid_datetime_raises():
    payload = {**VALID_PAYLOAD, "pickup_datetime": "not-a-date"}
    with pytest.raises(TripEventValidationError, match="invalid datetime"):
        TripEvent.from_dict(payload)


def test_from_dict_defaults_passenger_count_and_tip_amount():
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k not in ("passenger_count", "tip_amount")}
    event = TripEvent.from_dict(payload)
    assert event.passenger_count == 1
    assert event.tip_amount == 0.0


def test_to_json_is_valid_json():
    event = TripEvent.from_dict(VALID_PAYLOAD)
    parsed = json.loads(event.to_json())
    assert parsed["trip_id"] == "abc-123"
