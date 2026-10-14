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

    <div class="lead">Two streets a kilometre apart can differ by 8 °C on the same morning. Most of
    that difference comes down to what covers the ground.</div>

    We use the same 240 m squares as in lesson 1 (each about the size of eight football fields).
    Besides temperature, each square knows what covers it, measured from satellite pictures:
    `canopy` is the share under trees, `built` under buildings and roads, `water` under lakes.
    Let's download them (or read them from your laptop if lesson 1 already did):
    """)
    return


@app.cell
def _(datapack):
    px = datapack.table("pixels")  # the city in 240 m squares
    px[["ward", "lst_day", "canopy", "built", "water"]].head()
    return (px,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## More trees, cooler ground

    In the chart on the left, every dot is one of those squares. **Left to right**: how much of it is
    under trees. **Bottom to top**: how hot its ground was at 10:40 am. The dots slope down to the
    right, and the dashed line shows the trend: the more trees, the cooler.

    The box starts on the leafiest squares; the map on the right shows where they are. Drag your own
    box, for example over the hot squares with no trees at the top left.
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
    Trees cool in two ways. Their shade keeps sunlight off roads and roofs, and their leaves give off
    water, which carries heat away as it evaporates. Lakes do the second even better: they are the
    coolest squares in the city. Bare soil and dark roofs do neither, and they are the hottest.

    ## How much cooler?

    Let's put a number on the dashed line, using only the squares that are mostly buildings, where
    people live:
    """)
    return


@app.cell
def _(np, px):
    built = px[px.built > 0.5]  # squares that are mostly buildings and roads

    # fit a straight line: temperature = slope × canopy + intercept
    slope, intercept = np.polyfit(built.canopy, built.lst_day, deg=1)
    return built, slope


@app.cell(hide_code=True)
def _(built, mo, slope):
    mo.md(f"""
    Across {len(built):,} built-up squares, every extra 10 % of tree canopy goes with surfaces about
    **{-slope * 0.1:.1f} °C cooler**. A street with 40 % canopy instead of 5 % is about
    **{-slope * 0.35:.0f} °C cooler** at 10:40 am.

    Leafy areas also differ in other ways (older, less crowded), so this is a pattern, not proof. But
    it matches what you feel walking out of the sun into a tree-lined street.

    ## Day and night tell different stories

    Each row is a kind of place. The orange dot is the day, the blue dot the night. Right of the
    dashed line means warmer than the city's average, left means cooler.
    """)
    return


@app.cell(hide_code=True)
def _(charts, px):
    charts.day_night_by_cover(px)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Farmland is the hottest ground in the morning but cools fast after sunset. Buildings soak up
    the day's heat in concrete and brick and give it back at night: this is the **urban heat
    island**. That is why the next lesson uses both day and night heat.

    ## Try it

    1. Draw a box around the bluest dots, the water. Which lakes are they?
    2. Box the hottest squares with almost no trees (top left). Which wards are they in?
    3. Keep only the densest squares (`0.8` instead of `0.5`). Does the cooling per 10 % canopy
       change?
    """)
    return


@app.cell
def _(np, px):
    dense = px[px.built > 0.8]  # change the threshold here
    dense_slope, _ = np.polyfit(dense.canopy, dense.lst_day, deg=1)
    f"{len(dense):,} dense squares: about {-dense_slope * 0.1:.1f} °C cooler per 10 % more canopy"
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="next">Next → <b>3 · Who is at risk?</b></div>
    """)
    return


if __name__ == "__main__":
    app.run()
