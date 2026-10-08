# Extends the official Airflow image with the taxipulse_warehouse runtime
# (Java for PySpark, plus pyspark/delta-spark/geopandas/prophet/mlflow) so
# BashOperator tasks can shell out to `python -m taxipulse_warehouse.X`
# directly, mirroring how they're already run locally - no DockerOperator/
# remote-cluster indirection needed for this local demo. In the real target
# architecture, Airflow would instead trigger a job on an actual Databricks
# cluster rather than running Spark in-process; this image is a local-dev
# stand-in for that.
FROM apache/airflow:2.9.3-python3.11

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jdk-headless build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

USER airflow
# Re-stating the exact Airflow version pin alongside the constraints file
# is the documented way to add packages without pip trying (and failing)
# to resolve a different Airflow version - see pyproject.toml's `airflow`
# optional dependency group for the same note.
RUN pip install --no-cache-dir \
    "apache-airflow==2.9.3" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.3/constraints-3.11.txt" \
    "pyspark>=3.5" "delta-spark>=3.2" "geopandas>=1.0" "prophet>=1.1" "mlflow>=2.14"
