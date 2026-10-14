import marimo

__generated_with = "0.25.1"
app = marimo.App(
    app_title="4 · When should we warn?",
    layout_file="layouts/04_when_to_warn.slides.json",
    css_file="theme.css",
)


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import pandas as pd

    from wardheat import build, charts, climate, datapack, indices, warning
    from wardheat.wards import load_wards

    return build, charts, climate, datapack, indices, load_wards, mo, pd, warning


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="kicker">Lesson 4 · 13:30–14:45</div>

    # When should we warn?

    <div class="lead">Is tomorrow unusually hot for Bengaluru, at this time of year?</div>

    First, 35 years of daily highs (`tmax`) and lows (`tmin`) from ERA5, via Open-Meteo:
    """)
    return


@app.cell
def _(datapack):
    era5 = datapack.table("era5_daily")  # daily highest and lowest air temperature, °C
    era5[["tmax", "tmin"]].tail()
    return (era5,)


@app.cell(hide_code=True)
def _(build):
    build.recipe("era5")
    return


@app.cell(hide_code=True)
def _(era5, mo):
    _hot = era5["tmax"].idxmax()
    _n40 = int((era5["tmax"] >= 40).sum())
    mo.md(f"""
    ## 40 °C never comes

    Bengaluru's hottest day since 1991 was **{era5['tmax'].max():.1f} °C** ({_hot:%d %B %Y}; {_n40} days ever at 40 °C), so
    India's 40 °C rule would never warn the city. Instead we ask how unusual a day is for its time of year:
    """)
    return


@app.cell
def _(era5, warning):
    # what counts as hot for each date, from the 1991-2020 record
    normal = warning.climatology(era5, base=(1991, 2020))

    # a level (0-4) for every day since 1991
    levels = warning.heatrisk(era5.loc["1991":], normal)
    return levels, normal


@app.cell(hide_code=True)
def _(charts, era5, normal):
    charts.levels_explainer(era5, normal, day="2024-04-28")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The night's low is judged the same way, and hot days and nights in a row add a level. Every day
    since 1991:
    """)
    return


@app.cell(hide_code=True)
def _(charts, levels):
    charts.heat_calendar(levels, first_year=2024)
    return


@app.cell(hide_code=True)
def _(levels, mo):
    _s = levels[levels.index.month.isin([3, 4, 5])]
    _per_year = _s.groupby(_s.index.year)["level"].apply(lambda x: int((x >= 2).sum()))
    _dec = {f"{a}s": _per_year.loc[a:a + 9].mean() for a in (1991, 2001, 2011)}
    mo.md(f"""
    2024 had the longest run of Red and Magenta. Orange-or-worse days per season: **{_dec['1991s']:.0f}** in
    the 1990s, **{_dec['2011s']:.0f}** in the 2010s.

    ## Tomorrow's forecast
    """)
    return


@app.cell
def _(climate, normal, warning):
    forecast = climate.forecast(days=7, past_days=2)  # next 7 days' highs and lows, °C (minus the model's ~1 °C warm bias)
    week = warning.heatrisk(forecast, normal).loc[climate.today():]  # from today on
    week[["tmax", "tmin", "level", "in words"]].round(1)
    return (week,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 369 ward alerts

    Each ward's alert = the city's level × the ward's risk from lesson 3:

    | Tomorrow is… | normal | warm | hot | very hot | extreme |
    |---|---|---|---|---|---|
    | **High-risk ward** | – | take care | heat alert | emergency | emergency |
    | **Medium-risk ward** | – | take care | take care | heat alert | emergency |
    | **Low-risk ward** | – | – | take care | heat alert | emergency |
    """)
    return


@app.cell
def _(datapack, indices, levels, pd, warning, week):
    wards_risk = indices.ward_risk(indices.ward_table())["risk"]  # High / Medium / Low, as in lesson 3

    tomorrow = week.iloc[1]  # row 0 is today
    hot_day = levels[levels.level >= 2].iloc[-1]  # the last day that was "hot" or worse
    alerts = pd.DataFrame({
        "tomorrow": warning.ward_alerts(int(tomorrow.level), wards_risk),
        "hot_day": warning.ward_alerts(int(hot_day.level), wards_risk),
    })
    alerts.apply(lambda alert: alert.value_counts()).fillna(0).astype(int)  # how many wards get each alert
    return alerts, hot_day, tomorrow


@app.cell(hide_code=True)
def _(alerts, charts, datapack, hot_day, load_wards, tomorrow):
    _g = charts.ward_shapes(load_wards(), alerts.reset_index(), keep=["tomorrow", "hot_day"])
    charts.alert_maps(_g, [
        ("tomorrow", f"Tomorrow, {tomorrow.name:%d %b}", f"forecast {tomorrow.tmax:.0f} °C: {tomorrow['in words']}"),
        ("hot_day", f"{hot_day.name:%d %b %Y}", f"{hot_day.tmax:.1f} °C: {hot_day['in words']}"),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Try it

    1. Click 2016 and 2019 in the calendar. 2. Three hot days in a row instead of two:
    """)
    return


@app.cell
def _(era5, levels, normal, pd, warning):
    three_in_a_row = warning.heatrisk(era5.loc["1991":], normal, duration_days=3)  # change 3 here
    pd.DataFrame({
        "2 in a row": (levels.loc["2024", "level"] >= 3).sum(),
        "3 in a row": (three_in_a_row.loc["2024", "level"] >= 3).sum(),
    }, index=["Red or worse days in 2024"])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    3. "Normal" from 2001–2025 instead of 1991–2020:
    """)
    return


@app.cell
def _(era5, levels, pd, warning):
    recent_normal = warning.climatology(era5, base=(2001, 2025))  # change the years here
    recent_levels = warning.heatrisk(era5.loc["1991":], recent_normal)
    _season = lambda lv: lv[lv.index.month.isin([3, 4, 5])]
    pd.DataFrame({
        "normal = 1991–2020": _season(levels).groupby(_season(levels).index.year)["level"].apply(lambda x: (x >= 2).sum()),
        "normal = 2001–2025": _season(recent_levels).groupby(_season(recent_levels).index.year)["level"].apply(lambda x: (x >= 2).sum()),
    }).loc[2016:].rename_axis("Orange or worse days, Mar–May")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Next steps: tune the levels with hospital data, add humidity, add street sensors. Thank you!
    """)
    return


if __name__ == "__main__":
    app.run()
