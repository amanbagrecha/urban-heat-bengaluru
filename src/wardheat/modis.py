"""MODIS Terra + Aqua night-time land surface temperature (MOD11A2 / MYD11A2, 1 km, 8-day).

Landsat only flies over at ~10:40 in the morning. To know which wards *stay*
hot at night (no overnight relief = the dangerous part of a heatwave), we use
MODIS night passes: Terra ~22:30 and Aqua ~01:30 local time.

We use the 8-day composites (``modis-11A2-061``) rather than the daily files
of MOD11A1/MYD11A1: ~10x fewer files to read, already cloud-screened, and we take a
multi-year median anyway.

    LST [degC] = DN * 0.02 - 273.15      (DN = 0 means no data)
"""

from __future__ import annotations


from . import config, stac
from .grid import Grid, reproject_array


def items(datetime: str | None = None) -> list:
    return stac.search("modis-11A2-061", datetime=datetime or config.season_datetime())


def night_lst(items_: list, grid: Grid, coarse_res: float = 1000.0, which: str = "LST_Night_1km") -> dict:
    """Median night LST on a ~1 km UTM grid, plus a smooth bilinear version on ``grid``.

    Returns ``{"coarse": array, "coarse_grid": Grid, "fine": array on grid, "n": count}``.
    """
    import odc.stac

    coarse = grid.coarsen(int(round(coarse_res / grid.res)))
    ds = odc.stac.load(items_, bands=[which], geobox=coarse.geobox(), resampling="nearest", fail_on_error=False)
    dn = ds[which].astype("float32")
    lst = (dn * 0.02 - 273.15).where(dn > 0)
    med = lst.median("time", skipna=True).values.astype("float32")
    n = int(lst.sizes["time"])
    fine = reproject_array(med, coarse.transform, coarse.crs, grid)
    return {"coarse": med, "coarse_grid": coarse, "fine": fine, "n": n}


def platform_counts(items_: list) -> dict:
    from collections import Counter

    return dict(Counter(i.properties.get("platform") for i in items_))
