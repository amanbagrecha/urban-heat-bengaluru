"""Land cover and tree canopy.

* **ESA WorldCover 2021 v200** (10 m, Planetary Computer ``esa-worldcover``):
  built-up mask, cropland exclusion, vegetation fraction.
* **Meta / WRI High-Resolution Canopy Height Maps** (1.2 m, AWS Open Data):
  replaces Google Dynamic World tree probability, which is only available
  inside Earth Engine. At 1 m it resolves individual street trees, which 10 m
  classifications blur away.

  - ``v1`` (2024 release, Maxar imagery 2018-2020): our canopy layer.
  - ``v2`` (CHMv2, 2026 release, COGs): newer and faster to read, but over
    Bengaluru's dense built-up areas it reports ~26 % "canopy" on pixels with
    no vegetation at all (Sentinel-2 NDVI < 0.15) versus ~3 % for v1 — it reads
    buildings as trees.
"""

from __future__ import annotations

import math

import numpy as np
import rasterio
from affine import Affine
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

from . import config, stac
from .grid import Grid, block_mean, outer_window, reproject_array

# ---------------------------------------------------------------------------
# ESA WorldCover
# ---------------------------------------------------------------------------
WORLDCOVER_CLASSES = {
    10: ("Tree cover", "#006400"),
    20: ("Shrubland", "#ffbb22"),
    30: ("Grassland", "#ffff4c"),
    40: ("Cropland", "#f096ff"),
    50: ("Built-up", "#fa0000"),
    60: ("Bare / sparse vegetation", "#b4b4b4"),
    70: ("Snow and ice", "#f0f0f0"),
    80: ("Permanent water", "#0064c8"),
    90: ("Herbaceous wetland", "#0096a0"),
    95: ("Mangroves", "#00cf75"),
    100: ("Moss and lichen", "#fae6a0"),
}
VEGETATION = (10, 20, 30)
BUILT = 50
CROPLAND = 40
WATER = 80


def worldcover(grid10: Grid, year: int = 2021) -> np.ndarray:
    """WorldCover class codes on a 10 m grid (uint8, 0 = no data)."""
    import odc.stac

    items = stac.search("esa-worldcover", datetime=f"{year}-01-01/{year}-12-31", months=None)
    ds = odc.stac.load(items, bands=["map"], geobox=grid10.geobox(), resampling="nearest")
    return ds["map"].isel(time=0).values.astype("uint8")


def fractions(classes10: np.ndarray, factor: int = 3) -> dict[str, np.ndarray]:
    """Per-30 m-pixel fractions of built-up, vegetation, cropland and water from a 10 m class map."""
    valid = classes10 > 0
    f = lambda m: block_mean(np.where(valid, m, np.nan).astype("float32"), factor)  # noqa: E731
    return {
        "built_frac": f(classes10 == BUILT),
        "veg_frac": f(np.isin(classes10, VEGETATION)),
        "crop_frac": f(classes10 == CROPLAND),
        "water_frac": f(classes10 == WATER),
        "tree_frac_wc": f(classes10 == 10),
    }


# ---------------------------------------------------------------------------
# Meta / WRI canopy height
# ---------------------------------------------------------------------------
_S3 = "https://dataforgood-fb-data.s3.amazonaws.com/forests"
CHM = {
    # v1: one strip-encoded GeoTIFF per level-9 quadkey (no overviews; streaming reads whole rows)
    "v1": dict(base=f"{_S3}/v1/alsgedi_global_v6_float", zoom=9, tile_px=65536, nodata=None),
    # v2: Cloud-Optimized GeoTIFFs per level-10 quadkey
    "v2": dict(base=f"{_S3}/v2/global/dinov3_global_chm_v2_ml3", zoom=10, tile_px=32768, nodata=255),
}
_WEB_MERC_HALF = 20037508.342789244


def _tile_xy(lon: float, lat: float, z: int) -> tuple[int, int]:
    n = 2**z
    x = int((lon + 180) / 360 * n)
    lr = math.radians(lat)
    y = int((1 - math.log(math.tan(lr) + 1 / math.cos(lr)) / math.pi) / 2 * n)
    return x, y


def quadkey(x: int, y: int, z: int) -> str:
    """Bing/Web-Mercator quadkey string of tile (x, y) at zoom z."""
    digits = []
    for i in range(z, 0, -1):
        mask = 1 << (i - 1)
        digits.append(str((1 if x & mask else 0) + (2 if y & mask else 0)))
    return "".join(digits)


