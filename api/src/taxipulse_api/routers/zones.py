from __future__ import annotations

from enum import StrEnum

from fastapi import APIRouter, HTTPException, Query

from taxipulse_api.config import Settings, get_settings
from taxipulse_api.schemas import Zone, ZoneAggregate, ZoneDemand, ZoneForecast
from taxipulse_api.services import warehouse

router = APIRouter(prefix="/zones", tags=["zones"])


class DemandBucket(StrEnum):
    hourly = "hourly"
    daily = "daily"


class TopZonesMetric(StrEnum):
    trip_count = "trip_count"
    total_revenue = "total_revenue"


def _demand_path(settings: Settings, bucket: DemandBucket) -> str:
    return (
        settings.zone_demand_hourly_path
        if bucket == DemandBucket.hourly
        else settings.zone_demand_daily_path
    )


@router.get("", response_model=list[Zone])
def list_zones() -> list[dict]:
    settings = get_settings()
    return warehouse.list_zones(settings.stg_taxi_zones_path)


@router.get("/top", response_model=list[dict])
def top_zones(
    bucket: DemandBucket = DemandBucket.hourly,
    metric: TopZonesMetric = TopZonesMetric.trip_count,
    limit: int = Query(default=10, ge=1, le=100),
) -> list[dict]:
    settings = get_settings()
    path = _demand_path(settings, bucket)
    return warehouse.get_top_zones(path, metric.value, limit)


@router.get("/spikes", response_model=list[ZoneAggregate])
def latest_spikes(limit: int = Query(default=20, ge=1, le=200)) -> list[dict]:
    """Reads the streaming pipeline's zone_aggregates output (pipeline/,
    not warehouse/) - empty unless that pipeline has actually been run,
    since there's no continuously-running cloud streaming job for this
    portfolio project."""
    settings = get_settings()
    return warehouse.get_latest_spikes(settings.zone_aggregates_path, limit)


@router.get("/{location_id}", response_model=Zone)
def get_zone(location_id: int) -> dict:
    settings = get_settings()
    zone = warehouse.get_zone(settings.stg_taxi_zones_path, location_id)
    if zone is None:
        raise HTTPException(status_code=404, detail=f"zone {location_id} not found")
    return zone


@router.get("/{location_id}/demand", response_model=list[ZoneDemand])
def get_zone_demand(
    location_id: int,
    bucket: DemandBucket = DemandBucket.hourly,
    limit: int = Query(default=24, ge=1, le=500),
) -> list[dict]:
    settings = get_settings()
    path = _demand_path(settings, bucket)
    return warehouse.get_zone_demand(path, location_id, limit)


@router.get("/{location_id}/forecast", response_model=list[ZoneForecast])
def get_zone_forecast(
    location_id: int, limit: int = Query(default=24, ge=1, le=500)
) -> list[dict]:
    settings = get_settings()
    return warehouse.get_zone_forecast(settings.demand_forecast_path, location_id, limit)
