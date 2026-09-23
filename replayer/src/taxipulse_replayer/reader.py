"""Reads NYC TLC Parquet trip files and turns rows into chronologically
sorted TripEvent objects ready to be replayed."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path

import pandas as pd

from taxipulse_common.trip_event import TripEvent, TripEventValidationError

# Maps canonical TripEvent fields to the possible TLC source column names
# (yellow and green taxi datasets use slightly different names).
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "vendor_id": ("VendorID",),
    "pickup_datetime": ("tpep_pickup_datetime", "lpep_pickup_datetime"),
    "dropoff_datetime": ("tpep_dropoff_datetime", "lpep_dropoff_datetime"),
    "pickup_location_id": ("PULocationID",),
    "dropoff_location_id": ("DOLocationID",),
    "passenger_count": ("passenger_count",),
    "trip_distance": ("trip_distance",),
    "fare_amount": ("fare_amount",),
    "tip_amount": ("tip_amount",),
    "total_amount": ("total_amount",),
    "payment_type": ("payment_type",),
}


def _resolve_column(df_columns: list[str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in df_columns:
            return candidate
    return None


def load_trips(parquet_path: Path) -> pd.DataFrame:
    """Load a TLC Parquet file and normalize it to canonical column names,
    sorted chronologically by pickup time."""
    df = pd.read_parquet(parquet_path)
    columns = list(df.columns)

    rename_map: dict[str, str] = {}
    for canonical, candidates in COLUMN_ALIASES.items():
        source = _resolve_column(columns, candidates)
        if source is None:
            raise ValueError(f"could not find a source column for '{canonical}' in {parquet_path}")
        rename_map[source] = canonical

    normalized = df.rename(columns=rename_map)[list(COLUMN_ALIASES.keys())].copy()
    normalized["pickup_datetime"] = pd.to_datetime(normalized["pickup_datetime"])
    normalized["dropoff_datetime"] = pd.to_datetime(normalized["dropoff_datetime"])
    return normalized.sort_values("pickup_datetime").reset_index(drop=True)


def _safe_int(value: object, default: int) -> int:
    """TLC source rows sometimes have NaN in nullable integer-ish columns
    (e.g. passenger_count, payment_type); fall back to a default instead of
    letting NaN propagate into TripEvent validation."""
    if value is None or pd.isna(value):
        return default
    return int(value)


def iter_trip_events(df: pd.DataFrame) -> Iterator[TripEvent]:
    """Turn a normalized trips DataFrame into TripEvent objects, in
    chronological order. Rows that fail validation (e.g. negative fares,
    dropoff before pickup) are skipped - the source data is not perfectly
    clean, and that is a data-quality concern separate from the pipeline's
    own dead-letter handling of malformed *wire* payloads."""
    for row in df.itertuples(index=False):
        if pd.isna(row.trip_distance) or pd.isna(row.fare_amount) or pd.isna(row.total_amount):
            continue
        payload = {
            "trip_id": str(uuid.uuid4()),
            "vendor_id": _safe_int(row.vendor_id, default=0),
            "pickup_datetime": row.pickup_datetime.isoformat(),
            "dropoff_datetime": row.dropoff_datetime.isoformat(),
            "pickup_location_id": _safe_int(row.pickup_location_id, default=0),
            "dropoff_location_id": _safe_int(row.dropoff_location_id, default=0),
            "passenger_count": _safe_int(row.passenger_count, default=1),
            "trip_distance": row.trip_distance,
            "fare_amount": row.fare_amount,
            "tip_amount": row.tip_amount,
            "total_amount": row.total_amount,
            "payment_type": _safe_int(row.payment_type, default=0),
        }
        try:
            yield TripEvent.from_dict(payload)
        except TripEventValidationError:
            continue
