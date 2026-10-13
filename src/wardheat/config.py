"""Workshop-wide constants: area of interest, analysis grid, season, and paths.

Everything a participant might want to change for *another city* lives here,
so the rest of the package stays city-agnostic.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Area of interest
# ---------------------------------------------------------------------------
CITY = "Bengaluru (Greater Bengaluru Authority)"

# lon/lat bounding box of the 369 GBA wards, padded by ~1 km so that
# edge wards get full pixel coverage.
BBOX = (77.45, 12.82, 77.80, 13.155)

# Working projection. UTM zone 43N is the native projection of the Landsat
# and Sentinel-2 tiles over Bengaluru, so we never resample the thermal data
# more than once.
CRS = "EPSG:32643"

# Analysis grid resolution in metres (the Landsat thermal resolution).
RES = 30

# ---------------------------------------------------------------------------
# Time window
# ---------------------------------------------------------------------------
# Bengaluru's hottest months are March-May: the south-west monsoon arrives in
# early June. North Indian heat studies typically use April-July because the
# heat season there runs later.
SEASON_MONTHS = (3, 4, 5)
YEARS = (2022, 2026)  # inclusive -> five summers


def season_datetime(years: tuple[int, int] = YEARS) -> str:
    """STAC datetime range covering the March-May window of every year."""
    return f"{years[0]}-03-01/{years[1]}-05-31"


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    """Where the Bengaluru data pack lives.

    Defaults to ``<repo>/data`` when the package is installed from a clone
    (the normal workshop setup), otherwise ``~/.cache/wardheat``. Override with
    the ``WARDHEAT_DATA_DIR`` environment variable.
    """
    env = os.environ.get("WARDHEAT_DATA_DIR")
    if env:
        p = Path(env).expanduser()
    elif (_REPO_ROOT / "pyproject.toml").exists():
        p = _REPO_ROOT / "data"
    else:
        p = Path.home() / ".cache" / "wardheat"
    p.mkdir(parents=True, exist_ok=True)
    return p


def raw_dir() -> Path:
    """Scratch space for raw downloads (GHSL zips, WorldPop, ...)."""
    p = data_dir() / "_raw"
    p.mkdir(parents=True, exist_ok=True)
    return p


# Planetary Computer STAC endpoint (free, anonymous, URLs are signed on the fly)
PC_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"

# Overture Maps release used for buildings and places
OVERTURE_RELEASE = "2026-09-23.1"
