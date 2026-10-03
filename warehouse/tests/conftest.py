import os
from pathlib import Path

import pytest
from pyspark.sql import SparkSession

# applyInPandas UDFs (forecast.py) are shipped to the Python worker by
# reference and re-imported there. On Windows the worker is a genuinely
# separate process (not forked), so it does NOT inherit pytest's
# `pythonpath` ini-option sys.path trick - only a real PYTHONPATH env var
# propagates to it. Without this, the worker crashes ungracefully while
# re-importing taxipulse_warehouse during UDF unpickling, before PySpark's
# own exception handling is active (surfaces as an opaque "Python worker
# exited unexpectedly" rather than a clean ModuleNotFoundError).
_WAREHOUSE_SRC = str(Path(__file__).resolve().parent.parent / "src")
if _WAREHOUSE_SRC not in os.environ.get("PYTHONPATH", ""):
    os.environ["PYTHONPATH"] = os.pathsep.join(
        filter(None, [_WAREHOUSE_SRC, os.environ.get("PYTHONPATH")])
    )


@pytest.fixture(scope="session")
def spark():
    session = (
        SparkSession.builder.master("local[2]")
        .appName("taxipulse-warehouse-tests")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("WARN")
    yield session
    session.stop()
