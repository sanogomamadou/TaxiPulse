"""Weekly scheduled retrain of the per-zone demand forecasting model.

Separate from taxipulse_batch_pipeline_dag (which runs daily) since
retraining doesn't need to happen as often as the batch load - same
reasoning the original brief gave for splitting "batch load" from
"scheduled retraining" as distinct Composer/Airflow responsibilities.

Known simplification: this DAG assumes the marts the batch pipeline
produces already exist (it does not sensor/wait on the other DAG) - a
cross-DAG dependency would add real value in a production deployment but
isn't worth the added complexity for this portfolio project's local
schedule-only demo.
"""

from __future__ import annotations

from datetime import datetime

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator

PROJECT_ROOT = "{{ var.value.get('taxipulse_project_root', '.') }}"
WAREHOUSE_OUTPUT = "{{ var.value.get('taxipulse_warehouse_output', 'warehouse_output') }}"
TOP_N_ZONES = "{{ var.value.get('taxipulse_forecast_top_n_zones', '10') }}"

default_args = {
    "owner": "taxipulse",
    "retries": 1,
}

with DAG(
    dag_id="taxipulse_forecast_retrain",
    description="Weekly retrain of the per-zone demand forecasting model",
    schedule="@weekly",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["taxipulse", "warehouse", "ml"],
) as dag:
    forecast = BashOperator(
        task_id="train_and_forecast",
        bash_command=(
            f"python -m taxipulse_warehouse.forecast "
            f"--zone-demand-hourly-path {WAREHOUSE_OUTPUT}/marts/zone_demand_hourly "
            f"--output-path {WAREHOUSE_OUTPUT}/marts/demand_forecast "
            f"--top-n-zones {TOP_N_ZONES}"
        ),
        cwd=PROJECT_ROOT,
    )