def chm_tiles(bbox=config.BBOX, version: str = "v1") -> list[str]:
    """Quadkeys of the canopy-height tiles covering ``bbox``."""
    z = CHM[version]["zoom"]
    x0, y1 = _tile_xy(bbox[0], bbox[1], z)
    x1, y0 = _tile_xy(bbox[2], bbox[3], z)
    return [quadkey(x, y, z) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def chm_url(qk: str, version: str = "v1") -> str:
    return f"/vsicurl/{CHM[version]['base']}/chm/{qk}.tif"


def chm_window(bbox, version: str = "v1", max_pixels: int = 25_000_000) -> tuple[np.ndarray, Affine]:
    """Canopy height (m) at full 1.2 m resolution for a *small* lon/lat bbox (one ward, a park...).

    Refuses large areas — use :func:`canopy_fraction` for the whole city.
    """
    from rasterio.merge import merge

    srcs = []
    for qk in chm_tiles(bbox, version):
        srcs.append(rasterio.open(chm_url(qk, version)))
    try:
        b = transform_bounds(4326, "EPSG:3857", *bbox)
        npx = ((b[2] - b[0]) / 1.1943) * ((b[3] - b[1]) / 1.1943)
        if npx > max_pixels:
            raise ValueError(f"bbox covers {npx/1e6:.0f} M pixels; use canopy_fraction() for large areas")
        arr, tr = merge(srcs, bounds=b, nodata=255)
    finally:
        for s in srcs:
            s.close()
    a = arr[0].astype("float32")
    a[arr[0] == 255] = np.nan
    return a, tr


def canopy_fraction(grid: Grid, version: str = "v1", threshold_m: float = 3.0, agg: int = 8, strip: int = 2048, progress=None) -> np.ndarray:
    """Fraction of each ``grid`` pixel covered by tree canopy taller than ``threshold_m``.

    Streams each canopy-height tile in horizontal strips, thresholds at 1.2 m,
    averages ``agg x agg`` blocks (~9.6 m) in Web Mercator, and finally
    reprojects the fractions to ``grid`` with area-weighted averaging.
    """
    spec = CHM[version]
    tile_size = 2 * _WEB_MERC_HALF / 2 ** spec["zoom"]
    px = tile_size / spec["tile_px"]
    cres = px * agg
    b = transform_bounds(grid.crs, "EPSG:3857", *grid.bounds)
    # mosaic lattice snapped to the global CHM pixel lattice
    left = -_WEB_MERC_HALF + math.floor((b[0] + _WEB_MERC_HALF) / cres) * cres
    top = _WEB_MERC_HALF - math.floor((_WEB_MERC_HALF - b[3]) / cres) * cres
    W = int(math.ceil((b[2] - left) / cres))
    H = int(math.ceil((top - b[1]) / cres))
    mosaic = np.full((H, W), np.nan, dtype="float32")
    mtr = Affine(cres, 0, left, 0, -cres, top)
    tiles = chm_tiles(version=version)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="3", GDAL_CACHEMAX=512):
        for ti, qk in enumerate(tiles):
            with rasterio.open(chm_url(qk, version)) as src:
                ib = (max(b[0], src.bounds.left), max(b[1], src.bounds.bottom), min(b[2], src.bounds.right), min(b[3], src.bounds.top))
                if ib[0] >= ib[2] or ib[1] >= ib[3]:
                    continue
                win = outer_window(from_bounds(*ib, src.transform))
                # align window to agg-pixel blocks of the global lattice
                c0 = (int(win.col_off) // agg) * agg
                r0 = (int(win.row_off) // agg) * agg
                c1 = min(src.width, int(math.ceil((win.col_off + win.width) / agg)) * agg)
                r1 = min(src.height, int(math.ceil((win.row_off + win.height) / agg)) * agg)
                for rs in range(r0, r1, strip):
                    re_ = min(r1, rs + strip)
                    a = src.read(1, window=((rs, re_), (c0, c1)))
                    m = (a >= threshold_m).astype("float32")
                    if spec["nodata"] is not None:
                        m[a == spec["nodata"]] = np.nan
                    frac = block_mean(m, agg)
                    # place into mosaic
                    x_left = src.transform.c + c0 * px
                    y_top = src.transform.f - rs * px
                    mc = int(round((x_left - left) / cres))
                    mr = int(round((top - y_top) / cres))
                    hh, ww = frac.shape
                    rr0, cc0 = max(mr, 0), max(mc, 0)
                    rr1, cc1 = min(mr + hh, H), min(mc + ww, W)
                    if rr1 > rr0 and cc1 > cc0:
                        mosaic[rr0:rr1, cc0:cc1] = frac[rr0 - mr : rr1 - mr, cc0 - mc : cc1 - mc]
                    if progress:
                        progress(ti, len(tiles), rs, r1)
    return reproject_array(mosaic, mtr, "EPSG:3857", grid, resampling=Resampling.average)
