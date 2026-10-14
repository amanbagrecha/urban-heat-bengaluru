"""Charts for the lessons: one quiet look, with the interactivity inside the chart.

Every chart here is plain Altair (Vega-Lite). Sliders, toggles, hovering and
brushing all run in the browser, so a chart behaves the same inside marimo
and on a static web page exported with ``wardheat site``.
"""

from __future__ import annotations

import json
import warnings

import altair as alt
import geopandas as gpd
import numpy as np
import pandas as pd

from .warning import WORDS

# ---------------------------------------------------------------------------
# Look
# ---------------------------------------------------------------------------
INK, MUTED, RULE, PAPER = "#1d1b16", "#6b665c", "#e3ded2", "#faf8f3"
FONT = "IBM Plex Sans, system-ui, sans-serif"

HEAT = ["#fbf3dc", "#f5d58a", "#eda65a", "#d9693b", "#ad372c", "#5f1d2b"]
TREES = ["#f4f0e6", "#c9d9a8", "#8fb36b", "#4f8a3f", "#24572a"]
PEOPLE = ["#f4f0e6", "#dccbe0", "#b08fbf", "#7c5795", "#4a2b63"]
COVER = {"trees": "#4f7d4a", "water": "#3d7ea6", "mixed": "#b9b2a5", "built-up": "#8c5a4a", "farmland": "#d1a24f"}
RISK = {"Low": "#ece4cf", "Medium": "#e9a35a", "High": "#b23a2e"}
LEVEL_COLORS = ["#d9e6cc", "#f2cf5b", "#e8893a", "#c8442d", "#7d2a5c"]
ALERTS = ["No alert", "Take care", "Heat alert", "Emergency"]
ALERT_COLORS = ["#e2ddcf", "#f2cf5b", "#e8893a", "#b23a2e"]
MATRIX = {"Low": [0, 0, 1, 2, 3], "Medium": [0, 1, 1, 2, 3], "High": [0, 1, 2, 3, 3]}  # = warning.ALERT_MATRIX


def _theme():
    axis = dict(labelColor=MUTED, titleColor=MUTED, labelFontSize=11, titleFontSize=11, titleFontWeight=500,
                gridColor=RULE, domainColor="#cfc8b8", tickColor="#cfc8b8", labelFont=FONT, titleFont=FONT)
    return {"config": {
        "background": "transparent",
        "font": FONT,
        "view": {"stroke": None},
        "title": dict(font=FONT, fontSize=14, fontWeight=600, color=INK, anchor="start", offset=12,
                      subtitleFont=FONT, subtitleFontSize=12, subtitleColor=MUTED),
        "axis": axis,
        "axisY": {"domain": False, "ticks": False},
        "legend": dict(labelColor=MUTED, titleColor=INK, labelFontSize=11, titleFontSize=11, titleFontWeight=500,
                       labelFont=FONT, titleFont=FONT, orient="bottom", direction="horizontal", symbolType="square"),
        "text": {"font": FONT, "color": INK},
        "range": {"category": list(COVER.values())},
    }}


alt.theme.register("wardheat", enable=True)(_theme)
alt.data_transformers.disable_max_rows()  # the city map has ~12 000 cells; that is fine in a browser
# a hover selection shared by two linked views is merged by Altair on purpose
warnings.filterwarnings("ignore", message="Automatically deduplicated selection parameter")


def _when(param: str, options: dict[str, str]) -> str:
    """Vega expression picking ``datum[column]`` for the option chosen in ``param``."""
    parts = [f"{param} == {json.dumps(label)} ? datum[{json.dumps(col)}]" for label, col in options.items()]
    return " : ".join(parts) + " : null"


def _switch(name: str, options: list[str], label: str = ""):
    return alt.param(name=name, value=options[0], bind=alt.binding_radio(options=options, name=label))


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
def ward_shapes(wards: gpd.GeoDataFrame, table: pd.DataFrame | None = None, keep: list[str] | None = None) -> gpd.GeoDataFrame:
    """Wards in lon/lat with simplified outlines (~30 m) and only the columns a chart needs.

    Altair embeds every column of every feature in the page, so keeping this lean
    is what keeps the notebook (and the web page) light.
    """
    g = wards[["ward_uid", "label", "geometry"]].to_crs(4326)
    if table is not None:
        g = g.merge(table.drop(columns=["label"], errors="ignore"), on="ward_uid", how="left")
    if keep is not None:
        g = g[["ward_uid", "label", *[c for c in dict.fromkeys(keep) if c in g.columns and c not in ("ward_uid", "label")], "geometry"]]
    g = g.copy()
    g["geometry"] = g.geometry.simplify(0.0003, preserve_topology=True).set_precision(1e-5)
    for c in g.columns:
        if c not in ("geometry", "H", "E", "V", "score") and pd.api.types.is_float_dtype(g[c]):
            g[c] = g[c].round(3)
    return g


