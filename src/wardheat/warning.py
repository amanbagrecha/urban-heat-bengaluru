"""Early warning: *when* is it dangerous, and for which wards?

The satellite layers are static ("where is vulnerable"). The warning layer is
dynamic ("is tomorrow dangerous for this place at this time of year?").
We adapt the logic of the US National Weather Service **HeatRisk** product
(the engine behind heat.gov's 7-day heat map) to Bengaluru:

    forecast Tmax, Tmin ──▶ compare with local day-of-year climatology
                              (how unusual is it HERE, NOW?)
                        ──▶ day level + night level (no overnight relief)
                        ──▶ bump for duration (consecutive hot days+nights)
                        ──▶ city HeatRisk level 0-4
    city level × ward risk class ──▶ ward alert

Why percentiles instead of IMD's absolute 40 °C rule? Bengaluru (920 m
altitude) almost never reaches 40 °C, so an absolute threshold never fires,
yet people are acclimatised to ~33-35 °C and health impacts start well below
40 °C. A *relative* threshold adapts to local acclimatisation. A real system
would then calibrate those thresholds against local mortality / hospital
admission data, as the US CDC did for HeatRisk.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

LEVELS = {
    0: ("Green", "Little to no risk"),
    1: ("Yellow", "Minor: risk to the most heat-sensitive"),
    2: ("Orange", "Moderate: risk to sensitive groups and anyone outdoors for long"),
    3: ("Red", "Major: risk to anyone without cooling or water"),
    4: ("Magenta", "Extreme: rare, long heat, impacts likely for everyone"),
}

# percentile cut points (of the local, day-of-year climatology) for levels 1..4
DEFAULT_CUTS = {"tmax": (90, 95, 98, 99.5), "tmin": (90, 95, 98, 99.5)}


def pcol(var: str, p: float) -> str:
    """Column name of a climatology percentile: ``pcol('tmax', 95.0) == 'tmax_p95'``, 99.5 -> ``tmax_p99_5``."""
    return f"{var}_p{p:g}".replace(".", "_")


def climatology(daily: pd.DataFrame, base=(1991, 2020), window: int = 15, pcts=(50, 90, 95, 98, 99.5)) -> pd.DataFrame:
    """Day-of-year percentiles of Tmax and Tmin using a ±``window``-day moving window.

    Returns a frame indexed by day-of-year (1..366) with columns like ``tmax_p95``, plus the
    same percentiles over *all* days of the year (``tmax_ann_p95``, constant), used as an
    absolute floor by :func:`heatrisk`.
    """
    d = daily.loc[str(base[0]) : str(base[1]), ["tmax", "tmin"]].copy()
    d["doy"] = d.index.dayofyear
    annual = {pcol(v, p).replace("_p", "_ann_p"): np.percentile(d[v], p) for v in ("tmax", "tmin") for p in pcts}
    rows = {}
    for doy in range(1, 367):
        dist = (d["doy"] - doy).abs()
        dist = np.minimum(dist, 366 - dist)
        sub = d[dist <= window]
        rows[doy] = {pcol(v, p): np.percentile(sub[v], p) for v in ("tmax", "tmin") for p in pcts}
        rows[doy].update(tmax_mean=sub["tmax"].mean(), tmin_mean=sub["tmin"].mean(), **annual)
    out = pd.DataFrame.from_dict(rows, orient="index")
    out.index.name = "doy"
    return out


def _level(value: float, thresholds: list[float]) -> int:
    return int(sum(value >= t for t in thresholds))


def heatrisk(fc: pd.DataFrame, clim: pd.DataFrame, cuts: dict = DEFAULT_CUTS, duration_days: int = 2,
             annual_floor: bool = True) -> pd.DataFrame:
    """Daily HeatRisk-style level (0-4) for a forecast (or observed) frame with ``tmax``, ``tmin``.

    * a threshold is crossed when the value is unusual **for the date** (day-of-year percentile)
      **and**, with ``annual_floor``, at least as high as the same percentile over all days of
      the year — a transparent stand-in for HeatRisk's health-based thresholds, so that a
      warm-for-October 31 °C day does not raise an alarm
    * day level  = how many Tmax thresholds are exceeded
    * night level = same for Tmin (warm nights = no recovery)
    * level = max(day, night)
    * +1 (max 4) when both Tmax and Tmin have been above their P95 threshold for ``duration_days`` days in a row
    """
    col = pcol
    out = fc[["tmax", "tmin"]].copy()
    doy = out.index.dayofyear

    def thr_for(v, p):
        t = clim.loc[doy, col(v, p)].to_numpy()
        ann = col(v, p).replace("_p", "_ann_p")
        return np.maximum(t, clim.loc[doy, ann].to_numpy()) if annual_floor and ann in clim else t

    for v in ("tmax", "tmin"):
        thr = np.stack([thr_for(v, p) for p in cuts[v]], axis=1)
        out[f"{v}_level"] = [_level(x, t) for x, t in zip(out[v], thr)]
        out[f"{v}_normal"] = clim.loc[doy, f"{v}_mean"].to_numpy()
        out[f"{v}_p95"] = thr_for(v, 95)
        out[f"{v}_anom"] = out[v] - out[f"{v}_normal"]
    out["level"] = out[["tmax_level", "tmin_level"]].max(axis=1)
    both_hot = (out["tmax"] >= out["tmax_p95"]) & (out["tmin"] >= out["tmin_p95"])
    run = both_hot.groupby((~both_hot).cumsum()).cumsum()
    out["consecutive_hot"] = run
    out["duration_bump"] = (run >= duration_days).astype(int)
    out["level"] = (out["level"] + out["duration_bump"]).clip(upper=4)
    out["name"] = out["level"].map(lambda k: LEVELS[k][0])
    return out


def imd_heatwave(fc: pd.DataFrame, clim: pd.DataFrame) -> pd.Series:
    """IMD criteria for plains stations: Tmax >= 40 °C AND >= 4.5 °C above normal, or Tmax >= 45 °C."""
    normal = clim.loc[fc.index.dayofyear, "tmax_mean"].to_numpy()
    dep = fc["tmax"] - normal
    severe = ((fc["tmax"] >= 40) & (dep >= 6.5)) | (fc["tmax"] >= 47)
    hw = ((fc["tmax"] >= 40) & (dep >= 4.5)) | (fc["tmax"] >= 45)
    return pd.Series(np.where(severe, "Severe heatwave", np.where(hw, "Heatwave", "—")), index=fc.index)


# ---------------------------------------------------------------------------
# Impact-based ward alerts
# ---------------------------------------------------------------------------
ALERTS = {0: "No alert", 1: "Advisory", 2: "Heat alert", 3: "Heat emergency"}

# rows: city HeatRisk level 0..4, columns: ward risk class
ALERT_MATRIX = pd.DataFrame(
    {"Low": [0, 0, 1, 2, 3], "Medium": [0, 1, 1, 2, 3], "High": [0, 1, 2, 3, 3]},
    index=pd.Index(range(5), name="heatrisk_level"),
)


def ward_alerts(level: int, ward_class: pd.Series, matrix: pd.DataFrame = ALERT_MATRIX) -> pd.Series:
    """Alert level 0-3 for every ward given today's city HeatRisk level and each ward's risk class."""
    cls = ward_class.replace({"Excluded": "Low"})
    return cls.map(lambda c: int(matrix.loc[level, c]))
