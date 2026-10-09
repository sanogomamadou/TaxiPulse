import pandas as pd

from taxipulse_warehouse.zones import load_zone_reference


def test_load_zone_reference_reads_parquet_file(spark, tmp_path):
    reference_path = tmp_path / "taxi_zones.parquet"
    pd.DataFrame(
        [
            {
                "location_id": 100,
                "borough": "Manhattan",
                "zone_name": "Midtown",
                "service_zone": "Yellow Zone",
                "centroid_lat": 40.75,
                "centroid_lon": -73.98,
            }
        ]
    ).to_parquet(reference_path, index=False)

    result = load_zone_reference(spark, str(reference_path))

    row = result.collect()[0]
    assert row["location_id"] == 100
    assert row["borough"] == "Manhattan"
