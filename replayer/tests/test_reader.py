from pathlib import Path

import pandas as pd

from taxipulse_replayer.reader import iter_trip_events, load_trips

RAW_ROWS = [
    {
        "VendorID": 1,
        "tpep_pickup_datetime": pd.Timestamp("2024-01-01 08:05:00"),
        "tpep_dropoff_datetime": pd.Timestamp("2024-01-01 08:15:00"),
        "passenger_count": 1.0,
        "trip_distance": 2.1,
        "PULocationID": 142,
        "DOLocationID": 236,
        "payment_type": 1,
        "fare_amount": 10.0,
        "tip_amount": 2.0,
        "total_amount": 13.3,
    },
    {
        "VendorID": 2,
        "tpep_pickup_datetime": pd.Timestamp("2024-01-01 08:00:00"),
        "tpep_dropoff_datetime": pd.Timestamp("2024-01-01 08:10:00"),
        "passenger_count": float("nan"),  # missing in source data
        "trip_distance": 1.5,
        "PULocationID": 100,
        "DOLocationID": 200,
        "payment_type": float("nan"),  # missing in source data
        "fare_amount": 8.0,
        "tip_amount": 0.0,
        "total_amount": 9.3,
    },
    {
        # invalid row: negative fare, should be skipped by iter_trip_events
        "VendorID": 1,
        "tpep_pickup_datetime": pd.Timestamp("2024-01-01 08:20:00"),
        "tpep_dropoff_datetime": pd.Timestamp("2024-01-01 08:25:00"),
        "passenger_count": 1.0,
        "trip_distance": 1.0,
        "PULocationID": 50,
        "DOLocationID": 60,
        "payment_type": 1,
        "fare_amount": -5.0,
        "tip_amount": 0.0,
        "total_amount": -5.0,
    },
]


def write_sample_parquet(path: Path) -> Path:
    pd.DataFrame(RAW_ROWS).to_parquet(path)
    return path


def test_load_trips_sorts_chronologically_and_renames_columns(tmp_path):
    parquet_path = write_sample_parquet(tmp_path / "sample.parquet")

    df = load_trips(parquet_path)

    assert list(df.columns) == [
        "vendor_id",
        "pickup_datetime",
        "dropoff_datetime",
        "pickup_location_id",
        "dropoff_location_id",
        "passenger_count",
        "trip_distance",
        "fare_amount",
        "tip_amount",
        "total_amount",
        "payment_type",
    ]
    # row 2 (08:00) should now come before row 1 (08:05)
    assert df.iloc[0]["pickup_location_id"] == 100
    assert df.iloc[1]["pickup_location_id"] == 142


def test_iter_trip_events_skips_invalid_rows_and_fills_defaults(tmp_path):
    parquet_path = write_sample_parquet(tmp_path / "sample.parquet")
    df = load_trips(parquet_path)

    events = list(iter_trip_events(df))

    # the negative-fare row must be dropped
    assert len(events) == 2
    assert all(e.fare_amount >= 0 for e in events)

    # the row with NaN passenger_count/payment_type gets safe defaults
    event_100 = next(e for e in events if e.pickup_location_id == 100)
    assert event_100.passenger_count == 1
    assert event_100.payment_type == 0


def test_iter_trip_events_assigns_unique_trip_ids(tmp_path):
    parquet_path = write_sample_parquet(tmp_path / "sample.parquet")
    df = load_trips(parquet_path)

    events = list(iter_trip_events(df))

    assert len({e.trip_id for e in events}) == len(events)
