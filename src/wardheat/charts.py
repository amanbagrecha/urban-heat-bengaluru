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
LEVELS = ["Green", "Yellow", "Orange", "Red", "Magenta"]
LEVEL_COLORS = ["#e2ddcf", "#f2cf5b", "#e8893a", "#c8442d", "#7d2a5c"]
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
        if c != "geometry" and pd.api.types.is_float_dtype(g[c]):
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
def greens_explorer(px: pd.DataFrame):
    """Scatter of tree canopy vs daytime surface temperature, linked to the city map.

    Drag a box on the scatter: the matching cells light up on the map.
    """
    brush = alt.selection_interval(name="brush", encodings=["x", "y"], value={"x": [0.35, 1.0], "y": [30, 46]})
    data, names = _cells(px, {"canopy": "canopy", "lst": "lst_day", "cover": "cover"})
    base = alt.Chart(data).transform_lookup(lookup="w", from_=names)
    tips = [alt.Tooltip("ward:N", title="ward"), alt.Tooltip("canopy:Q", format=".0%", title="tree canopy"),
            alt.Tooltip("lst:Q", format=".1f", title="°C"), alt.Tooltip("cover:N", title="mostly")]
    scatter = (
        base.mark_circle(size=7)
        .encode(
            x=alt.X("canopy:Q", title="tree canopy cover", axis=alt.Axis(format="%")),
            y=alt.Y("lst:Q", title="surface temperature, 10:40 am (°C)", scale=alt.Scale(domain=[30, 46], clamp=True)),
            color=alt.when(brush).then(alt.Color("cover:N", scale=alt.Scale(domain=list(COVER), range=list(COVER.values())),
                                                 legend=alt.Legend(title=None))).otherwise(alt.value("#dcd6c8")),
            opacity=alt.value(0.55),
            tooltip=tips,
        )
        .add_params(brush)
        .properties(width=330, height=330, title=alt.Title("Each dot is a 240 m patch of the city", subtitle="Drag a box over any group of dots"))
    )
    trend = base.transform_regression("canopy", "lst").mark_line(color=INK, strokeWidth=1.5, strokeDash=[4, 3]).encode(x="canopy:Q", y="lst:Q")
    xy = _grid_xy(px, 2.6)
    city = (
        base.transform_calculate(c2="datum.c + 1.06", r2="datum.r + 1.06")
        .mark_rect()
        .encode(
            **xy["enc"],
            color=alt.when(brush).then(alt.Color("lst:Q", scale=alt.Scale(range=HEAT, domain=[34, 44], clamp=True),
                                                 legend=alt.Legend(title="°C", gradientLength=160, gradientThickness=8)))
            .otherwise(alt.value("#ebe7dd")),
            tooltip=tips,
        )
        .properties(**xy["size"], title=alt.Title("…and here they are", subtitle="Unselected patches fade to grey"))
    )
    return alt.hconcat(scatter + trend, city, spacing=24).resolve_scale(color="independent")


def day_night_by_cover(px: pd.DataFrame):
    """How much hotter or cooler than the city average each kind of place is, by day and by night."""
    rows = []
    for when, col in (("day (10:40 am)", "lst_day"), ("night (10:30 pm)", "lst_night")):
        mean = px[col].mean()
        d = px.groupby("cover")[col].mean().sub(mean).rename("diff").reset_index()
        d["when"] = when
        rows.append(d)
    df = pd.concat(rows)
    order = ["farmland", "built-up", "mixed", "trees", "water"]
    base = alt.Chart(df, title=alt.Title("Compared with the city average", subtitle="Farmland flips from hottest by day to cool at night; built-up stays warm"))
    rule = base.mark_rule(color=RULE).encode(y=alt.Y("cover:N", sort=order, title=None), x="min(diff):Q", x2="max(diff):Q")
    pts = base.mark_circle(size=110, opacity=1).encode(
        y=alt.Y("cover:N", sort=order, title=None),
        x=alt.X("diff:Q", title="°C warmer (+) or cooler (−) than the city average"),
        color=alt.Color("when:N", scale=alt.Scale(range=["#d9693b", "#3b4a7a"]), legend=alt.Legend(title=None)),
        tooltip=["cover:N", "when:N", alt.Tooltip("diff:Q", format="+.1f", title="°C vs city")],
    )
    zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=MUTED, strokeDash=[2, 2]).encode(x="x:Q")
    return (zero + rule + pts).properties(width=520, height=190)


