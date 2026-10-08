"""Daily batch pipeline: zone reference + raw TLC ingest -> staging -> marts
-> data quality gate.

Each task shells out to the corresponding `taxipulse_warehouse` CLI module -
the exact same entry points exercised locally via `make warehouse-*` and
verified end-to-end against a real TLC sample. Airflow's job here is
scheduling, retries and dependency ordering; it does not re-implement any
pipeline logic. The runtime environment (JAVA_HOME, the warehouse's Python
deps, the project root each task's `cwd` resolves against) is supplied by
the Airflow deployment itself (see orchestration/Dockerfile and
docker-compose.yml), not hardcoded in the DAG.

`quality_gate` fails the DAG run if any check fails (taxipulse_warehouse.
quality's CLI exits non-zero), which is what actually makes this a gate
rather than just another task.
"""

from __future__ import annotations

from datetime import datetime

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator

PROJECT_ROOT = "{{ var.value.get('taxipulse_project_root', '.') }}"
WAREHOUSE_OUTPUT = "{{ var.value.get('taxipulse_warehouse_output', 'warehouse_output') }}"
ZONE_REFERENCE_PATH = (
    "{{ var.value.get('taxipulse_zone_reference_path', 'data/reference/taxi_zones.parquet') }}"
)
TLC_INPUT_PATH = (
    "{{ var.value.get('taxipulse_tlc_input_path', "
    "'data/sample/yellow_tripdata_2024-01_sample.parquet') }}"
)

RAW_TRIPS_PATH = f"{WAREHOUSE_OUTPUT}/raw/trips"
STG_TRIPS_PATH = f"{WAREHOUSE_OUTPUT}/staging/stg_trips"
STG_TAXI_ZONES_PATH = f"{WAREHOUSE_OUTPUT}/staging/stg_taxi_zones"
ZONE_DEMAND_HOURLY_PATH = f"{WAREHOUSE_OUTPUT}/marts/zone_demand_hourly"
ZONE_DEMAND_DAILY_PATH = f"{WAREHOUSE_OUTPUT}/marts/zone_demand_daily"

default_args = {
    "owner": "taxipulse",
    "retries": 1,
}

with DAG(
    dag_id="taxipulse_batch_pipeline",
    description="Daily batch load: zone reference + raw ingest -> staging -> marts -> quality gate",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["taxipulse", "warehouse"],
) as dag:
    load_zones = BashOperator(
        task_id="load_zones",
        bash_command=(
            f"python -m taxipulse_warehouse.zones "
            f"--reference-path {ZONE_REFERENCE_PATH} "
            f"--output-path {STG_TAXI_ZONES_PATH}"
        ),
        cwd=PROJECT_ROOT,
    )

    batch_ingest = BashOperator(
        task_id="batch_ingest",
        bash_command=(
            f"python -m taxipulse_warehouse.batch_ingest {TLC_INPUT_PATH} "
            f"--output-path {RAW_TRIPS_PATH}"
        ),
        cwd=PROJECT_ROOT,
    )

    staging = BashOperator(
        task_id="staging",
        bash_command=(
            f"python -m taxipulse_warehouse.staging "
            f"--input-path {RAW_TRIPS_PATH} "
            f"--output-path {STG_TRIPS_PATH}"
        ),
        cwd=PROJECT_ROOT,
    )

    marts = BashOperator(
        task_id="marts",
        bash_command=(
            f"python -m taxipulse_warehouse.marts "
            f"--stg-trips-path {STG_TRIPS_PATH} "
            f"--stg-taxi-zones-path {STG_TAXI_ZONES_PATH} "
            f"--hourly-output-path {ZONE_DEMAND_HOURLY_PATH} "
            f"--daily-output-path {ZONE_DEMAND_DAILY_PATH}"
        ),
        cwd=PROJECT_ROOT,
    )

    quality_gate = BashOperator(
        task_id="quality_gate",
        bash_command=(
            f"python -m taxipulse_warehouse.quality "
            f"--stg-trips-path {STG_TRIPS_PATH} "
            f"--stg-taxi-zones-path {STG_TAXI_ZONES_PATH} "
            f"--zone-demand-hourly-path {ZONE_DEMAND_HOURLY_PATH}"
        ),
        cwd=PROJECT_ROOT,
    )

    batch_ingest >> staging
    [staging, load_zones] >> marts >> quality_gate
