"""30 m layers -> the 240 m cell table lessons 1 and 2 draw.

    30 m rasters ──8×8 block average──▶ pixel_table (one row per 240 m cell)

Temperatures in °C, fractions 0-1.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import datapack
from .grid import block_mean, city_grid, ward_labels
from .wards import load_wards


def pixel_table(factor: int = 8, wards=None) -> pd.DataFrame:
    """The 30 m layers averaged to ``30 × factor`` m cells (240 m by default), cells inside the city only.

    Small enough (~12 000 rows) to draw every cell as an interactive chart in the browser.
    Columns: ``col``, ``row`` (cell position, row 0 = north), ``ward_uid``, ``ward``, day/night surface
    temperature, tree canopy, built-up, water and farmland shares, and the cover type.
    """
    wards = wards if wards is not None else load_wards()
    g30 = city_grid(30)
    lab = ward_labels(wards, g30.coarsen(factor))
    L = datapack.layer
    built = L("built_frac")
    layers = {
        "lst_day": L("lst_day"),
        "lst_night": L("lst_night"),
        "canopy": L("canopy_frac"),
        "built": built,
        "water": L("water_frac"),
        "farmland": L("crop_frac"),
    }
    agg = {k: block_mean(v, factor) for k, v in layers.items()}
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
    for c in ("lst_day", "lst_night"):
        df[c] = df[c].round(1)
    for c in ("canopy", "built", "water", "farmland"):
        df[c] = df[c].round(2)
    return df.reset_index(drop=True)
