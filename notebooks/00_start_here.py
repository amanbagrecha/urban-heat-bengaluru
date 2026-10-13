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

    from wardheat import charts, datapack, indices
    from wardheat.wards import load_wards

    return charts, datapack, indices, load_wards, mo


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="kicker">Welcome · 09:00–09:30</div>

    # Urban heat, ward by ward

    <div class="lead">Bengaluru rarely crosses 40 °C, so it is easy to think heat is someone else's
    problem. But every March to May some neighbourhoods bake while others stay cool, and the people
    living there feel the difference. Today we use free satellite data and Python to find out where,
    for whom, and when to raise the alarm.</div>

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

    ## Where we are going

    By three o'clock you will have built this: a warning map that turns tomorrow's forecast into an
    alert for each of the city's 369 wards. Try the levels above the map.
    """)
    return


@app.cell(hide_code=True)
def _(charts, datapack, indices, load_wards):
    _f = datapack.table("ward_features")
    _g = charts.ward_shapes(load_wards(), _f.join(indices.ward_risk(_f)), keep=["label", "risk"])
    charts.alert_map(_g, level=2)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Today

    | Time | | |
    |---|---|---|
    | 09:00 | **Welcome** | setup, and how marimo notebooks work |
    | 09:30 | **1 · Where is it hot?** | satellite surface temperature, from pixels to wards |
    | 10:30 | *break* | |
    | 10:45 | **2 · Why are some places cooler?** | trees, water and what covers the ground |
    | 11:30 | **3 · Who is at risk?** | heat × people × lack of shade, on one map |
    | 12:30 | *lunch* | |
    | 13:30 | **4 · When should we warn?** | local thresholds, 35 years of hot seasons, ward alerts |
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
