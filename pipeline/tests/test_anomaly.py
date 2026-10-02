from taxipulse_pipeline.transforms.anomaly import detect_demand_spikes

AGG_SCHEMA = (
    "pickup_location_id INT, trip_count INT, total_revenue DOUBLE, "
    "avg_duration_seconds DOUBLE, avg_speed_mph DOUBLE"
)
HIST_SCHEMA = "pickup_location_id INT, historical_avg_trip_count DOUBLE"


def test_detect_demand_spikes_flags_zone_above_threshold(spark):
    agg = spark.createDataFrame([(100, 30, 300.0, 600.0, 12.0)], AGG_SCHEMA)
    hist = spark.createDataFrame([(100, 10.0)], HIST_SCHEMA)

    result = detect_demand_spikes(agg, hist).collect()[0]

    assert result["spike_ratio"] == 3.0
    assert result["is_spike"] is True


def test_detect_demand_spikes_does_not_flag_zone_below_threshold(spark):
    agg = spark.createDataFrame([(100, 30, 300.0, 600.0, 12.0)], AGG_SCHEMA)
    hist = spark.createDataFrame([(100, 25.0)], HIST_SCHEMA)

    result = detect_demand_spikes(agg, hist).collect()[0]

    assert result["is_spike"] is False


def test_detect_demand_spikes_never_flags_zone_without_historical_baseline(spark):
    agg = spark.createDataFrame([(999, 30, 300.0, 600.0, 12.0)], AGG_SCHEMA)
    hist = spark.createDataFrame([], HIST_SCHEMA)

    result = detect_demand_spikes(agg, hist).collect()[0]

    assert result["spike_ratio"] is None
    assert result["is_spike"] is False


def test_detect_demand_spikes_respects_custom_threshold(spark):
    agg = spark.createDataFrame([(100, 30, 300.0, 600.0, 12.0)], AGG_SCHEMA)
    hist = spark.createDataFrame([(100, 25.0)], HIST_SCHEMA)

    result = detect_demand_spikes(agg, hist, spike_ratio_threshold=1.1).collect()[0]

    assert result["is_spike"] is True
