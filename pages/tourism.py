"""
pages/tourism.py — Tourism mode.

gold_tourism_daily columns: location_name, date, wave_height_mean,
wind_speed_mean, sea_surface_temp_mean, uv_index_mean, precipitation_sum,
suitability_score, daylight_hours_covered, humidity_mean,
apparent_temperature_mean, air_temperature_max, cloud_cover_mean,
dominant_weather_code, sunshine_hours_sum, us_aqi_mean

Same verdict/detail split as Emergency: plain sentence + gauge + 7-day
strip always visible; charts and cross-location map behind "Show details".

suitability_score is HCI:Beach (Gunathilake et al. 2023, adapting Scott/
Rutty et al.'s Holiday Climate Index: Beach to Sri Lankan beaches) — see
pipeline/build_gold.py's compute_suitability_score for the formula and
citation. Not an ad-hoc placeholder anymore, but still an approximation
of real tourist comfort, not a guarantee.
"""

import dash
from dash import html, dcc, callback, Input, Output
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from data_access import get_tourism_data, get_tourism_extras
from design_system import (
    CARD, TEXT, MUTED, BORDER, NAVY, NAVY_2,
    ACCENT_BLUE, ACCENT_ORANGE, ACCENT_TEAL, ACCENT_PINK, ACCENT_PURPLE, ACCENT_GREEN,
    PAGE_STYLE, HERO_STYLE, CARD_STYLE, VERDICT_ZONE_CLASS, DETAIL_ZONE_CLASS,
    section_title, metric_card, chart_card, day_pill, day_strip_grid,
    empty_chart, empty_map, stat_gauge_figure,
)

try:
    from data_access import TOURISM_ONLY
except ImportError:
    TOURISM_ONLY = ["Mirissa", "Hikkaduwa", "Unawatuna", "Bentota", "Arugam Bay"]

try:
    from data_access import LOCATION_COORDS
except ImportError:
    LOCATION_COORDS = {}

dash.register_page(__name__, path="/tourism", name="Tourism")

# Score bands (0-40 Not ideal, 40-60 Fair, 60-100 Good) — used for the
# gauge bands, the cross-location map, and as the fallback below. Matches
# page_helpers.SCORE_BANDS: collapses HCI:Beach's published 5-tier scale
# (Gunathilake et al. 2023) into 3 dashboard-facing bands. Kept in sync
# manually with page_helpers.py — if you change one, change both.
SCORE_FAIR_MIN = 40
SCORE_GOOD_MIN = 60
HISTORY_MIN_ROWS = 30
CHART_WINDOW_DAYS = 30

_FALLBACK_SCORE_BANDS = [
    (SCORE_GOOD_MIN, "Good beach day", ACCENT_TEAL),
    (SCORE_FAIR_MIN, "Fair — some conditions worth checking", ACCENT_ORANGE),
    (0, "Not ideal today", ACCENT_PINK),
]

try:
    from page_helpers import score_band as _page_helpers_score_band
except ImportError:
    _page_helpers_score_band = None


def score_band(score):
    if score is None or pd.isna(score):
        return "Conditions unknown", MUTED
    if _page_helpers_score_band is not None:
        try:
            result = _page_helpers_score_band(score)
            if isinstance(result, (tuple, list)) and len(result) >= 2:
                return result[0], result[1]
        except Exception:
            pass
    for threshold, label, color in _FALLBACK_SCORE_BANDS:
        if score >= threshold:
            return label, color
    return _FALLBACK_SCORE_BANDS[-1][1], _FALLBACK_SCORE_BANDS[-1][2]


def suitability_gauge_figure(score, band_color):
    steps = [
        {"range": [0, SCORE_FAIR_MIN], "color": "rgba(176,58,107,0.55)"},
        {"range": [SCORE_FAIR_MIN, SCORE_GOOD_MIN], "color": "rgba(245,158,11,0.55)"},
        {"range": [SCORE_GOOD_MIN, 100], "color": "rgba(30,138,138,0.55)"},
    ]
    return stat_gauge_figure(score, 100, band_color, steps, suffix="")


