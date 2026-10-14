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
    import numpy as np

    from wardheat import build, charts, datapack
    from wardheat.grid import ward_labels, zonal_stats
    from wardheat.wards import load_wards

    return build, charts, datapack, load_wards, mo, np, ward_labels, zonal_stats


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="kicker">Lesson 3 · 11:30–12:30</div>

    # Who is at risk?

    <div class="lead">A hot surface is a risk where people are packed in without shade:
    risk = <b>surface temperature × crowding × lack of shade</b>.</div>

    ## Three maps from space

    Each ingredient is a map on the same 30 m squares. People come from the Census 2011 count of each ward, spread inside
    the ward the way WorldPop's 2025 map spreads them: a computer model that places people only in areas mapped as built up
    from satellite images.
    Download them:
    """)
    return


@app.cell
def _(datapack):
    day_surface_temp = datapack.layer("lst_day")  # °C, Landsat at 10:40 am (lesson 1)
    night_surface_temp = datapack.layer("lst_night")  # °C, MODIS at night (lesson 1)
    trees = datapack.layer("canopy_frac")  # 0-1 tree cover, Meta/WRI tree heights (lesson 2)
    people = datapack.layer("pop")  # people per square (Census 2011 + WorldPop 2025)
    return day_surface_temp, night_surface_temp, people, trees


@app.cell(hide_code=True)
def _(charts, day_surface_temp, people, trees):
    charts.images({
        "Surface temperature, 10:40 am · Landsat": (day_surface_temp, "surface temperature, °C", charts.HEAT),
        "Trees · Meta/WRI tree heights": (trees * 100, "% tree cover", charts.TREES),
        "People · Census 2011 + WorldPop": (people / 0.09, "people per hectare", charts.PEOPLE),
    })
    return


@app.cell(hide_code=True)
def _(build):
    build.recipe("population")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## One row per ward

    Average each map inside every ward, as in lesson 1 (a 30 m square is 0.09 hectare):
    """)
    return


@app.cell
def _(datapack, day_surface_temp, load_wards, night_surface_temp, np, people, trees, ward_labels, zonal_stats):
    wards = load_wards()
    labels = ward_labels(wards, datapack.grid30())  # each square -> its ward
    built_up = datapack.layer("built_frac") >= 0.5  # lesson 1's rule

    f = zonal_stats({
        "day_surface_temp": np.where(built_up, day_surface_temp, np.nan),
        "night_surface_temp": night_surface_temp,
        "trees": trees,
        "people_per_ha": people / 0.09,
    }, labels).rename(columns=lambda c: c.removesuffix("_mean"))
    f.insert(0, "ward", wards.set_index("ward_uid")["label"])
    f["surface_temp"] = (f.day_surface_temp + f.night_surface_temp) / 2  # one surface temperature: morning and night
    f = f.round({"day_surface_temp": 2, "night_surface_temp": 2, "surface_temp": 2, "trees": 3, "people_per_ha": 0})
    f.head()
    return f, wards


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
    Multiplying the three gives a high score only to a ward that is hot, packed and treeless at once, and the 30 % of
    wards with the highest scores are High risk; the score compares wards with each other, so it says where to act first.
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
    **{f.ward[_w]}**: {f.surface_temp[_w]:.2f} °C → {hot[_w]:.3f}, {f.people_per_ha[_w]:,.0f} people per hectare →
    {crowded[_w]:.3f}, {f.trees[_w]:.1%} tree cover → {no_shade[_w]:.3f}; {hot[_w]:.3f} × {crowded[_w]:.3f} ×
    {no_shade[_w]:.3f} = **{risk[_w]:.3f}**, the city's highest score.

    ## Your weights

    How much should each count? Drag the sliders; the top 30 % of wards are High risk.
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

    1. Set **People** to 0. 2. Set **Lack of shade** to 3. 3. A plain average instead of multiplying:
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
    `moved` = places a ward climbs. A risk map shows where to look first; check it on the ground.

    <div class="next">Next → <b>4 · When should we warn?</b></div>
    """)
    return


if __name__ == "__main__":
    app.run()
