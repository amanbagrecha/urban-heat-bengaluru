"""Environment check used by ``wardheat check`` and the first notebook."""

from __future__ import annotations

import importlib
import time

PACKAGES = ["marimo", "numpy", "pandas", "geopandas", "rasterio", "xarray", "odc.stac", "pystac_client",
            "planetary_computer", "altair", "matplotlib", "pooch"]

ENDPOINTS = {
    "Planetary Computer STAC": "https://planetarycomputer.microsoft.com/api/stac/v1",
    "Open-Meteo forecast": "https://api.open-meteo.com/v1/forecast?latitude=12.97&longitude=77.59&daily=temperature_2m_max&forecast_days=1",
    "Workshop files (GitHub)": None,  # filled in below: one small prepared file
}


def _fill_endpoints():
    from .datapack import DATA_URL

    ENDPOINTS["Workshop files (GitHub)"] = DATA_URL + "forecast_bias.parquet"


def check_packages() -> list[dict]:
    rows = []
    for name in PACKAGES:
        try:
            m = importlib.import_module(name)
            rows.append({"check": name, "ok": True, "detail": getattr(m, "__version__", "installed")})
        except Exception as e:  # noqa: BLE001
            rows.append({"check": name, "ok": False, "detail": str(e)[:80]})
    return rows


def check_network(timeout: float = 10) -> list[dict]:
    import requests

    _fill_endpoints()
    rows = []
    for name, url in ENDPOINTS.items():
        t0 = time.time()
        try:
            r = requests.get(url, timeout=timeout)
            rows.append({"check": name, "ok": r.ok, "detail": f"HTTP {r.status_code} in {time.time()-t0:.1f}s"})
        except Exception as e:  # noqa: BLE001
            rows.append({"check": name, "ok": False, "detail": type(e).__name__})
    return rows


def checks(network: bool = True):
    """One row per check: packages, then the internet services the lessons use."""
    import pandas as pd

    return pd.DataFrame(check_packages() + (check_network() if network else []))


def run_checks(verbose: bool = False, network: bool = True) -> bool:
    df = checks(network)
    if verbose:
        print(df.to_string(index=False))
    return bool(df.ok.all())