# ---------------------------------------------------------------------------
# Maps
# ---------------------------------------------------------------------------
def image(arr, unit: str = "°C", vmin: float | None = None, vmax: float | None = None):
    """A raster as a plain picture (matplotlib) in the same colours as the interactive maps."""
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap

    lo, hi = np.nanpercentile(arr, [2, 98])
    vmin, vmax = (lo if vmin is None else vmin), (hi if vmax is None else vmax)
    fig, ax = plt.subplots(figsize=(6.4, 6.2))
    im = ax.imshow(arr, cmap=LinearSegmentedColormap.from_list("heat", HEAT), vmin=vmin, vmax=vmax, interpolation="nearest")
    ax.set_axis_off()
    cb = fig.colorbar(im, ax=ax, orientation="horizontal", fraction=0.035, pad=0.02, aspect=40)
    cb.set_label(unit, color=MUTED, fontsize=9)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=8, colors=MUTED, length=0)
    fig.patch.set_alpha(0)
    return fig



def images(pictures: dict, unit: str = "°C"):
    """Rasters side by side as plain pictures, each with its own colour bar; keys are the titles.

    A value is an array, or ``(array, unit, colours)``.
    """
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    fig, axes = plt.subplots(1, len(pictures), figsize=(4.2 * len(pictures), 4.6))
    for ax, (title, pic) in zip(np.atleast_1d(axes), pictures.items()):
        arr, u, colours = pic if isinstance(pic, tuple) else (pic, unit, HEAT)
        lo, hi = np.nanpercentile(arr, [2, 98])
        im = ax.imshow(arr, cmap=LinearSegmentedColormap.from_list("c", colours), vmin=lo, vmax=hi, interpolation="nearest")
        ax.set_title(title, fontsize=10, color=INK, loc="left")
        ax.set_axis_off()
        cb = fig.colorbar(im, ax=ax, orientation="horizontal", fraction=0.04, pad=0.03, aspect=30)
        cb.set_label(u, color=MUTED, fontsize=9)
        cb.outline.set_visible(False)
        cb.ax.tick_params(labelsize=8, colors=MUTED, length=0)
    fig.patch.set_alpha(0)
    plt.close(fig)
    return fig

def _cells(px: pd.DataFrame, cols: dict[str, str]) -> tuple[pd.DataFrame, alt.LookupData]:
    """Compact cell table (short keys, ward ids) + a lookup table of ward names: ~3x smaller pages."""
    d = pd.DataFrame({"c": px["col"], "r": px["row"], "w": px["ward_uid"]})
    for k, v in cols.items():
        d[k] = px[v].astype("float64").round(2) if pd.api.types.is_float_dtype(px[v]) else px[v]  # float32 -> long JSON
    names = px.drop_duplicates("ward_uid")[["ward_uid", "ward"]].rename(columns={"ward_uid": "w"})
    return d, alt.LookupData(names, "w", ["ward"])


def _grid_xy(px: pd.DataFrame, cell: float) -> dict:
    """x/x2/y/y2 encodings placing each cell at its column/row (row 0 = north)."""
    c0, c1, r0, r1 = px.col.min(), px.col.max() + 1, px.row.min(), px.row.max() + 1
    return dict(
        enc=dict(x=alt.X("c:Q", scale=alt.Scale(domain=[c0, c1], nice=False, zero=False), axis=None), x2="c2:Q",
                 y=alt.Y("r:Q", scale=alt.Scale(domain=[r1, r0], nice=False, zero=False), axis=None), y2="r2:Q"),
        size=dict(width=float((c1 - c0) * cell), height=float((r1 - r0) * cell)),
    )


