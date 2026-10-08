from fastapi import FastAPI

from taxipulse_api.routers import health, zones

app = FastAPI(
    title="TaxiPulse API",
    description="Per-zone demand KPIs, forecasts, and live spike detection for NYC taxi trips.",
)

app.include_router(health.router)
app.include_router(zones.router)
