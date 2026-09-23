"""Download a NYC TLC trip record Parquet file and extract a small local sample.

The full TLC datasets are hosted publicly on CloudFront and are too large to
commit to the repo, so this script downloads one month of data into
``data/raw/`` (gitignored) and writes a trimmed-down sample into
``data/sample/`` for fast local development and tests.

Usage:
    python scripts/download_tlc_sample.py --year-month 2024-01 --sample-size 5000
    python scripts/download_tlc_sample.py --taxi-type green --year-month 2023-06
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import requests

TLC_BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
VALID_TAXI_TYPES = ("yellow", "green", "fhv", "fhvhv")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
SAMPLE_DIR = DATA_DIR / "sample"


def download_file(url: str, destination: Path) -> Path:
    if destination.exists():
        print(f"[skip] {destination.name} already downloaded")
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"[download] {url}")
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()

    tmp_path = destination.with_suffix(".part")
    total = int(response.headers.get("content-length", 0))
    written = 0
    with open(tmp_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
            written += len(chunk)
            if total:
                pct = written / total * 100
                print(f"\r  {written / 1e6:,.1f} MB / {total / 1e6:,.1f} MB ({pct:.0f}%)", end="")
    print()
    tmp_path.rename(destination)
    return destination


def make_sample(raw_path: Path, sample_path: Path, sample_size: int, seed: int) -> None:
    print(f"[sample] reading {raw_path.name}")
    df = pd.read_parquet(raw_path)
    print(f"[sample] {len(df):,} rows in source file")

    n = min(sample_size, len(df))
    sample_df = df.sample(n=n, random_state=seed).sort_index()

    sample_path.parent.mkdir(parents=True, exist_ok=True)
    sample_df.to_parquet(sample_path, index=False)
    print(f"[sample] wrote {len(sample_df):,} rows -> {sample_path}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--taxi-type",
        choices=VALID_TAXI_TYPES,
        default="yellow",
        help="TLC dataset to download (default: yellow)",
    )
    parser.add_argument(
        "--year-month",
        required=True,
        help="Period to download, format YYYY-MM (e.g. 2024-01)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=5000,
        help="Number of rows to keep in the local sample (default: 5000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampling (default: 42)",
    )
    parser.add_argument(
        "--keep-raw",
        action="store_true",
        help="Keep the full downloaded Parquet file in data/raw/ after sampling",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    file_name = f"{args.taxi_type}_tripdata_{args.year_month}.parquet"
    url = f"{TLC_BASE_URL}/{file_name}"
    raw_path = RAW_DIR / file_name
    sample_path = SAMPLE_DIR / f"{args.taxi_type}_tripdata_{args.year_month}_sample.parquet"

    try:
        download_file(url, raw_path)
    except requests.HTTPError as exc:
        print(f"[error] could not download {url}: {exc}", file=sys.stderr)
        return 1

    make_sample(raw_path, sample_path, args.sample_size, args.seed)

    if not args.keep_raw:
        raw_path.unlink(missing_ok=True)
        print(f"[cleanup] removed {raw_path.name} (use --keep-raw to keep it)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
