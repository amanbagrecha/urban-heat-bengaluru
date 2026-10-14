import marimo

__generated_with = "0.25.1"
app = marimo.App(
    width="compact",
    app_title="1 · Where is it hot?",
    css_file="theme.css",
)


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import numpy as np
    import pandas as pd

    from wardheat import build, charts, datapack
    from wardheat.grid import ward_labels, zonal_stats
    from wardheat.wards import load_wards

    return build, charts, datapack, load_wards, mo, np, pd, ward_labels, zonal_stats


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="kicker">Lesson 1 · 09:30–10:30</div>

    # Where is it hot?

    <div class="lead">A satellite can't touch the ground with a thermometer. It measures the invisible
    heat glow (thermal infrared) every surface gives off, and that glow is turned into <b>surface temperature</b>:
    how hot roofs, roads, trees and lakes are, not the air we breathe.</div>
    """)
    return


@app.cell(hide_code=True)
def _(charts, mo):
    mo.Html(charts.SATELLITE_SEES_HEAT)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Finding the pictures

    Landsat 8 and 9 (NASA and USGS) each pass over Bengaluru every 16 days, together every 8, always at 10:40 am. Their
    thermal camera sees 100 m squares, and USGS turns each picture into surface temperature on 30 m squares, correcting
    for the air in between. Free online catalogues (STAC) list every picture:
    """)
    return


@app.cell
def _(pd):
    import planetary_computer
    import pystac_client

    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,  # free, no account needed
    )
    search = catalog.search(
        collections=["landsat-c2-l2"],
        bbox=[77.45, 12.82, 77.80, 13.155],  # Bengaluru: west, south, east, north
        datetime="2024-03-01/2024-05-31",
        query={
            "platform": {"in": ["landsat-8", "landsat-9"]},
            "eo:cloud_cover": {"lt": 40},
        },
    )
    items = search.item_collection()

    pd.DataFrame({
        "date": [i.datetime.date() for i in items],
        "satellite": [i.properties["platform"] for i in items],
        "cloud %": [i.properties["eo:cloud_cover"] for i in items],
    })
    return catalog, items


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Reading one picture

    We download only the pixels over Bengaluru and turn the stored numbers into surface temperature in °C:
    """)
    return


@app.cell
def _(datapack, items, np):
    import rasterio
    from rasterio.windows import from_bounds

    # the clearest picture, and the city's edges in metres (the same map grid as the picture)
    scene = min(items, key=lambda item: item.properties["eo:cloud_cover"])
    city = datapack.grid30().bounds

    with rasterio.open(scene.assets["lwir11"].href) as image:  # lwir = the thermal infrared camera
        window = from_bounds(*city, image.transform)
        dn = image.read(1, window=window)  # only the pixels over the city

    # whole numbers -> surface temperature in °C (0 means no data)
    lst = np.where(dn > 0, dn * 0.00341802 + 149.0 - 273.15, np.nan)
    return lst, scene


@app.cell(hide_code=True)
def _(charts, lst):
    charts.image(lst, "surface temperature, °C")
    return


@app.cell(hide_code=True)
def _(mo, scene):
    mo.md(f"""
    Surface temperature at 10:40 am on {scene.datetime:%d %B %Y} ({scene.properties["platform"].title()}, the clearest picture
    of March–May 2024): pale is cooler (lakes, parks), dark is hotter (bare ground, roofs).

    ## At night: another satellite

    Landsat only passes in the morning. **MODIS**, a camera on NASA's Terra and Aqua satellites, also passes at night, in
    1 km squares; each MODIS file is the average of the clear nights in 8 days. We load the Terra file for the same 8 days
    as the Landsat picture:
    """)
    return


@app.cell
def _(catalog, np, scene):
    import odc.stac

    nights = catalog.search(
        collections=["modis-11A2-061"],  # MODIS surface temperature, one file per 8 days
        bbox=[77.45, 12.82, 77.80, 13.155],
        datetime=f"{scene.datetime:%Y-%m-%d}",  # the 8-day files that include the Landsat picture's day
    ).item_collection()
    terra = [i for i in nights if i.id.startswith("MOD")][0]  # MOD = Terra, MYD = Aqua

    night = odc.stac.load(
        [terra], bands=["LST_Night_1km", "Night_view_time"], bbox=[77.45, 12.82, 77.80, 13.155],
        crs="EPSG:32643", resolution=1000,  # Landsat's map grid, in 1 km squares
    )
    dn_night = night["LST_Night_1km"].values[0].astype("float32")
    lst_night = np.where(dn_night > 0, dn_night * 0.02 - 273.15, np.nan)  # -> surface temperature in °C

    # the file also records when the satellite looked, in sun time; India's clock runs 20 minutes ahead of it here
    seen = night["Night_view_time"].values[0]
    seen_at = np.median(seen[seen < 255]) * 0.1 + 20 / 60  # hours after midnight, India time
    return lst_night, seen_at, terra


@app.cell(hide_code=True)
def _(charts, lst, lst_night, pd, scene, seen_at, terra):
    _start, _end = (pd.Timestamp(terra.properties[k]) for k in ("start_datetime", "end_datetime"))
    _clock = pd.Timestamp(0) + pd.Timedelta(hours=seen_at)
    charts.images({
        f"Landsat · {scene.datetime:%d %b %Y}, 10:40 am · 30 m": lst,
        f"MODIS Terra · nights of {_start:%d}–{_end:%d %b %Y}, ~{_clock:%I:%M %p} · 1 km": lst_night,
    }, "surface temperature, °C")
    return


@app.cell(hide_code=True)
def _(lst, lst_night, mo, np):
    mo.md(f"""
    Same week, two satellites: the surface temperature is {np.nanmean(lst) - np.nanmean(lst_night):.0f} °C lower at night, and the centre stays warmest.

    ## Five summers in one map

    We repeated this for 44 Landsat mornings and 105 MODIS 8-day files (Terra at about 10 pm, Aqua at about 2:30 am),
    March–May 2022–26, and kept each square's middle value. So your browser can draw the whole city, the download
    averages each 8 × 8 block of 30 m squares into one 240 m square:
    """)
    return


@app.cell
def _(datapack):
    squares = datapack.table("pixels")  # 12,449 squares of 240 m, from the workshop GitHub page
    squares[["ward", "lst_day", "lst_night"]].head()  # surface temperature (°C) by day and at night
    return (squares,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Toggle day and night; hover to see the ward.
    """)
    return