def suitability_context_text(history_score_series, current_score, location_label):
    """Mirrors emergency.py's history_context_text — spends the full
    ~1.5 years of history on one sentence instead of nothing. Higher
    suitability score is BETTER (opposite direction from wave height),
    so the wording is inverted accordingly.
    """
    if current_score is None or pd.isna(current_score):
        return ""
    valid = history_score_series.dropna()
    if len(valid) < HISTORY_MIN_ROWS:
        return ""
    percentile = (valid <= current_score).mean() * 100
    if percentile >= 95:
        return f"One of the best beach days recorded at {location_label} — better than {percentile:.0f}% of days on record."
    if percentile >= 70:
        return f"Better than {percentile:.0f}% of days recorded at {location_label}."
    if percentile <= 30:
        return f"One of the less ideal days for {location_label} — lower than {100 - percentile:.0f}% of days recorded here."
    return f"Fairly typical for {location_label} — around the middle of the range recorded here."


def _uv_band(uv):
    if uv is None or pd.isna(uv):
        return "—"
    if uv < 3:
        return "Low"
    if uv < 6:
        return "Moderate"
    if uv < 8:
        return "High"
    if uv < 11:
        return "Very High"
    return "Extreme"


def _wave_band(wave):
    if wave is None or pd.isna(wave):
        return "—"
    if wave < 0.5:
        return "Calm"
    if wave < 1.0:
        return "Gentle"
    if wave < 1.5:
        return "Choppy"
    return "Rough"


def _rain_band(precip):
    if precip is None or pd.isna(precip):
        return "—"
    if precip < 1:
        return "Dry"
    if precip < 5:
        return "Light rain"
    return "Rainy"


def _us_aqi_band(aqi):
    """Official US EPA AQI bands — aqi here is Open-Meteo's own us_aqi
    (a real computed index combining PM2.5/PM10/ozone/NO2/SO2/CO), not a
    PM2.5-only approximation like the old _aqi_band it replaced."""
    if aqi is None or pd.isna(aqi):
        return "—"
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 150:
        return "Unhealthy for sensitive groups"
    if aqi <= 200:
        return "Unhealthy"
    if aqi <= 300:
        return "Very unhealthy"
    return "Hazardous"


# WMO weather codes actually observed in this dataset (per the EDA
# notebook's frequency table) — not the full WMO code list, just the
# ones Sri Lankan coastal weather actually produces.
_WMO_LABELS = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    95: "Thunderstorm",
}


def _weather_label(code):
    if code is None or pd.isna(code):
        return "—"
    return _WMO_LABELS.get(int(code), "Mixed conditions")


def _map_hover_text(location_name, score):
    lines = [f"<b>{location_name}</b>"]
    if pd.notna(score):
        lines.append(f"Score: {score:.0f}/100")
    return "<br>".join(lines)


# ============================================================
# LAYOUT
# ============================================================

layout = html.Div(
    [
        html.Div(
            [
                html.Div(id="tourism-hero", style=HERO_STYLE),
                html.Div(id="tourism-best-pick", style={"marginBottom": "24px"}),
                html.Div(
                    [
                        section_title("Last 7 days", "How conditions looked recently at this location."),
                        html.Div(id="tourism-day-strip"),
                    ],
                    style=CARD_STYLE,
                ),
            ],
            className=VERDICT_ZONE_CLASS,
        ),

        html.Div(style={"height": "24px"}),

        html.Div(
            [
                html.Div(
                    "Suitability score is HCI:Beach, a published tourism-climate "
                    "index (Gunathilake et al. 2023) adapted for Sri Lankan "
                    "beaches — a research approximation of comfort, not an "
                    "authoritative guarantee.",
                    style={
                        "backgroundColor": "#fff8e1", "padding": "12px 16px",
                        "borderLeft": f"4px solid {ACCENT_ORANGE}", "borderRadius": "6px",
                        "marginBottom": "24px", "fontSize": "12px", "color": TEXT,
                    },
                ),

                html.Div(
                    [],
                    id="tourism-condition-chips",
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(auto-fit, minmax(180px, 1fr))",
                        "gap": "18px", "marginBottom": "24px",
                    },
                ),

                section_title(
                    "Surf detail",
                    "Swell and wave period — latest available hourly readings for today, computed the same daylight-hours-mean way as everything above.",
                ),
                html.Div(
                    [],
                    id="tourism-extra-chips",
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(auto-fit, minmax(180px, 1fr))",
                        "gap": "18px", "marginBottom": "24px",
                    },
                ),

                chart_card("Sea & wind — last 30 days", "Mean wave height and wind speed during daylight hours.",
                           "tourism-sea-wind-chart", height=360),
                html.Div(style={"height": "24px"}),

                chart_card("Sun & rainfall — last 30 days", "Mean UV index and total precipitation during daylight hours.",
                           "tourism-sun-rain-chart", height=360),
                html.Div(style={"height": "24px"}),

                chart_card("Sea surface temperature — last 30 days", "Mean sea temperature during daylight hours.",
                           "tourism-sst-chart", height=320),
                html.Div(id="tourism-sst-note"),
                html.Div(style={"height": "24px"}),

                html.Div(
                    [
                        section_title("Suitability map — all locations, latest day",
                                      "How every location compares right now."),
                        dcc.Graph(id="tourism-map", config={"displayModeBar": False, "responsive": True},
                                  style={"height": "480px"}),
                    ],
                    style=CARD_STYLE,
                ),
                html.Div(style={"height": "24px"}),

                chart_card("Ranked comparison — all locations, latest day",
                           "This location's suitability score against every other location today.",
                           "tourism-ranked-comparison", height=360),
            ],
            className=DETAIL_ZONE_CLASS,
        ),
    ],
    style=PAGE_STYLE,
)


