import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark():
    # Plain local session, no Delta/Kafka packages needed here - these tests
    # only exercise the pure transform functions over batch DataFrames, not
    # the real streaming source/sink.
    session = (
        SparkSession.builder.master("local[2]")
        .appName("taxipulse-pipeline-tests")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("WARN")
    yield session
    session.stop()
