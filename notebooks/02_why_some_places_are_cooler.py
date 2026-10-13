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

    px = datapack.table("pixels")  # the city in 240 m squares
    return build, charts, mo, np, px


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="kicker">Lesson 2 · 10:45–11:30</div>

    # Why are some places cooler?

    <div class="lead">Two streets a kilometre apart can differ by 8 °C on the same morning. Most of
    that difference comes down to what covers the ground.</div>

    Below, every dot is one 240 m square of the city: how much of it is under tree canopy, and how
    hot its surface was at 10:40 am. The box starts on the leafiest squares, and the map shows where
    they are. Drag your own box anywhere on the scatter.
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

    ## How much cooler, per tree?

    A straight line through the built-up squares tells us how much temperature drops, on average,
    as tree cover goes up:
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

    This is a pattern, not proof: leafy neighbourhoods also tend to be older, less dense and better
    off. But the physics behind it is well understood, and it matches what you feel walking out of
    the sun into a tree-lined street.

    ## Day and night tell different stories
    """)
    return


@app.cell(hide_code=True)
def _(charts, px):
    charts.day_night_by_cover(px)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Farmland is the hottest ground in the morning but cools fast once the sun sets. Built-up areas
    hold the day's heat in concrete and brick and give it back at night. This is the *urban heat
    island*. It shows up at night, which is why we will use both day and night heat when we score
    risk in the next lesson.

    (The night data comes in 1 km pixels, so a small park or lake gets blurred into its
    surroundings at night. That is part of why the night dots sit so close together.)

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
