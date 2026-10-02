"""Flags demand spikes by comparing each window's per-zone trip count
against a historical average for that zone."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

DEFAULT_SPIKE_RATIO_THRESHOLD = 1.5


def detect_demand_spikes(
    zone_aggregates: DataFrame,
    historical_avg_by_zone: DataFrame,
    spike_ratio_threshold: float = DEFAULT_SPIKE_RATIO_THRESHOLD,
) -> DataFrame:
    """`historical_avg_by_zone` must have columns (pickup_location_id,
    historical_avg_trip_count). A zone absent from it is never flagged
    (historical_avg_trip_count/spike_ratio stay null) rather than guessed
    at. For a streaming `zone_aggregates`, this is a stream-static join -
    the same function works unchanged for batch (unit tests) and streaming
    (the real pipeline) input."""
    joined = zone_aggregates.join(historical_avg_by_zone, on="pickup_location_id", how="left")

    spike_ratio = F.when(
        F.col("historical_avg_trip_count").isNotNull() & (F.col("historical_avg_trip_count") > 0),
        F.round(F.col("trip_count") / F.col("historical_avg_trip_count"), 2),
    )

    return joined.withColumn("spike_ratio", spike_ratio).withColumn(
        "is_spike",
        F.coalesce(spike_ratio >= F.lit(spike_ratio_threshold), F.lit(False)),
    )
