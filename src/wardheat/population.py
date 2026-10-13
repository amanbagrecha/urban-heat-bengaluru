"""Population (exposure).

* **Census 2011 ward totals** (from the GBA ward file): the official headcount
  per ward, but 15 years old and with no detail inside a ward.
* **WorldPop Global2 R2025A, 2025, constrained, 100 m**: a modelled map of
  where people live today, but it undercounts Bengaluru (~6 M vs 8.4 M in 2011).

We combine them: each ward keeps its Census total, spread over the ward's
pixels following WorldPop's pattern (``census_anchored``). Both describe where
people *sleep*, not where they work in the afternoon.

The India WorldPop file is 778 MB and the server ignores HTTP range requests,
so the data-pack builder downloads it once and clips Bengaluru.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pooch
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

from . import config
from .grid import Grid, outer_window, read_to_grid

WORLDPOP_URL = (
    "https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2025/IND/v1/100m/constrained/"
    "ind_pop_2025_CN_100m_R2025A_v1.tif"
)


def clip_to_bbox(src_path: str, out_path: Path, bbox=config.BBOX, pad_deg: float = 0.02) -> Path:
    """Cut a lon/lat bbox (padded) out of a big raster, keeping its native CRS and pixels."""
    b = (bbox[0] - pad_deg, bbox[1] - pad_deg, bbox[2] + pad_deg, bbox[3] + pad_deg)
    with rasterio.open(src_path) as src:
        nb = transform_bounds(4326, src.crs, *b)
        win = outer_window(from_bounds(*nb, src.transform))
        arr = src.read(1, window=win)
        prof = src.profile.copy()
        prof.update(driver="COG", width=arr.shape[1], height=arr.shape[0], transform=src.window_transform(win), compress="ZSTD")
        for k in ("blockxsize", "blockysize", "tiled", "interleave"):
            prof.pop(k, None)
    with rasterio.open(out_path, "w", **prof) as dst:
        dst.write(arr, 1)
    return out_path


def download_worldpop(dest_dir: Path | None = None) -> str:
    """Download the full WorldPop India 2025 file (~780 MB, once)."""
    return pooch.retrieve(WORLDPOP_URL, known_hash=None, path=dest_dir or config.raw_dir(), progressbar=True)


def counts_to_grid(src: str, grid: Grid, resampling: Resampling = Resampling.bilinear) -> np.ndarray:
    """Re-grid a *count* raster (people per 100 m cell) onto ``grid`` without creating or losing people.

    Counts are not intensities, so we cannot just interpolate them:

    1. interpolate the counts (a smooth surface),
    2. multiply by (target pixel area / source pixel area),
    3. rescale so the city total equals the source total over the same area.
    """
    with rasterio.open(src) as ds:
        src_area = _pixel_area_m2(ds)
        nb = transform_bounds(grid.crs, ds.crs, *grid.bounds)
        win = outer_window(from_bounds(*nb, ds.transform))
        a = ds.read(1, window=win, masked=True, boundless=True).filled(0).astype("float64")
        src_total = float(a[a > 0].sum())
    dst = read_to_grid(src, grid, resampling=resampling)
    dst = np.where(np.isfinite(dst) & (dst > 0), dst, 0.0) * (grid.pixel_area / src_area)
    if dst.sum() > 0:
        dst *= src_total / dst.sum()
    return dst.astype("float32")


def _pixel_area_m2(ds) -> float:
    if ds.crs and ds.crs.is_geographic:
        lat = (ds.bounds.top + ds.bounds.bottom) / 2
        dx = abs(ds.transform.a) * 111_320 * math.cos(math.radians(lat))
        dy = abs(ds.transform.e) * 110_574
        return dx * dy
    return abs(ds.transform.a * ds.transform.e)


def census_anchored(weights: np.ndarray, labels: np.ndarray, ward_totals: "pd.Series") -> np.ndarray:  # noqa: F821
    """Dasymetric population: each ward's official total, spread over its pixels by ``weights``.

    ``weights`` is any population-like surface (here WorldPop 2025). Within a
    ward we trust its *pattern*; across wards we trust the Census *totals*.
    Wards where the weights are all zero get their total spread evenly.
    Pixels outside every ward keep the original weights.
    """
    w = np.where(np.isfinite(weights) & (weights > 0), weights, 0.0).astype("float64")
    n = int(labels.max()) + 1
    wsum = np.bincount(labels.ravel(), weights=w.ravel(), minlength=n)
    npx = np.bincount(labels.ravel(), minlength=n).astype("float64")
    tot = np.zeros(n)
    tot[ward_totals.index.to_numpy(dtype=int)] = ward_totals.to_numpy(dtype="float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        scale = np.where(wsum > 0, tot / wsum, 0.0)
        even = np.where((wsum == 0) & (npx > 0), tot / npx, 0.0)
    out = np.where(labels > 0, w * scale[labels] + even[labels], w)
    return out.astype("float32")
