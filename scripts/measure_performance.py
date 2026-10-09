"""Produces the real numbers for the README's "Measured results" section:
batch processing throughput, data volume, forecast accuracy, and Azure
cost. Deliberately does NOT try to re-measure live streaming throughput or
API latency against a running cloud deployment - those were measured once,
live, during an actual cloud session (see CLAUDE.md), and are cited in the
README as dated, point-in-time findings rather than something this script
re-derives on every run (that would mean keeping Azure resources running
just to re-run a benchmark, which this project's budget discipline argues
against).

Usage:
    python scripts/measure_performance.py

Requires: the warehouse pipeline already run at least once (see README's
"Running the warehouse pipeline locally") so warehouse_output/ exists, and
JAVA_HOME/HADOOP_HOME set the same way as any other local Spark run in this
project. Azure cost figures need `az login`; skipped with a note if
unavailable rather than failing the whole report.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from pathlib import Path

# On Windows, `az` is a .cmd shim, not a directly-executable .exe - passing
# just "az" to subprocess without shell=True fails with WinError 2 (file
# not found), even though `az` works fine from an interactive shell.
# shutil.which() resolves the real, platform-correct path up front.
AZ_CLI = shutil.which("az") or "az"

logger = logging.getLogger(__name__)

WAREHOUSE_OUTPUT = Path("warehouse_output")
TLC_SAMPLE_PATH = Path("data/sample/yellow_tripdata_2024-01_sample.parquet")


def measure_batch_throughput() -> dict:
    """Times a fresh batch_ingest -> staging -> marts run against the real
    TLC sample, in-process (no subprocess/CLI overhead, no Airflow task-
    scheduling overhead) so the timing reflects Spark's actual processing
    time. One shared SparkSession is reused across all three steps -
    JVM/session startup (a fixed cost regardless of data volume) is timed
    separately so it doesn't inflate the per-trip throughput figure for
    what is, honestly, a small demo-scale sample."""
    from taxipulse_warehouse.batch_ingest import ingest
    from taxipulse_warehouse.marts import build_zone_demand_mart
    from taxipulse_warehouse.spark_session import build_spark_session
    from taxipulse_warehouse.staging import build_stg_trips
    from taxipulse_warehouse.zones import load_zone_reference

    session_start = time.perf_counter()
    spark = build_spark_session(app_name="taxipulse-measure-performance")
    session_elapsed = time.perf_counter() - session_start

    zones = load_zone_reference(spark, "data/reference/taxi_zones.parquet")

    processing_start = time.perf_counter()
    raw_trips = ingest(spark, str(TLC_SAMPLE_PATH))
    trip_count = raw_trips.count()
    stg_trips = build_stg_trips(raw_trips)
    stg_trip_count = stg_trips.count()
    hourly_mart = build_zone_demand_mart(stg_trips, zones, "hour")
    mart_row_count = hourly_mart.count()
    processing_elapsed = time.perf_counter() - processing_start

    spark.stop()

    return {
        "spark_session_startup_seconds": round(session_elapsed, 2),
        "processing_seconds": round(processing_elapsed, 2),
        "trips_ingested": trip_count,
        "trips_staged": stg_trip_count,
        "zone_demand_hourly_rows": mart_row_count,
        "trips_per_second": round(trip_count / processing_elapsed, 1),
        "note": (
            "processing_seconds covers batch_ingest+staging+marts only, "
            "not Spark session startup (a fixed cost independent of data "
            "volume, timed separately above) - trips_per_second would "
            "look artificially low if startup were included, and "
            "artificially high if extrapolated to a much larger batch "
            "without accounting for this being local[*], single-node."
        ),
    }


def measure_volume() -> dict:
    sample_bytes = TLC_SAMPLE_PATH.stat().st_size if TLC_SAMPLE_PATH.exists() else None
    warehouse_bytes = sum(f.stat().st_size for f in WAREHOUSE_OUTPUT.rglob("*") if f.is_file())
    return {
        "tlc_sample_file_bytes": sample_bytes,
        "warehouse_output_total_bytes": warehouse_bytes,
    }


def measure_forecast_accuracy() -> dict:
    from deltalake import DeltaTable

    forecast_path = WAREHOUSE_OUTPUT / "marts" / "demand_forecast"
    if not forecast_path.exists():
        return {"note": f"{forecast_path} not found - run `make warehouse-forecast` first"}

    df = DeltaTable(str(forecast_path)).to_pandas()
    per_zone = df.groupby("pickup_location_id")[["mae", "mape"]].first()
    return {
        "zones_forecast": int(per_zone.shape[0]),
        "avg_mae": round(float(per_zone["mae"].mean()), 3),
        "avg_mape_pct": round(float(per_zone["mape"].mean()), 1),
    }


def measure_azure_cost() -> dict:
    """Real month-to-date cost for the subscription used throughout this
    project, via the Cost Management API (not a pricing-calculator
    estimate) - covers every phase's cloud usage, not just the current
    session. Requires `az login`; returns a note instead of raising if the
    CLI isn't available or the account isn't authenticated, since cost
    reporting is a nice-to-have on top of the performance numbers, not a
    hard requirement for this script to be useful."""
    try:
        subscription_id = subprocess.run(
            [AZ_CLI, "account", "show", "--query", "id", "-o", "tsv"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        return {"note": f"Azure CLI not available/authenticated - skipping cost figures ({exc})"}

    body = {
        "type": "ActualCost",
        "timeframe": "MonthToDate",
        "dataset": {
            "granularity": "None",
            "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
            "grouping": [{"type": "Dimension", "name": "ServiceName"}],
        },
    }
    try:
        result = subprocess.run(
            [
                AZ_CLI,
                "rest",
                "--method",
                "POST",
                "--uri",
                f"https://management.azure.com/subscriptions/{subscription_id}"
                "/providers/Microsoft.CostManagement/query?api-version=2023-11-01",
                "--body",
                json.dumps(body),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
    except subprocess.SubprocessError as exc:
        return {"note": f"Cost Management query failed - skipping cost figures ({exc})"}

    rows = json.loads(result.stdout)["properties"]["rows"]
    by_service = {service: round(cost, 4) for cost, service, _currency in rows}
    return {
        "currency": "USD",
        "month_to_date_total": round(sum(by_service.values()), 2),
        "by_service": by_service,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    report = {
        "batch_throughput": measure_batch_throughput(),
        "volume": measure_volume(),
        "forecast_accuracy": measure_forecast_accuracy(),
        "azure_cost": measure_azure_cost(),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