def cell_map(px: pd.DataFrame, show: dict[str, str], unit: str, palette=HEAT, cell: float = 4, title: str = "",
             subtitle: str = "", fmt: str = ".1f", domains: dict[str, list] | None = None):
    """Every 240 m cell of the city as a small square. ``show`` maps a button label to a column.

    ``domains`` fixes the colour range per option (e.g. day 34-44 °C, night 22-27 °C).
    Hovering a cell lights up its whole ward.
    """
    keys = {f"v{i}": col for i, col in enumerate(show.values())}
    data, names = _cells(px, keys)
    base = alt.Chart(data, title=alt.Title(title, subtitle=subtitle) if title else alt.Undefined)
    params = []
    if len(show) > 1:
        params.append(_switch("layer", list(show)))
        base = base.transform_calculate(value=_when("layer", dict(zip(show, keys))))
    else:
        base = base.transform_calculate(value="datum.v0")
    hover = alt.selection_point(name="ward_hover", fields=["w"], on="pointerover", clear="pointerout")
    xy = _grid_xy(px, cell)
    scale = dict(range=palette, zero=False)
    if domains:
        if len(show) > 1:
            expr = " : ".join(f"layer == {json.dumps(k)} ? {json.dumps(v)}" for k, v in domains.items()) + " : null"
            scale.update(domain=alt.ExprRef(expr), clamp=True)
        else:
            scale.update(domain=next(iter(domains.values())), clamp=True)
    return (
        base.transform_lookup(lookup="w", from_=names)
        .transform_calculate(c2="datum.c + 1.06", r2="datum.r + 1.06")
        .mark_rect()
        .encode(
            **xy["enc"],
            color=alt.Color("value:Q", scale=alt.Scale(**scale), legend=alt.Legend(title=unit, gradientLength=220, gradientThickness=8)),
            opacity=alt.when(hover).then(alt.value(1)).otherwise(alt.value(0.3)),
            tooltip=[alt.Tooltip("ward:N", title="ward"), alt.Tooltip("value:Q", format=fmt, title=unit)],
        )
        .add_params(hover, *params)
        .properties(**xy["size"])
    )


def ward_map(g: gpd.GeoDataFrame, show: dict[str, str], unit: str = "", palette=HEAT, title: str = "", subtitle: str = "",
             tooltip: list | None = None, width: int = 500, height: int = 520, fmt: str = ".1f"):
    """Ward choropleth; with several entries in ``show`` you get a toggle above the map."""
    chart = alt.Chart(g, title=alt.Title(title, subtitle=subtitle) if title else alt.Undefined)
    if len(show) > 1:
        chart = chart.add_params(_switch("ward_layer", list(show))).transform_calculate(value=_when("ward_layer", show))
    else:
        chart = chart.transform_calculate(value=f"datum[{json.dumps(next(iter(show.values())))}]")
    tips = tooltip or [alt.Tooltip("label:N", title="ward"), alt.Tooltip("value:Q", format=fmt, title=unit or "value")]
    return (
        chart.mark_geoshape(stroke=PAPER, strokeWidth=0.5)
        .encode(color=alt.Color("value:Q", scale=alt.Scale(range=palette, zero=False),
                                legend=alt.Legend(title=unit, gradientLength=220, gradientThickness=8)),
                tooltip=tips)
        .project("mercator")
        .properties(width=width, height=height)
    )


# ---------------------------------------------------------------------------
# Lesson 2: why are some places cooler?
# ---------------------------------------------------------------------------
LANDMARKS = {"Cubbon Park": (77.5929, 12.9763), "Lalbagh": (77.5848, 12.9507)}  # lon, lat


def _landmarks(factor: int = 8) -> pd.DataFrame:
    """Column/row of each landmark in the 240 m cell grid, to label the city maps."""
    from pyproj import Transformer

    from . import datapack

    g = datapack.grid30()
    to_grid = Transformer.from_crs(4326, g.crs, always_xy=True)
    rows = []
    for name, (lon, lat) in LANDMARKS.items():
        x, y = to_grid.transform(lon, lat)
        rows.append({"name": name, "c": (x - g.transform.c) / g.transform.a / factor,
                     "r": (y - g.transform.f) / g.transform.e / factor})
    return pd.DataFrame(rows)


