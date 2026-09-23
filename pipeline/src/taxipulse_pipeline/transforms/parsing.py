"""Parses raw Pub/Sub message bytes into TripEvent objects, routing invalid
payloads to a dead-letter output instead of failing the pipeline."""

from __future__ import annotations

import apache_beam as beam

from taxipulse_common.trip_event import TripEvent, TripEventValidationError

DEAD_LETTER_TAG = "dead_letter"
MAIN_TAG = "trips"


class ParseTripEvent(beam.DoFn):
    """Emits a valid TripEvent on the main ("trips") output, or a
    (raw_bytes, error_message) pair on the "dead_letter" tagged output."""

    def process(self, element: bytes):
        try:
            event = TripEvent.from_json(element)
        except TripEventValidationError as exc:
            yield beam.pvalue.TaggedOutput(DEAD_LETTER_TAG, (element, str(exc)))
            return
        yield beam.pvalue.TaggedOutput(MAIN_TAG, event)


def parse_with_dead_letter(raw_messages: beam.PCollection) -> tuple[beam.PCollection, beam.PCollection]:
    """Returns a (valid_events, dead_letter) pair of PCollections."""
    results = raw_messages | "ParseTripEvent" >> beam.ParDo(ParseTripEvent()).with_outputs(
        DEAD_LETTER_TAG, MAIN_TAG
    )
    return results[MAIN_TAG], results[DEAD_LETTER_TAG]
