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
    # tomorrow's real forecast, and this year's hottest day, through the system we build today
    _era5 = datapack.table("era5_daily")
    _normal = warning.climatology(_era5, base=(1991, 2020))
    tomorrow = warning.levels(climate.forecast(days=3), normal=_normal).loc[climate.today() + pd.Timedelta(days=1)]
    _levels = warning.levels(_era5.loc["1991":])
    _this_year = _era5.loc[str(_era5.index[-1].year), "tmax"]
    hot_day = _levels.loc[_this_year.idxmax()]  # this year's highest air temperature in the ERA5 record
    _wards = load_wards()
    _risk = indices.ward_risk(indices.ward_table(_wards))["risk"]  # as in lesson 3
    _f = _risk.to_frame().assign(tomorrow=warning.ward_alerts(int(tomorrow.level), _risk),
                                 hot_day=warning.ward_alerts(int(hot_day.level), _risk)).reset_index()
    alert_wards = charts.ward_shapes(_wards, _f, keep=["tomorrow", "hot_day"])
    return alert_wards, hot_day, tomorrow


@app.cell(hide_code=True)
def _(alert_wards, hot_day, mo, tomorrow):
    _warned = int((alert_wards["tomorrow"] != "No alert").sum())
    _hot = alert_wards["hot_day"].value_counts()
    _hot_alerts = " and ".join(f"{_hot[a]} on {a.lower()}" for a in ["Emergency", "Heat alert", "Take care"] if a in _hot)
    if tomorrow.level == 0:
        _tomorrow = (f"{tomorrow.tmax:.1f} °C, {tomorrow.tmax - tomorrow.tmax_normal:+.1f} °C from an average "
                     f"{tomorrow.name:%d %B} but below the 33 °C alert line, so no ward is warned")
    else:
        _tomorrow = f"{tomorrow.tmax:.1f} °C, which is {tomorrow['in words']}, so {_warned} wards are warned"
    mo.md(f"""
    ## Where we are going

    By 3 pm you will turn the air temperature forecast into a heat alert for each of the 369 wards. Tomorrow's
    forecast high is {_tomorrow}. On this year's hottest afternoon, {hot_day.name:%d %B %Y} ({hot_day.tmax:.1f} °C air
    temperature, ERA5, {hot_day['in words']}), the same rule would have put {_hot_alerts} of the 369 wards.
    """)
    return


@app.cell(hide_code=True)
def _(alert_wards, charts, hot_day, tomorrow):
    charts.alert_maps(alert_wards, [
        ("tomorrow", f"Tomorrow, {tomorrow.name:%d %b}", f"air temperature forecast: {tomorrow.tmax:.1f} °C · {tomorrow['in words']}"),
        ("hot_day", f"{hot_day.name:%d %b %Y}, this year's hottest day", f"air temperature (ERA5): {hot_day.tmax:.1f} °C · {hot_day['in words']}"),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Today

    | Time | | |
    |---|---|---|
    | 09:00 | **Welcome** | get set up |
    | 09:30 | **1 · Where is it hot?** | surface temperature from satellites, day and night |
    | 10:30 | *break* | |
    | 10:45 | **2 · Why are some places cooler?** | trees, lakes and concrete vs surface temperature |
    | 11:30 | **3 · Who is at risk?** | surface temperature, people and shade per ward |
    | 12:30 | *lunch* | |
    | 13:30 | **4 · When should we warn?** | air temperature forecast → tomorrow's alert per ward |
    | 15:00 | close | |

    Change a number in a cell and everything that depends on it reruns; hover, click and drag the
    charts, nothing can break.

    ## The data

    | What | How it is measured | When | Squares |
    |---|---|---|---|
    | Wards | [GBA ward boundaries](https://data.opencity.in/dataset/gba-wards-delimitation-2025) (OpenCity) | Dec 2025 | 369 wards |
    | Surface temperature, day | [Landsat 8 & 9](https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2): thermal camera, 705 km up | 10:40 am, Mar–May 2022–26 (44 pictures) | 30 m |
    | Surface temperature, night | [MODIS](https://planetarycomputer.microsoft.com/dataset/modis-11A2-061) on Terra and Aqua: thermal camera, 8-day averages | ~10 pm and ~2:30 am, Mar–May 2022–26 (105 files) | 1 km |
    | Ground cover | [ESA WorldCover](https://esa-worldcover.org): Sentinel-1 radar and Sentinel-2 photos sorted into 11 classes | 2021 | 10 m |
    | Trees | [Meta & WRI tree heights](https://registry.opendata.aws/dataforgood-fb-forests/): an AI model reading Maxar satellite photos | photos mostly 2018–2020 | ~1 m |
    | People | Census 2011 headcount of each ward, in the GBA ward file (next census: February 2027) | 1 March 2011 | 369 wards |
    | Air temperature, past | [ERA5](https://open-meteo.com/en/docs/historical-weather-api) (ECMWF): station, balloon and satellite readings fed into a weather model | each day's highest and lowest, 1991 to Sep 2026 | ~25 km |
    | Air temperature, forecast | [Open-Meteo forecast](https://open-meteo.com/en/docs): ECMWF's global weather model | the next 7 days | 9 km |

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