def greens_explorer(px: pd.DataFrame):
    """Scatter of tree canopy vs daytime surface temperature, linked to the city map.

    Drag a box on the scatter: the matching cells light up on the map. Cubbon Park and Lalbagh are labelled.
    """
    brush = alt.selection_interval(name="brush", encodings=["x", "y"], value={"x": [0.35, 1.0], "y": [29, 47]})
    data, names = _cells(px, {"canopy": "canopy", "lst": "lst_day", "cover": "cover"})
    base = alt.Chart(data).transform_lookup(lookup="w", from_=names)
    tips = [alt.Tooltip("ward:N", title="ward"), alt.Tooltip("canopy:Q", format=".0%", title="tree canopy"),
            alt.Tooltip("lst:Q", format=".1f", title="surface °C"), alt.Tooltip("cover:N", title="mostly")]
    scatter = (
        base.mark_circle(size=7)
        .encode(
            x=alt.X("canopy:Q", title="tree canopy cover", axis=alt.Axis(format="%")),
            y=alt.Y("lst:Q", title="surface temperature, 10:40 am (°C)", scale=alt.Scale(domain=[29, 47], nice=False)),
            color=alt.when(brush).then(alt.Color("cover:N", scale=alt.Scale(domain=list(COVER), range=list(COVER.values())),
                                                 legend=alt.Legend(title=None))).otherwise(alt.value("#dcd6c8")),
            opacity=alt.value(0.55),
            tooltip=tips,
        )
        .add_params(brush)
        .properties(width=330, height=330, title=alt.Title("Each dot is a 240 m patch of the city",
                                                           subtitle="Drag a box over any group of dots; dashed: trend through all dots"))
    )
    trend = base.transform_regression("canopy", "lst").mark_line(color=INK, strokeWidth=1.5, strokeDash=[4, 3]).encode(x="canopy:Q", y="lst:Q")
    xy = _grid_xy(px, 2.6)
    city = (
        base.transform_calculate(c2="datum.c + 1.06", r2="datum.r + 1.06")
        .mark_rect()
        .encode(
            **xy["enc"],
            color=alt.when(brush).then(alt.Color("cover:N", scale=alt.Scale(domain=list(COVER), range=list(COVER.values())),
                                                 legend=None))
            .otherwise(alt.value("#efebe3")),
            tooltip=tips,
        )
        .properties(**xy["size"], title=alt.Title("…and here they are", subtitle="Selected patches in the dots' colours"))
    )
    marks = alt.Chart(_landmarks())
    ring = marks.mark_point(shape="circle", filled=False, size=90, color=INK, strokeWidth=1.5).encode(
        x=alt.X("c:Q"), y=alt.Y("r:Q"), tooltip=alt.Tooltip("name:N", title="park"))
    name = marks.mark_text(align="left", dx=8, fontSize=11, fontWeight=600, color=INK).encode(
        x=alt.X("c:Q"), y=alt.Y("r:Q"), text="name:N")
    return alt.hconcat(scatter + trend, city + ring + name, spacing=24).resolve_scale(color="independent")


def day_night_by_cover(px: pd.DataFrame):
    """How much hotter or cooler than the city average each kind of place is, by day and by night."""
    rows = []
    for when, col in (("day, 10:40 am (Landsat)", "lst_day"), ("night, ~10 pm and ~2:30 am (MODIS)", "lst_night")):
        mean = px[col].mean()
        d = px.groupby("cover")[col].mean().sub(mean).rename("diff").reset_index()
        d["when"] = when
        rows.append(d)
    df = pd.concat(rows)
    order = ["farmland", "built-up", "mixed", "trees", "water"]
    base = alt.Chart(df, title=alt.Title("Surface temperature compared with the city average", subtitle="Farmland flips from hottest by day to cool at night; built-up stays warm"))
    rule = base.mark_rule(color=RULE).encode(y=alt.Y("cover:N", sort=order, title=None), x="min(diff):Q", x2="max(diff):Q")
    pts = base.mark_circle(size=110, opacity=1).encode(
        y=alt.Y("cover:N", sort=order, title=None),
        x=alt.X("diff:Q", title="°C warmer (+) or cooler (−) than the city average"),
        color=alt.Color("when:N", scale=alt.Scale(range=["#d9693b", "#3b4a7a"]), legend=alt.Legend(title=None, labelLimit=320)),
        tooltip=["cover:N", "when:N", alt.Tooltip("diff:Q", format="+.1f", title="°C vs city")],
    )
    zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=MUTED, strokeDash=[2, 2]).encode(x="x:Q")
    return (zero + rule + pts).properties(width=520, height=190)


# ---------------------------------------------------------------------------
# Lesson 3: who is at risk?
# ---------------------------------------------------------------------------
def ingredient_maps(g: gpd.GeoDataFrame, width: int = 215, height: int = 240):
    """What was measured in each ward, in real units: surface temperature, people per hectare, tree cover.

    ``g`` needs ``label``, ``surface_temp`` (°C), ``people_per_ha`` and ``trees`` (0-1).
    """
    maps = []
    for col, title, subtitle, scale, fmt, tip in [
        ("surface_temp", "Surface temperature", "°C, average of 10:40 am and night",
         alt.Scale(range=HEAT, domain=[29.5, 34.5]), ".2f", "surface °C"),
        ("people_per_ha", "People", "per hectare (log colour scale)", alt.Scale(range=PEOPLE[1:], type="log", domain=[10, 1500]),
         ",.0f", "people per hectare"),
        ("trees", "Tree cover", "% of the ward under trees", alt.Scale(range=TREES[1:], domain=[0, 0.6]), ".1%",
         "tree cover"),
    ]:
        maps.append(
            alt.Chart(g, title=alt.Title(title, subtitle=subtitle))
            .mark_geoshape(stroke=PAPER, strokeWidth=0.3)
            .encode(color=alt.Color(f"{col}:Q", scale=scale,
                                    legend=alt.Legend(title=None, format=fmt.replace(".1%", ".0%").replace(".2f", ".1f"), orient="bottom",
                                                      gradientLength=190, gradientThickness=8)),
                    tooltip=[alt.Tooltip("label:N", title="ward"), alt.Tooltip(f"{col}:Q", format=fmt, title=tip)])
            .project("mercator")
            .properties(width=width, height=height)
        )
    return alt.hconcat(*maps, spacing=10).resolve_scale(color="independent")


