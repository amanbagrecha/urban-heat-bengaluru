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

    Climate scientists write this as **risk = hazard × exposure × vulnerability**. In plain words,
    we ask three questions about each ward:

    - **How hot does it get?** Its built-up ground by day, and the night (lesson 1).
    - **How many people live there?** People per km².
    - **How little shade do they have?** The less tree cover, the worse (lesson 2).

    ## Where people live

    The 2011 Census counted the people in every ward, but not where they live inside it. WorldPop,
    a free population map made from satellite pictures of buildings, has that detail. We keep each
    ward's Census count and spread it out the way WorldPop does. Let's download the result, one row
    per ward:
    """)
    return


@app.cell
def _(datapack):
    f = datapack.table("ward_features")  # one row per ward: heat, people, trees
    f[["label", "lst_built", "lst_night", "pop_density", "canopy_frac"]].head()
    return (f,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    `lst_built` is the daytime heat of built-up ground, `lst_night` the night, `pop_density` people
    per km², `canopy_frac` the share under trees. Here is where people live, in 240 m squares:
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

    Heat is in °C, people in people per km² and shade in %. To combine them, we first turn each
    into a score from 0 (the lowest wards in the city) to 1 (the highest). Then we multiply the
    three, so a ward only scores high when all three are high: a scorching ward where nobody lives
    stays low.
    """)
    return


@app.cell
def _(f, np):
    def scale(x):
        """0 = among the city's lowest 5 %, 1 = among its highest 5 %."""
        lo, hi = x.quantile([0.05, 0.95])
        return ((x - lo) / (hi - lo)).clip(0.05, 1)

    H = (scale(f.lst_built) + scale(f.lst_night)) / 2  # hazard: hot by day and at night
    E = scale(np.log(f.pop_density))  # exposure: people per km² (log: twice as crowded counts more, not double)
    V = scale(-f.canopy_frac)  # vulnerability: the less canopy, the higher
    risk = (H * E * V) ** (1 / 3) * 100  # multiply; the cube root keeps it on the same 0-100 scale
    return E, H, V, risk


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Here are the three scores on the map. Darker means more risk.
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

    How much should heat count compared with people or shade? There is no right answer: it is a
    choice a city should discuss in the open. Drag the sliders (0 leaves one out) and the map and
    the list update. The top 30 % of wards are High risk.
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
