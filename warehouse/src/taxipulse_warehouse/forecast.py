"""Per-zone demand forecasting with Prophet, trained in parallel across
zones via a Spark grouped pandas UDF (`applyInPandas`) rather than looping
sequentially on the driver - each zone's model trains independently, so
this scales across a cluster the same way the rest of the warehouse does.
Scoped to the top-N busiest zones (not all ~260 TLC zones): enough to
demonstrate the approach and produce a meaningful MAE/MAPE without an
excessive number of models for a portfolio project's data volume.

Metrics (MAE, MAPE on a held-out tail of each zone's history) and the run's
aggregate numbers are logged to MLflow.
"""

from __future__ import annotations

import argparse
import logging

import mlflow
import pandas as pd
from prophet import Prophet
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType, StructField, StructType, TimestampType

from taxipulse_warehouse.spark_session import build_spark_session

logger = logging.getLogger(__name__)

DEFAULT_TOP_N_ZONES = 10
DEFAULT_FORECAST_HOURS = 24
DEFAULT_TEST_HOLDOUT_HOURS = 24

FORECAST_SCHEMA = StructType(
    [
        StructField("pickup_location_id", StringType()),
        StructField("forecast_timestamp", TimestampType()),
        StructField("predicted_trip_count", DoubleType()),
        StructField("predicted_lower", DoubleType()),
        StructField("predicted_upper", DoubleType()),
        StructField("mae", DoubleType()),
        StructField("mape", DoubleType()),
    ]
)


def select_top_zones(zone_demand_hourly: DataFrame, top_n: int) -> list[int]:
    totals = (
        zone_demand_hourly.groupBy("pickup_location_id")
        .agg(F.sum("trip_count").alias("total_trips"))
        .orderBy(F.desc("total_trips"))
        .limit(top_n)
        .collect()
    )
    return [row["pickup_location_id"] for row in totals]


def _train_and_forecast_one_zone(
    zone_df: pd.DataFrame, forecast_hours: int, holdout_hours: int
) -> pd.DataFrame:
    zone_df = zone_df.sort_values("period_start")
    prophet_df = zone_df.rename(columns={"period_start": "ds", "trip_count": "y"})[["ds", "y"]]

    if len(prophet_df) <= holdout_hours + 2:
        # Not enough history for a meaningful held-out test window - still
        # fit on everything available, just skip MAE/MAPE for this zone.
        train_df, test_df = prophet_df, pd.DataFrame(columns=["ds", "y"])
    else:
        train_df = prophet_df.iloc[:-holdout_hours]
        test_df = prophet_df.iloc[-holdout_hours:]

    model = Prophet()
    model.fit(train_df)

    if not test_df.empty:
        test_forecast = model.predict(test_df[["ds"]])
        errors = test_df["y"].to_numpy() - test_forecast["yhat"].to_numpy()
        mae = float(abs(errors).mean())
        actual = test_df["y"].to_numpy()
        nonzero = actual != 0
        mape = (
            float((abs(errors[nonzero]) / actual[nonzero]).mean() * 100)
            if nonzero.any()
            else float("nan")
        )
    else:
        mae, mape = float("nan"), float("nan")

    future = model.make_future_dataframe(periods=forecast_hours, freq="h", include_history=False)
    forecast = model.predict(future)

    zone_id = str(zone_df["pickup_location_id"].iloc[0])
    return pd.DataFrame(
        {
            "pickup_location_id": zone_id,
            "forecast_timestamp": forecast["ds"],
            "predicted_trip_count": forecast["yhat"].clip(lower=0),
            "predicted_lower": forecast["yhat_lower"].clip(lower=0),
            "predicted_upper": forecast["yhat_upper"].clip(lower=0),
            "mae": mae,
            "mape": mape,
        }
    )


def train_and_forecast(
    zone_demand_hourly: DataFrame,
    top_n_zones: int = DEFAULT_TOP_N_ZONES,
    forecast_hours: int = DEFAULT_FORECAST_HOURS,
    holdout_hours: int = DEFAULT_TEST_HOLDOUT_HOURS,
) -> DataFrame:
    zone_ids = select_top_zones(zone_demand_hourly, top_n_zones)
    scoped = zone_demand_hourly.filter(F.col("pickup_location_id").isin(zone_ids))

    def _udf(pdf: pd.DataFrame) -> pd.DataFrame:
        return _train_and_forecast_one_zone(pdf, forecast_hours, holdout_hours)

    return scoped.groupBy("pickup_location_id").applyInPandas(_udf, schema=FORECAST_SCHEMA)


def log_run_to_mlflow(forecast_pdf: pd.DataFrame, experiment_name: str) -> None:
    mlflow.set_experiment(experiment_name)
    per_zone = forecast_pdf.groupby("pickup_location_id")[["mae", "mape"]].first()
    with mlflow.start_run(run_name="zone_demand_forecast"):
        mlflow.log_param("zone_count", len(per_zone))
        mlflow.log_metric("avg_mae", float(per_zone["mae"].mean(skipna=True)))
        mlflow.log_metric("avg_mape", float(per_zone["mape"].mean(skipna=True)))


def run(
    zone_demand_hourly_path: str,
    output_path: str,
    top_n_zones: int,
    experiment_name: str,
) -> None:
    spark = build_spark_session(app_name="taxipulse-warehouse-forecast")
    zone_demand_hourly = spark.read.format("delta").load(zone_demand_hourly_path)

    forecast = train_and_forecast(zone_demand_hourly, top_n_zones=top_n_zones)
    forecast.write.format("delta").mode("overwrite").save(output_path)

    forecast_pdf = forecast.toPandas()
    log_run_to_mlflow(forecast_pdf, experiment_name)
    logger.info(
        "forecast complete: %d zones, avg MAE=%.2f, avg MAPE=%.1f%% -> %s",
        forecast_pdf["pickup_location_id"].nunique(),
        forecast_pdf["mae"].mean(skipna=True),
        forecast_pdf["mape"].mean(skipna=True),
        output_path,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--zone-demand-hourly-path", default="warehouse_output/marts/zone_demand_hourly"
    )
    parser.add_argument("--output-path", default="warehouse_output/marts/demand_forecast")
    parser.add_argument("--top-n-zones", type=int, default=DEFAULT_TOP_N_ZONES)
    parser.add_argument("--experiment-name", default="taxipulse-demand-forecast")
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    run(args.zone_demand_hourly_path, args.output_path, args.top_n_zones, args.experiment_name)
