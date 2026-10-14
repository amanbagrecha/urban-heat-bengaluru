"""Ward boundaries: the Greater Bengaluru Authority's 369 wards (final delimitation, Nov/Dec 2025).

Source: OpenCity "GBA Wards Delimitation 2025" (public domain, source GBA).
The KML also carries each ward's Census 2011 headcount (1 March 2011), the latest official count;
lesson 3 uses it for people per hectare.
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd
import pooch

from . import config

WARDS_KML_URL = (
    "https://data.opencity.in/dataset/863209cb-4ced-4f51-b5c5-156939c50922/resource/"
    "9013d656-8051-4e2d-9648-46efd0d86d3d/download/gba-369-wards-december-2025.kml"
)

_KEEP = {
    "corporation_id": "corporation_id",
    "Corporation": "corporation",
    "ward_id": "ward_no",
    "ward_name": "ward_name",
    "ward_name_kn": "ward_name_kn",
    "zone_name": "zone",
    "Assembly": "assembly",
    "TOT_P": "census2011_pop",
    "SC_P": "census2011_sc",
    "ST_P": "census2011_st",
}


def download_kml() -> str:
    """Fetch the raw KML once (cached by pooch)."""
    return pooch.retrieve(WARDS_KML_URL, known_hash=None, fname="gba-369-wards-2025.kml", path=config.raw_dir())


def clean_wards(raw: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Tidy the KML attributes into an analysis-ready ward table.

    * ``ward_uid`` 1..369 is a stable integer key (ward numbers restart in each
      of the five corporations, so ``ward_no`` alone is not unique).
    * Geometries are repaired with ``make_valid`` (a few KML rings self-intersect).
    """
    g = raw[list(_KEEP) + ["geometry"]].rename(columns=_KEEP).copy()
    for c in ["corporation_id", "ward_no"]:
        g[c] = pd.to_numeric(g[c]).astype(int)
    for c in ["census2011_pop", "census2011_sc", "census2011_st"]:
        g[c] = pd.to_numeric(g[c]).astype(float)
    g["geometry"] = g.geometry.make_valid()
    # make_valid can return GeometryCollections; keep the polygonal part only
    g["geometry"] = g.geometry.apply(
        lambda geom: geom if geom.geom_type in ("Polygon", "MultiPolygon")
        else gpd.GeoSeries([p for p in getattr(geom, "geoms", []) if p.geom_type in ("Polygon", "MultiPolygon")]).union_all()
    )
    g = g.sort_values(["corporation_id", "ward_no"]).reset_index(drop=True)
    g.insert(0, "ward_uid", range(1, len(g) + 1))
    g["area_km2"] = g.to_crs(config.CRS).area / 1e6
    g["label"] = g["corporation"] + " " + g["ward_no"].astype(str) + " · " + g["ward_name"]
    return g.set_crs(4326, allow_override=True)


def build_wards(path=None) -> gpd.GeoDataFrame:
    """Download + clean the KML and save it as GeoParquet in the data pack."""
    raw = gpd.read_file(download_kml())
    wards = clean_wards(raw)
    wards.to_parquet(path or config.data_dir() / "wards.parquet")
    return wards


def load_wards() -> gpd.GeoDataFrame:
    """The 369 GBA wards (EPSG:4326), downloaded the first time they are needed."""
    from . import datapack

    return gpd.read_parquet(datapack.fetch("wards"))