# ---------------------------------------------------------------------------
# Lesson 3: who is at risk?
# ---------------------------------------------------------------------------
def ingredient_maps(g: gpd.GeoDataFrame, width: int = 215, height: int = 240):
    """Heat, crowding and lack of shade as three small ward maps; each is a rank among wards (0-1).

    ``g`` needs ``label``, ``H``, ``E``, ``V`` and the real values ``lst_built``, ``lst_night``,
    ``people_per_ha``, ``canopy_frac`` for the tooltips.
    """
    color = alt.Color("rank:Q", scale=alt.Scale(range=HEAT, domain=[0, 1]),
                      legend=alt.Legend(title="share of wards it beats", format=".0%", orient="bottom",
                                        gradientLength=300, gradientThickness=8))
    maps = []
    for col, title, beats, real in [
        ("H", "Heat", "hotter than", [alt.Tooltip("day_heat:Q", format=".1f", title="day °C"),
                                      alt.Tooltip("night_heat:Q", format=".1f", title="night °C")]),
        ("E", "Crowding", "more crowded than", [alt.Tooltip("people_per_ha:Q", format=",.0f", title="people / hectare")]),
        ("V", "Lack of shade", "less shaded than", [alt.Tooltip("trees:Q", format=".0%", title="tree cover")]),
    ]:
        maps.append(
            alt.Chart(g, title=alt.Title(title, subtitle=f"{beats} … of wards"))
            .transform_calculate(rank=f"datum.{col}")
            .mark_geoshape(stroke=PAPER, strokeWidth=0.3)
            .encode(color=color, tooltip=[alt.Tooltip("label:N", title="ward"),
                                          alt.Tooltip("rank:Q", format=".0%", title=f"{beats} … of wards"), *real])
            .project("mercator")
            .properties(width=width, height=height)
        )
    return alt.hconcat(*maps, spacing=10)


def risk_explorer(g: gpd.GeoDataFrame):
    """Weighted geometric mean of H, E, V computed in the browser; sliders change the weights.

    ``g`` needs columns ``label``, ``H``, ``E``, ``V`` (0-1) and any tooltip columns.
    """
    wH = alt.param(name="wH", value=1, bind=alt.binding_range(min=0, max=3, step=0.5, name="Heat "))
    wE = alt.param(name="wE", value=1, bind=alt.binding_range(min=0, max=3, step=0.5, name="People "))
    wV = alt.param(name="wV", value=1, bind=alt.binding_range(min=0, max=3, step=0.5, name="Lack of shade "))
    hl = alt.selection_point(name="hl", fields=["label"], on="pointerover", clear="pointerout", empty=False)
    score = "exp((wH * log(datum.H) + wE * log(datum.E) + wV * log(datum.V)) / max(wH + wE + wV, 0.001)) * 100"
    base = (
        alt.Chart(g)
        .add_params(wH, wE, wV)
        .transform_calculate(score=score)
        .transform_window(rank="percent_rank()", sort=[alt.SortField("score", order="ascending")])
        .transform_calculate(risk="datum.rank >= 0.7 ? 'High' : datum.rank >= 0.4 ? 'Medium' : 'Low'")
    )
    risk_color = alt.Color("risk:N", scale=alt.Scale(domain=list(RISK), range=list(RISK.values())), legend=alt.Legend(title=None))
    extra = {"day_heat": (".1f", "day °C"), "night_heat": (".1f", "night °C"),
             "people_per_ha": (",.0f", "people / hectare"), "trees": (".0%", "tree cover")}
    tips = [alt.Tooltip("label:N", title="ward"), alt.Tooltip("risk:N")]
    tips += [alt.Tooltip(f"{c}:Q", format=f, title=t) for c, (f, t) in extra.items() if c in g.columns]
    city = (
        base.mark_geoshape()
        .encode(color=risk_color, tooltip=tips,
                stroke=alt.when(hl).then(alt.value(INK)).otherwise(alt.value(PAPER)),
                strokeWidth=alt.when(hl).then(alt.value(1.5)).otherwise(alt.value(0.4)))
        .add_params(hl)
        .project("mercator")
        .properties(width=390, height=410, title=alt.Title("Heat risk by ward", subtitle="Top 30 % of wards = High"))
    )
    top = (
        base.transform_window(n="row_number()", sort=[alt.SortField("score", order="descending")])
        .transform_filter("datum.n <= 20")
        .mark_bar(height=11)
        .encode(
            x=alt.X("score:Q", title="risk score", scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(values=[0, 50, 100])),
            y=alt.Y("label:N", sort="-x", title=None, axis=alt.Axis(labelLimit=170, labelFontSize=10)),
            color=alt.when(hl).then(alt.value(INK)).otherwise(alt.value(RISK["High"])),
            tooltip=tips,
        )
        .add_params(hl)
        .properties(width=130, height=380, title=alt.Title("20 highest", subtitle=" "))
    )
    return alt.hconcat(city, top, spacing=10)