def risk_explorer(g: gpd.GeoDataFrame):
    """Risk = H^wH × E^wE × V^wV computed in the browser (all weights 1 = the plain product); sliders change the weights.

    ``g`` needs columns ``label``, ``H``, ``E``, ``V`` (0-1) and any tooltip columns.
    """
    wH = alt.param(name="wH", value=1, bind=alt.binding_range(min=0, max=3, step=0.5, name="Surface temperature "))
    wE = alt.param(name="wE", value=1, bind=alt.binding_range(min=0, max=3, step=0.5, name="People "))
    wV = alt.param(name="wV", value=1, bind=alt.binding_range(min=0, max=3, step=0.5, name="Lack of shade "))
    hl = alt.selection_point(name="hl", fields=["label"], on="pointerover", clear="pointerout", empty=False)
    score = "pow(datum.H, wH) * pow(datum.E, wE) * pow(datum.V, wV)"
    base = (
        alt.Chart(g)
        .add_params(wH, wE, wV)
        .transform_calculate(score=score)
        .transform_window(rank="percent_rank()", sort=[alt.SortField("score", order="ascending")])
        .transform_calculate(risk="datum.rank >= 0.7 ? 'High' : datum.rank >= 0.4 ? 'Medium' : 'Low'")
    )
    risk_color = alt.Color("risk:N", scale=alt.Scale(domain=list(RISK), range=list(RISK.values())), legend=alt.Legend(title=None))
    extra = {"surface_temp": (".2f", "surface °C"),
             "people_per_ha": (",.0f", "people / hectare"), "trees": (".1%", "tree cover")}
    tips = [alt.Tooltip("label:N", title="ward"), alt.Tooltip("risk:N"), alt.Tooltip("score:Q", format=".3f", title="risk score")]
    tips += [alt.Tooltip(f"{c}:Q", format=f, title=t) for c, (f, t) in extra.items() if c in g.columns]
    city = (
        base.mark_geoshape()
        .encode(color=risk_color, tooltip=tips,
                stroke=alt.when(hl).then(alt.value(INK)).otherwise(alt.value(PAPER)),
                strokeWidth=alt.when(hl).then(alt.value(1.5)).otherwise(alt.value(0.4)))
        .add_params(hl)
        .project("mercator")
        .properties(width=320, height=340, title=alt.Title("Heat risk by ward", subtitle="Top 30 % of wards = High"))
    )
    top = (
        base.transform_window(n="row_number()", sort=[alt.SortField("score", order="descending")])
        .transform_filter("datum.n <= 20")
        .mark_bar(height=11)
        .encode(
            x=alt.X("score:Q", title="risk score", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(values=[0, 0.5, 1])),
            y=alt.Y("label:N", sort="-x", title=None, axis=alt.Axis(labelLimit=160, labelFontSize=10)),
            color=alt.when(hl).then(alt.value(INK)).otherwise(alt.value(RISK["High"])),
            tooltip=tips,
        )
        .add_params(hl)
        .properties(width=100, height=320, title=alt.Title("20 highest", subtitle=" "))
    )
    return alt.hconcat(city, top, spacing=10)


