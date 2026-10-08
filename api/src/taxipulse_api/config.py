"""Runtime configuration for the serving API - just the Delta table paths
it reads from, all relative to one configurable warehouse output root so
a single env var repoints every endpoint at once (a different local run,
or eventually an abfss:// path once deployed)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    warehouse_output: str
    pipeline_output: str

    @property
    def stg_taxi_zones_path(self) -> str:
        return f"{self.warehouse_output}/staging/stg_taxi_zones"

    @property
    def zone_demand_hourly_path(self) -> str:
        return f"{self.warehouse_output}/marts/zone_demand_hourly"

    @property
    def zone_demand_daily_path(self) -> str:
        return f"{self.warehouse_output}/marts/zone_demand_daily"

    @property
    def demand_forecast_path(self) -> str:
        return f"{self.warehouse_output}/marts/demand_forecast"

    @property
    def zone_aggregates_path(self) -> str:
        return f"{self.pipeline_output}/zone_aggregates"


def get_settings() -> Settings:
    return Settings(
        warehouse_output=os.environ.get("TAXIPULSE_WAREHOUSE_OUTPUT", "warehouse_output"),
        pipeline_output=os.environ.get("TAXIPULSE_PIPELINE_OUTPUT", "output"),
    )
