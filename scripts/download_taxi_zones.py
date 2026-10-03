"""Downloads the official NYC TLC taxi zone lookup table and zone shapefile,
reprojects the shapefile to WGS84, computes each zone's centroid (lat/lon),
and writes a single reference file joining the two - this is the "enriched
with geography" zone dimension table used by the warehouse's marts layer
(warehouse/src/taxipulse_warehouse/zones.py reads this file to populate
staging.stg_taxi_zones).

Not a GIS engine (no polygon storage, no spatial queries) - just a lookup
table with borough/zone names plus a representative lat/lon per zone,
which is what the project's actual use case (per-zone KPIs, mapping)
needs. See CLAUDE.md for the scoping decision.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

LOOKUP_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
SHAPEFILE_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
REFERENCE_DIR = DATA_DIR / "reference"
OUTPUT_PATH = REFERENCE_DIR / "taxi_zones.parquet"

logger = logging.getLogger(__name__)


def download(url: str, destination: Path) -> Path:
    if destination.exists():
        logger.info("skip: %s already downloaded", destination.name)
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    logger.info("downloading %s", url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    destination.write_bytes(response.content)
    return destination


def build_zone_reference() -> pd.DataFrame:
    lookup_path = download(LOOKUP_URL, RAW_DIR / "taxi_zone_lookup.csv")
    shapefile_zip_path = download(SHAPEFILE_URL, RAW_DIR / "taxi_zones.zip")

    shapefile_dir = RAW_DIR / "taxi_zones"
    if not shapefile_dir.exists():
        with zipfile.ZipFile(shapefile_zip_path) as zf:
            zf.extractall(shapefile_dir)

    shp_files = list(shapefile_dir.glob("**/*.shp"))
    if not shp_files:
        raise FileNotFoundError(f"no .shp file found under {shapefile_dir}")

    zones_gdf = gpd.read_file(shp_files[0])
    # NYC taxi zone shapefile ships in a projected CRS (feet-based state
    # plane). Compute centroids there (planar, accurate), then reproject
    # just the resulting points to WGS84 (EPSG:4326) for plain lat/lon
    # degrees - reprojecting the polygons to a geographic CRS first and
    # computing centroids in degree-space would distort them.
    centroids = zones_gdf.geometry.centroid.to_crs(epsg=4326)
    zones_gdf["centroid_lon"] = centroids.x
    zones_gdf["centroid_lat"] = centroids.y

    zones_df = zones_gdf[["LocationID", "centroid_lat", "centroid_lon"]].rename(
        columns={"LocationID": "location_id"}
    )

    lookup_df = pd.read_csv(lookup_path).rename(
        columns={
            "LocationID": "location_id",
            "Borough": "borough",
            "Zone": "zone_name",
            "service_zone": "service_zone",
        }
    )

    merged = lookup_df.merge(zones_df, on="location_id", how="left")
    return merged


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    reference = build_zone_reference()
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    reference.to_parquet(OUTPUT_PATH, index=False)
    logger.info("wrote %d zones -> %s", len(reference), OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
