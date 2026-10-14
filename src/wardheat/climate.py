"""Air temperature: climatology (ERA5 reanalysis) and forecasts, via the Open-Meteo API.

Satellites tell us *where* a city is hot. An early-warning system also needs
to know *when*: tomorrow's forecast, compared with what is normal for this
place at this time of year. Open-Meteo (open-source, no API key for
non-commercial use) serves both:

* ``archive-api.open-meteo.com``  ERA5 reanalysis, 1940 -> ~5 days ago (~25 km)
* ``api.open-meteo.com``          16-day forecasts from national weather models
"""

from __future__ import annotations

import pandas as pd
import requests

# Bengaluru city centre (Vidhana Soudha); ERA5 is ~25 km so one point represents the city.
CITY_POINT = (12.9794, 77.5907)

DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "relative_humidity_2m_mean",
    "apparent_temperature_max",
]
FORECAST_VARS = DAILY_VARS + ["wet_bulb_temperature_2m_max"]


def _to_frame(js: dict) -> pd.DataFrame:
    d = pd.DataFrame(js["daily"])
    d["time"] = pd.to_datetime(d["time"])
    return d.set_index("time").rename(
        columns={
            "temperature_2m_max": "tmax",
            "temperature_2m_min": "tmin",
            "temperature_2m_mean": "tmean",
            "relative_humidity_2m_mean": "rh_mean",
            "apparent_temperature_max": "feels_like_max",
            "wet_bulb_temperature_2m_max": "wetbulb_max",
        }
    )


def _session() -> requests.Session:
    """A requests session that tries again (up to 4 times) when the connection drops or the service is busy."""
    from requests.adapters import HTTPAdapter, Retry

    s = requests.Session()
    s.mount("https://", HTTPAdapter(max_retries=Retry(total=4, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])))
    return s


def today() -> pd.Timestamp:
    """Today's date in Bengaluru (computers in other time zones may already be on another day)."""
    return pd.Timestamp.now(tz="Asia/Kolkata").normalize().tz_localize(None)


def era5_daily(start: str = "1991-01-01", end: str = "2025-12-31", point=CITY_POINT, model: str = "era5") -> pd.DataFrame:
    """Daily ERA5 history for one point (°C, %)."""
    r = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params=dict(latitude=point[0], longitude=point[1], start_date=start, end_date=end,
                    daily=",".join(DAILY_VARS), timezone="Asia/Kolkata", models=model),
        timeout=120,
    )
    r.raise_for_status()
    return _to_frame(r.json())


def forecast(days: int = 7, point=CITY_POINT, past_days: int = 0, bias_correct: bool = True) -> pd.DataFrame:
    """Daily forecast for the next ``days`` days (default model blend chosen by Open-Meteo).

    Forecast models and ERA5 do not agree exactly (at Bengaluru the forecast models run
    ~1 °C warmer in Tmax in March-May). Because warnings compare the forecast with an ERA5
    climatology, we subtract the monthly mean difference (``forecast_bias`` table in the
    data pack) — otherwise model bias alone would raise false alarms.
    """
    r = _session().get(
        "https://api.open-meteo.com/v1/forecast",
        params=dict(latitude=point[0], longitude=point[1], daily=",".join(FORECAST_VARS),
                    timezone="Asia/Kolkata", forecast_days=days, past_days=past_days),
        timeout=60,
    )
    r.raise_for_status()
    fc = _to_frame(r.json())
    if bias_correct:
        fc = remove_bias(fc)
    return fc


def historical_forecast(start: str, end: str, point=CITY_POINT) -> pd.DataFrame:
    """Archived forecast-model analyses (2022 onwards) — what the forecast models said at the time."""
    r = requests.get(
        "https://historical-forecast-api.open-meteo.com/v1/forecast",
        params=dict(latitude=point[0], longitude=point[1], start_date=start, end_date=end,
                    daily="temperature_2m_max,temperature_2m_min", timezone="Asia/Kolkata"),
        timeout=120,
    )
    r.raise_for_status()
    return _to_frame(r.json())


def bias_table(era5: pd.DataFrame, start: str = "2022-01-01", end: str = "2026-09-30") -> pd.DataFrame:
    """Monthly mean (forecast model − ERA5) for Tmax and Tmin."""
    h = historical_forecast(start, end)
    e = era5.loc[start:end, ["tmax", "tmin"]]
    diff = (h[["tmax", "tmin"]] - e).dropna()
    out = diff.groupby(diff.index.month).mean().rename(columns={"tmax": "tmax_bias", "tmin": "tmin_bias"})
    out.index.name = "month"
    return out


def remove_bias(fc: pd.DataFrame) -> pd.DataFrame:
    """Subtract the monthly forecast-minus-ERA5 bias, a small prepared table."""
    from . import datapack

    b = datapack.table("forecast_bias")
    fc = fc.copy()
    m = fc.index.month
    fc["tmax"] = fc["tmax"] - b["tmax_bias"].reindex(m).fillna(0).to_numpy()
    fc["tmin"] = fc["tmin"] - b["tmin_bias"].reindex(m).fillna(0).to_numpy()
    return fc