# ---------------------------------------------------------------------------
# Lesson 4: when should we warn?
# ---------------------------------------------------------------------------
def heat_calendar(hr: pd.DataFrame, first_year: int = 2024, line: float = 33.0):
    """Every March-May day since 1991 coloured by its level; click a year to see its highest air temperatures.

    ``hr`` is the output of ``warning.levels`` (index = date).
    """
    d = hr[hr.index.month.isin([3, 4, 5])].rename_axis("date").reset_index().rename(columns={"in words": "words"})
    d["year"] = d["date"].dt.year
    d["day"] = (d["date"] - pd.to_datetime(d["year"].astype(str) + "-03-01")).dt.days
    d["date_s"] = d["date"].dt.strftime("%d %b %Y")
    d = d[["date_s", "year", "day", "level", "words", "tmax"]].round(1)
    year = alt.selection_point(name="year_pick", fields=["year"], value=[{"year": first_year}], on="click", clear=False)
    ticks = "datum.value == 0 ? '1 Mar' : datum.value == 31 ? '1 Apr' : datum.value == 61 ? '1 May' : ''"
    level_color = alt.Color("words:N", scale=alt.Scale(domain=WORDS, range=LEVEL_COLORS),
                            legend=alt.Legend(title=None, orient="bottom", direction="horizontal"))
    tips = [alt.Tooltip("date_s:N", title="date"), alt.Tooltip("words:N", title="level"),
            alt.Tooltip("tmax:Q", title="highest air °C")]
    cal = (
        alt.Chart(d, title=alt.Title("36 hot seasons, one row each", subtitle="Click a year to see it below"))
        .mark_rect(stroke=PAPER, strokeWidth=0.3)
        .encode(
            x=alt.X("day:O", title=None, axis=alt.Axis(values=[0, 31, 61], labelExpr=ticks, labelAngle=0, domain=False, ticks=False)),
            y=alt.Y("year:O", title=None, sort="descending", axis=alt.Axis(values=list(range(1991, 2027, 5)) + [2024])),
            color=level_color,
            opacity=alt.when(year).then(alt.value(1)).otherwise(alt.value(0.55)),
            tooltip=tips,
        )
        .add_params(year)
        .properties(width=560, height=330)
    )
    sel = alt.Chart(d).transform_filter(year)
    x = alt.X("day:Q", title=None, scale=alt.Scale(domain=[0, 91], nice=False),
              axis=alt.Axis(values=[0, 31, 61], labelExpr=ticks, grid=False))
    y = alt.Y("tmax:Q", title="highest air temperature (ERA5), °C", scale=alt.Scale(domain=[25, 38]))
    tmax = sel.mark_line(color="#b03a2e", strokeWidth=1.8).encode(x=x, y=y)
    alert = alt.Chart(pd.DataFrame({"t": [line]})).mark_rule(color=INK, strokeDash=[4, 3], strokeWidth=1).encode(y="t:Q")
    strip = sel.mark_rect().encode(
        x=x, x2="day2:Q", y=alt.value(326), y2=alt.value(336),
        color=alt.Color("words:N", scale=alt.Scale(domain=WORDS, range=LEVEL_COLORS), legend=None), tooltip=tips,
    ).transform_calculate(day2="datum.day + 1")
    label = sel.transform_aggregate(year="max(year)").mark_text(align="left", fontSize=13, fontWeight=600, dx=4, dy=4).encode(
        x=alt.value(0), y=alt.value(0), text="year:O")
    detail = (tmax + alert + strip + label).properties(
        width=560, height=340,
        title=alt.Title("Each day's highest air temperature, ERA5", subtitle=f"Dashed: the {line:.0f} °C alert line. Strip: the level"),
    )
    return alt.vconcat(cal, detail, spacing=28)


def alert_maps(g: gpd.GeoDataFrame, maps: list[tuple[str, str, str]], width: int = 320, height: int = 340):
    """Ward alert maps side by side. ``maps`` lists (column of alert names, title, subtitle)."""
    color = alt.Color("alert:N", scale=alt.Scale(domain=ALERTS, range=ALERT_COLORS),
                      legend=alt.Legend(title=None, orient="bottom", direction="horizontal"))
    charts = [
        alt.Chart(g, title=alt.Title(title, subtitle=subtitle))
        .transform_calculate(alert=f"datum[{json.dumps(col)}]")
        .mark_geoshape(stroke=PAPER, strokeWidth=0.4)
        .encode(color=color, tooltip=[alt.Tooltip("label:N", title="ward"), alt.Tooltip("alert:N", title="alert")])
        .project("mercator")
        .properties(width=width, height=height)
        for col, title, subtitle in maps
    ]
    return alt.hconcat(*charts, spacing=16)


