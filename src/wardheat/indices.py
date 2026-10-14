"""Ward heat risk = surface temperature × crowding × lack of shade (hazard × exposure × vulnerability, IPCC AR6).

Each ingredient is rescaled from 0 (the city's lowest ward) to 1 (its highest): surface temperature (the
average of the 10:40 am Landsat and night MODIS values, °C), people per hectare (Census 2011 headcount ÷
ward area), and lack of tree cover
(1 = the ward with the fewest trees). Multiplying them means a ward only scores high when all three are
high. Top 30 % of wards → High, next 30 % → Medium, the rest → Low.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CLASS_ORDER = ["Low", "Medium", "High"]


def scale(x: pd.Series) -> pd.Series:
    """0 = the city's lowest ward, 1 = its highest."""
    return (x - x.min()) / (x.max() - x.min())


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
    f = zonal_stats({"day_surface_temp": datapack.layer("lst_day"),
                     "night_surface_temp": datapack.layer("lst_night"),
                     "trees": datapack.layer("canopy_frac")}, labels)
    f = f.rename(columns=lambda c: c.removesuffix("_mean"))
    w = wards.set_index("ward_uid")
    f.insert(0, "ward", w["label"])
    f["people_per_ha"] = w["census2011_pop"] / (w["area_km2"] * 100)
    f["surface_temp"] = (f.day_surface_temp + f.night_surface_temp) / 2
    return f.round({"day_surface_temp": 2, "night_surface_temp": 2, "surface_temp": 2, "trees": 3, "people_per_ha": 0})


def ward_risk(f: pd.DataFrame) -> pd.DataFrame:
    """Surface temperature, crowding and lack of shade, each from 0 (lowest ward) to 1 (highest), their product and the class."""
    H = scale(f["surface_temp"])  # surface (satellite), average of morning and night
    E = scale(f["people_per_ha"])  # more crowded
    V = scale(-f["trees"])  # fewer trees
    score = H * E * V
    return pd.DataFrame({"H": H, "E": E, "V": V, "score": score, "risk": classify(score)}, index=f.index)
