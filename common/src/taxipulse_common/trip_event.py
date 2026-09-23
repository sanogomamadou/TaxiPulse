"""Canonical schema for a taxi trip event.

This is the single source of truth for the "wire format" exchanged between
the replayer (producer) and the Beam pipeline (consumer) over Pub/Sub, so the
two components can never drift apart on field names or types.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

# NYC TLC pickup/dropoff timestamps have no timezone information in the
# source Parquet files. We treat them as-is (naive, source local time) rather
# than assuming a timezone - a production system would localize them to
# America/New_York using the historical UTC offset for each trip's date.
REQUIRED_FIELDS = (
    "trip_id",
    "vendor_id",
    "pickup_datetime",
    "dropoff_datetime",
    "pickup_location_id",
    "dropoff_location_id",
    "trip_distance",
    "fare_amount",
    "total_amount",
)


class TripEventValidationError(ValueError):
    """Raised when a raw payload cannot be turned into a valid TripEvent."""


@dataclass(frozen=True, slots=True)
class TripEvent:
    trip_id: str
    vendor_id: int
    pickup_datetime: str  # ISO 8601, naive (TLC source local time)
    dropoff_datetime: str  # ISO 8601, naive (TLC source local time)
    pickup_location_id: int
    dropoff_location_id: int
    passenger_count: int
    trip_distance: float
    fare_amount: float
    tip_amount: float
    total_amount: float
    payment_type: int
    publish_time: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> TripEvent:
        missing = [f for f in REQUIRED_FIELDS if payload.get(f) in (None, "")]
        if missing:
            raise TripEventValidationError(f"missing required fields: {missing}")

        try:
            pickup = datetime.fromisoformat(str(payload["pickup_datetime"]))
            dropoff = datetime.fromisoformat(str(payload["dropoff_datetime"]))
        except ValueError as exc:
            raise TripEventValidationError(f"invalid datetime: {exc}") from exc

        if dropoff < pickup:
            raise TripEventValidationError("dropoff_datetime is before pickup_datetime")

        try:
            trip_distance = float(payload["trip_distance"])
            fare_amount = float(payload["fare_amount"])
            total_amount = float(payload["total_amount"])
        except (TypeError, ValueError) as exc:
            raise TripEventValidationError(f"invalid numeric field: {exc}") from exc

        if trip_distance < 0 or fare_amount < 0 or total_amount < 0:
            raise TripEventValidationError("negative distance/fare/total is not allowed")

        try:
            vendor_id = int(payload["vendor_id"])
            pickup_location_id = int(payload["pickup_location_id"])
            dropoff_location_id = int(payload["dropoff_location_id"])
        except (TypeError, ValueError) as exc:
            raise TripEventValidationError(f"invalid id field: {exc}") from exc

        return cls(
            trip_id=str(payload["trip_id"]),
            vendor_id=vendor_id,
            pickup_datetime=pickup.isoformat(),
            dropoff_datetime=dropoff.isoformat(),
            pickup_location_id=pickup_location_id,
            dropoff_location_id=dropoff_location_id,
            passenger_count=int(payload.get("passenger_count") or 1),
            trip_distance=trip_distance,
            fare_amount=fare_amount,
            tip_amount=float(payload.get("tip_amount") or 0.0),
            total_amount=total_amount,
            payment_type=int(payload.get("payment_type") or 0),
            publish_time=(
                str(payload["publish_time"])
                if payload.get("publish_time")
                else datetime.now(UTC).isoformat()
            ),
        )

    @classmethod
    def from_json(cls, raw: bytes | str) -> TripEvent:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TripEventValidationError(f"invalid JSON: {exc}") from exc
        return cls.from_dict(payload)
