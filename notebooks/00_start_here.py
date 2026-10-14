import marimo

__generated_with = "0.25.1"
app = marimo.App(
    width="compact",
    app_title="Urban heat, ward by ward",
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

    # Urban heat, ward by ward

    <div class="lead">Bengaluru rarely crosses 40 °C, so it is easy to think heat is someone else's
    problem. But every March to May some neighbourhoods bake while others stay cool, and the people
    living there feel the difference. Today you will use free satellite pictures and a little Python
    to find out where it gets hot, who lives there, and when to warn them.</div>

    ## About me

    I'm Aman Bagrecha, a geospatial consultant working on remote sensing, computer vision and
    open-source tools. I write about maps, satellites and code at
    [amanbagrecha.com](https://amanbagrecha.com), and I've spoken about open-source geospatial tools
    at FOSS4G in Kosovo, Seoul and Hiroshima. In Bengaluru I co-run
    [Let's Talk Spatial](https://letstalkspatial.in), a community for anyone into GIS, remote sensing
    and maps: free meetups, talks and workshops.

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

    By three o'clock you will have built a heat alert for each of the city's 369 wards, made from
    the weather forecast. Tomorrow, {tomorrow.name:%A %d %B}, the forecast is {tomorrow.tmax:.0f} °C:
    **{tomorrow["in words"]}** for the time of year, so {_warned or "no"} ward{"" if _warned == 1 else "s"}
    get an alert. The last hot day in our record was {hot_day.name:%d %B %Y} ({hot_day.tmax:.1f} °C,
    **{hot_day["in words"]}** for the time of year). The same weather is more dangerous where many
    people live with little shade, so those {_alerts.get("Heat alert", 0) + _alerts.get("Emergency", 0)}
    wards would have got a heat alert, and the rest a "take care".
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
    | 09:00 | **Welcome** | get set up, and how these notebooks work |
    | 09:30 | **1 · Where is it hot?** | how satellites see heat, by day and by night |
    | 10:30 | *break* | |
    | 10:45 | **2 · Why are some places cooler?** | trees, lakes and concrete |
    | 11:30 | **3 · Who is at risk?** | heat, people and shade, on one map |
    | 12:30 | *lunch* | |
    | 13:30 | **4 · When should we warn?** | what counts as hot for Bengaluru, and tomorrow's alerts |
    | 14:45 | questions | |
    | 15:00 | close | |

    Each lesson is one notebook in the `notebooks/` folder. They run independently, so if you fall
    behind you can always open the next one fresh.

    ## How these notebooks work

    A marimo notebook reruns itself: change a number in a cell and every cell that depends on it
    updates. You only need to read the code cells that are shown; the plotting code lives in
    `wardheat/charts.py` if you are curious.

    The charts are the point. Hover them, click them, drag the sliders and boxes. Nothing you do
    there can break anything.

    ## The data

    Everything is open and needs no account. Five summers of satellite pictures take minutes and
    gigabytes to process, so most charts read small files we prepared from these sources, all on
    one 30 m grid. Under each such chart, **How this file was made** shows the code that made it.

    | What we want to know | Dataset | Detail |
    |---|---|---|
    | Ward boundaries | [GBA wards, Dec 2025](https://data.opencity.in) (OpenCity) | 369 wards |
    | How hot surfaces get by day | [Landsat 8 & 9](https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2) surface temperature | 30 m, 44 passes, Mar–May 2022–26 |
    | How hot they stay at night | [MODIS](https://planetarycomputer.microsoft.com/dataset/modis-11A2-061) night surface temperature | 1 km |
    | What covers the ground | [ESA WorldCover](https://esa-worldcover.org) | 10 m |
    | Where the trees are | [Meta / WRI canopy height](https://registry.opendata.aws/dataforgood-fb-forests/) | 1.2 m |
    | Where people live | Census 2011 ward totals spread with [WorldPop 2025](https://www.worldpop.org) | 100 m |
    | How hot the air is, past and next week | [ERA5 and forecasts](https://open-meteo.com) via Open-Meteo | daily, ~25 km |

    ## Get set up

    You need [uv](https://docs.astral.sh/uv/), which installs Python and every package for you.

    **Windows.** Open PowerShell (Start menu, type "PowerShell") and run these one at a time:

    ```powershell
    # 1. install uv, once. Then close PowerShell and open it again.
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

    # 2. download the workshop and install its packages (no git needed)
    irm https://github.com/amanbagrecha/urban-heat-bengaluru/archive/main.zip -OutFile workshop.zip
    Expand-Archive workshop.zip -DestinationPath .
    cd urban-heat-bengaluru-main
    uv sync

    # 3. open the notebooks in your browser
    uv run marimo edit notebooks
    ```

    **macOS and Linux.** In a terminal:

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh     # once; then open a new terminal
    git clone https://github.com/amanbagrecha/urban-heat-bengaluru
    cd urban-heat-bengaluru
    uv sync
    uv run marimo edit notebooks
    ```

    To come back later, open a terminal in the workshop folder and run `uv run marimo edit notebooks`
    again.

    There is no data to download first. Lesson 1 reads a Landsat image straight from the cloud, and
    the small files we prepared in advance download themselves the first time a notebook needs them.

    ## Check your setup

    This checks the Python packages and the internet services we use. Everything should say `True`.
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