# ---------------------------------------------------------------------------
# Explainers
# ---------------------------------------------------------------------------
SATELLITE_SEES_HEAT = """
<svg viewBox="0 0 660 250" width="100%" style="max-width:660px; font: 12px var(--sans, sans-serif)" role="img"
     aria-label="Warm surfaces give off thermal infrared light; the satellite measures it">
  <rect x="270" y="8" width="120" height="30" rx="4" fill="#1d1b16"/><rect x="236" y="17" width="34" height="12" fill="#6b665c"/>
  <rect x="390" y="17" width="34" height="12" fill="#6b665c"/>
  <text x="330" y="28" fill="#faf8f3" text-anchor="middle">Landsat</text>
  <text x="440" y="27" fill="#6b665c">705 km up: a camera for heat glow</text>
  <circle cx="40" cy="40" r="18" fill="#f2cf5b"/><text x="40" y="74" fill="#6b665c" text-anchor="middle">sun</text>
  <path d="M60 52 L120 150" stroke="#f2cf5b" stroke-width="2" stroke-dasharray="4 4"/>
  <g fill="none" stroke-linecap="round">
    <path d="M110 150 q-6 -12 0 -24 q6 -12 0 -24 q-6 -12 0 -24 q6 -12 0 -24 q-6 -12 0 -24" stroke="#b23a2e" stroke-width="5"/>
    <path d="M330 150 q-6 -12 0 -24 q6 -12 0 -24 q-6 -12 0 -24 q6 -12 0 -24" stroke="#e8893a" stroke-width="3"/>
    <path d="M550 150 q-6 -12 0 -24 q6 -12 0 -24 q-6 -12 0 -24" stroke="#f2cf5b" stroke-width="1.5"/>
  </g>
  <rect x="40" y="155" width="140" height="22" fill="#3a3632"/><text x="110" y="198" text-anchor="middle" fill="#1d1b16">roofs and roads</text>
  <text x="110" y="214" text-anchor="middle" fill="#b23a2e" font-weight="600">≈ 40 °C, glows most</text>
  <circle cx="300" cy="145" r="16" fill="#3f7d3a"/><circle cx="330" cy="140" r="20" fill="#3f7d3a"/><circle cx="360" cy="146" r="15" fill="#3f7d3a"/>
  <rect x="270" y="160" width="120" height="17" fill="#5f8a4f"/><text x="330" y="198" text-anchor="middle" fill="#1d1b16">trees</text>
  <text x="330" y="214" text-anchor="middle" fill="#e8893a" font-weight="600">≈ 37 °C</text>
  <rect x="480" y="158" width="140" height="19" rx="9" fill="#4a7fb0"/><text x="550" y="198" text-anchor="middle" fill="#1d1b16">lake</text>
  <text x="550" y="214" text-anchor="middle" fill="#b0902a" font-weight="600">≈ 32 °C, glows least</text>
  <text x="330" y="242" text-anchor="middle" fill="#6b665c">Bengaluru's surface temperature (Landsat), 10:40 am, middle value of March–May 2022–26</text>
</svg>
"""


def zonal_explainer(values: np.ndarray, labels: np.ndarray, names: pd.Series, row: int, col: int, size: int = 60,
                    mark: str | None = None):
    """What zonal_stats does, on a real ``size`` x ``size`` block of 30 m squares: left, every square's value with the
    ward borders; right, every square painted with its ward's average (over all of the ward's squares)."""
    from .grid import zonal_stats

    means = zonal_stats({"v": values}, labels)["v_mean"]
    lab = labels[row:row + size, col:col + size]
    val = values[row:row + size, col:col + size]
    rr, cc = np.mgrid[0:size, 0:size]
    cells = pd.DataFrame({"x": cc.ravel(), "y": rr.ravel(), "w": lab.ravel(), "v": np.round(val.ravel(), 1)})
    cells = cells[cells.w > 0]
    cells["m"] = cells.w.map(means).round(1)
    cells["ward"] = cells.w.map(names)
    cells[["x2", "y2"]] = cells[["x", "y"]] + 1.05  # a hair of overlap so no seams show between squares
    edges = [dict(x=j + 1, x2=j + 1, y=i, y2=i + 1) for i in range(size) for j in range(size - 1) if lab[i, j] != lab[i, j + 1]]
    edges += [dict(x=j, x2=j + 1, y=i + 1, y2=i + 1) for i in range(size - 1) for j in range(size) if lab[i, j] != lab[i + 1, j]]
    x = alt.X("x:Q", scale=alt.Scale(domain=[0, size], nice=False), axis=None)
    y = alt.Y("y:Q", scale=alt.Scale(domain=[size, 0], nice=False), axis=None)
    lo, hi = np.nanpercentile(val[lab > 0], [5, 95])
    heat = alt.Scale(range=HEAT, domain=[round(lo, 1), round(hi, 1)], clamp=True)
    borders = alt.Chart(pd.DataFrame(edges)).mark_rule(color=INK, strokeWidth=1.2).encode(x=x, x2="x2:Q", y=y, y2="y2:Q")
    left = alt.Chart(cells).mark_rect().encode(
        x=x, x2="x2:Q", y=y, y2="y2:Q",
        color=alt.when("isValid(datum.v)").then(alt.Color("v:Q", scale=heat, legend=alt.Legend(title="surface °C", orient="bottom",
                                                                                               gradientLength=260, gradientThickness=8)))
        .otherwise(alt.value("#e9e5dc")),
        tooltip=[alt.Tooltip("ward:N"), alt.Tooltip("v:Q", format=".1f", title="this square, surface °C")])
    right = alt.Chart(cells).mark_rect().encode(
        x=x, x2="x2:Q", y=y, y2="y2:Q", color=alt.Color("m:Q", scale=heat, legend=None),
        tooltip=[alt.Tooltip("ward:N"), alt.Tooltip("m:Q", format=".1f", title="ward average, surface °C")])
    layers_r = [right, borders]
    if mark is not None and (lab == mark).any():
        r_, c_ = np.nonzero(lab == mark)
        label = pd.DataFrame({"x": [c_.mean() + 0.5], "y": [r_.mean() + 0.5], "t": [str(names[mark]).split(" · ")[-1]]})
        layers_r.append(alt.Chart(label).mark_text(fontSize=11, fontWeight=600, color=INK).encode(x=x, y=y, text="t:N"))
    w = h = 280
    return alt.hconcat(
        alt.layer(left, borders).properties(width=w, height=h, title=alt.Title("Before: every 30 m square",
                                                                                subtitle="Lines are ward borders")),
        alt.layer(*layers_r).properties(width=w, height=h, title=alt.Title("After zonal_stats: one number per ward",
                                                                            subtitle="Each ward painted with the average of its squares")),
        spacing=18,
    )


