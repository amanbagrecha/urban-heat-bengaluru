import marimo

__generated_with = "0.25.1"
app = marimo.App(
    width="compact",
    app_title="Urban heat risk monitoring",
    css_file="theme.css",
)


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import pandas as pd

    from wardheat import charts, climate, datapack, indices, warning
    from wardheat.wards import load_wards

    return charts, climate, datapack, indices, load_wards, mo, pd, warning


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="kicker">Welcome · 09:00–09:30</div>

    # Urban heat risk monitoring

    <div class="lead">Every March–May some Bengaluru neighbourhoods bake while others stay cool. Today you
    use free satellite pictures and a little Python to find where, who lives there, and when to warn them.</div>

    ## About me

    I'm Aman Bagrecha, a geospatial consultant; I write at [amanbagrecha.com](https://amanbagrecha.com)
    and co-run [Let's Talk Spatial](https://letstalkspatial.in), Bengaluru's free community for maps and satellites.

    <div style="display:flex; flex-wrap:wrap; gap:12px; margin:14px 0 6px">
      <figure style="flex:1 1 220px; margin:0">
        <img src="https://amanbagrecha.com/_astro/geonerds.rsHE1WLH_Z1p2iL2.webp" alt="Presenting at FOSS4G 2023" style="display:block; width:100%; height:170px; object-fit:cover; border-radius:4px">
        <figcaption style="font-size:12px; color:#6b665c; margin-top:4px">Presenting at FOSS4G 2023, Prizren, Kosovo</figcaption>
      </figure>
      <figure style="flex:1 1 220px; margin:0">
        <img src="https://letstalkspatial.in/images/2026/05/Event_22_Group.jpg" alt="Let's Talk Spatial meetup group photo" style="display:block; width:100%; height:170px; object-fit:cover; border-radius:4px">
        <figcaption style="font-size:12px; color:#6b665c; margin-top:4px">Let's Talk Spatial #22, Takshashila Institution, May 2026</figcaption>
      </figure>
    </div>
    """)
    return


@app.cell(hide_code=True)
def _(charts, climate, datapack, indices, load_wards, pd, warning):
    # tomorrow's real forecast, and the hottest day in the record, through the system we build today
    _era5 = datapack.table("era5_daily")
    _normal = warning.climatology(_era5, base=(1991, 2020))
    tomorrow = warning.heatrisk(climate.forecast(days=3, past_days=2), _normal).loc[climate.today() + pd.Timedelta(days=1)]
    _levels = warning.heatrisk(_era5.loc["1991":], _normal)
    hot_day = _levels[_levels.level >= 2].iloc[-1]  # the last hot day in the record
    _f = datapack.table("ward_features")
    _risk = indices.ward_risk(_f)["risk"]
    _f = _f.assign(tomorrow=warning.ward_alerts(int(tomorrow.level), _risk),
                   hot_day=warning.ward_alerts(int(hot_day.level), _risk))
    alert_wards = charts.ward_shapes(load_wards(), _f, keep=["tomorrow", "hot_day"])
    return alert_wards, hot_day, tomorrow


@app.cell(hide_code=True)
def _(alert_wards, hot_day, mo, tomorrow):
    _warned = int((alert_wards["tomorrow"] != "No alert").sum())
    _alerts = alert_wards["hot_day"].value_counts()
    mo.md(f"""
    ## Where we are going

    By 3 pm you will turn the weather forecast into a heat alert for each of the 369 wards. Tomorrow
    ({tomorrow.name:%d %b}, {tomorrow.tmax:.0f} °C) is **{tomorrow["in words"]}**, so {_warned or "no"} wards are warned;
    on the last hot day, {hot_day.name:%d %b %Y}, {_alerts.get("Heat alert", 0) + _alerts.get("Emergency", 0)} crowded, shadeless wards got a heat alert.
    """)
    return


@app.cell(hide_code=True)
def _(alert_wards, charts, hot_day, tomorrow):
    charts.alert_maps(alert_wards, [
        ("tomorrow", f"Tomorrow, {tomorrow.name:%d %b}", f"forecast {tomorrow.tmax:.0f} °C: {tomorrow['in words']}"),
        ("hot_day", f"{hot_day.name:%d %b %Y}", f"{hot_day.tmax:.1f} °C: {hot_day['in words']}"),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Today

    | Time | | |
    |---|---|---|
    | 09:00 | **Welcome** | get set up |
    | 09:30 | **1 · Where is it hot?** | how satellites see heat, day and night |
    | 10:30 | *break* | |
    | 10:45 | **2 · Why are some places cooler?** | trees, lakes and concrete |
    | 11:30 | **3 · Who is at risk?** | heat, people and shade on one map |
    | 12:30 | *lunch* | |
    | 13:30 | **4 · When should we warn?** | tomorrow's alert for every ward |
    | 15:00 | close | |

    Change a number in a cell and everything that depends on it reruns; hover, click and drag the
    charts, nothing can break.

    ## The data

    | What | Source | Squares |
    |---|---|---|
    | Wards | [GBA wards, Dec 2025](https://data.opencity.in) (OpenCity) | 369 wards |
    | Heat by day | [Landsat 8 & 9](https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2) | 30 m |
    | Heat at night | [MODIS](https://planetarycomputer.microsoft.com/dataset/modis-11A2-061) | 1 km |
    | Ground cover | [ESA WorldCover](https://esa-worldcover.org) | 10 m |
    | Trees | [Meta / WRI canopy height](https://registry.opendata.aws/dataforgood-fb-forests/) | 1.2 m |
    | People | Census 2011 + [WorldPop 2025](https://www.worldpop.org) | 100 m |
    | Air temperature | [ERA5 and forecasts](https://open-meteo.com) (Open-Meteo) | ~25 km |

    ## Get set up

    **Windows** (PowerShell):

    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"   # then reopen PowerShell
    irm https://github.com/amanbagrecha/urban-heat-bengaluru/archive/main.zip -OutFile workshop.zip
    Expand-Archive workshop.zip -DestinationPath .
    cd urban-heat-bengaluru-main
    uv sync
    uv run marimo edit notebooks
    ```

    **macOS / Linux:**

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh     # then open a new terminal
    git clone https://github.com/amanbagrecha/urban-heat-bengaluru && cd urban-heat-bengaluru
    uv sync
    uv run marimo edit notebooks
    ```

    Then check that everything says `True`:
    """)
    return


@app.cell
def _():
    from wardheat.setup_check import checks

    checks()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="next">Next → <b>1 · Where is it hot?</b></div>
    """)
    return


if __name__ == "__main__":
    app.run()
