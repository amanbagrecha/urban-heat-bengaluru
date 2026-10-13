"""Prepared files: every layer, pre-computed on the shared grids.

Five summers of Landsat, 1.2 m tree canopy and a country-wide population map take minutes and
gigabytes to process, so the lessons read small prepared files instead. Each one downloads
itself the first time a notebook asks for it (``fetch``).

    uv run wardheat datapack status
    uv run wardheat datapack download     # everything at once (~40 MB), for a room with weak Wi-Fi

Layout (inside ``config.data_dir()``)::

    wards.parquet                 369 GBA wards (GeoParquet, EPSG:4326)
    grid30/<layer>.tif            30 m UTM-43N COGs, all on the same grid
    grid10/<layer>.tif            10 m UTM-43N COGs (nested 3x3 in the 30 m grid)
    source/<layer>.tif            native-resolution clips (100 m population, 1 km MODIS)
    tables/<name>.parquet         climate series, scene list, ward and 240 m cell tables
    manifest.json                 what is in the pack and where it came from
"""

from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .grid import Grid, city_grid, load_geotiff

DATA_URL = os.environ.get(  # one file per item below, plus the whole pack as a zip
    "WARDHEAT_DATA_URL", "https://github.com/amanbagrecha/urban-heat-bengaluru/releases/download/data-v1/")
DATAPACK_URL = DATA_URL + "wardheat-datapack.zip"

LAYERS: dict[str, dict] = {
    # ---- hazard
    "lst_day": dict(path="grid30/lst_day.tif", units="°C", desc="Landsat 8/9 LST, Mar-May 2022-26 median (~10:40 IST)"),
    "lst_day_nobs": dict(path="grid30/lst_day_nobs.tif", units="scenes", desc="Clear Landsat observations per pixel"),
    "lst_night": dict(path="grid30/lst_night.tif", units="°C", desc="MODIS Terra+Aqua night LST median, 1 km, bilinear to 30 m"),
    # ---- land cover / canopy
    "worldcover": dict(path="grid10/worldcover.tif", units="class", desc="ESA WorldCover 2021 v200 classes, 10 m"),
    "built_frac": dict(path="grid30/built_frac.tif", units="0-1", desc="Built-up fraction (WorldCover class 50) per 30 m pixel"),
    "veg_frac": dict(path="grid30/veg_frac.tif", units="0-1", desc="Tree+shrub+grass fraction (WorldCover) per 30 m pixel"),
    "crop_frac": dict(path="grid30/crop_frac.tif", units="0-1", desc="Cropland fraction (WorldCover class 40)"),
    "water_frac": dict(path="grid30/water_frac.tif", units="0-1", desc="Open water fraction (WorldCover class 80)"),
    "canopy_frac": dict(path="grid30/canopy_frac.tif", units="0-1", desc="Tree canopy >= 3 m fraction (Meta/WRI canopy height v1, 1.2 m, imagery 2018-20)"),
    # ---- people
    "pop": dict(path="grid30/pop.tif", units="people", desc="Census-2011 ward totals spread within each ward by WorldPop 2025"),
    "pop_worldpop": dict(path="grid30/pop_worldpop.tif", units="people", desc="WorldPop R2025A 2025 constrained, people per 30 m pixel"),
}

TABLES = {
    "landsat_scenes": "tables/landsat_scenes.parquet",
    "era5_daily": "tables/era5_daily.parquet",
    "forecast_bias": "tables/forecast_bias.parquet",
    "ward_features": "tables/ward_features.parquet",
    "pixels": "tables/pixels_240m.parquet",
}


def root() -> Path:
    return config.data_dir()


def _rel(key: str) -> str:
    rel = "wards.parquet" if key == "wards" else LAYERS.get(key, {}).get("path") or TABLES.get(key)
    if rel is None:
        raise KeyError(f"unknown data-pack item {key!r}")
    return rel


def path(key: str) -> Path:
    """Where a layer, vector or table of the pack lives on this computer (it may not be there yet)."""
    return root() / _rel(key)


def exists(key: str) -> bool:
    return path(key).exists()


def fetch(key: str) -> Path:
    """The local copy of one prepared file, downloaded the first time it is needed."""
    p = path(key)
    if not p.exists():
        import pooch

        pooch.get_logger().setLevel("WARNING")   # no hash advice in the notebook
        print(f"downloading {p.name} (once)")
        pooch.retrieve(DATA_URL + p.name, known_hash=None, fname=p.name, path=p.parent, progressbar=False)
    return p


def grid30() -> Grid:
    return city_grid(30)


def grid10() -> Grid:
    return city_grid(10)


def layer(key: str) -> np.ndarray:
    """Load a raster layer as a float32 array (NaN = no data) on its native pack grid."""
    return load_geotiff(fetch(key))


def layer_da(key: str):
    """Load a layer as a georeferenced xarray.DataArray (handy for plotting)."""
    g = grid10() if LAYERS[key]["path"].startswith("grid10") else grid30()
    return g.to_xarray(layer(key), name=key, attrs={"units": LAYERS[key]["units"], "long_name": LAYERS[key]["desc"]})


def table(key: str) -> pd.DataFrame:
    return pd.read_parquet(fetch(key))


def _files() -> list[str]:
    return ["wards.parquet"] + [m["path"] for m in LAYERS.values()] + list(TABLES.values())


def status() -> pd.DataFrame:
    """Which prepared files are on this computer, with sizes."""
    rows = []
    for rel in _files():
        p = root() / rel
        rows.append({"file": rel, "present": p.exists(), "MB": round(p.stat().st_size / 1e6, 1) if p.exists() else None})
    return pd.DataFrame(rows)


def download(url: str | None = None, force: bool = False) -> Path:
    """Download and unzip the whole pack (skipped if everything is there)."""
    import pooch

    if not force and status().present.all():
        return root()
    zpath = pooch.retrieve(url or DATAPACK_URL, known_hash=None, path=config.raw_dir(), progressbar=True)
    with zipfile.ZipFile(zpath) as zf:
        zf.extractall(root())
    Path(zpath).unlink(missing_ok=True)  # keep only the extracted files
    return root()


def zip_pack(out: str | Path = "dist/wardheat-datapack.zip") -> Path:
    """The whole pack as one zip, and every file on its own in ``files/`` next to it.

    Attach all of them to a GitHub release tagged ``data-v1``: ``fetch`` downloads single files by
    name, ``download`` the zip.
    """
    import shutil

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    files = _files()
    assert len({Path(rel).name for rel in files}) == len(files), "file names must be unique"
    flat = out.parent / "files"
    flat.mkdir(exist_ok=True)
    for rel in files:
        shutil.copy2(root() / rel, flat / Path(rel).name)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_STORED) as zf:
        for rel in files:
            zf.write(root() / rel, rel)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.0f} MB, {len(files)} files)")
    return out


def write_manifest(extra: dict | None = None) -> Path:
    st = status()
    man = {
        "city": config.CITY,
        "crs": config.CRS,
        "bbox": config.BBOX,
        "season_months": config.SEASON_MONTHS,
        "years": config.YEARS,
        "items": st.to_dict(orient="records"),
        **(extra or {}),
    }
    p = root() / "manifest.json"
    p.write_text(json.dumps(man, indent=2, default=str), encoding="utf-8")
    return p
