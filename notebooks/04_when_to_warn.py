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

    For that we need air temperature, every day, for decades. ERA5 is a reconstruction of the
    world's weather since 1940, built by the European weather centre from every observation it
    has. Open-Meteo serves it for free. The data pack has the city centre from 1991 to today:
    """)
    return


@app.cell
def _(datapack):
    era5 = datapack.table("era5_daily")  # daily max and min air temperature
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

    We borrow the idea behind HeatRisk, the US National Weather Service's warning scale on
    [heat.gov](https://www.heat.gov). For every date we look at the same date ±15 days in
    1991–2020 and find how hot the hottest 10 %, 5 %, 2 % and 0.5 % of days were. A day climbs one
    level for every one of those bars its maximum *or* its night minimum clears:

    | Level | The day or night is hotter than… | Who is at risk |
    |---|---|---|
    | 0 Green | normal | almost nobody |
    | 1 Yellow | 90 % of days for that date | the most heat-sensitive |
    | 2 Orange | 95 % | sensitive groups, anyone outdoors for long |
    | 3 Red | 98 % | anyone without cooling or water |
    | 4 Magenta | 99.5 % | everyone, rare and long |

    Hot days *and* hot nights in a row raise the level by one: heat that doesn't let up is the
    dangerous kind.
    """)
    return


@app.cell
def _(era5, warning):
    # what counts as hot for each date, from the 1991-2020 record
    normal = warning.climatology(era5, base=(1991, 2020))

    # a HeatRisk level for every day since 1991
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

    ## This week's forecast

    The same rules work on a forecast. This asks Open-Meteo for the next week. Forecast models run
    about 1 °C warmer than ERA5 here in spring, so we take that bias off before comparing.
    """)
    return


@app.cell
def _(climate, normal, pd, warning):
    import requests

    reply = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": 12.98, "longitude": 77.59, "timezone": "Asia/Kolkata",
        "daily": "temperature_2m_max,temperature_2m_min", "past_days": 5,
    }, timeout=30).json()["daily"]
    forecast = pd.DataFrame(
        {"tmax": reply["temperature_2m_max"], "tmin": reply["temperature_2m_min"]},
        index=pd.to_datetime(reply["time"]),
    )
    forecast = climate.remove_bias(forecast)
    week = warning.heatrisk(forecast, normal).loc[pd.Timestamp.today().normalize():]
    week[["tmax", "tmin", "name"]].round(1)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Outside March–May it rarely goes above Yellow. Run it again in April.

    ## One city level, 369 ward alerts

    The forecast gives one level for the whole city. But the same weather is more dangerous in a
    crowded, treeless ward than in a leafy one. So each ward's alert combines the city level with
    the ward's risk class from lesson 3. Pick a level and see who gets warned.
    """)
    return


@app.cell(hide_code=True)
def _(charts, datapack, indices, load_wards):
    _f = datapack.table("ward_features")
    _g = charts.ward_shapes(load_wards(), _f.join(indices.ward_risk(_f)), keep=["risk"])
    charts.alert_map(_g, level=2)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    At Orange, only the High-risk wards get a full heat alert. At Red, everyone is alerted and the
    High-risk wards move to an emergency.

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
