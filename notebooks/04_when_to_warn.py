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

    <div class="lead">Satellites can't see tomorrow, so the alert uses <b>air temperature</b> (2 m above the ground):
    is tomorrow's forecast unusually high for Bengaluru at this time of year?</div>

    First, 35 years of each day's highest (`tmax`) and lowest (`tmin`) air temperature from ERA5: ECMWF, Europe's weather
    centre, rebuilds past weather hour by hour on ~25 km squares by feeding station, balloon and satellite readings into a
    weather model. A 25 km square mixes town and countryside, so it reads about 1 °C below the city's weather station on
    March–May afternoons:
    """)
    return


@app.cell
def _(datapack):
    era5 = datapack.table("era5_daily")  # each day's highest and lowest air temperature (ERA5, via Open-Meteo), °C
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

    Bengaluru's highest air temperature (ERA5) since 1991 was **{era5['tmax'].max():.1f} °C** on {_hot:%d %B %Y}, and
    {"no day" if _n40 == 0 else f"only {_n40} days"} reached 40 °C, so India's 40 °C rule would never warn the city. Instead we
    ask how unusual a day is for its time of year:
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
def _(mo, normal):
    mo.md(f"""
    The night's lowest air temperature is judged the same way, and hot days and nights in a row add a level. A day must
    also be among the hottest 10 % of the whole year ({normal["tmax_ann_p90"].iloc[0]:.1f} °C by day), so a warm October
    day stays below the alert line. Every March–May since 1991:
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
    _red = levels["level"] >= 3
    _run = _red.groupby((~_red).cumsum()).cumsum()
    mo.md(f"""
    {_run.idxmax():%Y} had the longest run of Red or Magenta ({_run.max()} days in a row). Orange-or-worse days per season:
    **{_dec['1991s']:.1f}** in the 1990s, **{_dec['2011s']:.1f}** in the 2010s.

    ## Tomorrow's forecast

    Open-Meteo gives each coming day's highest and lowest air temperature from the sharpest weather model for the place,
    for Bengaluru mostly ECMWF's 9 km model; we subtract its average difference from ERA5 for that month, so the forecast
    is on the same scale as the 35 years:
    """)
    return


@app.cell
def _(climate, normal, warning):
    forecast = climate.forecast(days=7, past_days=2)  # next 7 days' highest and lowest air temperature, °C
    week = warning.heatrisk(forecast, normal).loc[climate.today():]  # from today on
    week[["tmax", "tmax_normal", "tmax_alert", "tmin", "level", "in words"]].round(1)  # normal = a usual day for the date
    return (week,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 369 ward alerts

    Each ward's alert = the city's level × the ward's risk from lesson 3:

    | Tomorrow is… | below the alert line | warm | hot | very hot | extreme |
    |---|---|---|---|---|---|
    | **High-risk ward** | – | take care | heat alert | emergency | emergency |
    | **Medium-risk ward** | – | take care | take care | heat alert | emergency |
    | **Low-risk ward** | – | – | take care | heat alert | emergency |
    """)
    return


@app.cell
def _(era5, indices, levels, pd, warning, week):
    wards_risk = indices.ward_risk(indices.ward_table())["risk"]  # High / Medium / Low, as in lesson 3

    tomorrow = week.iloc[1]  # row 0 is today
    this_year = era5.loc[str(era5.index[-1].year), "tmax"]
    hot_day = levels.loc[this_year.idxmax()]  # this year's highest air temperature (ERA5)
    alerts = pd.DataFrame({
        "tomorrow": warning.ward_alerts(int(tomorrow.level), wards_risk),
        "hot_day": warning.ward_alerts(int(hot_day.level), wards_risk),
    })
    alerts.apply(lambda alert: alert.value_counts()).fillna(0).astype(int)  # how many wards get each alert
    return alerts, hot_day, tomorrow


@app.cell(hide_code=True)
def _(alerts, charts, hot_day, load_wards, tomorrow):
    _g = charts.ward_shapes(load_wards(), alerts.reset_index(), keep=["tomorrow", "hot_day"])
    charts.alert_maps(_g, [
        ("tomorrow", f"Tomorrow, {tomorrow.name:%d %b}", f"air temperature forecast: {tomorrow.tmax:.1f} °C · {tomorrow['in words']}"),
        ("hot_day", f"{hot_day.name:%d %b %Y}, this year's hottest day", f"air temperature (ERA5): {hot_day.tmax:.1f} °C · {hot_day['in words']}"),
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
