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

    <div class="lead">A scorching field with nobody in it is not a problem. Heat becomes a risk
    where it meets people who can't get away from it.</div>

    Climate scientists (the IPCC) write this as **risk = hazard × exposure × vulnerability**. For
    each ward we use one simple measure of each:

    - **Hazard: how hot it gets.** Built-up surfaces by day, plus the night.
    - **Exposure: how many people live there.** People per km².
    - **Vulnerability: how little protection they have.** Here, how little tree shade there is.

    Real risk indices also use age, income, housing and health records. Shade is the one
    vulnerability we can map for every ward from open satellite data.

    ## Where people live

    The 2011 Census counted every ward, but it is 15 years old and says nothing about where people
    live *inside* a ward. WorldPop's 2025 map has that detail, but it counts about two million fewer
    people than the Census did in 2011. So we keep each ward's Census total and spread it out
    following WorldPop's pattern.
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
    The crowded core stands out. Many of the hot patches at the city's edge are nearly empty.

    ## Three ingredients, one score

    Heat is in °C, people in people per km² and shade in percent, so first we put all three on the
    same 0–1 scale: 0 means among the lowest 5 % of wards in the city, 1 among the highest 5 %.
    Then we combine them with a *geometric mean*, which only gives a high score if all three are
    high.
    """)
    return


@app.cell
def _(datapack, np):
    f = datapack.table("ward_features")  # one row per ward

    def scale(x):
        """0 = among the city's lowest 5 %, 1 = among its highest 5 %."""
        lo, hi = x.quantile([0.05, 0.95])
        return ((x - lo) / (hi - lo)).clip(0.05, 1)

    H = (scale(f.lst_built) + scale(f.lst_night)) / 2  # hazard: hot by day and at night
    E = scale(np.log(f.pop_density))  # exposure: people per km²
    V = scale(-f.canopy_frac)  # vulnerability: the less canopy, the higher
    risk = (H * E * V) ** (1 / 3) * 100
    return E, H, V, f, risk


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Two small choices are worth knowing about. The floor of 0.05 stops one zero from wiping out a
    ward completely. The logarithm of density means a ward twice as crowded counts as more
    exposed, but not twice as much.

    Here are the three ingredients on the map. Darker means more risk.
    """)
    return


@app.cell(hide_code=True)
def _(E, H, V, charts, f, risk, wards):
    from wardheat.indices import classify

    table = f.assign(H=H, E=E, V=V, score=risk, risk=classify(risk))
    g = charts.ward_shapes(wards, table, keep=["H", "E", "V", "risk", "score", "lst_built", "lst_night", "pop_density", "canopy_frac"])
    charts.ward_map(g, {"Heat (H)": "H", "People (E)": "E", "Lack of shade (V)": "V"}, "0 = lowest, 1 = highest", fmt=".2f")
    return (g,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Your weights

    How much should heat count compared with people or shade? That is a judgement call, not a
    scientific fact, and it is one a city should argue about in the open. The sliders weight each
    ingredient (0 leaves it out). The map and the list recompute as you drag. The top 30 % of wards
    are labelled High.
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

    1. Set **People** to 0. Which wards leave the top 20, and why?
    2. Set **Lack of shade** to 3. Which parts of the city move up?
    3. Try a plain average `(H + E + V) / 3` instead of the geometric mean. Wards that are very hot
       but nearly empty: where do they end up?
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
    The `moved` column is how many places a ward climbs with the plain average.

    This map shows where to look first, not who is affected. Before acting on it, a city would check
    it against hospital records and walk the streets of the top wards.
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
