"""Early warning: *when* is it dangerous, and for which wards?

The satellite layers say *where* (lesson 3's ward risk). The warning says *when*, from the forecast
high air temperature read off one fixed Bengaluru gauge, the same every day of the year:

    forecast high ──▶ level: below 33 °C, warm 33, hot 34, very hot 35, extreme 36
    city level + ward risk class ──▶ ward alert

India's heat-wave rule starts at 40 °C, which Bengaluru (920 m) has not reached since 1991 (ERA5).
33 °C is hotter than about 9 in 10 days of 1991-2020, and each level is one degree more. A real
system would set these lines from local hospital and death records.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

LINES = (33.0, 34.0, 35.0, 36.0)  # °C, the forecast high at which warm, hot, very hot and extreme start
WORDS = ["below the alert line", "warm", "hot", "very hot", "extreme"]  # the five levels, in plain words


def climatology(daily: pd.DataFrame, base=(1991, 2020), window: int = 15) -> pd.DataFrame:
    """The average highest and lowest air temperature for every day of the year (±``window`` days), over ``base`` years."""
    d = daily.loc[str(base[0]) : str(base[1]), ["tmax", "tmin"]].copy()
    d["doy"] = d.index.dayofyear
    rows = {}
    for doy in range(1, 367):
        gap = (d["doy"] - doy).abs()
        sub = d[np.minimum(gap, 366 - gap) <= window]
        rows[doy] = {"tmax_mean": sub["tmax"].mean(), "tmin_mean": sub["tmin"].mean()}
    out = pd.DataFrame.from_dict(rows, orient="index")
    out.index.name = "doy"
    return out


def levels(daily: pd.DataFrame, lines=LINES, normal: pd.DataFrame | None = None) -> pd.DataFrame:
    """The level (0-4) of every day in ``daily`` from its highest air temperature, with the level in words.

    With ``normal`` (from :func:`climatology`) it also adds the average high for each date.
    """
    out = daily[["tmax", "tmin"]].copy()
    out["level"] = np.digitize(out["tmax"], lines)
    out["in words"] = out["level"].map(lambda k: WORDS[k])
    if normal is not None:
        out["tmax_normal"] = normal.loc[out.index.dayofyear, "tmax_mean"].to_numpy()
    return out


# ---------------------------------------------------------------------------
# Impact-based ward alerts
# ---------------------------------------------------------------------------
ALERTS = {0: "No alert", 1: "Take care", 2: "Heat alert", 3: "Emergency"}

# rows: city level 0..4, columns: ward risk class
ALERT_MATRIX = pd.DataFrame(
    {"Low": [0, 0, 1, 2, 3], "Medium": [0, 1, 1, 2, 3], "High": [0, 1, 2, 3, 3]},
    index=pd.Index(range(5), name="city_level"),
)


def ward_alerts(level: int, ward_class: pd.Series, matrix: pd.DataFrame = ALERT_MATRIX) -> pd.Series:
    """The alert for every ward (No alert ... Emergency), given the city's level for the day and each ward's risk."""
    cls = ward_class.replace({"Excluded": "Low"})
    return cls.map(lambda c: ALERTS[int(matrix.loc[level, c])])
