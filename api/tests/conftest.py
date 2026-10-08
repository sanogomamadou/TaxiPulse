from datetime import UTC, datetime

import pandas as pd
import pytest
from deltalake import write_deltalake
from fastapi.testclient import TestClient


@pytest.fixture
def warehouse_root(tmp_path, monkeypatch):
    monkeypatch.setenv("TAXIPULSE_WAREHOUSE_OUTPUT", str(tmp_path / "warehouse_output"))
    monkeypatch.setenv("TAXIPULSE_PIPELINE_OUTPUT", str(tmp_path / "output"))
    return tmp_path


@pytest.fixture
def seeded_warehouse(warehouse_root):
    zones = pd.DataFrame(
        [
            {
                "location_id": 100,
                "borough": "Manhattan",
                "zone_name": "Midtown",
                "service_zone": "Yellow Zone",
                "centroid_lat": 40.75,
                "centroid_lon": -73.98,
            },
            {
                "location_id": 200,
                "borough": "Queens",
                "zone_name": "Jamaica",
                "service_zone": "Boro Zone",
                "centroid_lat": 40.70,
                "centroid_lon": -73.80,
            },
            # Real TLC zone data has placeholder zones with missing
            # borough/zone_name/service_zone. pandas represents a missing
            # *string* cell as float NaN, not None (that's what reading
            # the real CSV produces) - using float("nan") here, not None,
            # reproduces exactly that, which is what caught the NaN-vs-
            # None bug that none of the other fixture rows exercised.
            {
                "location_id": 264,
                "borough": "Unknown",
                "zone_name": float("nan"),
                "service_zone": float("nan"),
                "centroid_lat": float("nan"),
                "centroid_lon": float("nan"),
            },
        ]
    )
    write_deltalake(
        str(warehouse_root / "warehouse_output" / "staging" / "stg_taxi_zones"),
        zones,
        mode="overwrite",
    )

    hourly = pd.DataFrame(
        [
            {
                "period_start": datetime(2024, 1, 1, 8, tzinfo=UTC),
                "pickup_location_id": 100,
                "trip_count": 50,
                "total_revenue": 500.0,
                "avg_duration_seconds": 600.0,
                "avg_speed_mph": 12.0,
                "borough": "Manhattan",
                "zone_name": "Midtown",
            },
            {
                "period_start": datetime(2024, 1, 1, 9, tzinfo=UTC),
                "pickup_location_id": 100,
                "trip_count": 30,
                "total_revenue": 300.0,
                "avg_duration_seconds": 620.0,
                "avg_speed_mph": 11.0,
                "borough": "Manhattan",
                "zone_name": "Midtown",
            },
            {
                "period_start": datetime(2024, 1, 1, 8, tzinfo=UTC),
                "pickup_location_id": 200,
                "trip_count": 5,
                "total_revenue": 50.0,
                "avg_duration_seconds": 500.0,
                "avg_speed_mph": 14.0,
                "borough": "Queens",
                "zone_name": "Jamaica",
            },
        ]
    )
    write_deltalake(
        str(warehouse_root / "warehouse_output" / "marts" / "zone_demand_hourly"),
        hourly,
        mode="overwrite",
    )

    forecast = pd.DataFrame(
        [
            {
                "pickup_location_id": "100",
                "forecast_timestamp": datetime(2024, 1, 2, 0, tzinfo=UTC),
                "predicted_trip_count": 45.0,
                "predicted_lower": 40.0,
                "predicted_upper": 50.0,
                "mae": 1.2,
                "mape": 5.5,
            }
        ]
    )
    write_deltalake(
        str(warehouse_root / "warehouse_output" / "marts" / "demand_forecast"),
        forecast,
        mode="overwrite",
    )

    aggregates = pd.DataFrame(
        [
            {
                "window_start": datetime(2024, 1, 1, 8, tzinfo=UTC),
                "window_end": datetime(2024, 1, 1, 8, 5, tzinfo=UTC),
                "pickup_location_id": 100,
                "trip_count": 20,
                "total_revenue": 200.0,
                "avg_duration_seconds": 600.0,
                "avg_speed_mph": 12.0,
                "historical_avg_trip_count": 5.0,
                "spike_ratio": 4.0,
                "is_spike": True,
            },
            {
                "window_start": datetime(2024, 1, 1, 8, tzinfo=UTC),
                "window_end": datetime(2024, 1, 1, 8, 5, tzinfo=UTC),
                "pickup_location_id": 200,
                "trip_count": 5,
                "total_revenue": 50.0,
                "avg_duration_seconds": 500.0,
                "avg_speed_mph": 14.0,
                "historical_avg_trip_count": 5.0,
                "spike_ratio": 1.0,
                "is_spike": False,
            },
        ]
    )
    write_deltalake(
        str(warehouse_root / "output" / "zone_aggregates"),
        aggregates,
        mode="overwrite",
    )
    return warehouse_root


@pytest.fixture
def client(warehouse_root):
    from taxipulse_api.main import app

    return TestClient(app)
