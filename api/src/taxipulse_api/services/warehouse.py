"""Reads already-materialized Delta tables for the API - via `deltalake`
(delta-rs), not pyspark. A request-serving API shouldn't spin up a JVM/
Spark session per request just to read a table someone else already
wrote; that tradeoff belongs to the batch/streaming jobs in warehouse/
and pipeline/, not here.

A table that doesn't exist yet (nothing has been run) is treated as "no
data available", not an error - callers get an empty list back rather
than a 500, since "the pipeline hasn't produced this yet" is an expected
state for a project with no continuously-running cloud infrastructure."""

from __future__ import annotations

import pandas as pd
from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError


def _read_table(path: str) -> pd.DataFrame | None:
    try:
        return DeltaTable(path).to_pandas()
    except TableNotFoundError:
        return None


def _records(df: pd.DataFrame) -> list[dict]:
    # pandas represents a missing *string* value as float NaN, not None -
    # real TLC zone data has this for a couple of placeholder zones (e.g.
    # "N/A"/unknown). Pydantic's `str | None` rejects NaN outright (it's
    # neither a str nor the literal None), which only surfaces once real
    # data with actual gaps is served - every unit test fixture so far had
    # fully-populated rows. A plain `df.where(df.notna(), None)` isn't
    # enough on its own: pandas' dedicated "str" extension dtype (what
    # deltalake's to_pandas() returns for string columns) refuses to hold
    # a bare Python None and silently reverts it back to its own NA
    # marker, which still comes out as NaN. `astype(object)` first forces
    # plain Python objects, which actually keep the None.
    return df.astype(object).where(df.notna(), None).to_dict(orient="records")


def list_zones(stg_taxi_zones_path: str) -> list[dict]:
    df = _read_table(stg_taxi_zones_path)
    if df is None:
        return []
    return _records(df.sort_values("location_id"))


def get_zone(stg_taxi_zones_path: str, location_id: int) -> dict | None:
    df = _read_table(stg_taxi_zones_path)
    if df is None:
        return None
    matches = df[df["location_id"] == location_id]
    if matches.empty:
        return None
    return _records(matches)[0]


def get_zone_demand(demand_path: str, location_id: int, limit: int) -> list[dict]:
    df = _read_table(demand_path)
    if df is None:
        return []
    zone_df = df[df["pickup_location_id"] == location_id].sort_values(
        "period_start", ascending=False
    )
    return _records(zone_df.head(limit))


def get_top_zones(demand_path: str, metric: str, limit: int) -> list[dict]:
    df = _read_table(demand_path)
    if df is None or df.empty:
        return []
    totals = (
        df.groupby(["pickup_location_id", "borough", "zone_name"], as_index=False, dropna=False)[
            metric
        ]
        .sum()
        .sort_values(metric, ascending=False)
    )
    return _records(totals.head(limit))


def get_zone_forecast(forecast_path: str, location_id: int, limit: int) -> list[dict]:
    df = _read_table(forecast_path)
    if df is None:
        return []
    zone_df = df[df["pickup_location_id"] == str(location_id)].sort_values("forecast_timestamp")
    return _records(zone_df.head(limit))


def get_latest_spikes(zone_aggregates_path: str, limit: int) -> list[dict]:
    df = _read_table(zone_aggregates_path)
    if df is None or df.empty:
        return []
    spikes = df[df["is_spike"]].sort_values("window_end", ascending=False)
    return _records(spikes.head(limit))
