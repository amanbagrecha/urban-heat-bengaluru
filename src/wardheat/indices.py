"""Ward heat risk = surface temperature × crowding × lack of shade (hazard × exposure × vulnerability, IPCC AR6).

Each ingredient is a ward's place among the city's wards, from 0 to 1 (``rank(pct=True)``): 0.88 means 88 % of
wards are at or below it. Surface temperature is the average of the 10:40 am (Landsat) and night (MODIS) values (percentile ranks, as in the US CDC's Social Vulnerability Index). Multiplying them means a
ward only scores high when all three are high. Top 30 % of wards → High, next 30 % → Medium, the
rest → Low.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FLOOR = 0.05
CLASS_ORDER = ["Low", "Medium", "High"]


def scale01(x: pd.Series, floor: float = FLOOR) -> pd.Series:
    """0 = among the city's lowest 5 %, 1 = among the highest 5 %."""
    x = pd.Series(x, dtype="float64")
    lo, hi = np.nanpercentile(x, [5, 95])
    return ((x - lo) / (hi - lo)).clip(floor, 1)


def classify(score: pd.Series, cuts=(40, 70)) -> pd.Series:
    """Low / Medium / High by city percentiles of ``score``."""
    lo, hi = np.nanpercentile(score, cuts)
    return pd.Series(np.select([score >= hi, score >= lo], ["High", "Medium"], "Low"), index=score.index)


def ward_table(wards=None) -> pd.DataFrame:
    """One row per ward, averaged from the 30 m satellite maps exactly as lesson 3 does it."""
    from . import datapack
    from .grid import ward_labels, zonal_stats
    from .wards import load_wards

    wards = wards if wards is not None else load_wards()
    labels = ward_labels(wards, datapack.grid30())
    built_up = datapack.layer("built_frac") >= 0.5
    f = zonal_stats({"day_surface_temp": np.where(built_up, datapack.layer("lst_day"), np.nan),
                     "night_surface_temp": datapack.layer("lst_night"),
                     "trees": datapack.layer("canopy_frac"),
                     "people_per_ha": datapack.layer("pop") / 0.09}, labels)
    f = f.rename(columns=lambda c: c.removesuffix("_mean"))
    f.insert(0, "ward", wards.set_index("ward_uid")["label"])
    return f


def ward_risk(f: pd.DataFrame) -> pd.DataFrame:
    """Surface temperature, crowding and lack of shade as places among wards (0-1), their product and the class."""
    H = ((f["day_surface_temp"] + f["night_surface_temp"]) / 2).rank(pct=True)  # surface (satellite), morning and night
    E = f["people_per_ha"].rank(pct=True)  # more crowded
    V = (-f["trees"]).rank(pct=True)  # less tree shade
    score = H * E * V
    return pd.DataFrame({"H": H, "E": E, "V": V, "score": score, "risk": classify(score)}, index=f.index)
