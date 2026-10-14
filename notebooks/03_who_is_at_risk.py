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
    from wardheat.wards import load_wards

    wards = load_wards()
    return build, charts, datapack, mo, np, wards


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="kicker">Lesson 3 · 11:30–12:30</div>

    # Who is at risk?

    <div class="lead">Heat is a risk where it meets people who can't escape it:
    risk = **heat × people × lack of shade**.</div>

    ## Where people live

    Census 2011 ward counts, spread inside each ward with WorldPop's 2025 map. Download one row per ward:
    """)
    return


@app.cell
def _(datapack):
    f = datapack.table("ward_features")  # one row per ward: heat, people, trees
    f["people_per_ha"] = (f.pop_density / 100).round()  # people per hectare, the same unit as the map below
    f[["label", "lst_built", "lst_night", "people_per_ha", "canopy_frac"]].head()
    return (f,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The same people per hectare (a 100 m × 100 m patch), now square by square: darker is more crowded.
    """)
    return


@app.cell(hide_code=True)
def _(charts, datapack):
    charts.cell_map(
        datapack.table("pixels"),
        {"people per hectare": "people_per_ha"},
        "people per hectare",
        palette=charts.PEOPLE,
        domains={"people per hectare": [0, 400]},
        fmt=",.0f",
    )
    return


@app.cell(hide_code=True)
def _(build):
    build.recipe("population")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Three ingredients, one score

    Each ingredient becomes a rank among wards: heat 0.88 means hotter than 88 % of wards.
    """)
    return


@app.cell
def _(f):
    # rank(pct=True): 0.88 = higher than 88 % of wards
    heat = (f.lst_built.rank(pct=True) + f.lst_night.rank(pct=True)) / 2  # day and night
    crowding = f.people_per_ha.rank(pct=True)
    no_shade = (-f.canopy_frac).rank(pct=True)  # less tree cover = higher

    risk = heat * crowding * no_shade  # high only if all three are high
    return crowding, heat, no_shade, risk


@app.cell(hide_code=True)
def _(charts, crowding, f, heat, no_shade, risk, wards):
    from wardheat.indices import classify

    table = f.assign(H=heat, E=crowding, V=no_shade, score=risk, risk=classify(risk))
    g = charts.ward_shapes(wards, table, keep=["H", "E", "V", "risk", "lst_built", "lst_night", "people_per_ha", "canopy_frac"])
    charts.ingredient_maps(g)
    return (g,)


@app.cell(hide_code=True)
def _(crowding, f, heat, mo, no_shade, risk):
    _w = risk.idxmax()
    mo.md(f"""
    **{f.label[_w]}** is hotter than {heat[_w]:.0%} of wards, more crowded than {crowding[_w]:.0%} and
    less shaded than {no_shade[_w]:.0%}: {heat[_w]:.2f} × {crowding[_w]:.2f} × {no_shade[_w]:.2f} =
    **{risk[_w]:.2f}**, the city's highest risk.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
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
    compare = f[["label"]].assign(multiplied=risk.rank(ascending=False), plain=plain.rank(ascending=False))
    compare.assign(moved=compare.multiplied - compare.plain).nlargest(10, "moved")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    `moved` = places a ward climbs. A risk map shows where to look first; check it on the ground.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="next">Next → <b>4 · When should we warn?</b></div>
    """)
    return


if __name__ == "__main__":
    app.run()
