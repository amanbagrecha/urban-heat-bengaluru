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

    ## How a satellite sees heat

    **Remote sensing** means measuring something from far away, without touching it. A satellite
    700 km up can't hold a thermometer to a road. What it can do is record light.

    Everything warm gives off light we can't see, called **thermal infrared**. The hotter a
    surface, the more of it it gives off; that is how night-vision cameras see people in the dark.
    Landsat 8 and 9, two NASA satellites, carry a camera for this light. From how strongly each
    patch of ground glows, we can work out its **land surface temperature**: how hot the roof, road
    or lawn is. It is not the air temperature you feel: on an April morning a tar road can be 15 °C
    hotter than the air above it.

    Landsat passes over Bengaluru every 8 days, at about 10:40 in the morning.

    ## Finding the pictures

    Satellite pictures are listed in free online catalogues. They follow one standard, called STAC,
    so the same code works for many satellites. This asks Microsoft's Planetary Computer for every
    Landsat picture of Bengaluru from March–May 2024 with less than 40 % cloud:
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

    One Landsat picture covers 185 km, far more than the city. The file is stored so that we can
    download just the part over Bengaluru. It stores the glow as whole numbers; one line from the
    Landsat handbook turns them into °C.
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
    That is Bengaluru at 10:40 am on {scene.datetime:%d %B %Y}, in 30 m squares. Pale is cooler:
    lakes and big parks. Dark is hotter: bare ground, factory roofs and the airport. You just read a
    satellite picture straight from the cloud.

    ## At night: another satellite

    Landsat only ever passes in the morning. To see the city at night we use **MODIS**, a camera on
    two other NASA satellites, Terra and Aqua. Together they photograph the whole Earth every day
    and every night. The catch: their squares are 1 km wide instead of 30 m. Same catalogue, same
    kind of search; each MODIS file averages up to 8 clear nights:
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
    The night picture is blocky because each square is 1 km, and it is about
    {np.nanmean(lst) - np.nanmean(lst_night):.0f} °C cooler. Look at where the warm squares are: at
    night the centre of the city stays warmest.

    ## Five summers in one map

    One morning can mislead: a passing cloud, a windy day. So we repeated what you just did for 44
    Landsat mornings and 105 MODIS nights over five summers (March–May 2022–2026), and kept the
    middle value for each spot. That takes about 8 minutes, so we did it in advance and saved the
    result. Let's download it (once; next time it is read from your laptop):
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
    Each row is one 240 m square: the ward it is in, its temperature by day and by night. Switch
    between day and night on the map, and hover to see the ward.
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
    Two things to notice:

    - **By day the hottest ground is at the edges**: dry fields, quarries and factory roofs. The
      old city centre is not the hottest place at 10:40 am.
    - **At night it flips.** Fields cool quickly after sunset, while the packed centre holds on to
      the day's heat. Warm nights matter for health, because the body cannot recover.

    ## From squares to wards

    The city takes decisions ward by ward, so we want one temperature per ward: the average of the
    30 m squares inside it.

    But not every square. By day the hottest ground is empty farmland and the coolest is lakes, and
    nobody lives in either. We want to know how hot it gets **where people live and work**, so we
    keep only the squares that are mostly buildings and roads.

    How do we know what is in a square? The ESA WorldCover map labels every 10 m of the planet as
    trees, crops, water, buildings and so on. Nine of those small squares fit in one of our 30 m
    squares. `built_frac` is the share of the nine that are buildings or roads, from 0 to 1. We keep
    a square if at least 5 of its 9 are built (0.5 or more).
    """)
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
    The hottest ward, **{_names[_t.idxmax()]}**, averages {_t.max():.1f} °C on its built-up
    ground; the coolest, **{_names[_t.idxmin()]}**, {_t.min():.1f} °C. That is
    **{_t.max() - _t.min():.1f} °C** between two parts of the same city on the same mornings.

    ## Does the 0.5 matter?

    What if half a square is buildings and the other half trees, or bare land? Let's check by
    redoing the average with a stricter rule (0.8: at least 7 of 9 built) and with no rule at all:
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
def _(built_frac, mo, rules):
    def _same_top(a, b, n=10):
        return len(set(rules[a].nlargest(n).index) & set(rules[b].nlargest(n).index))

    _kept = built_frac[built_frac >= 0.5]
    mo.md(f"""
    - **0.5 or 0.8 hardly matters.** The squares we keep are {_kept.mean():.0%} built on average,
      so "half trees" squares are rare. Ward averages move by
      {(rules["built ≥ 0.8"] - rules["built ≥ 0.5"]).abs().mean():.2f} °C, and
      {_same_top("built ≥ 0.5", "built ≥ 0.8")} of the 10 hottest wards stay the same.
    - **Using every square changes more.** Lakes pull some wards down and farmland pushes edge wards
      up: {_same_top("every square", "built ≥ 0.5")} of the 10 hottest stay. That is why we keep only
      the built-up squares: it is the heat people live in.

    ## Try it

    1. Find your own ward on the map. Is it hotter or cooler than its neighbours?
    2. Search March–May 2019 instead of 2024. How many clear pictures were there?
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
    3. Read the MODIS **day** picture instead of the night one: change `LST_Night_1km` to
       `LST_Day_1km` in both places below. Does it look like Landsat's?
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
