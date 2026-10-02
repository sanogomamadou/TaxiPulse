"""Event-time preparation, dedup, and sliding-window per-zone aggregation.

Output mode note: the pipeline writes to a Delta sink using `append` output
mode (see io/delta_io.py), which is the only mode Spark's native file/Delta
streaming sinks support for a windowed aggregation. That means each window
is emitted exactly once, as a single final row, once the watermark passes
its end - any late data that arrives before that point is included in the
aggregate; anything after is dropped. This is a deliberate simplification
vs. the earlier Beam/Dataflow version, which used `update`-equivalent
accumulating early+late firings to give a continuously-updating live
dashboard. Getting that behavior back in Spark would mean a `foreachBatch`
+ Delta `MERGE` upsert sink instead of a plain file sink - a reasonable
follow-up, not implemented here to keep this phase's scope bounded.
"""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

DEFAULT_WINDOW_DURATION = "5 minutes"
DEFAULT_SLIDE_DURATION = "1 minute"
DEFAULT_WATERMARK_DELAY = "2 minutes"


def add_trip_metrics(df: DataFrame) -> DataFrame:
    """Adds per-trip duration_seconds and speed_mph columns, derived from
    pickup/dropoff timestamps and trip_distance."""
    duration_seconds = F.greatest(
        F.unix_timestamp("dropoff_datetime") - F.unix_timestamp("pickup_datetime"), F.lit(0)
    ).cast("double")
    return df.withColumn("duration_seconds", duration_seconds).withColumn(
        "speed_mph",
        F.when(
            F.col("duration_seconds") > 0,
            F.col("trip_distance") / (F.col("duration_seconds") / 3600),
        ).otherwise(F.lit(0.0)),
    )


def with_watermark(df: DataFrame, delay: str = DEFAULT_WATERMARK_DELAY) -> DataFrame:
    """Streaming-only: marks pickup_datetime as the event-time column Spark
    tracks the watermark against. A no-op-equivalent concept doesn't exist
    for batch DataFrames - batch callers (e.g. unit tests) simply skip this
    step and test the aggregation logic directly."""
    return df.withWatermark("pickup_datetime", delay)


def deduplicate_by_trip_id(df: DataFrame) -> DataFrame:
    """Streaming-only: drops duplicate trip_ids seen within the watermark
    window. `df` must already have a watermark set (see with_watermark).
    Spark's built-in dropDuplicatesWithinWatermark bounds dedup state the
    same way the earlier Beam version's stateful DoFn + expiry timer did -
    one built-in call instead of custom state/timer code, worth noting as a
    framework-idiom contrast."""
    return df.dropDuplicatesWithinWatermark(["trip_id"])


def aggregate_by_zone(
    df: DataFrame,
    window_duration: str = DEFAULT_WINDOW_DURATION,
    slide_duration: str = DEFAULT_SLIDE_DURATION,
) -> DataFrame:
    """Sliding-window per-zone aggregation: trip count, total revenue, and
    average duration/speed. `df` must already have duration_seconds/speed_mph
    (see add_trip_metrics)."""
    return (
        df.groupBy(
            F.window(F.col("pickup_datetime"), window_duration, slide_duration),
            F.col("pickup_location_id"),
        )
        .agg(
            F.count(F.lit(1)).alias("trip_count"),
            F.round(F.sum("total_amount"), 2).alias("total_revenue"),
            F.round(F.avg("duration_seconds"), 1).alias("avg_duration_seconds"),
            F.round(F.avg("speed_mph"), 1).alias("avg_speed_mph"),
        )
        .withColumn("window_start", F.col("window.start"))
        .withColumn("window_end", F.col("window.end"))
        .drop("window")
    )