# ============================================================
# MAIN CALLBACK
# ============================================================

@callback(
    Output("tourism-hero", "children"),
    Output("tourism-day-strip", "children"),
    Output("tourism-condition-chips", "children"),
    Output("tourism-extra-chips", "children"),
    Output("tourism-sea-wind-chart", "figure"),
    Output("tourism-sun-rain-chart", "figure"),
    Output("tourism-sst-chart", "figure"),
    Output("tourism-sst-note", "children"),
    Input("selected-location", "data"),
)
def update_tourism_page(location):

    if not location:
        return (
            html.Div("Choose a location to see beach conditions.", style={"color": "white", "fontSize": "16px"}),
            html.Div(), [], [], empty_chart(), empty_chart(), empty_chart(), html.Div(),
        )

    try:
        df = get_tourism_data(location)
    except Exception:
        return (
            html.Div(f"We couldn't load data for {location} right now.", style={"color": "white", "fontSize": "16px"}),
            html.Div(), [], [], empty_chart(), empty_chart(), empty_chart(), html.Div(),
        )

    if df is None or df.empty:
        return (
            html.Div(f"No data available for {location}.", style={"color": "white", "fontSize": "16px"}),
            html.Div(), [], [], empty_chart(), empty_chart(), empty_chart(), html.Div(),
        )

    data = df.copy()
    if "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
        data = data.sort_values("date")

    for col in [
        "wave_height_mean", "wind_speed_mean", "sea_surface_temp_mean", "uv_index_mean",
        "precipitation_sum", "suitability_score", "daylight_hours_covered",
        "humidity_mean", "apparent_temperature_mean", "air_temperature_max",
        "cloud_cover_mean", "dominant_weather_code", "sunshine_hours_sum", "us_aqi_mean",
    ]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    latest = data.iloc[-1]
    score = latest.get("suitability_score")
    band_label, band_color = score_band(score)
    score_text = f"{score:.0f}/100" if pd.notna(score) else "—"
    date_text = latest["date"].strftime("%d %b %Y") if pd.notna(latest.get("date")) else ""

    history_note = suitability_context_text(data["suitability_score"], score, location) if "suitability_score" in data.columns else ""
    gauge_fig = suitability_gauge_figure(score, band_color)

    # --- Hero (verdict zone) — same shape as Emergency's hero ---
    hero = html.Div(
        [
            html.Div(
                [
                    html.Div(
                        "CURRENT BEACH CONDITIONS",
                        style={"fontSize": "10px", "fontWeight": "750", "letterSpacing": "1.4px", "color": "#8EA6B0", "marginBottom": "20px"},
                    ),
                    html.Div(
                        [
                            html.Div(location, style={"fontSize": "24px", "fontWeight": "750", "color": "white"}),
                            html.Span(
                                score_text,
                                style={
                                    "marginLeft": "14px", "backgroundColor": band_color, "color": "white",
                                    "padding": "7px 12px", "borderRadius": "20px", "fontSize": "11px", "fontWeight": "800",
                                },
                            ),
                        ],
                        style={"display": "flex", "alignItems": "center", "flexWrap": "wrap", "rowGap": "10px"},
                    ),
                    html.Div(
                        band_label,
                        style={"fontSize": "18px", "fontWeight": "600", "lineHeight": "1.7", "color": "white", "marginTop": "18px", "maxWidth": "480px"},
                    ),
                    html.Div(
                        history_note,
                        style={"fontSize": "13px", "lineHeight": "1.6", "color": "#B8C9CF", "marginTop": "10px", "maxWidth": "480px"},
                    ),
                    html.Div(
                        f"Latest observation: {date_text}" if date_text else "Latest observation available",
                        style={"fontSize": "11px", "color": "#718991", "marginTop": "22px"},
                    ),
                ],
                style={"flex": "1"},
            ),
            html.Div(
                [
                    html.Div(
                        "SUITABILITY SCORE",
                        style={"fontSize": "10px", "fontWeight": "700", "letterSpacing": "1px", "color": "#8EA6B0", "textAlign": "center", "marginBottom": "10px"},
                    ),
                    dcc.Graph(figure=gauge_fig, config={"displayModeBar": False}, style={"height": "190px", "width": "240px"}),
                ],
                style={"minWidth": "240px"},
            ),
        ],
        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "gap": "40px", "width": "100%"},
    )

    # --- 7-day strip ---
    recent = data.tail(7)
    pills = []
    for _, row in recent.iterrows():
        _, row_color = score_band(row.get("suitability_score"))
        row_score = row.get("suitability_score")
        badge_text = f"{row_score:.0f}" if pd.notna(row_score) else "—"
        day_label = row["date"].strftime("%a") if pd.notna(row.get("date")) else "—"
        date_label = row["date"].strftime("%d %b") if pd.notna(row.get("date")) else "—"
        pills.append(day_pill(day_label, date_label, row_color, f"{row_color}22", badge_text))
    day_strip = day_strip_grid(pills)

    # --- Condition metric cards ---
    wave_label = _wave_band(latest.get("wave_height_mean"))
    uv_label = _uv_band(latest.get("uv_index_mean"))
    rain_label = _rain_band(latest.get("precipitation_sum"))
    sst = latest.get("sea_surface_temp_mean")
    sst_text = f"{sst:.1f}°C" if pd.notna(sst) else "N/A"

    wave_val = latest.get("wave_height_mean")
    wind_val = latest.get("wind_speed_mean")
    uv_val = latest.get("uv_index_mean")
    precip_val = latest.get("precipitation_sum")

    humidity_val = latest.get("humidity_mean")
    feels_like_val = latest.get("apparent_temperature_mean")
    sunshine_val = latest.get("sunshine_hours_sum")
    weather_text = _weather_label(latest.get("dominant_weather_code"))
    cloud_val = latest.get("cloud_cover_mean")
    weather_note = f"{cloud_val:.0f}% cloud cover" if pd.notna(cloud_val) else None
    aqi_val = latest.get("us_aqi_mean")

    chips = [
        metric_card("\u2601", "Weather", weather_text, "", accent=ACCENT_PURPLE, note=weather_note),
        metric_card("\U0001F321", "Feels like", f"{feels_like_val:.0f}" if pd.notna(feels_like_val) else "\u2014", "\u00b0C", accent=ACCENT_PINK),
        metric_card("\U0001F30A", "Wave height", f"{wave_val:.2f}" if pd.notna(wave_val) else "\u2014", "m", accent=ACCENT_BLUE, note=wave_label),
        metric_card("\U0001F4A8", "Wind speed", f"{wind_val:.1f}" if pd.notna(wind_val) else "\u2014", "km/h", accent=ACCENT_PURPLE),
        metric_card("\U0001F4A7", "Humidity", f"{humidity_val:.0f}" if pd.notna(humidity_val) else "\u2014", "%", accent=ACCENT_BLUE),
        metric_card("\u2600", "UV index", f"{uv_val:.1f}" if pd.notna(uv_val) else "\u2014", "", accent=ACCENT_ORANGE, note=uv_label),
        metric_card("\U0001F327", "Rainfall", f"{precip_val:.1f}" if pd.notna(precip_val) else "\u2014", "mm", accent=ACCENT_TEAL, note=rain_label),
        metric_card("\U0001F321", "Sea temp", sst_text, "", accent=ACCENT_PINK),
        metric_card("\u2600", "Sunshine", f"{sunshine_val:.1f}" if pd.notna(sunshine_val) else "\u2014", "hrs", accent=ACCENT_ORANGE),
        metric_card("\U0001F4A8", "Air quality", f"{aqi_val:.0f}" if pd.notna(aqi_val) else "\u2014", "AQI", accent=ACCENT_GREEN, note=_us_aqi_band(aqi_val)),
    ]

    # --- Surf detail — latest hourly snapshot from silver_hourly, not
    # part of gold_tourism_daily (swell/wave-period aren't Gold fields).
    # Degrades to an empty grid rather than crashing the page if the
    # extra query fails.
    try:
        extras = get_tourism_extras(location)
    except Exception:
        extras = {}

    swell_height_val = extras.get("swell_height_mean")
    swell_period_val = extras.get("swell_period_mean")
    wave_period_val = extras.get("wave_period_mean")

    extra_chips = [
        metric_card("\U0001F30A", "Swell height", f"{swell_height_val:.2f}" if pd.notna(swell_height_val) else "—", "m", accent=ACCENT_BLUE),
        metric_card("⏱", "Swell period", f"{swell_period_val:.1f}" if pd.notna(swell_period_val) else "—", "s", accent=ACCENT_PURPLE),
        metric_card("\U0001F30A", "Wave period", f"{wave_period_val:.1f}" if pd.notna(wave_period_val) else "—", "s", accent=ACCENT_TEAL),
    ] if extras else []

    # --- SST note — based on the latest row only ---
    if pd.isna(sst):
        if location in TOURISM_ONLY:
            sst_note = html.Div(
                f"Sea surface temperature isn't collected for {location} — this location doesn't fetch marine data. Not a data error.",
                style={"color": MUTED, "fontStyle": "italic", "fontSize": "12px", "marginTop": "10px"},
            )
        else:
            sst_note = html.Div(
                f"Sea surface temperature is temporarily unavailable for {location} (a gap in the source archive) — not a data error.",
                style={"color": MUTED, "fontStyle": "italic", "fontSize": "12px", "marginTop": "10px"},
            )
    else:
        sst_note = html.Div()

    # --- Charts, windowed to last 30 days ---
    chart_data = data.tail(CHART_WINDOW_DAYS)

    sea_wind_fig = go.Figure()
    sw_data = chart_data.dropna(subset=["date"])
    if "wave_height_mean" in sw_data.columns:
        sea_wind_fig.add_trace(go.Scatter(x=sw_data["date"], y=sw_data["wave_height_mean"], name="Wave height (m)",
                                           line=dict(color=ACCENT_BLUE, width=3), marker=dict(size=6, color=ACCENT_BLUE), mode="lines+markers"))
    if "wind_speed_mean" in sw_data.columns:
        sea_wind_fig.add_trace(go.Scatter(x=sw_data["date"], y=sw_data["wind_speed_mean"], name="Wind speed (km/h)", yaxis="y2",
                                           line=dict(color=ACCENT_PURPLE, width=3), marker=dict(size=6, color=ACCENT_PURPLE), mode="lines+markers"))
    sea_wind_fig.update_layout(
        paper_bgcolor=CARD, plot_bgcolor=CARD, margin=dict(l=50, r=60, t=15, b=45),
        font=dict(family="Inter, Arial", color=TEXT, size=11),
        xaxis=dict(showgrid=False, zeroline=False, showline=True, linecolor=BORDER, tickfont=dict(color=MUTED)),
        yaxis=dict(title="Wave height (m)", showgrid=True, gridcolor="#EDF1F3", title_font=dict(size=11, color=ACCENT_BLUE), tickfont=dict(color=MUTED)),
        yaxis2=dict(title="Wind speed (km/h)", overlaying="y", side="right", showgrid=False, title_font=dict(size=11, color=ACCENT_PURPLE), tickfont=dict(color=MUTED)),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1, font=dict(size=11, color=MUTED)),
        hoverlabel=dict(bgcolor=NAVY, font_color="white"),
    )

    sun_rain_fig = go.Figure()
    if "uv_index_mean" in sw_data.columns:
        sun_rain_fig.add_trace(go.Scatter(x=sw_data["date"], y=sw_data["uv_index_mean"], name="UV index",
                                           line=dict(color=ACCENT_ORANGE, width=3), marker=dict(size=6, color=ACCENT_ORANGE), mode="lines+markers"))
    if "precipitation_sum" in sw_data.columns:
        sun_rain_fig.add_trace(go.Bar(x=sw_data["date"], y=sw_data["precipitation_sum"], name="Precipitation (mm)", yaxis="y2",
                                       marker_color=ACCENT_TEAL, opacity=0.45))
    sun_rain_fig.update_layout(
        paper_bgcolor=CARD, plot_bgcolor=CARD, margin=dict(l=50, r=60, t=15, b=45),
        font=dict(family="Inter, Arial", color=TEXT, size=11),
        xaxis=dict(showgrid=False, zeroline=False, showline=True, linecolor=BORDER, tickfont=dict(color=MUTED)),
        yaxis=dict(title="UV index", showgrid=True, gridcolor="#EDF1F3", title_font=dict(size=11, color=ACCENT_ORANGE), tickfont=dict(color=MUTED)),
        yaxis2=dict(title="Precipitation (mm)", overlaying="y", side="right", showgrid=False, title_font=dict(size=11, color=ACCENT_TEAL), tickfont=dict(color=MUTED)),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1, font=dict(size=11, color=MUTED)),
        hoverlabel=dict(bgcolor=NAVY, font_color="white"),
    )

    sst_fig = go.Figure()
    sst_data = chart_data.dropna(subset=["date", "sea_surface_temp_mean"]) if "sea_surface_temp_mean" in chart_data.columns else pd.DataFrame()
    if not sst_data.empty:
        sst_fig.add_trace(go.Scatter(x=sst_data["date"], y=sst_data["sea_surface_temp_mean"], name="Sea temp (°C)",
                                      line=dict(color=ACCENT_PINK, width=3), marker=dict(size=6, color=ACCENT_PINK),
                                      mode="lines+markers", fill="tozeroy", fillcolor="rgba(176,58,107,0.08)"))
        sst_fig.update_layout(
            paper_bgcolor=CARD, plot_bgcolor=CARD, margin=dict(l=50, r=20, t=15, b=45),
            font=dict(family="Inter, Arial", color=TEXT, size=11),
            xaxis=dict(showgrid=False, zeroline=False, showline=True, linecolor=BORDER, tickfont=dict(color=MUTED)),
            yaxis=dict(title="Sea temp (°C)", showgrid=True, gridcolor="#EDF1F3", title_font=dict(size=11, color=MUTED), tickfont=dict(color=MUTED)),
            hoverlabel=dict(bgcolor=NAVY, font_color="white"),
        )
    else:
        sst_fig = empty_chart("No sea temperature data for this location")

    return hero, day_strip, chips, extra_chips, sea_wind_fig, sun_rain_fig, sst_fig, sst_note


