"""Thin helpers around the Microsoft Planetary Computer STAC API.

STAC (SpatioTemporal Asset Catalog) is a JSON standard for describing
satellite scenes: each *item* is one acquisition with a footprint, a time,
metadata (cloud cover, platform...) and links (*assets*) to Cloud-Optimized
GeoTIFFs. We search the catalog, then let ``odc-stac`` read only the pixels
that fall on our grid.
"""

from __future__ import annotations

import pystac_client

from . import config


def client() -> pystac_client.Client:
    """Anonymous Planetary Computer client; asset URLs are signed automatically."""
    import planetary_computer

    return pystac_client.Client.open(config.PC_STAC, modifier=planetary_computer.sign_inplace)


def search(
    collection: str,
    bbox=config.BBOX,
    datetime: str | None = None,
    months: tuple[int, ...] | None = config.SEASON_MONTHS,
    query: dict | None = None,
    max_items: int | None = None,
) -> list:
    """Search one collection and keep only items in ``months`` (None = all months)."""
    items = client().search(
        collections=[collection], bbox=bbox, datetime=datetime, query=query, max_items=max_items
    ).item_collection()
    items = [i for i in items if months is None or item_time(i).month in months]
    return sorted(items, key=item_time)


def item_time(item):
    """Acquisition time of an item (composites such as MODIS 8-day only carry a start/end range)."""
    if item.datetime is not None:
        return item.datetime
    from datetime import datetime

    return datetime.fromisoformat(item.properties["start_datetime"].replace("Z", "+00:00"))


def landsat_items(datetime: str | None = None, max_cloud: float = 40) -> list:
    """Landsat 8 and 9 Collection 2 Level-2 scenes over the city in the heat season."""
    return search(
        "landsat-c2-l2",
        datetime=datetime or config.season_datetime(),
        query={"platform": {"in": ["landsat-8", "landsat-9"]}, "eo:cloud_cover": {"lt": max_cloud}},
    )


def items_table(items: list):
    """A tidy DataFrame of item metadata — handy for showing what a search returned."""
    import pandas as pd

    rows = []
    for it in items:
        p = it.properties
        rows.append(
            {
                "id": it.id,
                "datetime": it.datetime,
                "platform": p.get("platform"),
                "cloud_cover": p.get("eo:cloud_cover"),
                "year": it.datetime.year,
                "month": it.datetime.month,
            }
        )
    return pd.DataFrame(rows)
