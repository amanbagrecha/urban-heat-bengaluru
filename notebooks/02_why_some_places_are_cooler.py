import marimo

__generated_with = "0.25.1"
app = marimo.App(
    width="compact",
    app_title="2 · Why are some places cooler?",
    css_file="theme.css",
)


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import numpy as np

    from wardheat import build, charts, datapack

    return build, charts, datapack, mo, np


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="kicker">Lesson 2 · 10:45–11:30</div>

    # Why are some places cooler?

    <div class="lead">What covers the ground decides its surface temperature.</div>

    Tree cover (`canopy`) comes from Meta and WRI's tree-height map: an AI model measured the height of every ~1 m spot
    from Maxar satellite photos taken mostly in 2018–2020, and we count the share of each square under trees taller than 3 m.
    Buildings (`built`) and water come from ESA's WorldCover map, which sorts every 10 m cell into trees, crops, buildings,
    water and so on from 2021 Sentinel-1 radar and Sentinel-2 photos. Each 240 m square is the average of its 8 × 8 squares
    of 30 m:
    """)
    return


@app.cell
def _(datapack):
    px = datapack.table("pixels")  # the city in 240 m squares
    px[["ward", "lst_day", "canopy", "built", "water"]].head()  # lst_day = surface temperature at 10:40 am, °C
    return (px,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## More trees, cooler ground

    Each dot is a square (across: tree cover, up: surface temperature at 10:40 am). Drag a box to see where they are.
    """)
    return


@app.cell(hide_code=True)
def _(charts, px):
    charts.greens_explorer(px)
    return


@app.cell(hide_code=True)
def _(build):
    build.recipe("canopy")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Shade and evaporating water lower the surface temperature; bare soil and dark roofs raise it.

    ## How much cooler?
    """)
    return


@app.cell
def _(np, px):
    built = px[px.built > 0.5]  # squares that are mostly buildings and roads

    # fit a straight line: surface temperature = slope × canopy + intercept
    slope, intercept = np.polyfit(built.canopy, built.lst_day, deg=1)
    return built, slope


@app.cell(hide_code=True)
def _(built, mo, slope):
    mo.md(f"""
    Every extra 10 % of tree cover ≈ **{-slope * 0.1:.1f} °C lower** surface temperature ({len(built):,} built-up squares).

    ## Day and night
    """)
    return


@app.cell(hide_code=True)
def _(charts, px):
    charts.day_night_by_cover(px)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Farmland has the highest surface temperature by day and is cool at night; concrete stays warm after dark: the **urban heat island**.

    ## Try it

    1. Box the bluest dots: which lakes? 2. Box hot squares with no trees: which wards? 3. Densest squares only:
    """)
    return


@app.cell
def _(np, px):
    dense = px[px.built > 0.8]  # change the threshold here
    dense_slope, _ = np.polyfit(dense.canopy, dense.lst_day, deg=1)
    f"{len(dense):,} dense squares: about {-dense_slope * 0.1:.1f} °C lower surface temperature per 10 % more canopy"
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="next">Next → <b>3 · Who is at risk?</b></div>
    """)
    return


if __name__ == "__main__":
    app.run()