@app.cell(hide_code=True)
def _(charts, squares):
    charts.cell_map(
        squares,
        {"Day, 10:40 am (Landsat)": "lst_day", "Night, ~10 pm and ~2:30 am (MODIS)": "lst_night"},
        "surface °C",
        domains={"Day, 10:40 am (Landsat)": [34, 44], "Night, ~10 pm and ~2:30 am (MODIS)": [22, 27]},
    )
    return


@app.cell(hide_code=True)
def _(build):
    build.recipe("lst")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    By day the highest surface temperature is on farmland at the edges; at night it flips and the packed centre stays warmest.

    ## From squares to wards

    Each ward's surface temperature is the average of all the 30 m squares inside it:
    """)
    return


@app.cell
def _(datapack, load_wards, ward_labels, zonal_stats):
    wards = load_wards()  # the 369 GBA wards' boundaries (OpenCity)
    lst_day = datapack.layer("lst_day")  # surface temperature at 10:40 am, 5-summer middle value, 30 m squares, °C

    labels = ward_labels(wards, datapack.grid30())  # each square -> the number of its ward
    ward_temp = zonal_stats({"lst": lst_day}, labels)  # average of each ward's squares
    ward_temp.head()
    return labels, lst_day, ward_temp, wards


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    `zonal_stats` drops every square into its ward's bucket and averages each bucket; here are 16 wards in the old city:
    """)
    return


@app.cell(hide_code=True)
def _(charts, labels, lst_day, wards):
    _uid = int(wards.set_index("label").loc["Central 52 · Padarayanapura", "ward_uid"])
    charts.zonal_explainer(lst_day, labels, wards.set_index("ward_uid")["label"], row=681, col=342, size=60, mark=_uid)
    return


@app.cell(hide_code=True)
def _(charts, ward_temp, wards):
    _g = charts.ward_shapes(wards, ward_temp.reset_index().rename(columns={"lst_mean": "lst"}))
    charts.ward_map(_g, {"surface temperature, 10:40 am": "lst"}, "°C")
    return


@app.cell(hide_code=True)
def _(mo, ward_temp, wards):
    _t = ward_temp["lst_mean"]
    _names = wards.set_index("ward_uid")["label"]
    mo.md(f"""
    **{_names[_t.idxmax()]}** has the highest surface temperature ({_t.max():.1f} °C), **{_names[_t.idxmin()]}** the lowest ({_t.min():.1f} °C): {_t.max() - _t.min():.1f} °C apart.

    ## Try it

    1. Find your ward on the map. 2. Search 2019 instead of 2024:
    """)
    return


@app.cell
def _(catalog):
    passes_2019 = catalog.search(
        collections=["landsat-c2-l2"],
        bbox=[77.45, 12.82, 77.80, 13.155],
        datetime="2019-03-01/2019-05-31",  # change the year here
        query={"platform": {"in": ["landsat-8", "landsat-9"]}, "eo:cloud_cover": {"lt": 40}},
    ).item_collection()
    f"{len(passes_2019)} clear pictures in March–May 2019"
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    3. MODIS surface temperature by day: change `LST_Night_1km` to `LST_Day_1km`.
    """)
    return


@app.cell
def _(catalog, charts, np):
    import odc.stac as _stac

    _items = catalog.search(collections=["modis-11A2-061"], bbox=[77.45, 12.82, 77.80, 13.155],
                            datetime="2024-04-01/2024-04-30").item_collection()
    _day = _stac.load([i for i in _items if i.id.startswith("MOD")][:1], bands=["LST_Day_1km"],
                      bbox=[77.45, 12.82, 77.80, 13.155], crs="EPSG:32643", resolution=1000)
    _dn = _day["LST_Day_1km"].values[0].astype("float32")
    charts.image(np.where(_dn > 0, _dn * 0.02 - 273.15, np.nan), "surface temperature, °C")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="next">Next → <b>2 · Why are some places cooler?</b></div>
    """)
    return


if __name__ == "__main__":
    app.run()
