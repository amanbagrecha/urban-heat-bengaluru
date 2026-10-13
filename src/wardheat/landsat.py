"""Landsat 8/9 Collection 2 Level-2 land surface temperature (LST).

USGS already corrects the thermal band ``ST_B10`` (asset ``lwir11``) for the
atmosphere and surface emissivity. Overpass is ~10:40 IST. Scale factors:

    LST [K]           = DN * 0.00341802 + 149.0
    ST uncertainty K  = DN * 0.01        (asset ``qa``,    band ST_QA)
    cloud distance km = DN * 0.01        (asset ``cdist``, band ST_CDIST)
"""

from __future__ import annotations

import xarray as xr

from .grid import Grid

ST_SCALE, ST_OFFSET = 0.00341802, 149.0
BANDS = ["lwir11", "qa", "cdist", "qa_pixel"]

# QA_PIXEL bit flags (Collection 2)
QA_BITS = {"fill": 0, "dilated_cloud": 1, "cirrus": 2, "cloud": 3, "cloud_shadow": 4, "snow": 5, "water": 7}


def qa_mask(qa_pixel: xr.DataArray, bits=("fill", "dilated_cloud", "cirrus", "cloud", "cloud_shadow")) -> xr.DataArray:
    """True where the pixel is *clear* (none of the given QA_PIXEL bits are set)."""
    flags = sum(1 << QA_BITS[b] for b in bits)
    return (qa_pixel.astype("uint16") & flags) == 0


def load(items: list, grid: Grid, bands=BANDS, pool: int = 8) -> xr.Dataset:
    """Read the requested bands of every item straight onto ``grid`` (no resampling for Landsat)."""
    import odc.stac

    return odc.stac.load(items, bands=bands, geobox=grid.geobox(), groupby="solar_day",
                         resampling="nearest", pool=pool, fail_on_error=False)


def to_physical(ds: xr.Dataset, max_st_uncertainty_k: float = 5.0, min_cloud_distance_km: float = 0.3) -> xr.Dataset:
    """DN -> °C, keeping only clear pixels (QA bits, <= 5 K uncertainty, >= 300 m from cloud)."""
    clear = qa_mask(ds["qa_pixel"]) & (ds["lwir11"] > 0)
    if "qa" in ds:
        clear = clear & (ds["qa"] * 0.01 <= max_st_uncertainty_k)
    if "cdist" in ds:
        clear = clear & (ds["cdist"] * 0.01 >= min_cloud_distance_km)
    out = xr.Dataset(coords=ds.coords)
    out["lst"] = (ds["lwir11"] * ST_SCALE + ST_OFFSET - 273.15).where(clear).astype("float32")
    out["clear"] = clear
    return out


def median_composite(phys: xr.Dataset, min_obs: int = 3) -> xr.Dataset:
    """Per-pixel median across all clear scenes; pixels with fewer than ``min_obs`` clear looks -> NaN."""
    n = phys["lst"].notnull().sum("time")
    comp = phys[["lst"]].median("time", skipna=True).where(n >= min_obs)
    comp["n_obs"] = n.astype("int16")
    return comp


def scene_stats(phys: xr.Dataset) -> "pd.DataFrame":  # noqa: F821
    """One row per scene: clear fraction and city-mean LST."""
    import pandas as pd

    clear = phys["clear"].mean(("y", "x")).to_series()
    mean_lst = phys["lst"].mean(("y", "x"), skipna=True).to_series()
    return pd.DataFrame({"clear_fraction": clear, "mean_lst": mean_lst})