def levels_explainer(era5: pd.DataFrame, normal: pd.DataFrame, day: str, lines=(33.0, 34.0, 35.0, 36.0), base=(1991, 2020)):
    """The fixed gauge as a coloured scale in °C, with how many days of ``base`` fell in each zone, and one day pinned."""
    d = pd.Timestamp(day)
    past = era5.loc[str(base[0]):str(base[1]), "tmax"]
    counts = np.histogram(past, bins=[-np.inf, *lines, np.inf])[0]
    usual = float(normal.loc[d.dayofyear, "tmax_mean"])
    that = float(era5.loc[day, "tmax"])
    lo, hi = np.floor(min(usual, lines[0]) - 2), max(np.ceil(that), lines[-1]) + 1.5
    zones = pd.DataFrame({
        "from": [lo, *lines], "to": [*lines, hi],
        "words": WORDS,
        "days": [f"{c:,}" for c in counts],
        "ink": [INK, INK, INK, PAPER, PAPER],
    })
    x = alt.X("from:Q", scale=alt.Scale(domain=[lo, hi], nice=False), title="highest air temperature of the day, °C",
              axis=alt.Axis(values=list(lines), format=".0f", grid=False))
    base_ = alt.Chart(zones)
    bar = base_.mark_rect(stroke=PAPER, strokeWidth=2).encode(
        x=x, x2="to:Q", y=alt.value(40), y2=alt.value(100),
        color=alt.Color("words:N", scale=alt.Scale(domain=WORDS, range=LEVEL_COLORS), legend=None))
    mid = base_.transform_calculate(m="(datum.from + datum.to) / 2")
    words = mid.mark_text(fontSize=11, fontWeight="bold").encode(x="m:Q", y=alt.value(62), text="words:N",
                                                                 color=alt.Color("ink:N", scale=None))
    n_days = mid.mark_text(fontSize=11).encode(x="m:Q", y=alt.value(82), text="days:N", color=alt.Color("ink:N", scale=None))
    marks = pd.DataFrame({"t": [usual, that], "label": [f"average {d:%d %B}: {usual:.1f} °C", f"{d:%d %b %Y}: {that:.1f} °C"]})
    pin = alt.Chart(marks).mark_rule(color=INK, strokeWidth=2).encode(x="t:Q", y=alt.value(28), y2=alt.value(46))
    pin_text = alt.Chart(marks).mark_text(fontSize=11, color=INK, dy=-2, baseline="bottom").encode(
        x="t:Q", y=alt.value(28), text="label:N")
    return alt.layer(bar, words, n_days, pin, pin_text).properties(
        width=600, height=110, title=alt.Title("The Bengaluru heat gauge, the same every day of the year",
                                               subtitle=f"The numbers: how many of the {len(past):,} days of {base[0]}–{base[1]} fell in each zone"))
