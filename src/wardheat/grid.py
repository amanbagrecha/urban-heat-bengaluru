"""The 30 m analysis grid, reprojection onto it, and ward zonal statistics.

Every raster in the workshop is brought onto ONE grid (same CRS, same pixel
edges, same shape). Once that is true, combining layers is plain numpy
arithmetic, and ward statistics are a ``bincount`` over a label raster.

    sources (10 m, 30 m, 100 m, 1 km; various CRSs)
                     |  reproject / resample once
                     v
            30 m UTM grid  (Grid)
                     |  label raster of ward ids
                     v
            ward table  (zonal_stats)
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from functools import cached_property

import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from affine import Affine
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.vrt import WarpedVRT

from . import config

# Landsat Collection 2 pixel edges over Bengaluru sit at x, y = 15 (mod 30).
# Snapping our grid to the same edges means the thermal band is never resampled.
_LANDSAT_OFFSET = 15.0


@dataclass(frozen=True)
class Grid:
    """A north-up raster grid: CRS + affine transform + shape."""

    crs: str
    transform: Affine
    width: int
    height: int

    @property
    def res(self) -> float:
        return self.transform.a

    @property
    def shape(self) -> tuple[int, int]:
        return (self.height, self.width)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        left, top = self.transform.c, self.transform.f
        return (left, top - self.height * self.res, left + self.width * self.res, top)

    @cached_property
    def x(self) -> np.ndarray:
        """Pixel-centre x coordinates."""
        return self.transform.c + (np.arange(self.width) + 0.5) * self.res

    @cached_property
    def y(self) -> np.ndarray:
        """Pixel-centre y coordinates (descending)."""
        return self.transform.f - (np.arange(self.height) + 0.5) * self.res

    @property
    def pixel_area(self) -> float:
        return self.res * self.res

    def geobox(self):
        """The equivalent ``odc.geo.GeoBox`` (used by odc-stac to load STAC items)."""
        from odc.geo.geobox import GeoBox

        return GeoBox((self.height, self.width), self.transform, self.crs)

    def refine(self, factor: int) -> "Grid":
        """A finer grid nested exactly inside this one (e.g. 30 m -> 10 m with factor 3)."""
        t = self.transform
        return Grid(
            self.crs,
            Affine(t.a / factor, 0, t.c, 0, t.e / factor, t.f),
            self.width * factor,
            self.height * factor,
        )

    def coarsen(self, factor: int) -> "Grid":
        t = self.transform
        return Grid(
            self.crs,
            Affine(t.a * factor, 0, t.c, 0, t.e * factor, t.f),
            int(np.ceil(self.width / factor)),
            int(np.ceil(self.height / factor)),
        )

    def to_xarray(self, data: np.ndarray, name: str | None = None, attrs: dict | None = None) -> xr.DataArray:
        """Wrap a 2-D numpy array as a georeferenced DataArray (rioxarray-aware)."""
        da = xr.DataArray(data, dims=("y", "x"), coords={"y": self.y, "x": self.x}, name=name, attrs=attrs or {})
        return da.rio.write_crs(self.crs).rio.write_transform(self.transform)

    def lonlat(self) -> tuple[np.ndarray, np.ndarray]:
        """2-D arrays of pixel-centre longitude and latitude."""
        xx, yy = np.meshgrid(self.x, self.y)
        tr = Transformer.from_crs(self.crs, 4326, always_xy=True)
        return tr.transform(xx, yy)


def city_grid(res: float = config.RES, bbox: tuple = config.BBOX, crs: str = config.CRS) -> Grid:
    """The workshop grid: ``bbox`` projected to UTM 43N and snapped to Landsat pixel edges."""
    tr = Transformer.from_crs(4326, crs, always_xy=True)
    xs, ys = tr.transform([bbox[0], bbox[2], bbox[0], bbox[2]], [bbox[1], bbox[1], bbox[3], bbox[3]])
    snap = 30.0  # always snap to the 30 m Landsat lattice, even for 10 m grids
    x0 = np.floor((min(xs) - _LANDSAT_OFFSET) / snap) * snap + _LANDSAT_OFFSET
    y1 = np.ceil((max(ys) - _LANDSAT_OFFSET) / snap) * snap + _LANDSAT_OFFSET
    x1 = np.ceil((max(xs) - _LANDSAT_OFFSET) / snap) * snap + _LANDSAT_OFFSET
    y0 = np.floor((min(ys) - _LANDSAT_OFFSET) / snap) * snap + _LANDSAT_OFFSET
    width = int(round((x1 - x0) / res))
    height = int(round((y1 - y0) / res))
    return Grid(crs, Affine(res, 0, x0, 0, -res, y1), width, height)


# ---------------------------------------------------------------------------
# Reading / reprojecting onto the grid
# ---------------------------------------------------------------------------
def read_to_grid(
    src: str,
    grid: Grid,
    resampling: Resampling = Resampling.bilinear,
    band: int = 1,
    nodata: float | None = None,
    dtype: str = "float32",
) -> np.ndarray:
    """Read any GDAL-readable raster (local path, URL, /vsicurl/...) warped onto ``grid``.

    Uses a ``WarpedVRT`` so only the pixels covering the grid are fetched,
    which is what makes Cloud-Optimized GeoTIFFs fast over HTTP.
    Nodata pixels come back as NaN.
    """
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="3"):
        with rasterio.open(src) as ds:
            src_nodata = ds.nodata if nodata is None else nodata
            with WarpedVRT(
                ds,
                crs=grid.crs,
                transform=grid.transform,
                width=grid.width,
                height=grid.height,
                resampling=resampling,
                src_nodata=src_nodata,
                nodata=src_nodata,
            ) as vrt:
                arr = vrt.read(band, out_dtype=dtype, masked=True)
    return arr.filled(np.nan) if np.issubdtype(np.dtype(dtype), np.floating) else arr.filled(0)


def reproject_array(
    data: np.ndarray,
    src_transform: Affine,
    src_crs,
    grid: Grid,
    resampling: Resampling = Resampling.bilinear,
    src_nodata: float | None = np.nan,
) -> np.ndarray:
    """Reproject an in-memory array onto ``grid`` (NaN = nodata)."""
    from rasterio.warp import reproject

    out = np.full(grid.shape, np.nan, dtype="float32")
    reproject(
        source=data.astype("float32"),
        destination=out,
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=grid.transform,
        dst_crs=grid.crs,
        resampling=resampling,
        src_nodata=src_nodata,
        dst_nodata=np.nan,
    )
    return out


def block_mean(arr: np.ndarray, factor: int) -> np.ndarray:
    """Aggregate a fine grid to a coarse one by averaging ``factor x factor`` blocks (NaN-aware).

    With a boolean/0-1 input this returns the *fraction* of each coarse cell,
    e.g. a 10 m tree mask -> 30 m tree-cover fraction.
    """
    h, w = arr.shape
    H, W = int(np.ceil(h / factor)), int(np.ceil(w / factor))
    pad = np.full((H * factor, W * factor), np.nan, dtype="float32")
    pad[:h, :w] = arr
    blocks = pad.reshape(H, factor, W, factor)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN blocks -> NaN
        return np.nanmean(blocks, axis=(1, 3)).astype("float32")


def outer_window(win):
    """Expand a fractional rasterio Window to whole pixels (floor offsets, ceil far edges)."""
    from rasterio.windows import Window

    c0, r0 = int(np.floor(win.col_off)), int(np.floor(win.row_off))
    c1 = int(np.ceil(win.col_off + win.width))
    r1 = int(np.ceil(win.row_off + win.height))
    return Window(c0, r0, c1 - c0, r1 - r0)


def save_geotiff(path, arr: np.ndarray, grid: Grid, nodata=np.nan, scale: float | None = None, **tags) -> None:
    """Write a single-band Cloud-Optimized GeoTIFF on ``grid``.

    With ``scale`` (e.g. ``1e-4`` for albedo, ``0.01`` for a 0-1 fraction) a float
    array is stored as integers ``round(value / scale)`` and the scale is written
    into the file, which shrinks continuous 10 m layers 3-8x. :func:`load_geotiff`
    applies it back transparently.
    """
    if scale is not None:
        lo, hi = np.nanmin(arr) / scale, np.nanmax(arr) / scale
        dtype, nod = ("uint8", 255) if lo >= 0 and hi <= 254 else ("int16", -32768)
        data = np.where(np.isfinite(arr), np.round(arr / scale), nod).astype(dtype)
        arr, nodata = data, nod
    profile = dict(
        driver="COG",
        dtype=str(arr.dtype),
        width=grid.width,
        height=grid.height,
        count=1,
        crs=grid.crs,
        transform=grid.transform,
        nodata=nodata,
        compress="ZSTD",
        predictor=3 if np.issubdtype(arr.dtype, np.floating) else 2,
        overview_resampling="average" if scale is None else "nearest",
    )
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr, 1)
        if scale is not None:
            dst.scales = (scale,)
            dst.offsets = (0.0,)
        if tags:
            dst.update_tags(**{k: str(v) for k, v in tags.items()})


def load_geotiff(path, grid: Grid | None = None) -> np.ndarray:
    """Load a single-band GeoTIFF as float32 with NaN for nodata (optionally warped to ``grid``).

    Integer-coded layers written with a ``scale`` are converted back to physical values.
    """
    if grid is not None:
        return read_to_grid(str(path), grid)
    with rasterio.open(path) as ds:
        arr = ds.read(1, masked=True).astype("float32")
        scale, offset = ds.scales[0], ds.offsets[0]
    out = arr.filled(np.nan)
    if scale not in (None, 1.0) or offset not in (None, 0.0):
        out = out * np.float32(scale) + np.float32(offset)
    return out


# ---------------------------------------------------------------------------
# Wards -> label raster -> zonal statistics
# ---------------------------------------------------------------------------
def ward_labels(wards, grid: Grid, id_col: str = "ward_uid") -> np.ndarray:
    """Burn ward polygons into an int32 raster: pixel value = ward's integer id, 0 = outside.

    A pixel belongs to the ward that contains its centre (``all_touched=False``),
    so every pixel is counted exactly once.
    """
    w = wards.to_crs(grid.crs)
    shapes = zip(w.geometry, w[id_col].astype("int32"))
    return rasterize(shapes, out_shape=grid.shape, transform=grid.transform, fill=0, dtype="int32")


def zonal_stats(layers: dict[str, np.ndarray], labels: np.ndarray, stats=("mean",)) -> pd.DataFrame:
    """Per-ward statistics of one or more rasters that share the label raster's grid.

    ``stats`` may include ``mean``, ``sum``, ``count`` (valid pixels), ``median``,
    ``p10``/``p90`` style percentiles, ``min``, ``max``, ``std``.
    NaN pixels are ignored. Returns one row per ward id (index ``ward_uid``).
    """
    n = int(labels.max()) + 1
    flat_lab = labels.ravel()
    inside = flat_lab > 0
    out = {}
    for name, arr in layers.items():
        v = np.asarray(arr, dtype="float64").ravel()
        ok = inside & np.isfinite(v)
        lab, val = flat_lab[ok], v[ok]
        simple = {s for s in stats if s in ("mean", "sum", "count")}
        if simple:
            s = np.bincount(lab, weights=val, minlength=n)
            c = np.bincount(lab, minlength=n).astype("float64")
            if "sum" in simple:
                out[f"{name}_sum"] = s
            if "count" in simple:
                out[f"{name}_count"] = c
            if "mean" in simple:
                with np.errstate(invalid="ignore", divide="ignore"):
                    out[f"{name}_mean"] = np.where(c > 0, s / c, np.nan)
        other = [s for s in stats if s not in ("mean", "sum", "count")]
        if other:
            g = pd.Series(val).groupby(lab)
            for s in other:
                if s.startswith("p") and s[1:].isdigit():
                    r = g.quantile(int(s[1:]) / 100)
                else:
                    r = getattr(g, s)()
                out[f"{name}_{s}"] = r.reindex(range(n)).to_numpy()
    df = pd.DataFrame(out)
    df.index.name = "ward_uid"
    return df.iloc[1:]  # drop label 0 (outside every ward)
