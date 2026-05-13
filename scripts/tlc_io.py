"""
Notes
- High-Volume FHV files are named 'fhvhv_tripdata_YYYY-MM.parquet' on TLC.
- The CBD congestion fee is active from 2025-01-05 and applies in Manhattan’s CBD only.
  We still download *all* boroughs so you can compare boroughs in analysis.
"""
from __future__ import annotations

from urllib.request import urlretrieve, Request, urlopen
from urllib.error import HTTPError, URLError
import os, csv, time, zipfile
from pathlib import Path
from typing import Iterable, Sequence

# -----------------------
# Constants
# -----------------------
BASE_TRIP_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
ZONE_ZIP_URL  = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"
ZONE_CSV_URL  = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"

RAW_SUBDIRS = {
    "fhv_hv": ("data", "raw", "fhv_hv"),
    "zones":  ("data", "raw", "taxi_zones"),
}
MANIFEST_PATH = ("data", "raw", "download_manifest.csv")

# -----------------------
# Path helpers
# -----------------------

def _root_path(root: str | os.PathLike | None) -> Path:
    """Resolve project root. If None, use current working directory."""
    if root:
        return Path(root)
    cwd = Path(os.getcwd())
    return cwd.parent if cwd.name == "notebooks" else cwd

def _ensure_dirs(root: Path) -> dict[str, Path]:
    paths = {k: root.joinpath(*v) for k, v in RAW_SUBDIRS.items()}
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def _manifest_path(root: Path) -> Path:
    return root.joinpath(*MANIFEST_PATH)

# -----------------------
# HTTP helpers
# -----------------------

def _head_size(url: str, timeout: float = 20.0) -> int:
    try:
        req = Request(url, method="HEAD")
        with urlopen(req, timeout=timeout) as resp:
            cl = resp.headers.get("Content-Length")
            return int(cl) if cl else -1
    except Exception:
        return -1


def _download_file(url: str, out_path: Path) -> tuple[str, int, float, str]:
    """Return (status, size_bytes, elapsed_s, error)."""
    if out_path.exists() and out_path.stat().st_size > 0:
        return ("exists", out_path.stat().st_size, 0.0, "")
    expected = _head_size(url)
    t0 = time.time()
    try:
        urlretrieve(url, out_path.as_posix())
        elapsed = time.time() - t0
        size = out_path.stat().st_size if out_path.exists() else 0
        status = "downloaded"
        if expected > 0 and size < expected * 0.5:
            status = "downloaded_warn_size"
        return (status, size, elapsed, "")
    except HTTPError as e:
        return ("missing", 0, 0.0, str(e))
    except URLError as e:
        return ("error", 0, 0.0, str(e))
    except Exception as e:
        return ("error", 0, 0.0, str(e))


def _write_manifest(rows: Iterable[list], manifest_path: Path) -> None:
    header = ["taxi_type","year","month","url","local_path","status","size_bytes","elapsed_s","error"]
    exists = manifest_path.exists()
    with manifest_path.open("a", newline="") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(header)
        for r in rows:
            w.writerow(r)

# -----------------------
# Public API
# -----------------------

def download_zones(root: str | os.PathLike | None = None, unzip: bool = True) -> dict[str, Path]:
    """Download taxi zone lookup CSV and shapefile ZIP. Optionally unzip.

    Returns a dict with paths: {"csv": Path, "zip": Path, "dir": Path}
    """
    rootp = _root_path(root)
    paths = _ensure_dirs(rootp)
    zones_dir = paths["zones"]

    csv_path = zones_dir / "taxi_zone_lookup.csv"
    zip_path = zones_dir / "taxi_zones.zip"

    status_csv = _download_file(ZONE_CSV_URL, csv_path)
    print(f"zone CSV: {status_csv[0]} → {csv_path}")

    status_zip = _download_file(ZONE_ZIP_URL, zip_path)
    print(f"zone ZIP: {status_zip[0]} → {zip_path}")

    if unzip and zip_path.exists():
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(zones_dir)
            print(f"unzipped to {zones_dir}")
        except zipfile.BadZipFile:
            print("warning: taxi_zones.zip is not a valid zip (skipping extract)")

    return {"csv": csv_path, "zip": zip_path, "dir": zones_dir}


def download_trips(
    types: Sequence[str],
    years: Sequence[str | int],
    months: Sequence[int],
    root: str | os.PathLike | None = None,
    write_manifest: bool = True,
) -> list[dict]:
    """Download TLC trip parquet files for given taxi types/years/months.

    types: ['yellow', 'fhv_hv']
    years: e.g., ['2024','2025']
    months: e.g., range(1,7)

    Returns a list of info dicts per attempt.
    """
    rootp = _root_path(root)
    paths = _ensure_dirs(rootp)
    results: list[dict] = []

    def prefix(t: str) -> str:
        return "fhvhv" if t == "fhv_hv" else t

    for t in types:
        if t not in ("fhv_hv"):
            print(f"! skipping unsupported type: {t}")
            continue
        out_dir = paths[t]
        for y in map(str, years):
            for m in months:
                mm = f"{int(m):02d}"
                fname = f"{prefix(t)}_tripdata_{y}-{mm}.parquet"
                url = f"{BASE_TRIP_URL}/{fname}"
                out_path = out_dir / fname
                status, size, elapsed, err = _download_file(url, out_path)
                print(f"{t} {y}-{mm}: {status} ({size/1e6:.1f} MB) → {out_path}")
                results.append({
                    "taxi_type": t, "year": y, "month": mm, "url": url,
                    "local_path": str(out_path), "status": status,
                    "size_bytes": size, "elapsed_s": elapsed, "error": err,
                })

    if write_manifest:
        _write_manifest([
            [r["taxi_type"], r["year"], r["month"], r["url"], r["local_path"], r["status"], r["size_bytes"], f"{r['elapsed_s']:.2f}", r["error"]]
            for r in results
        ], _manifest_path(rootp))
        print(f"manifest → {_manifest_path(rootp)}")

    return results


# Optional: allow running as a script
if __name__ == "__main__":
    # Minimal CLI for convenience; primary use is via import from notebooks.
    import argparse
    parser = argparse.ArgumentParser(description="Download TLC trips and zone metadata")
    parser.add_argument("--types", nargs="*", default=["yellow","fhv_hv"], help="yellow fhv_hv")
    parser.add_argument("--years", nargs="*", default=["2024","2025"], help="e.g. 2025 2024")
    parser.add_argument("--months", nargs="*", default=[1,2,3,4,5,6], type=int)
    parser.add_argument("--no-unzip", action="store_true", help="do not unzip taxi_zones.zip")
    args = parser.parse_args()

    download_zones(unzip=not args.no_unzip)
    download_trips(types=args.types, years=args.years, months=args.months)
