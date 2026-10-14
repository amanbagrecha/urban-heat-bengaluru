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

    <div class="lead">The maps tell us where. A warning system also needs to know when: is tomorrow
    unusually hot for Bengaluru, at this time of year?</div>

    For that we need the air temperature of every day, for decades. **ERA5** is a record of the
    weather everywhere on Earth since 1940, rebuilt by Europe's weather centre from millions of
    past measurements. The free service Open-Meteo serves it. Let's download the daily high
    (`tmax`) and low (`tmin`) for the city centre since 1991:
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

    The India Meteorological Department declares a heatwave on the plains when the maximum reaches
    40 °C. Bengaluru sits 920 m up, and its hottest day since 1991 in this record was
    **{era5['tmax'].max():.1f} °C on {_hot:%d %B %Y}**. Days at 40 °C or more: **{_n40}**. Under
    that rule the city would never be warned.

    Yet people here do get ill from heat well below 40 °C, because bodies get used to the local
    normal. So instead of a fixed number we ask: **how unusual is this day for this place and this
    date?**

    ## A local warning scale

    For every date, we look at the same weeks of the year in 1991–2020 and ask how often it was
    this hot. This is how HeatRisk, the US weather service's scale on [heat.gov](https://www.heat.gov),
    works:

    | Level | In words | The day (or night) is hotter than… | Who is at risk |
    |---|---|---|---|
    | 0 Green | normal | – | almost nobody |
    | 1 Yellow | warm for the season | 9 in 10 days at that time of year | the most heat-sensitive |
    | 2 Orange | hot | 19 in 20 | old people, small children, anyone working outdoors |
    | 3 Red | very hot | 49 in 50 | anyone without cooling or water |
    | 4 Magenta | extreme | 199 in 200 | everyone |

    Hot days *and* hot nights in a row raise the level by one: heat that doesn't let up is the
    dangerous kind.
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
def _(charts, levels):
    charts.heat_calendar(levels, first_year=2024)
    return


@app.cell(hide_code=True)
def _(levels, mo):
    _s = levels[levels.index.month.isin([3, 4, 5])]
    _per_year = _s.groupby(_s.index.year)["level"].apply(lambda x: int((x >= 2).sum()))
    _dec = {f"{a}s": _per_year.loc[a:a + 9].mean() for a in (1991, 2001, 2011)}
    mo.md(f"""
    April and early May 2024 was the longest run of Red and Magenta days in the record. Orange or
    worse days per season averaged **{_dec['1991s']:.0f}** in the 1990s, **{_dec['2001s']:.0f}** in
    the 2000s and **{_dec['2011s']:.0f}** in the 2010s.

    Notice also how rare the colours are. A warning that fires every week gets ignored, so a good
    scale stays green most of the time.

    ## Tomorrow's forecast

    The same rules work on a forecast. Let's download the next week's forecast from Open-Meteo
    ([api.open-meteo.com](https://open-meteo.com)) and give each day a level:
    """)
    return


@app.cell
def _(climate, normal, warning):
    forecast = climate.forecast(days=7, past_days=2)  # highs and lows for the next 7 days, °C
    week = warning.heatrisk(forecast, normal).loc[climate.today():]  # from today on
    week[["tmax", "tmin", "level", "in words"]].round(1)
    return (week,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    (Forecast models run about 1 °C warmer than ERA5 here, so `climate.forecast` takes that off
    before we compare.)

    ## One city level, 369 ward alerts

    The forecast gives one level for the whole city. But the same weather is more dangerous in a
    crowded, treeless ward than in a leafy one. So each ward's alert combines the city's level with
    the ward's risk from lesson 3:

    | Tomorrow is… | normal | warm | hot | very hot | extreme |
    |---|---|---|---|---|---|
    | **High-risk ward** | no alert | take care | heat alert | emergency | emergency |
    | **Medium-risk ward** | no alert | take care | take care | heat alert | emergency |
    | **Low-risk ward** | no alert | no alert | take care | heat alert | emergency |

    Here is tomorrow, for real, next to the last hot day in our record:
    """)
    return


@app.cell
def _(datapack, indices, levels, pd, warning, week):
    wards_risk = indices.ward_risk(datapack.table("ward_features"))["risk"]  # High / Medium / Low, lesson 3

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
    _g = charts.ward_shapes(load_wards(), datapack.table("ward_features")[["ward_uid"]].join(alerts), keep=["tomorrow", "hot_day"])
    charts.alert_maps(_g, [
        ("tomorrow", f"Tomorrow, {tomorrow.name:%d %b}", f"forecast {tomorrow.tmax:.0f} °C: {tomorrow['in words']}"),
        ("hot_day", f"{hot_day.name:%d %b %Y}", f"{hot_day.tmax:.1f} °C: {hot_day['in words']}"),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    On a hot day, only the High-risk wards get a full heat alert. On a very hot day every ward gets
    one, and the High-risk wards move to an emergency.

    ## Try it

    1. Click 2016 and 2019 in the calendar. How do they compare with 2024?
    2. By default, 2 hot days and nights in a row raise the level. With 3, how many Red days does
       2024 keep?
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
    3. Measure "normal" on 2001–2025 instead of 1991–2020. What happens when it includes the recent
       hot years?
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
    ## Where to go from here

    - **Check against health data.** HeatRisk's thresholds were tuned on US hospital and death
      records. Bengaluru's should be tuned on its own.
    - **Add humidity.** Humid heat is harder on the body; Open-Meteo also serves humidity.
    - **Local thermometers.** ERA5 is a 25 km average. A few street-level sensors would show the
      real spread between wards.

    Thank you for spending the day on this. Everything here is open, so take it to your own city.
    """)
    return


if __name__ == "__main__":
    app.run()
