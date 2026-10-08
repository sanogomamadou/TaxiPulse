"""Pydantic response models - field names/types mirror the warehouse
marts' actual Delta schemas (see warehouse/src/taxipulse_warehouse/{zones,
marts,forecast}.py), not re-derived or renamed, so a schema change there
is immediately visible here rather than silently drifting."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Zone(BaseModel):
    location_id: int
    borough: str | None
    zone_name: str | None
    service_zone: str | None
    centroid_lat: float | None
    centroid_lon: float | None


class ZoneDemand(BaseModel):
    period_start: datetime
    pickup_location_id: int
    trip_count: int
    total_revenue: float
    avg_duration_seconds: float | None
    avg_speed_mph: float | None
    borough: str | None
    zone_name: str | None


class ZoneForecast(BaseModel):
    pickup_location_id: str
    forecast_timestamp: datetime
    predicted_trip_count: float
    predicted_lower: float
    predicted_upper: float
    mae: float | None
    mape: float | None


class ZoneAggregate(BaseModel):
    window_start: datetime
    window_end: datetime
    pickup_location_id: int
    trip_count: int
    total_revenue: float
    avg_duration_seconds: float | None
    avg_speed_mph: float | None
    historical_avg_trip_count: float | None
    spike_ratio: float | None
    is_spike: bool
