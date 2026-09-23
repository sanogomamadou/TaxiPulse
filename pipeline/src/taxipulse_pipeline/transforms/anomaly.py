"""Flags demand spikes by comparing each window's per-zone trip count
against a historical average for that zone."""

from __future__ import annotations

import apache_beam as beam

DEFAULT_SPIKE_RATIO_THRESHOLD = 1.5


class DetectDemandSpike(beam.DoFn):
    """Given (zone_id, aggregate) and a side-input mapping of
    zone_id -> historical average trip count, emits an enriched record with
    `spike_ratio` and `is_spike` fields.

    Zones with no historical baseline available are never flagged (ratio is
    None, is_spike is False) rather than guessed at - until Phase 3 wires up
    a real baseline from BigQuery/BQML, this is every zone.
    """

    def __init__(self, spike_ratio_threshold: float = DEFAULT_SPIKE_RATIO_THRESHOLD) -> None:
        self._threshold = spike_ratio_threshold

    def process(self, element, historical_avg_by_zone):
        zone_id, aggregate = element
        historical_avg = historical_avg_by_zone.get(zone_id)

        if not historical_avg or historical_avg <= 0:
            ratio = None
            is_spike = False
        else:
            ratio = round(aggregate["trip_count"] / historical_avg, 2)
            is_spike = ratio >= self._threshold

        yield {
            "pickup_location_id": zone_id,
            **aggregate,
            "historical_avg_trip_count": historical_avg,
            "spike_ratio": ratio,
            "is_spike": is_spike,
        }


def detect_demand_spikes(
    zone_aggregates: beam.PCollection,
    historical_avg_by_zone,
    spike_ratio_threshold: float = DEFAULT_SPIKE_RATIO_THRESHOLD,
) -> beam.PCollection:
    return zone_aggregates | "DetectDemandSpike" >> beam.ParDo(
        DetectDemandSpike(spike_ratio_threshold), historical_avg_by_zone
    )
