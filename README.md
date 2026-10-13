# Urban heat, ward by ward

[![Fresh install](https://github.com/amanbagrecha/urban-heat-bengaluru/actions/workflows/fresh-install.yml/badge.svg)](https://github.com/amanbagrecha/urban-heat-bengaluru/actions/workflows/fresh-install.yml)

A hands-on workshop for people who know some Python but are new to satellite data. The whole day
follows one city, Bengaluru, and one question: where does it get dangerously hot, who lives there,
and when should they be warned? The answer is a heat alert for each of the city's 369 wards.

- **Morning: where and for whom.** Landsat and MODIS surface temperature read from the cloud,
  tree canopy and land cover, and a ward-level risk score: hazard × exposure × vulnerability.
- **Afternoon: when.** 35 years of daily air temperature, a local warning scale in the spirit of
  the US HeatRisk, this week's forecast, and one alert per ward.

Four short [marimo](https://marimo.io) notebooks with interactive charts (toggles, sliders,
brushing). Open data and open-source Python only; no Earth Engine.

The course pages, with every chart: [amanbagrecha.com/presentations/urban_heat_wards_2026](https://amanbagrecha.com/presentations/urban_heat_wards_2026/).

## Setup

You need [uv](https://docs.astral.sh/uv/), which also installs the right Python (3.12).

**Windows** (PowerShell, no git needed):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"   # then reopen PowerShell
irm https://github.com/amanbagrecha/urban-heat-bengaluru/archive/main.zip -OutFile workshop.zip
Expand-Archive workshop.zip -DestinationPath .
cd urban-heat-bengaluru-main
uv sync
uv run wardheat check                 # everything should say True
uv run marimo edit notebooks
```

**macOS and Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh     # then open a new terminal
git clone https://github.com/amanbagrecha/urban-heat-bengaluru && cd urban-heat-bengaluru
uv sync
uv run wardheat check                 # everything should say True
uv run marimo edit notebooks
```

The badge above is a weekly check that exactly these steps work on machines with nothing
installed: Windows (PowerShell, no git), macOS and Linux, all the way to running every notebook.

There is no data to download first. Lesson 1 reads a Landsat image live, and the small prepared
files (everything on one 30 m grid) download themselves the first time a notebook needs them. On
weak Wi-Fi, fetch them all at once with `uv run wardheat datapack download` (~40 MB).

## Data

| Lesson | What | Source | Detail | Licence |
|---|---|---|---|---|
| all | Wards | GBA wards, Dec 2025, with Census 2011 population ([OpenCity](https://data.opencity.in/dataset/gba-wards-delimitation-2025)) | 369 polygons | see source |
| 1 | Day heat | Landsat 8/9 Collection 2 surface temperature ([Planetary Computer](https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2)) | 30 m, 44 passes, Mar–May 2022–26 | public domain |
| 1, 2 | Night heat | MODIS MOD11A2/MYD11A2 ([Planetary Computer](https://planetarycomputer.microsoft.com/dataset/modis-11A2-061)) | 1 km | public domain |
| 1, 2 | Land cover | [ESA WorldCover 2021](https://esa-worldcover.org) | 10 m | CC BY 4.0 |
| 2, 3 | Tree canopy | [Meta / WRI canopy height v1](https://registry.opendata.aws/dataforgood-fb-forests/), trees ≥ 3 m | 1.2 m | CC BY 4.0 |
| 3 | People | Census 2011 ward totals spread with [WorldPop 2025](https://www.worldpop.org) | 100 m | CC BY 4.0 |
| 4 | Air temperature | ERA5 1991–today and 7-day forecasts via [Open-Meteo](https://open-meteo.com) | daily, ~25 km | CC BY 4.0 |

## Method in brief

Each ward gets three ingredients: **hazard** (surface temperature of built-up ground by day,
averaged with night), **exposure** (people per km², log-scaled) and **vulnerability** (lack of tree
canopy). Each is scaled 0–1 between the city's 5th and 95th percentiles and combined with a
geometric mean; the top 30 % of wards are High risk. The warning compares a day's max and night min
with the 1991–2020 record for that date (90/95/98/99.5th percentiles → levels 1–4, +1 for hot days
and nights in a row). Forecasts are bias-corrected to ERA5. A ward's alert combines the city level
with its risk class.

Limitations: surface temperature is not air temperature, and Landsat passes at 10:40 am, before the
daily peak. Population is modelled and canopy imagery is from 2018–20. Warning thresholds are not
yet calibrated against Bengaluru health records. A risk map shows where to look first; check it on
the ground before acting on it.

## Repository

```
notebooks/        the lessons (marimo) + theme.css
src/wardheat/
  charts.py       every chart (Altair), interactivity included
  indices.py      hazard × exposure × vulnerability
  warning.py      climatology, HeatRisk levels, ward alerts
  features.py     ward table and 240 m cell table from the rasters
  stac.py landsat.py modis.py landcover.py population.py climate.py wards.py grid.py
  site.py         notebooks -> static website (site.css)
  datapack.py build.py cli.py config.py setup_check.py
tests/run_notebook.py
```

For another city, edit `config.py` (bounding box, UTM zone, season), provide ward polygons with a
population column (`wards.py`), and run `uv run wardheat datapack build`.

Code: MIT. Data: see each source's licence above.
