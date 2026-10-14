import marimo

__generated_with = "0.25.1"
app = marimo.App(
    width="compact",
    app_title="3 · Who is at risk?",
    css_file="theme.css",
)


@app.cell(hide_code=True)
def _():
    import marimo as mo

    from wardheat import charts, datapack
    from wardheat.grid import ward_labels, zonal_stats
    from wardheat.wards import load_wards

    return charts, datapack, load_wards, mo, ward_labels, zonal_stats


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="kicker">Lesson 3 · 11:30–12:30</div>

    # Who is at risk?

    <div class="lead">A hot surface is a risk where people are packed in without shade:
    risk = <b>surface temperature × crowding × lack of shade</b>.</div>

    ## Two maps from space, one headcount

    Surface temperature and tree cover come from satellites on the same 30 m squares (lessons 1 and 2). People come from
    the Census 2011 headcount of each ward, carried in the GBA ward file: the latest official count, as India's next census
    counts people in February 2027. The ward map with every headcount is on
    [OpenCity](https://data.opencity.in/dataset/gba-wards-delimitation-2025) (KML: opens in QGIS or Google Earth).
    Download them:
    """)
    return


@app.cell
def _(datapack, load_wards):
    day_surface_temp = datapack.layer("lst_day")  # °C, Landsat at 10:40 am (lesson 1)
    night_surface_temp = datapack.layer("lst_night")  # °C, MODIS at night (lesson 1)
    trees = datapack.layer("canopy_frac")  # 0-1 tree cover, Meta/WRI tree heights (lesson 2)
    wards = load_wards()  # the 369 GBA wards, with their Census 2011 headcount
    wards[["label", "census2011_pop", "area_km2"]].head()  # area in km²
    return day_surface_temp, night_surface_temp, trees, wards


@app.cell(hide_code=True)
def _(charts, day_surface_temp, trees):
    charts.images({
        "Surface temperature, 10:40 am · Landsat": (day_surface_temp, "surface temperature, °C", charts.HEAT),
        "Trees · Meta/WRI tree heights": (trees * 100, "% tree cover", charts.TREES),
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## One row per ward

    Average each map inside every ward with `zonal_stats` (lesson 1), and divide each ward's headcount by its area
    (1 km² = 100 hectares):
    """)
    return


@app.cell
def _(datapack, day_surface_temp, night_surface_temp, trees, ward_labels, wards, zonal_stats):
    labels = ward_labels(wards, datapack.grid30())  # each square -> its ward

    f = zonal_stats({
        "day_surface_temp": day_surface_temp,
        "night_surface_temp": night_surface_temp,
        "trees": trees,
    }, labels).rename(columns=lambda c: c.removesuffix("_mean"))
    w = wards.set_index("ward_uid")
    f.insert(0, "ward", w["label"])
    f["people_per_ha"] = w["census2011_pop"] / (w["area_km2"] * 100)  # Census 2011 people ÷ hectares
    f["surface_temp"] = (f.day_surface_temp + f.night_surface_temp) / 2  # one surface temperature: morning and night
    f = f.round({"day_surface_temp": 2, "night_surface_temp": 2, "surface_temp": 2, "trees": 3, "people_per_ha": 0})
    f.head()
    return (f,)


@app.cell(hide_code=True)
def _(charts, f, wards):
    charts.ingredient_maps(charts.ward_shapes(wards, f.reset_index(), keep=["surface_temp", "people_per_ha", "trees"]))
    return


@app.cell(hide_code=True)
def _(f, mo):
    _t, _p, _c = f.surface_temp, f.people_per_ha, f.trees * 100
    mo.md(f"""
    ## From three numbers to one score

    The three numbers are in different units, so we rescale each from 0 for the city's lowest ward to 1 for its highest:
    surface temperature from {_t.min():.2f} °C (0) to {_t.max():.2f} °C (1), people from {_p.min():,.0f} (0) to
    {_p.max():,.0f} per hectare (1), and lack of shade from {_c.max():.1f} % tree cover (0) to {_c.min():.1f} % (1).
    Multiplying the three gives a high score only to a ward that is hot, packed and treeless at once: the top 30 % of
    scores are High risk, the next 30 % Medium and the rest Low. The score compares wards with each other, so it says
    where to act first.
    """)
    return


@app.cell
def _(f):
    def scale(x):  # 0 = the city's lowest ward, 1 = its highest
        return (x - x.min()) / (x.max() - x.min())

    hot = scale(f.surface_temp)
    crowded = scale(f.people_per_ha)
    no_shade = scale(-f.trees)  # 1 = the ward with the fewest trees

    risk = hot * crowded * no_shade  # high only if all three are high
    return crowded, hot, no_shade, risk


@app.cell(hide_code=True)
def _(charts, crowded, f, hot, no_shade, risk, wards):
    from wardheat.indices import classify

    table = f.assign(H=hot, E=crowded, V=no_shade, score=risk, risk=classify(risk)).reset_index()
    g = charts.ward_shapes(wards, table, keep=["H", "E", "V", "risk", "surface_temp", "people_per_ha", "trees"])
    return (g,)


@app.cell(hide_code=True)
def _(crowded, f, hot, mo, no_shade, risk):
    _w = risk.idxmax()
    mo.md(f"""
    **{f.ward[_w]}**: {f.surface_temp[_w]:.2f} °C surface temperature → ({f.surface_temp[_w]:.2f} − {f.surface_temp.min():.2f}) ÷
    ({f.surface_temp.max():.2f} − {f.surface_temp.min():.2f}) = {hot[_w]:.3f}; {f.people_per_ha[_w]:,.0f} people per hectare →
    {crowded[_w]:.3f}; {f.trees[_w]:.1%} tree cover → {no_shade[_w]:.3f}. Score: {hot[_w]:.3f} × {crowded[_w]:.3f} ×
    {no_shade[_w]:.3f} = **{risk[_w]:.3f}**, the city's highest.

    ## Your weights

    How much should each count? Each slider is a power: 1 counts it once, 2 counts it twice, 0 leaves it out. The top
    30 % of wards are High risk.
    """)
    return


@app.cell(hide_code=True)
def _(charts, g):
    charts.risk_explorer(g)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Try it

    1. Set **People** to 0.

    2. Set **Lack of shade** to 3.

    3. A plain average instead of multiplying:
    """)
    return


@app.cell
def _(crowded, f, hot, no_shade, risk):
    plain = (hot + crowded + no_shade) / 3  # a plain average instead of multiplying
    compare = f[["ward"]].assign(multiplied=risk.rank(ascending=False), plain=plain.rank(ascending=False))
    compare.assign(moved=compare.multiplied - compare.plain).nlargest(10, "moved")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    `moved` = how many places a ward climbs when the three are averaged instead of multiplied. A risk map shows where to look first; check it on the ground.

    <div class="next">Next → <b>4 · When should we warn?</b></div>
    """)
    return


if __name__ == "__main__":
    app.run()
