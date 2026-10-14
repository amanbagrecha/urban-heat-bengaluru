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

    Each becomes a 0–1 score across wards; multiplying them means only wards high on all three score high:
    """)
    return


@app.cell
def _(f, np):
    def scale(x):
        """0 = among the city's lowest 5 %, 1 = among its highest 5 %."""
        lo, hi = x.quantile([0.05, 0.95])
        return ((x - lo) / (hi - lo)).clip(0.05, 1)

    H = (scale(f.lst_built) + scale(f.lst_night)) / 2  # hazard: hot by day and at night
    E = scale(np.log(f.people_per_ha))  # exposure: how crowded (log: twice as crowded counts more, not double)
    V = scale(-f.canopy_frac)  # vulnerability: the less canopy, the higher
    risk = (H * E * V) ** (1 / 3) * 100  # multiply; the cube root keeps it on the same 0-100 scale
    return E, H, V, risk


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Darker = more risk.
    """)
    return


@app.cell(hide_code=True)
def _(E, H, V, charts, f, risk, wards):
    from wardheat.indices import classify

    table = f.assign(H=H, E=E, V=V, score=risk, risk=classify(risk))
    g = charts.ward_shapes(wards, table, keep=["H", "E", "V", "risk", "score", "lst_built", "lst_night", "people_per_ha", "canopy_frac"])
    charts.ward_map(g, {"Heat (H)": "H", "People (E)": "E", "Lack of shade (V)": "V"}, "0 = lowest, 1 = highest", fmt=".2f")
    return (g,)


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
def _(E, H, V, f, risk):
    plain = (H + E + V) / 3 * 100  # a plain average instead of the geometric mean
    compare = f[["label"]].assign(geometric=risk.rank(ascending=False), plain=plain.rank(ascending=False))
    compare.assign(moved=compare.geometric - compare.plain).nlargest(10, "moved")
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
