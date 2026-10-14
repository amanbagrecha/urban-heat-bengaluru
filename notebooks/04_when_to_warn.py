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
    <div class="kicker">Lesson 4 · 13:30–15:00</div>

    # When should we warn?

    <div class="lead">Satellites can't see tomorrow, so the alert uses <b>air temperature</b> (2 m above the ground):
    is tomorrow's forecast unusually high for this time of year, and hot for Bengaluru at all?</div>

    First, each day's highest (`tmax`) and lowest (`tmin`) air temperature since 1991 from ERA5, Europe's hour-by-hour
    rebuild of past weather on ~25 km squares (it reads about 1.5 °C below the city's weather station on summer afternoons).

    **See it, get it.** [Climate Pulse](https://pulse.climate.copernicus.eu/) maps ERA5 for the whole world, day by day, and
    [Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api) gives any place's daily values as a CSV, which is what
    we download for Bengaluru (35 years in 0.2 MB):
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
    _n40 = int((era5["tmax"] >= 40).sum())
    mo.md(f"""
    ## 40 °C never comes

    In 35 years {"no day" if _n40 == 0 else f"only {_n40} days"} in Bengaluru reached 40 °C, so India's 40 °C rule would never
    warn the city. Instead we ask how unusual a day is for its time of year:
    """)
    return


@app.cell
def _(era5, warning):
    # for every date: how hot the days around it were in 1991-2020
    normal = warning.climatology(era5, base=(1991, 2020))

    # a level for every day since 1991: below the alert line, warm, hot, very hot or extreme
    levels = warning.heatrisk(era5.loc["1991":], normal)
    return levels, normal


@app.cell(hide_code=True)
def _(era5, mo):
    example = era5.loc[str(era5.index[-1].year), "tmax"].idxmax()  # our example: this year's hottest day
    mo.md(f"""
    For each date we line up the days around it in 1991–2020 (the 30 years weather services use as "normal"): a day
    hotter than 90 % of them is warm, 95 % hot, 98 % very hot, 99.5 % extreme. Here is {example:%d %B %Y}, this year's
    hottest day:
    """)
    return (example,)


@app.cell(hide_code=True)
def _(charts, era5, example, normal):
    charts.levels_explainer(era5, normal, day=example)
    return


@app.cell(hide_code=True)
def _(mo, normal):
    mo.md(f"""
    A day must also beat {normal["tmax_ann_p90"].iloc[0]:.1f} °C, hotter than 90 % of all days of the year, so a warm
    October day never warns; nights are judged the same way, and hot days and nights in a row add a level. Every March–May
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
    _red = levels["level"] >= 3
    _run = _red.groupby((~_red).cumsum()).cumsum()
    mo.md(f"""
    {_run.idxmax():%Y} had the longest run of very hot or extreme days ({_run.max()} in a row). Hot-or-worse days each
    March–May: **{_dec['1991s']:.1f}** a year on average in 1991–2000, **{_dec['2011s']:.1f}** in 2011–2020.

    ## Tomorrow's forecast

    Open-Meteo's free [forecast](https://open-meteo.com/en/docs) gives the coming days' highest and lowest air temperature;
    we shift it slightly (by under 1.5 °C) so it reads like ERA5, the record we compare it with:
    """)
    return


@app.cell
def _(climate, normal, warning):
    forecast = climate.forecast(days=7, past_days=2)  # highest and lowest air temperature, today and the next 6 days, °C
    week = warning.heatrisk(forecast, normal).loc[climate.today():]  # from today on
    week[["tmax", "tmax_normal", "tmax_alert", "tmin", "in words"]].round(1).rename(columns={
        "tmax": "high °C", "tmax_normal": "average high °C", "tmax_alert": "alert line °C", "tmin": "low °C", "in words": "level"})
    return (week,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 369 ward alerts

    Each ward's alert combines the city's level with the ward's risk class from lesson 3:

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
    hot_day = levels.loc[this_year.idxmax()]  # the example above: this year's hottest day (ERA5)
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
    ## Sending the alerts

    Every warned ward gets a message for its officers and residents; when tomorrow has no alerts, the cell shows what this
    year's hottest day would have sent:
    """)
    return


@app.cell
def _(alerts, hot_day, load_wards, tomorrow):
    day, when = ("tomorrow", tomorrow) if (alerts.tomorrow != "No alert").any() else ("hot_day", hot_day)
    advice = {
        "Take care": "drink water often and stay out of the sun from 12 noon to 3 pm.",
        "Heat alert": "stay out of the sun from 12 noon to 3 pm, drink water and ORS, check on older neighbours and outdoor workers.",
        "Emergency": "stay indoors from 12 noon to 3 pm, drink water and ORS, call 108 for anyone who collapses in the heat.",
    }
    send = alerts.loc[alerts[day] != "No alert", [day]].rename(columns={day: "alert"})
    send.insert(0, "ward", load_wards().set_index("ward_uid")["label"])
    send["message"] = send.alert.map(lambda a: f"{a} for {when.name:%d %B}: {when.tmax:.0f} °C air temperature; " + advice[a])
    send.sort_values(["alert", "ward"]).head(10)
    return (send,)


@app.cell(hide_code=True)
def _(mo, send):
    mo.md(f"""
    {len(send)} messages in all: {", ".join(f"{n} {a}" for a, n in send.alert.value_counts().items())}.

    ## The same idea, live

    The US weather service runs this every day: its [HeatRisk map](https://www.wpc.ncep.noaa.gov/heatrisk/) colours the
    whole country green to magenta for the next 7 days by comparing the forecast with local records, and
    [heat.gov](https://www.heat.gov/) tells people what to do.

    ## Try it

    1. Click 2016 and 2019 in the calendar.

    2. Add a level only after three hot days and nights in a row, instead of two:
    """)
    return


@app.cell
def _(era5, levels, normal, pd, warning):
    three_in_a_row = warning.heatrisk(era5.loc["1991":], normal, duration_days=3)  # change 3 here
    _red = lambda lv: (lv["level"] >= 3).groupby(lv.index.year).sum()
    pd.DataFrame({"2 in a row": _red(levels), "3 in a row": _red(three_in_a_row)}).loc[2010:].rename_axis("very hot or worse days")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    3. Compare with 2001–2025 instead of 1991–2020:
    """)
    return


@app.cell
def _(era5, levels, pd, warning):
    recent_normal = warning.climatology(era5, base=(2001, 2025))  # change the years here
    recent_levels = warning.heatrisk(era5.loc["1991":], recent_normal)
    _season = lambda lv: lv[lv.index.month.isin([3, 4, 5])]
    pd.DataFrame({
        "compared with 1991–2020": _season(levels).groupby(_season(levels).index.year)["level"].apply(lambda x: (x >= 2).sum()),
        "compared with 2001–2025": _season(recent_levels).groupby(_season(recent_levels).index.year)["level"].apply(lambda x: (x >= 2).sum()),
    }).loc[2016:].rename_axis("hot or worse days, Mar–May")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Next steps: tune the levels with hospital data, add humidity, add street sensors. Thank you!
    """)
    return


if __name__ == "__main__":
    app.run()
