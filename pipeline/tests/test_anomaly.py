import apache_beam as beam
from apache_beam.testing.test_pipeline import TestPipeline
from apache_beam.testing.util import assert_that, equal_to

from taxipulse_pipeline.transforms.anomaly import detect_demand_spikes

BASE_AGGREGATE = {
    "trip_count": 30,
    "total_revenue": 300.0,
    "avg_duration_seconds": 600.0,
    "avg_speed_mph": 12.0,
    "window_start": "2024-01-01T08:00:00",
    "window_end": "2024-01-01T08:05:00",
}


def test_detect_demand_spikes_flags_zone_above_threshold():
    zone_aggregates = [(100, BASE_AGGREGATE)]  # 30 trips vs historical avg 10 => ratio 3.0
    historical_avg = {100: 10.0}

    with TestPipeline() as p:
        aggregates = p | beam.Create(zone_aggregates)
        result = detect_demand_spikes(
            aggregates, beam.pvalue.AsDict(p | "Hist" >> beam.Create(list(historical_avg.items())))
        )
        flags = result | beam.Map(lambda r: (r["pickup_location_id"], r["is_spike"], r["spike_ratio"]))

        assert_that(flags, equal_to([(100, True, 3.0)]))


def test_detect_demand_spikes_does_not_flag_zone_below_threshold():
    zone_aggregates = [(100, BASE_AGGREGATE)]  # 30 trips vs historical avg 25 => ratio 1.2
    historical_avg = {100: 25.0}

    with TestPipeline() as p:
        aggregates = p | beam.Create(zone_aggregates)
        result = detect_demand_spikes(
            aggregates, beam.pvalue.AsDict(p | "Hist" >> beam.Create(list(historical_avg.items())))
        )
        flags = result | beam.Map(lambda r: (r["pickup_location_id"], r["is_spike"]))

        assert_that(flags, equal_to([(100, False)]))


def test_detect_demand_spikes_never_flags_zone_without_historical_baseline():
    zone_aggregates = [(999, BASE_AGGREGATE)]
    historical_avg: dict[int, float] = {}  # no baseline for zone 999

    with TestPipeline() as p:
        aggregates = p | beam.Create(zone_aggregates)
        result = detect_demand_spikes(
            aggregates, beam.pvalue.AsDict(p | "Hist" >> beam.Create(list(historical_avg.items())))
        )
        flags = result | beam.Map(lambda r: (r["pickup_location_id"], r["is_spike"], r["spike_ratio"]))

        assert_that(flags, equal_to([(999, False, None)]))


def test_detect_demand_spikes_respects_custom_threshold():
    zone_aggregates = [(100, BASE_AGGREGATE)]  # ratio 1.2
    historical_avg = {100: 25.0}

    with TestPipeline() as p:
        aggregates = p | beam.Create(zone_aggregates)
        result = detect_demand_spikes(
            aggregates,
            beam.pvalue.AsDict(p | "Hist" >> beam.Create(list(historical_avg.items()))),
            spike_ratio_threshold=1.1,
        )
        flags = result | beam.Map(lambda r: r["is_spike"])

        assert_that(flags, equal_to([True]))
