"""DAG-integrity tests: each DAG module must import cleanly (no syntax/
import errors Airflow's own parser would otherwise catch at schedule time)
and wire up the task dependency graph exactly as designed. These don't
require a running Airflow instance - just the `airflow` package itself
(an optional extra: pip install -e ".[airflow]"). Skipped entirely when
it's not installed, e.g. the main dev venv, which deliberately keeps
pyspark/mlflow/prophet out of the same environment as Airflow to avoid
their dependency ranges colliding (found the hard way - airflow's pinned
alembic range conflicts with mlflow's)."""

import importlib
import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("airflow") is None,
    reason="apache-airflow is an optional extra (pip install -e '.[airflow]')",
)


def _load_dag(module_name: str, dag_id: str):
    module = importlib.import_module(module_name)
    dag = module.dag
    assert dag.dag_id == dag_id
    return dag


def test_batch_pipeline_dag_imports_and_has_expected_tasks():
    dag = _load_dag("taxipulse_batch_pipeline_dag", "taxipulse_batch_pipeline")
    assert set(dag.task_dict) == {
        "load_zones",
        "batch_ingest",
        "staging",
        "marts",
        "quality_gate",
    }


def test_batch_pipeline_dag_dependency_graph():
    dag = _load_dag("taxipulse_batch_pipeline_dag", "taxipulse_batch_pipeline")
    tasks = dag.task_dict

    assert tasks["batch_ingest"].downstream_task_ids == {"staging"}
    assert tasks["staging"].downstream_task_ids == {"marts"}
    assert tasks["load_zones"].downstream_task_ids == {"marts"}
    assert tasks["marts"].downstream_task_ids == {"quality_gate"}
    assert tasks["quality_gate"].downstream_task_ids == set()


def test_forecast_dag_imports_and_has_expected_task():
    dag = _load_dag("taxipulse_forecast_dag", "taxipulse_forecast_retrain")
    assert set(dag.task_dict) == {"train_and_forecast"}
    assert dag.task_dict["train_and_forecast"].downstream_task_ids == set()
