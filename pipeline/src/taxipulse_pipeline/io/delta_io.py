"""Delta Lake sink for the pipeline's streaming outputs. Works the same way
whether `path` is a local filesystem path (dev runs) or an ADLS Gen2
`abfss://` path (deployed) - only the path scheme changes."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql.streaming import StreamingQuery


def write_to_delta(df: DataFrame, path: str, checkpoint_path: str) -> StreamingQuery:
    return (
        df.writeStream.format("delta")
        .outputMode("append")
        .option("checkpointLocation", checkpoint_path)
        .start(path)
    )
