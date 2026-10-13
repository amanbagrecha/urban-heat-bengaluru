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

    <div class="lead">A thermometer tells you how hot the air is at one spot. A satellite can tell you
    how hot every rooftop, road, park and lake in the city is, all at the same moment.</div>

    ## Satellites see the ground, not the air

    Landsat 8 and 9 fly over Bengaluru every eight days at about 10:40 in the morning. Their thermal
    camera records the heat coming off surfaces: the **land surface temperature**. On an April
    morning a tar road can be 15 °C hotter than the air above it, and a shaded lawn barely warmer.
    It is not what your body feels, but it shows which surfaces soak up the sun.

    ## Finding the pictures

    Satellite images sit in open catalogues that follow a standard called STAC. This asks
    Microsoft's Planetary Computer for every Landsat pass over the city in March–May 2024 with
    less than 40 % cloud:
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
        bbox=[77.45, 12.82, 77.80, 13.155],  # Bengaluru
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
    ## Reading one image

    Each image is a *Cloud-Optimized GeoTIFF*: a file on the web that lets us read just the pixels
    over Bengaluru instead of downloading all 200 km of the scene. The file stores whole numbers;
    one line from the Landsat handbook turns them into degrees.
    """)
    return


@app.cell
def _(datapack, items, np):
    import rasterio
    from rasterio.windows import from_bounds

    # the clearest pass, and the city's edges in metres (UTM 43N, like the image)
    scene = min(items, key=lambda item: item.properties["eo:cloud_cover"])
    city = datapack.grid30().bounds

    with rasterio.open(scene.assets["lwir11"].href) as image:
        window = from_bounds(*city, image.transform)
        dn = image.read(1, window=window)  # only the pixels over the city

    # the file stores whole numbers; this turns them into °C
    lst = np.where(dn > 0, dn * 0.00341802 + 149.0 - 273.15, np.nan)
    return lst, scene


@app.cell(hide_code=True)
def _(charts, lst):
    charts.image(lst)
    return


@app.cell(hide_code=True)
def _(mo, scene):
    mo.md(f"""
    That is Bengaluru at 10:40 am on {scene.datetime:%d %B %Y}. The pale streaks are lakes and big
    parks; the dark patches are bare ground, factory roofs and the airport. You just read a
    satellite image straight from the cloud.

    ## Five summers in one map

    One morning can mislead: a passing cloud, a breezy day. So the data pack holds the **median**
    of 44 clear passes from March–May 2022–2026, plus a night version from the MODIS satellites
    (about 10:30 pm, 1 km pixels). To keep this page light, both are averaged to 240 m squares.
    Switch between day and night, and hover to see which ward a square belongs to.
    """)
    return


@app.cell(hide_code=True)
def _(charts, datapack):
    charts.cell_map(
        datapack.table("pixels"),
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
    Two things to notice:

    - **By day the hottest ground is at the edges**: dry fields, quarries and industrial roofs.
      The dense old city is not the hottest place at 10:40 am.
    - **At night it flips.** Fields cool quickly after sunset, while the packed centre holds on
      to the day's heat. Warm nights matter for health because the body cannot recover.

    ## From pixels to wards

    Decisions are made ward by ward, so we need one number per ward. We give every 30 m pixel the
    number of the ward it falls in, then average the pixels in each ward. We only use built-up
    pixels, the places where people actually live and work, so a farm at the edge of a ward
    doesn't count.
    """)
    return


@app.cell
def _(datapack, load_wards, np, ward_labels, zonal_stats):
    wards = load_wards()
    lst_day = datapack.layer("lst_day")  # 5-summer median, 30 m, °C
    built_up = datapack.layer("built_frac") >= 0.5  # mostly buildings and roads

    labels = ward_labels(wards, datapack.grid30())  # each pixel -> its ward number
    hot_ground = np.where(built_up, lst_day, np.nan)
    ward_heat = zonal_stats({"lst": hot_ground}, labels)
    ward_heat.head()
    return labels, lst_day, ward_heat, wards


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
    The hottest ward, **{_names[_t.idxmax()]}**, averages {_t.max():.1f} °C on its built-up
    ground; the coolest, **{_names[_t.idxmin()]}**, {_t.min():.1f} °C. That is
    **{_t.max() - _t.min():.1f} °C** between two parts of the same city on the same mornings.

    ## Try it

    1. Find your own ward on the map. Is it hotter or cooler than its neighbours?
    2. Search March–May 2019 instead of 2024. How many clear passes were there?
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
    f"{len(passes_2019)} clear passes in March–May 2019"
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    3. Keep only the most built-up pixels (`0.8` instead of `0.5`). Does the list of the ten
       hottest wards change?
    """)
    return


@app.cell
def _(datapack, labels, lst_day, np, pd, ward_heat, wards, zonal_stats):
    mostly_built = datapack.layer("built_frac") >= 0.8  # change the threshold here
    strict_heat = zonal_stats({"lst": np.where(mostly_built, lst_day, np.nan)}, labels)
    ward_name = wards.set_index("ward_uid")["label"]
    pd.DataFrame({
        "built-up ≥ 0.5": ward_name[ward_heat["lst_mean"].nlargest(10).index].values,
        "built-up ≥ 0.8": ward_name[strict_heat["lst_mean"].nlargest(10).index].values,
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="next">Next → <b>2 · Why are some places cooler?</b></div>
    """)
    return


if __name__ == "__main__":
    app.run()