# ============================================================
# CROSS-LOCATION CALLBACK — ranked bar + map, one shared fetch
# ============================================================

def _best_pick_note(latest, selected_location):
    """Always-visible planning aid: which of the 15 locations has the
    best conditions right now. Deliberately backward/present-looking
    only (today's Gold row), not a forecast claim — there's no
    Forecasts table for Tourism yet (that's Fisherman's blocked-on-
    SARIMA territory).
    """
    if latest.empty or "suitability_score" not in latest.columns:
        return html.Div()

    top = latest.iloc[0]
    top_name = top.get("location_name")
    top_score = top.get("suitability_score")
    if pd.isna(top_score):
        return html.Div()

    own_row = latest[latest["location_name"] == selected_location]
    own_score = own_row.iloc[0].get("suitability_score") if not own_row.empty else None

    if selected_location and top_name == selected_location:
        text = f"You're already at today's top-rated location for a beach day — {top_name} leads all 15 with a score of {top_score:.0f}/100."
    elif pd.notna(own_score):
        text = (
            f"Today's best pick across all 15 locations is {top_name} (score {top_score:.0f}/100). "
            f"{selected_location} scores {own_score:.0f}/100 today."
        )
    else:
        text = f"Today's best pick across all 15 locations is {top_name} (score {top_score:.0f}/100)."

    return html.Div(
        text,
        style={
            "backgroundColor": "#EAF7F5", "padding": "12px 16px",
            "borderLeft": f"4px solid {ACCENT_TEAL}", "borderRadius": "6px",
            "fontSize": "13px", "color": TEXT, "lineHeight": "1.6",
        },
    )


