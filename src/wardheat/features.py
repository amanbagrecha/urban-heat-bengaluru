"""Pixel layers -> tables the lessons use.

    30 m rasters ──zonal statistics──▶ ward_features (one row per ward, 369 rows)
    30 m rasters ──8×8 block average──▶ pixel_table (one row per 240 m cell)

Conventions
-----------
* ``lst_built`` is the mean daytime LST over **built-up pixels only**. In
  March-May dry fields around the city are hotter than the city by day, so we
  measure heat where people actually live and work.
* ``pop`` is Census-2011 ward totals spread inside each ward by WorldPop 2025.
* ``*_anom`` columns are differences from the city-wide mean.
* Temperatures in °C, fractions 0-1, areas in km².
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import datapack
from .grid import block_mean, city_grid, ward_labels, zonal_stats
from .wards import load_wards


def build_ward_features(wards=None) -> pd.DataFrame:
    """One row per ward: heat by day and night, land cover, tree canopy, people."""
    wards = wards if wards is not None else load_wards()
    g30 = city_grid(30)
    lab = ward_labels(wards, g30)
    L = datapack.layer

    lst, lst_n = L("lst_day"), L("lst_night")
    built, crop = L("built_frac"), L("crop_frac")
    in_city = lab > 0
    urban = ~(crop > 0.5)  # leave out pixels that are mostly farmland
    lst_u = np.where(urban, lst, np.nan)
    lst_b = np.where(built >= 0.5, lst, np.nan)

    means = zonal_stats(
        {
            "lst_day": lst_u,
            "lst_built": lst_b,
            "lst_night": lst_n,
            "built_frac": built,
            "veg_frac": L("veg_frac"),
            "crop_frac": crop,
            "water_frac": L("water_frac"),
            "canopy_frac": np.where(urban, L("canopy_frac"), np.nan),
        },
        lab,
    ).rename(columns=lambda c: c.removesuffix("_mean"))
    sums = zonal_stats({"pop": L("pop"), "built_pixels": (built >= 0.5).astype("float32")}, lab, stats=("sum",))
    sums = sums.rename(columns=lambda c: c.removesuffix("_sum"))

    keep = ["ward_uid", "corporation", "ward_no", "ward_name", "zone", "label", "area_km2", "census2011_pop"]
    f = wards[keep].set_index("ward_uid").join(means).join(sums)
    f["lst_day_anom"] = f["lst_day"] - np.nanmean(lst_u[in_city])
    f["lst_built_anom"] = f["lst_built"] - np.nanmean(lst_b[in_city])
    f["lst_night_anom"] = f["lst_night"] - np.nanmean(lst_n[in_city])
    f["pop_density"] = f["pop"] / f["area_km2"]
    return f.reset_index()


def pixel_table(factor: int = 8, wards=None) -> pd.DataFrame:
    """The 30 m layers averaged to ``30 × factor`` m cells (240 m by default), cells inside the city only.

    Small enough (~12 000 rows) to draw every cell as an interactive chart in the browser.
    Columns: ``col``, ``row`` (cell position, row 0 = north), ``ward_uid``, ``ward``, day/night LST,
    tree canopy, built-up, water and farmland shares, people per hectare.
    """
    wards = wards if wards is not None else load_wards()
    g30 = city_grid(30)
    lab = ward_labels(wards, g30.coarsen(factor))
    L = datapack.layer
    built = L("built_frac")
    layers = {
        "lst_day": L("lst_day"),
        "lst_built": np.where(built >= 0.5, L("lst_day"), np.nan),
        "lst_night": L("lst_night"),
        "canopy": L("canopy_frac"),
        "built": built,
        "water": L("water_frac"),
        "farmland": L("crop_frac"),
    }
    agg = {k: block_mean(v, factor) for k, v in layers.items()}
    pop = block_mean(np.nan_to_num(L("pop")), factor) * factor * factor  # people per cell
    agg["people_per_ha"] = pop / ((30 * factor) ** 2 / 1e4)
    rows, cols = np.nonzero(lab > 0)
    df = pd.DataFrame({"col": cols, "row": rows, "ward_uid": lab[rows, cols]})
    for k, v in agg.items():
        df[k] = v[rows, cols].astype("float64")
    df.insert(3, "ward", df["ward_uid"].map(wards.set_index("ward_uid")["label"]))
    df = df.dropna(subset=["lst_day"])
    df["cover"] = np.select(
        [df.water > 0.3, df.canopy > 0.35, df.farmland > 0.4, df.built > 0.6],
        ["water", "trees", "farmland", "built-up"],
        "mixed",
    )
    for c in ("lst_day", "lst_built", "lst_night"):
        df[c] = df[c].round(1)
    for c in ("canopy", "built", "water", "farmland"):
        df[c] = df[c].round(2)
    df["people_per_ha"] = df["people_per_ha"].round(0)
    return df.reset_index(drop=True)