# ---------------------------------------------------------------------------
# Lesson 4: when should we warn?
# ---------------------------------------------------------------------------
def heat_calendar(hr: pd.DataFrame, first_year: int = 2024):
    """Every March-May day since 1991 coloured by HeatRisk level; click a year to see its temperatures.

    ``hr`` is the output of ``warning.heatrisk`` (index = date).
    """
    d = hr[hr.index.month.isin([3, 4, 5])].rename_axis("date").reset_index()
    d["year"] = d["date"].dt.year
    d["day"] = (d["date"] - pd.to_datetime(d["year"].astype(str) + "-03-01")).dt.days
    d["date_s"] = d["date"].dt.strftime("%d %b %Y")
    d = d[["date_s", "year", "day", "level", "name", "tmax", "tmin", "tmax_p95", "tmin_p95", "tmax_normal"]].round(1)
    year = alt.selection_point(name="year_pick", fields=["year"], value=[{"year": first_year}], on="click", clear=False)
    ticks = "datum.value == 0 ? '1 Mar' : datum.value == 31 ? '1 Apr' : datum.value == 61 ? '1 May' : ''"
    level_color = alt.Color("name:N", scale=alt.Scale(domain=LEVELS, range=LEVEL_COLORS), legend=alt.Legend(title="HeatRisk"))
    cal = (
        alt.Chart(d, title=alt.Title("36 hot seasons, one row each", subtitle="Click a year to see it below"))
        .mark_rect(stroke=PAPER, strokeWidth=0.3)
        .encode(
            x=alt.X("day:O", title=None, axis=alt.Axis(values=[0, 31, 61], labelExpr=ticks, labelAngle=0, domain=False, ticks=False)),
            y=alt.Y("year:O", title=None, sort="descending", axis=alt.Axis(values=list(range(1991, 2027, 5)) + [2024])),
            color=level_color,
            opacity=alt.when(year).then(alt.value(1)).otherwise(alt.value(0.55)),
            tooltip=[alt.Tooltip("date_s:N", title="date"), alt.Tooltip("name:N", title="HeatRisk"),
                     alt.Tooltip("tmax:Q", title="max °C"), alt.Tooltip("tmin:Q", title="min °C")],
        )
        .add_params(year)
        .properties(width=560, height=330)
    )
    sel = alt.Chart(d).transform_filter(year)
    x = alt.X("day:Q", title=None, scale=alt.Scale(domain=[0, 91], nice=False),
              axis=alt.Axis(values=[0, 31, 61], labelExpr=ticks, grid=False))
    y = alt.Y("tmax:Q", title="°C", scale=alt.Scale(domain=[15, 40]))
    tmax = sel.mark_line(color="#b03a2e", strokeWidth=1.8).encode(x=x, y=y)
    tmin = sel.mark_line(color="#3b4a7a", strokeWidth=1.8).encode(x=x, y="tmin:Q")
    p95x = sel.mark_line(color="#b03a2e", strokeDash=[3, 3], strokeWidth=1).encode(x=x, y="tmax_p95:Q")
    p95n = sel.mark_line(color="#3b4a7a", strokeDash=[3, 3], strokeWidth=1).encode(x=x, y="tmin_p95:Q")
    strip = sel.mark_rect().encode(
        x=x, x2="day2:Q", y=alt.value(326), y2=alt.value(336), color=alt.Color("name:N", scale=alt.Scale(domain=LEVELS, range=LEVEL_COLORS), legend=None),
        tooltip=[alt.Tooltip("date_s:N", title="date"), alt.Tooltip("name:N", title="HeatRisk"), "tmax:Q", "tmin:Q"],
    ).transform_calculate(day2="datum.day + 1")
    label = sel.transform_aggregate(year="max(year)").mark_text(align="left", fontSize=13, fontWeight=600, dx=4, dy=4).encode(
        x=alt.value(0), y=alt.value(0), text="year:O")
    detail = (tmax + tmin + p95x + p95n + strip + label).properties(
        width=560, height=340,
        title=alt.Title("Daily max (red) and night min (blue)", subtitle="Dashed: the local 95th percentile for that date. Strip: the HeatRisk level"),
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
WORLDCOVER = {10: ("trees", "#3f7d3a"), 20: ("shrubs", "#8fa957"), 30: ("grass", "#c4d48a"), 40: ("crops", "#e3c35b"),
              50: ("buildings & roads", "#b23a2e"), 60: ("bare ground", "#cdb89a"), 80: ("water", "#4a7fb0"),
              90: ("wetland", "#6aa3a0")}

SATELLITE_SEES_HEAT = """
<svg viewBox="0 0 660 230" width="100%" style="max-width:660px; font: 12px var(--sans, sans-serif)" role="img"
     aria-label="Warm surfaces give off thermal infrared light; the satellite measures it">
  <rect x="270" y="8" width="120" height="30" rx="4" fill="#1d1b16"/><rect x="236" y="17" width="34" height="12" fill="#6b665c"/>
  <rect x="390" y="17" width="34" height="12" fill="#6b665c"/>
  <text x="330" y="28" fill="#faf8f3" text-anchor="middle">Landsat</text>
  <text x="440" y="27" fill="#6b665c">700 km up: a camera for heat glow</text>
  <circle cx="40" cy="40" r="18" fill="#f2cf5b"/><text x="40" y="74" fill="#6b665c" text-anchor="middle">sun</text>
  <path d="M60 52 L120 150" stroke="#f2cf5b" stroke-width="2" stroke-dasharray="4 4"/>
  <g fill="none" stroke-linecap="round">
    <path d="M110 150 q-6 -12 0 -24 q6 -12 0 -24 q-6 -12 0 -24 q6 -12 0 -24 q-6 -12 0 -24" stroke="#b23a2e" stroke-width="5"/>
    <path d="M330 150 q-6 -12 0 -24 q6 -12 0 -24 q-6 -12 0 -24 q6 -12 0 -24" stroke="#e8893a" stroke-width="3"/>
    <path d="M550 150 q-6 -12 0 -24 q6 -12 0 -24 q-6 -12 0 -24" stroke="#f2cf5b" stroke-width="1.5"/>
  </g>
  <rect x="40" y="155" width="140" height="22" fill="#3a3632"/><text x="110" y="198" text-anchor="middle" fill="#1d1b16">tar road</text>
  <text x="110" y="214" text-anchor="middle" fill="#b23a2e" font-weight="600">≈ 50 °C, glows most</text>
  <circle cx="300" cy="145" r="16" fill="#3f7d3a"/><circle cx="330" cy="140" r="20" fill="#3f7d3a"/><circle cx="360" cy="146" r="15" fill="#3f7d3a"/>
  <rect x="270" y="160" width="120" height="17" fill="#5f8a4f"/><text x="330" y="198" text-anchor="middle" fill="#1d1b16">trees</text>
  <text x="330" y="214" text-anchor="middle" fill="#e8893a" font-weight="600">≈ 35 °C</text>
  <rect x="480" y="158" width="140" height="19" rx="9" fill="#4a7fb0"/><text x="550" y="198" text-anchor="middle" fill="#1d1b16">lake</text>
  <text x="550" y="214" text-anchor="middle" fill="#b0902a" font-weight="600">≈ 28 °C, glows least</text>
</svg>
"""


def built_rule(wc: np.ndarray, start: float = 5 / 9):
    """A real 600 m patch of WorldCover (10 m cells) with our 30 m squares on top; a slider sets how
    built-up a square must be to count. ``wc`` is a block of class codes whose sides are multiples of 3."""
    h, w = wc.shape
    rr, cc = np.mgrid[0:h, 0:w]
    cells = pd.DataFrame({"x": cc.ravel(), "y": rr.ravel(), "code": wc.ravel().astype(int)})
    cells["cover"] = cells.code.map(lambda k: WORLDCOVER.get(k, ("other", "#ccc"))[0])
    cells[["x2", "y2"]] = cells[["x", "y"]] + 1
    sq = cells.assign(sx=cells.x // 3, sy=cells.y // 3, b=(cells.code == 50)).groupby(["sx", "sy"])["b"].sum().reset_index()
    sq = sq.assign(x=sq.sx * 3, x2=sq.sx * 3 + 3, y=sq.sy * 3, y2=sq.sy * 3 + 3, built=sq.b)
    t = alt.param(name="t", value=round(start * 9),
                  bind=alt.binding_range(min=0, max=9, step=1, name="keep a square if this many of its 9 cells are built: "))
    present = [k for k in WORLDCOVER if k in set(cells.code)]
    x = alt.X("x:Q", scale=alt.Scale(domain=[0, w], nice=False), axis=None)
    y = alt.Y("y:Q", scale=alt.Scale(domain=[h, 0], nice=False), axis=None)
    ground = alt.Chart(cells).mark_rect().encode(
        x=x, x2="x2:Q", y=y, y2="y2:Q",
        color=alt.Color("cover:N", scale=alt.Scale(domain=[WORLDCOVER[k][0] for k in present], range=[WORLDCOVER[k][1] for k in present]),
                        legend=alt.Legend(title="WorldCover, 10 m cells", orient="bottom", columns=4, direction="horizontal")),
        tooltip=[alt.Tooltip("cover:N", title="this 10 m cell")])
    squares = alt.Chart(sq).add_params(t).mark_rect(stroke=PAPER, strokeWidth=1).encode(
        x=x, x2="x2:Q", y=y, y2="y2:Q",
        fill=alt.value(PAPER),
        fillOpacity=alt.when("datum.built < t").then(alt.value(0.7)).otherwise(alt.value(0)),
        tooltip=[alt.Tooltip("built:Q", title="built cells (of 9)")])
    kept = alt.Chart(sq).transform_filter("datum.built >= t").transform_aggregate(n="count()").transform_calculate(
        label=f"'kept: ' + datum.n + ' of {len(sq)} squares of 30 m'").mark_text(align="left", dx=2, dy=-8, fontSize=12, color=INK).encode(
        x=alt.value(0), y=alt.value(0), text="label:N")
    return alt.layer(ground, squares, kept).properties(
        width=380, height=380, title=alt.Title("A real 600 m patch of east Bengaluru", subtitle="Faded 30 m squares are left out"))


def levels_explainer(era5: pd.DataFrame, normal: pd.DataFrame, day: str = "2024-04-28"):
    """The warning levels for one date as a coloured scale in °C, with how many days in 100 fall in each."""
    d = pd.Timestamp(day)
    doy = d.dayofyear
    cuts = [max(normal.loc[doy, f"tmax_p{p}"], normal[f"tmax_ann_p{p}"].iloc[0]) for p in ("90", "95", "98", "99_5")]
    usual = float(normal.loc[doy, "tmax_p50"])
    that = float(era5.loc[day, "tmax"])
    lo, hi = np.floor(usual - 2), np.ceil(max(that, cuts[-1]) + 1)
    zones = pd.DataFrame({
        "from": [lo, *cuts], "to": [*cuts, hi],
        "words": ["normal", "warm", "hot", "very hot", "extreme"],
        "share": ["90", "5", "3", "1.5", "0.5"],
        "ink": [INK, INK, INK, PAPER, PAPER],
    })
    x = alt.X("from:Q", scale=alt.Scale(domain=[lo, hi], nice=False), title=f"daily high around {d:%d %B}, °C",
              axis=alt.Axis(values=[round(c, 1) for c in cuts], format=".1f", grid=False))
    base = alt.Chart(zones)
    bar = base.mark_rect(stroke=PAPER, strokeWidth=2).encode(
        x=x, x2="to:Q", y=alt.value(40), y2=alt.value(100),
        color=alt.Color("words:N", scale=alt.Scale(domain=list(zones.words), range=LEVEL_COLORS), legend=None))
    mid = base.transform_calculate(m="(datum.from + datum.to) / 2")
    words = mid.mark_text(fontSize=11, fontWeight="bold").encode(x="m:Q", y=alt.value(62), text="words:N",
                                                                 color=alt.Color("ink:N", scale=None))
    share = mid.mark_text(fontSize=11).encode(x="m:Q", y=alt.value(82), text="share:N", color=alt.Color("ink:N", scale=None))
    marks = pd.DataFrame({"t": [usual, that], "label": [f"a usual day: {usual:.1f} °C", f"{d:%d %b %Y}: {that:.1f} °C"]})
    pin = alt.Chart(marks).mark_rule(color=INK, strokeWidth=2).encode(x="t:Q", y=alt.value(28), y2=alt.value(100))
    pin_text = alt.Chart(marks).mark_text(fontSize=11, color=INK, dy=-2, baseline="bottom").encode(
        x="t:Q", y=alt.value(28), text="label:N")
    return alt.layer(bar, words, share, pin, pin_text).properties(
        width=600, height=110, title=alt.Title(f"How hot is too hot around {d:%d %B}?",
                                               subtitle="The numbers: how many of every 100 days around this date (1991–2020) reached each zone"))