@callback(
    Output("tourism-ranked-comparison", "figure"),
    Output("tourism-map", "figure"),
    Output("tourism-best-pick", "children"),
    Input("selected-location", "data"),  # also compares ALL locations, not just this one
)
def update_cross_location_views(selected_location):
    try:
        all_data = get_tourism_data(location=None)
    except Exception:
        return empty_chart(), empty_map(), html.Div()

    if all_data is None or all_data.empty:
        return empty_chart(), empty_map(), html.Div()

    data = all_data.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["suitability_score"] = pd.to_numeric(data["suitability_score"], errors="coerce")

    latest_date = data["date"].max()
    latest = data[data["date"] == latest_date].sort_values("suitability_score", ascending=False)

    if latest.empty:
        return empty_chart(), empty_map(), html.Div()

    best_pick_note = _best_pick_note(latest, selected_location)

    bar_fig = px.bar(
        latest, x="location_name", y="suitability_score",
        labels={"location_name": "Location", "suitability_score": "Score"},
        color_discrete_sequence=[ACCENT_TEAL],
    )
    # Pick the current location out of the pack instead of leaving every
    # bar the same color — otherwise "how do we compare" takes a manual
    # scan of 15 x-axis labels.
    bar_colors = [ACCENT_TEAL if name == selected_location else "#CFE3E3" for name in latest["location_name"]]
    bar_fig.update_traces(marker_color=bar_colors)
    bar_fig.update_layout(
        paper_bgcolor=CARD, plot_bgcolor=CARD, margin=dict(l=45, r=20, t=10, b=60),
        font=dict(family="Inter, Arial", color=TEXT, size=11),
        yaxis=dict(title="Score (0-100)", range=[0, 100], gridcolor="#EDF1F3"),
        xaxis=dict(title=None, tickangle=-35),
    )

    map_fig = go.Figure()
    bands = [("Good", SCORE_GOOD_MIN, 100, ACCENT_TEAL), ("Fair", SCORE_FAIR_MIN, SCORE_GOOD_MIN, ACCENT_ORANGE), ("Not ideal", 0, SCORE_FAIR_MIN, ACCENT_PINK)]
    for label, lo, hi, color in bands:
        group = latest[(latest["suitability_score"] >= lo) & (latest["suitability_score"] < hi + (0.01 if hi == 100 else 0))]
        lats, lons, names, hover = [], [], [], []
        for _, row in group.iterrows():
            loc_name = row.get("location_name", "")
            coords = LOCATION_COORDS.get(loc_name)
            if coords is None:
                continue
            lat = coords.get("lat") if isinstance(coords, dict) else coords[0]
            lon = coords.get("lon") if isinstance(coords, dict) else coords[1]
            if lat is None or lon is None:
                continue
            lats.append(lat)
            lons.append(lon)
            names.append(loc_name)
            hover.append(_map_hover_text(loc_name, row.get("suitability_score")))
        if lats:
            map_fig.add_trace(go.Scattermap(lat=lats, lon=lons, mode="markers", name=label, text=names,
                                             hovertext=hover, hoverinfo="text", marker=dict(size=13, color=color, opacity=0.9)))

    if selected_location in LOCATION_COORDS:
        coords = LOCATION_COORDS[selected_location]
        lat = coords.get("lat") if isinstance(coords, dict) else coords[0]
        lon = coords.get("lon") if isinstance(coords, dict) else coords[1]
        if lat is not None and lon is not None:
            map_fig.add_trace(go.Scattermap(lat=[lat], lon=[lon], mode="markers", hoverinfo="skip",
                                             marker=dict(size=22, color="#102A36", opacity=0.22), showlegend=False))
            map_fig.add_trace(go.Scattermap(lat=[lat], lon=[lon], mode="markers", hoverinfo="skip",
                                             marker=dict(size=8, color="#102A36", opacity=1), showlegend=False))

    map_fig.update_layout(
        map=dict(style="open-street-map", center=dict(lat=7.5, lon=80.7), zoom=6),
        margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor=CARD,
        legend=dict(orientation="h", yanchor="bottom", y=0.02, xanchor="left", x=0.02,
                    bgcolor="rgba(255,255,255,0.92)", bordercolor=BORDER, borderwidth=1, font=dict(size=11, color=TEXT)),
    )

    return bar_fig, map_fig, best_pick_note