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
    heat glow (thermal infrared) every surface gives off, and we turn that glow into temperature.</div>
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

    Landsat 8 and 9 pass every 8 days at 10:40 am; free online catalogues (STAC) list every picture:
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

    We download only the pixels over Bengaluru and turn the stored numbers into °C:
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

    # whole numbers -> °C (0 means no data)
    lst = np.where(dn > 0, dn * 0.00341802 + 149.0 - 273.15, np.nan)
    return lst, scene


@app.cell(hide_code=True)
def _(charts, lst):
    charts.image(lst)
    return


@app.cell(hide_code=True)
def _(mo, scene):
    mo.md(f"""
    Bengaluru at 10:40 am on {scene.datetime:%d %B %Y}: pale is cool (lakes, parks), dark is hot (bare ground, roofs).

    ## At night: another satellite

    Landsat only passes in the morning; **MODIS** (on NASA's Terra and Aqua) passes every night too, but in 1 km squares:
    """)
    return


@app.cell
def _(catalog, np):
    import odc.stac

    nights = catalog.search(
        collections=["modis-11A2-061"],  # MODIS surface temperature, 8 days per file
        bbox=[77.45, 12.82, 77.80, 13.155],
        datetime="2024-04-01/2024-04-30",
    ).item_collection()
    terra = [i for i in nights if i.id.startswith("MOD")][0]  # MOD = Terra, about 10:30 pm

    night = odc.stac.load(
        [terra], bands=["LST_Night_1km"], bbox=[77.45, 12.82, 77.80, 13.155],
        crs="EPSG:32643", resolution=1000,  # Landsat's map grid, in 1 km squares
    )
    dn_night = night["LST_Night_1km"].values[0].astype("float32")
    lst_night = np.where(dn_night > 0, dn_night * 0.02 - 273.15, np.nan)  # -> °C
    return (lst_night,)


@app.cell(hide_code=True)
def _(charts, lst, lst_night):
    charts.images({"Landsat, 10:40 am, 30 m squares": lst, "MODIS, about 10:30 pm, 1 km squares": lst_night})
    return


@app.cell(hide_code=True)
def _(lst, lst_night, mo, np):
    mo.md(f"""
    Same city, two satellites: the night is {np.nanmean(lst) - np.nanmean(lst_night):.0f} °C cooler and blockier, and the centre stays warmest.

    ## Five summers in one map

    We repeated this for 44 mornings and 105 nights (March–May 2022–26) and kept the middle value. Download the result:
    """)
    return


@app.cell
def _(datapack):
    squares = datapack.table("pixels")  # 240 m squares, from the workshop GitHub page
    squares[["ward", "lst_day", "lst_night"]].head()
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
        {"Day, 10:40 am": "lst_day", "Night, 10:30 pm": "lst_night"},
        "°C",
        domains={"Day, 10:40 am": [34, 44], "Night, 10:30 pm": [22, 27]},
    )
    return


@app.cell(hide_code=True)
def _(build):
    build.recipe("lst")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    By day the hottest ground is farmland at the edges; at night it flips and the packed centre stays warm.

    ## From squares to wards

    We average each ward's 30 m squares, but only those mostly covered by buildings, where people feel the heat:
    """)
    return


@app.cell(hide_code=True)
def _(charts, datapack):
    charts.built_rule(datapack.layer("worldcover")[1245:1305, 3135:3195])  # 600 m, on the 30 m grid
    return


@app.cell
def _(datapack, load_wards, np, ward_labels, zonal_stats):
    wards = load_wards()  # the 369 wards' boundaries
    lst_day = datapack.layer("lst_day")  # 5-summer middle value, 30 m squares, °C
    built_frac = datapack.layer("built_frac")  # 0 = no buildings, 1 = all buildings and roads
    built_up = built_frac >= 0.5  # mostly buildings and roads

    labels = ward_labels(wards, datapack.grid30())  # each square -> the number of its ward
    hot_ground = np.where(built_up, lst_day, np.nan)  # leave out squares that aren't built up
    ward_heat = zonal_stats({"lst": hot_ground}, labels)  # average per ward
    ward_heat.head()
    return built_frac, labels, lst_day, ward_heat, wards


@app.cell(hide_code=True)
def _(charts, ward_heat, wards):
    _g = charts.ward_shapes(wards, ward_heat.reset_index().rename(columns={"lst_mean": "lst"}))
    charts.ward_map(_g, {"built-up surface temperature": "lst"}, "°C")
    return


@app.cell(hide_code=True)
def _(mo, ward_heat, wards):
    _t = ward_heat["lst_mean"]
    _names = wards.set_index("ward_uid")["label"]
    mo.md(f"""
    **{_names[_t.idxmax()]}** is the hottest ward ({_t.max():.1f} °C), **{_names[_t.idxmin()]}** the coolest ({_t.min():.1f} °C): {_t.max() - _t.min():.1f} °C apart.

    ## Does the 0.5 matter?
    """)
    return


@app.cell
def _(built_frac, labels, lst_day, np, pd, ward_heat, zonal_stats):
    rules = pd.DataFrame({
        "every square": zonal_stats({"lst": lst_day}, labels)["lst_mean"],
        "built ≥ 0.5": ward_heat["lst_mean"],
        "built ≥ 0.8": zonal_stats({"lst": np.where(built_frac >= 0.8, lst_day, np.nan)}, labels)["lst_mean"],
    })
    rules.describe().round(1)
    return (rules,)


@app.cell(hide_code=True)
def _(mo, rules):
    def _same_top(a, b, n=10):
        return len(set(rules[a].nlargest(n).index) & set(rules[b].nlargest(n).index))

    mo.md(f"""
    0.5 or 0.8 barely matters ({_same_top("built ≥ 0.5", "built ≥ 0.8")} of the 10 hottest wards stay the same); using every square lets in fields and lakes ({_same_top("every square", "built ≥ 0.5")} of 10 stay).

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
    3. MODIS by day: change `LST_Night_1km` to `LST_Day_1km`.
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
    charts.image(np.where(_dn > 0, _dn * 0.02 - 273.15, np.nan))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="next">Next → <b>2 · Why are some places cooler?</b></div>
    """)
    return


if __name__ == "__main__":
    app.run()
