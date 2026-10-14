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
    f.round(2).head()
    return f, wards


@app.cell(hide_code=True)
def _(charts, f, wards):
    charts.ingredient_maps(charts.ward_shapes(wards, f.assign(
        H=f.surface_temp.rank(pct=True), E=f.people_per_ha.rank(pct=True), V=(-f.trees).rank(pct=True)).reset_index()))
    return


@app.cell(hide_code=True)
def _(f, mo):
    _iqr = f.surface_temp.quantile(0.75) - f.surface_temp.quantile(0.25)
    mo.md(f"""
    ## From three numbers to one score

    The three numbers are in different units (°C, people, % trees), so we can't add them. Instead we line the 369 wards
    up for each number and give every ward its place in the line, from 0 to 1: 0.95 means 95 % of wards are at or below
    it. Multiplying the three places gives a high score only to a ward near the top of all three lines at once (hot,
    packed and treeless), and the top 30 % of scores are High risk. A place in the line says which wards to look at first,
    not how much hotter they are: the middle half of wards are within {_iqr:.1f} °C of each other.
    """)
    return


@app.cell
def _(f):
    hotter = f.surface_temp.rank(pct=True)  # 0.95 = 95 % of wards have this surface temperature or lower
    crowding = f.people_per_ha.rank(pct=True)
    no_shade = (-f.trees).rank(pct=True)  # less tree cover = higher

    risk = hotter * crowding * no_shade  # high only if all three are high
    return crowding, hotter, no_shade, risk


@app.cell(hide_code=True)
def _(charts, crowding, f, hotter, no_shade, risk, wards):
    from wardheat.indices import classify

    table = f.assign(H=hotter, E=crowding, V=no_shade, score=risk, risk=classify(risk)).reset_index()
    g = charts.ward_shapes(wards, table, keep=["H", "E", "V", "risk", "surface_temp", "people_per_ha", "trees"])
    return (g,)


@app.cell(hide_code=True)
def _(crowding, f, hotter, mo, no_shade, risk):
    _w = risk.idxmax()
    mo.md(f"""
    **{f.ward[_w]}**: surface {f.surface_temp[_w]:.1f} °C, {f.people_per_ha[_w]:,.0f} people per hectare, {f.trees[_w]:.0%}
    tree cover. Places in line: {hotter[_w]:.2f} × {crowding[_w]:.2f} × {no_shade[_w]:.2f} = **{risk[_w]:.2f}**, the city's
    highest score.

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
def _(crowding, f, hotter, no_shade, risk):
    plain = (hotter + crowding + no_shade) / 3  # a plain average instead of multiplying
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
