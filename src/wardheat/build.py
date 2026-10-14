"""Build the Bengaluru data pack from the original open sources.

Run everything:            wardheat datapack build
Run one step:              wardheat datapack build --step landsat
Rebuild even if present:   wardheat datapack build --step canopy --force

Each step is independent and writes into ``config.data_dir()``; steps that
depend on wards/grids create them on the fly. Total runtime ~20-30 min on a
good connection (Landsat and canopy are the slow ones).
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from . import config, datapack
from .grid import city_grid, save_geotiff, ward_labels


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _out(key: str) -> Path:
    p = datapack.path(key)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def step_wards(force=False):
    from .wards import build_wards

    if (config.data_dir() / "wards.parquet").exists() and not force:
        return
    w = build_wards()
    _log(f"wards: {len(w)} wards, {w.area_km2.sum():.0f} km²")


def step_landsat(force=False):
    from . import landsat, stac

    if datapack.exists("lst_day") and not force:
        return
    g = city_grid(30)
    items = stac.landsat_items()
    _log(f"landsat: {len(items)} scenes (Mar-May {config.YEARS[0]}-{config.YEARS[1]})")
    ds = landsat.load(items, g)
    phys = landsat.to_physical(ds)
    comp = landsat.median_composite(phys)
    save_geotiff(_out("lst_day"), comp["lst"].values.astype("float32"), g, source="Landsat C2 L2 ST_B10")
    _log(f"landsat: done, median city LST {np.nanmedian(comp['lst'].values):.1f} °C")


def step_modis(force=False):
    from . import modis

    if datapack.exists("lst_night") and not force:
        return
    g = city_grid(30)
    items = modis.items()
    _log(f"modis: {len(items)} 8-day composites {modis.platform_counts(items)}")
    r = modis.night_lst(items, g)
    save_geotiff(_out("lst_night"), r["fine"], g, n_composites=r["n"])
    src = config.data_dir() / "source"
    src.mkdir(exist_ok=True)
    save_geotiff(src / "lst_night_1km.tif", r["coarse"], r["coarse_grid"])
    _log(f"modis: done, median night LST {np.nanmedian(r['coarse']):.1f} °C")


def step_landcover(force=False):
    from . import landcover

    if datapack.exists("built_frac") and not force:
        return
    g10, g30 = city_grid(10), city_grid(30)
    wc = landcover.worldcover(g10)
    for k, v in landcover.fractions(wc).items():
        if k in datapack.LAYERS:
            save_geotiff(_out(k), v[: g30.height, : g30.width], g30)
    _log("landcover: done")


def step_canopy(force=False):
    from . import landcover
    from .grid import block_mean

    if datapack.exists("canopy_frac") and not force:
        return
    g10, g30 = city_grid(10), city_grid(30)
    _log(f"canopy: streaming Meta canopy-height v1 tiles {landcover.chm_tiles()}")
    last = {"t": 0}

    def prog(ti, nt, rs, r1):
        if time.time() - last["t"] > 30:
            _log(f"  canopy tile {ti+1}/{nt} row {rs}/{r1}")
            last["t"] = time.time()

    f10 = landcover.canopy_fraction(g10, progress=prog)
    save_geotiff(_out("canopy_frac"), block_mean(f10, 3)[: g30.height, : g30.width], g30)
    _log(f"canopy: done, city canopy {np.nanmean(f10)*100:.1f}%")


def step_climate(force=False):
    from . import climate

    if datapack.exists("era5_daily") and not force:
        return
    d = climate.era5_daily("1991-01-01", "2026-09-30")
    d.to_parquet(_out("era5_daily"))
    _log(f"climate: {len(d)} days of ERA5")


def step_forecast_bias(force=False):
    from . import climate

    if datapack.exists("forecast_bias") and not force:
        return
    b = climate.bias_table(datapack.table("era5_daily"))
    b.to_parquet(_out("forecast_bias"))
    _log(f"forecast_bias: {b.round(2).to_dict()}")


def step_features(force=False):
    from . import features

    px = features.pixel_table()
    px.to_parquet(_out("pixels"), index=False)
    _log(f"features: {len(px)} cells of 240 m")


STEPS = {
    "wards": step_wards,
    "landsat": step_landsat,
    "modis": step_modis,
    "landcover": step_landcover,
    "canopy": step_canopy,
    "climate": step_climate,
    "forecast_bias": step_forecast_bias,
    "features": step_features,
}


def run(steps: list[str] | None = None, force: bool = False) -> None:
    steps = steps or list(STEPS)
    if "wards" not in steps:
        step_wards()
    for s in steps:
        t0 = time.time()
        _log(f"=== {s}")
        STEPS[s](force=force)
        _log(f"=== {s} finished in {time.time() - t0:.0f}s")
    datapack.write_manifest()


# ---------------------------------------------------------------------------
# Recipes: how each prepared file the charts read is made, shown folded under the chart
# ---------------------------------------------------------------------------
def _recipes() -> dict:
    from . import climate, landcover, landsat

    return {  # name -> (prepared file, the code that makes it, build steps to run, what making it reads)
        "lst": ("lst_day", [step_landsat, landsat.median_composite, step_modis], ["landsat", "modis", "features"],
                "44 Landsat passes and 105 MODIS night composites from Planetary Computer, about 8 minutes"),
        "canopy": ("canopy_frac", [step_canopy, landcover.canopy_fraction], ["canopy", "features"],
                   "Meta and WRI's ~1 m tree-height map over the whole city, about 3 minutes"),
        "era5": ("era5_daily", [climate.era5_daily, step_climate], ["climate"],
                 "35 years of daily ERA5 from Open-Meteo, a few seconds"),
    }


def recipe(name: str):
    """A folded "How this file was made" box: the code behind a prepared file, and what it reads."""
    import inspect

    import marimo as mo
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import PythonLexer

    key, funcs, steps, cost = _recipes()[name]
    code = highlight("\n\n".join(inspect.getsource(f) for f in funcs), PythonLexer(), HtmlFormatter(nowrap=True))
    size = datapack.fetch(key).stat().st_size
    size = f"{size / 1e6:.1f} MB" if size > 1e5 else f"{size / 1e3:.0f} kB"
    cmd = "uv run wardheat datapack build " + " ".join(f"--step {s}" for s in steps) + " --force"
    return mo.Html(
        f'<details class="recipe"><summary>How this file was made <span>· making it reads {cost}</span></summary>'
        f"<p>The chart reads a small prepared file ({size}): your copy in <code>data/</code> if you have one, "
        f"otherwise it downloads once. To make it yourself from the original data, run <code>{cmd}</code>. "
        f"This is the code that runs:</p><pre class=\"code\">{code}</pre></details>")
