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

    <div class="lead">Heat is a risk where it meets people who can't escape it:
    risk = <b>heat × crowding × lack of shade</b>.</div>

    ## Three maps from space

    Each ingredient is a map made from satellite pictures, on the same 30 m squares. Download them:
    """)
    return


@app.cell
def _(datapack):
    day_heat = datapack.layer("lst_day")  # °C, Landsat by day (lesson 1)
    night_heat = datapack.layer("lst_night")  # °C, MODIS at night (lesson 1)
    trees = datapack.layer("canopy_frac")  # 0-1 tree cover, from sharp satellite photos
    people = datapack.layer("pop")  # people per square (Census 2011 + WorldPop)
    return day_heat, night_heat, people, trees


@app.cell(hide_code=True)
def _(charts, day_heat, people, trees):
    charts.images({
        "Heat by day · Landsat": day_heat,
        "Trees · Meta's map from satellite photos": (trees * 100, "% tree cover", charts.TREES),
        "People · WorldPop, from mapped buildings": (people / 0.09, "people per hectare", charts.PEOPLE),
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
def _(datapack, day_heat, load_wards, night_heat, np, people, trees, ward_labels, zonal_stats):
    wards = load_wards()
    labels = ward_labels(wards, datapack.grid30())  # each square -> its ward
    built_up = datapack.layer("built_frac") >= 0.5  # lesson 1's rule

    f = zonal_stats({
        "day_heat": np.where(built_up, day_heat, np.nan),
        "night_heat": night_heat,
        "trees": trees,
        "people_per_ha": people / 0.09,
    }, labels).rename(columns=lambda c: c.removesuffix("_mean"))
    f.insert(0, "ward", wards.set_index("ward_uid")["label"])
    f.round(2).head()
    return f, wards


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Three ingredients, one score

    Turn each column into a rank among wards: heat 0.88 means hotter than 88 % of wards.
    """)
    return


@app.cell
def _(f):
    heat = (f.day_heat.rank(pct=True) + f.night_heat.rank(pct=True)) / 2  # day and night
    crowding = f.people_per_ha.rank(pct=True)
    no_shade = (-f.trees).rank(pct=True)  # less tree cover = higher

    risk = heat * crowding * no_shade  # high only if all three are high
    return crowding, heat, no_shade, risk


@app.cell(hide_code=True)
def _(charts, crowding, f, heat, no_shade, risk, wards):
    from wardheat.indices import classify

    table = f.assign(H=heat, E=crowding, V=no_shade, score=risk, risk=classify(risk)).reset_index()
    g = charts.ward_shapes(wards, table, keep=["H", "E", "V", "risk", "day_heat", "night_heat", "people_per_ha", "trees"])
    charts.ingredient_maps(g)
    return (g,)


@app.cell(hide_code=True)
def _(crowding, f, heat, mo, no_shade, risk):
    _w = risk.idxmax()
    mo.md(f"""
    **{f.ward[_w]}** is hotter than {heat[_w]:.0%} of wards, more crowded than {crowding[_w]:.0%} and
    less shaded than {no_shade[_w]:.0%}: {heat[_w]:.2f} × {crowding[_w]:.2f} × {no_shade[_w]:.2f} =
    **{risk[_w]:.2f}**, the city's highest risk.

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
def _(crowding, f, heat, no_shade, risk):
    plain = (heat + crowding + no_shade) / 3  # a plain average instead of multiplying
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
