from taxipulse_warehouse.quality import (
    check_no_nulls,
    check_non_negative,
    check_not_empty,
    check_zone_referential_integrity,
)


def test_check_not_empty_passes_for_non_empty_df(spark):
    df = spark.createDataFrame([(1,)], "x INT")

    result = check_not_empty(df, "test")

    assert result.passed is True


def test_check_not_empty_fails_for_empty_df(spark):
    df = spark.createDataFrame([], "x INT")

    result = check_not_empty(df, "test")

    assert result.passed is False


def test_check_no_nulls_passes_when_no_nulls(spark):
    df = spark.createDataFrame([(1, "a")], "x INT, y STRING")

    result = check_no_nulls(df, ["x", "y"], "test")

    assert result.passed is True


def test_check_no_nulls_fails_when_null_present(spark):
    df = spark.createDataFrame([(1, None)], "x INT, y STRING")

    result = check_no_nulls(df, ["x", "y"], "test")

    assert result.passed is False
    assert "y" in result.detail


def test_check_non_negative_fails_on_negative_value(spark):
    df = spark.createDataFrame([(-5.0,)], "amount DOUBLE")

    result = check_non_negative(df, ["amount"], "test")

    assert result.passed is False


def test_check_non_negative_passes_on_zero_and_positive(spark):
    df = spark.createDataFrame([(0.0,), (5.0,)], "amount DOUBLE")

    result = check_non_negative(df, ["amount"], "test")

    assert result.passed is True


def test_check_zone_referential_integrity_passes_when_all_known(spark):
    demand = spark.createDataFrame([(100,)], "pickup_location_id INT")
    zones = spark.createDataFrame([(100,)], "location_id INT")

    result = check_zone_referential_integrity(demand, zones, "test")

    assert result.passed is True


def test_check_zone_referential_integrity_fails_on_unknown_zone(spark):
    demand = spark.createDataFrame([(999,)], "pickup_location_id INT")
    zones = spark.createDataFrame([(100,)], "location_id INT")

    result = check_zone_referential_integrity(demand, zones, "test")

    assert result.passed is False
