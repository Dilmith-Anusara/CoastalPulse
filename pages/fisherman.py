"""
pages/fisherman.py — Fisherman mode.

UPDATED: forecast source switched from our own per-location SARIMA fit to
Open-Meteo's live Marine/Forecast API (get_marine_forecast(), reading the
`marine_forecasts` table written by pipeline/fetch_marine_forecast.py) — a
real physics-based operational forecast (ECMWF WAM, NOAA GFS Wave,
MeteoFrance MFWAM, DWD EWAM/GWAM, blended by Open-Meteo), up to 8 days
ahead instead of SARIMA's 48h, and aware of approaching weather systems
SARIMA's pure autoregression on one location's own past wave heights never
was. SARIMA didn't stop being useful — it moved to the Analytics page as a
forecasting case study (the actual modeling-skill demonstration), see
pipeline/build_forecasts.py's docstring.

Unlike SARIMA's output, Open-Meteo's forecast doesn't carry a confidence
interval or a backtest_rmse we measured ourselves — this page attributes
the source honestly instead of implying an error margin we don't have.

If the pipeline hasn't been run yet for the selected location (or ever),
get_marine_forecast() returns an empty DataFrame — this page says so
explicitly rather than showing an empty chart with no explanation.

LAYOUT — now matches Emergency/Tourism's structure exactly, which this
page originally skipped:
  - a HERO_STYLE navy gradient card (verdict sentence + wave gauge), a
    7-day classification strip, and the current-conditions snapshot sit
    in the always-visible cp-verdict-zone;
  - both charts sit in cp-detail-zone, hidden until the header's global
    "Show details" switch is on — previously this page ignored that
    switch entirely.
This also answers "is the forecast alone enough info for a fisherman" —
it wasn't. Beyond the two charts, this page now also gives:
  - a go/no-go verdict based on the latest *observed* wave height (not
    the forecast — the most recent real reading is the more honest
    answer to "right now"), using the same Safe/Caution/Dangerous
    thresholds pipeline/build_gold.py's classify_wave_height() uses for
    Emergency, rendered through the same gauge/hero visual language;
  - a 7-day classification strip and a "how does today compare to
    history" sentence, reusing get_emergency_data() (gold_emergency_daily)
    — the exact same Gold table and thresholds Emergency already shows,
    so a fisherman sees the identical verdict Emergency would give for
    this location, just framed for going out on a boat instead of
    swimming;
  - a current-conditions snapshot (wind, swell, sea temp) from the
    latest silver_hourly row;
  - the calmest/roughest hour in the 48h SARIMA forecast, so the chart
    doesn't have to be read by eye.
None of this needed new pipeline work — everything above already existed
in gold_emergency_daily, silver_hourly, or the forecasts table.
"""

import dash
from dash import html, dcc, callback, Input, Output
import plotly.graph_objects as go
import pandas as pd

from data_access import get_marine_forecast, get_fisherman_silver, get_emergency_data
from design_system import (
    PAGE_STYLE, TEXT, MUTED, CARD_STYLE, HERO_STYLE,
    VERDICT_ZONE_CLASS, DETAIL_ZONE_CLASS,
    ACCENT_BLUE, ACCENT_PURPLE, ACCENT_ORANGE, ACCENT_GREEN, ACCENT_TEAL,
    section_title, metric_card, chart_card, day_pill, day_strip_grid,
    empty_chart, stat_gauge_figure,
)
from page_helpers import CLASSIFICATION_COLORS

dash.register_page(__name__, path="/fisherman", name="Fisherman")

# Same thresholds as pipeline/build_gold.py's classify_wave_height() (the
# source of truth for Emergency's classification column) — duplicated here
# rather than imported since it's a small pipeline-side function, not a
# shared module; keep these in sync if that function's bands ever change.
# Also matches pages/emergency.py's own local WAVE_SAFE_MAX/WAVE_CAUTION_MAX
# — same duplication pattern already established there.
WAVE_SAFE_MAX = 2.0
WAVE_CAUTION_MAX = 3.0
WAVE_GAUGE_MAX = 5.0

HISTORY_MIN_ROWS = 30

# Locations where wave height doesn't reliably reflect wind conditions —
# from validation_scripts/eda_weather_indicators.ipynb Section 9.4 (real
# same-hour wind_speed vs wave_height correlation, computed across all 15
# locations' full hourly history): these three sit at r=0.35-0.40, the
# loosest relationships in the dataset, vs. ~0.61 average and ~0.65-0.88
# everywhere else. A fisherman here can face meaningful wind even when the
# wave-height verdict above reads calm, since there's no wind forecast
# model (see Section 9's feasibility finding — technically buildable, but
# not built, since wind is ~9x noisier hour-to-hour than wave height).
LOW_WIND_WAVE_CORRELATION_LOCATIONS = {"Trincomalee", "Batticaloa", "Arugam Bay"}

# Fishing-specific phrasing — Emergency's copy is written for "is it safe
# to swim/be near the coast", not "should a boat go out", so this page
# uses its own sentences against the same classification labels and
# colors (CLASSIFICATION_COLORS, shared via page_helpers.py).
_FISHERMAN_VERDICT_TEXT = {
    "Safe": "Good conditions to head out.",
    "Caution": "Rough seas today — experienced crews only, and stay within sight of shore.",
    "Dangerous": "Not safe to go out — stay in port until conditions ease.",
    None: "Not enough recent data for this location to advise.",
}

_COMPASS_POINTS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def _classify_wave(value):
    if value is None or pd.isna(value):
        return None
    if value < WAVE_SAFE_MAX:
        return "Safe"
    if value <= WAVE_CAUTION_MAX:
        return "Caution"
    return "Dangerous"


def _classification_style(classification):
    color = CLASSIFICATION_COLORS.get(classification, "#71828C")
    return color, f"{color}22"


def _hex_to_rgba(hex_color, alpha=0.55):
    hex_color = (hex_color or "#71828C").lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _compass(degrees):
    """16-point compass label for a wind/swell/wave direction in degrees,
    since a raw '214°' means little to most readers but 'SW' does.
    """
    if degrees is None or pd.isna(degrees):
        return None
    idx = int((float(degrees) / 22.5) + 0.5) % 16
    return _COMPASS_POINTS[idx]


def _wave_gauge_figure(wave_value, status_color):
    """Same visual construction as emergency.py's wave gauge (via the
    shared stat_gauge_figure helper both pages can use), same Safe/
    Caution/Dangerous bands — a fisherman and a swimmer read the same
    wave-height gauge, just under different verdict copy.
    """
    steps = [
        {"range": [0, WAVE_SAFE_MAX], "color": _hex_to_rgba(CLASSIFICATION_COLORS.get("Safe"))},
        {"range": [WAVE_SAFE_MAX, WAVE_CAUTION_MAX], "color": _hex_to_rgba(CLASSIFICATION_COLORS.get("Caution"))},
        {"range": [WAVE_CAUTION_MAX, WAVE_GAUGE_MAX], "color": _hex_to_rgba(CLASSIFICATION_COLORS.get("Dangerous"))},
    ]
    return stat_gauge_figure(wave_value, WAVE_GAUGE_MAX, status_color, steps, suffix=" m")


def _history_context_text(history_wave_series, current_wave, location_label):
    """Mirrors emergency.py's history_context_text — same full-history
    percentile comparison, so a fisherman gets the same "how unusual is
    this" context Emergency already gives, not a plainer version.
    """
    if current_wave is None or pd.isna(current_wave):
        return ""
    valid = history_wave_series.dropna()
    if len(valid) < HISTORY_MIN_ROWS:
        return ""
    percentile = (valid <= current_wave).mean() * 100
    if percentile >= 95:
        return f"Among the roughest days recorded at {location_label} — higher than {percentile:.0f}% of days on record."
    if percentile >= 70:
        return f"Higher than {percentile:.0f}% of days recorded at {location_label}."
    if percentile <= 30:
        return f"Calmer than usual — lower than {100 - percentile:.0f}% of days recorded at {location_label}."
    return f"Fairly typical for {location_label} — around the middle of the range recorded here."


def _hero_left(classification, wave_value, observed_time, history_note):
    color, _ = _classification_style(classification)
    verdict_text = _FISHERMAN_VERDICT_TEXT.get(classification, _FISHERMAN_VERDICT_TEXT[None])
    time_text = (
        "Latest reading: " + observed_time.strftime("%d %b, %H:%M")
        if observed_time is not None and pd.notna(observed_time)
        else ""
    )

    return html.Div(
        [
            html.Div(
                "CURRENT FISHING CONDITIONS",
                style={
                    "fontSize": "10px", "fontWeight": "750", "letterSpacing": "1.4px",
                    "color": "#8EA6B0", "marginBottom": "20px",
                },
            ),
            html.Div(
                html.Span(
                    (classification or "UNKNOWN").upper(),
                    style={
                        "fontSize": "11px", "fontWeight": "800", "letterSpacing": "0.6px",
                        "backgroundColor": f"{color}22", "color": color,
                        "padding": "7px 12px", "borderRadius": "20px",
                    },
                ),
            ),
            html.Div(
                verdict_text,
                style={
                    "fontSize": "18px", "fontWeight": "600", "lineHeight": "1.7",
                    "color": "white", "marginTop": "18px", "maxWidth": "480px",
                },
            ),
            html.Div(history_note, style={"fontSize": "13px", "lineHeight": "1.6", "color": "#B8C9CF", "marginTop": "10px", "maxWidth": "480px"}) if history_note else None,
            html.Div(time_text, style={"fontSize": "11px", "color": "#718991", "marginTop": "22px"}) if time_text else None,
        ],
        style={"flex": "1"},
    )


def _day_strip(daily_df):
    """Last-7-days classification strip, reusing gold_emergency_daily via
    get_emergency_data — the exact same source and thresholds Emergency
    shows, so this page never invents a second definition of Safe/
    Caution/Dangerous history.
    """
    if daily_df is None or daily_df.empty:
        return []
    recent = daily_df.tail(7)
    pills = []
    for _, row in recent.iterrows():
        classification = str(row.get("classification", "Unknown"))
        dot_color, bg_color = _classification_style(classification)
        date_val = row.get("date")
        if pd.notna(date_val):
            day_label, date_label = date_val.strftime("%a"), date_val.strftime("%d %b")
        else:
            day_label, date_label = "—", "—"
        pills.append(day_pill(day_label, date_label, dot_color, bg_color, classification))
    return pills


def _conditions_grid(latest_row):
    """Current-conditions snapshot from the latest silver_hourly row —
    the practical numbers for handling a boat and finding fish, not just
    'is it safe'. sea_surface_temp is null by design at the 5
    TOURISM_ONLY locations (no marine_ocean fetch there) — shown as
    unavailable rather than a blank/zero.
    """
    def get(col):
        val = latest_row.get(col) if latest_row is not None else None
        return val if val is not None and pd.notna(val) else None

    wind_speed, wind_gust, wind_dir = get("wind_speed"), get("wind_gust"), get("wind_direction")
    swell_h, swell_p, swell_dir = get("swell_height"), get("swell_period"), get("swell_direction")
    wave_p, wave_dir = get("wave_period"), get("wave_direction")
    sst = get("sea_surface_temp")

    wind_note = f"Gusting {wind_gust:.0f} km/h" if wind_gust is not None else None
    if wind_dir is not None:
        wind_note = f"{wind_note} · from {_compass(wind_dir)}" if wind_note else f"From {_compass(wind_dir)}"

    swell_note = f"{swell_p:.0f}s period" if swell_p is not None else None
    if swell_dir is not None:
        swell_note = f"{swell_note} · from {_compass(swell_dir)}" if swell_note else f"From {_compass(swell_dir)}"

    wave_note = f"From {_compass(wave_dir)}" if wave_dir is not None else None

    cards = [
        metric_card(
            "≋", "Wind",
            f"{wind_speed:.0f}" if wind_speed is not None else "—",
            "km/h", ACCENT_PURPLE, note=wind_note,
        ),
        metric_card(
            "≈", "Swell",
            f"{swell_h:.1f}" if swell_h is not None else "—",
            "m", ACCENT_BLUE, note=swell_note,
        ),
        metric_card(
            "≈", "Wave period",
            f"{wave_p:.0f}" if wave_p is not None else "—",
            "s", ACCENT_GREEN, note=wave_note,
        ),
        metric_card(
            "~", "Sea surface temp",
            f"{sst:.1f}" if sst is not None else "—",
            "°C" if sst is not None else "", ACCENT_ORANGE,
            note=None if sst is not None else "Not measured at this location",
        ),
    ]
    return html.Div(
        cards,
        style={
            "display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(180px, 1fr))",
            "gap": "18px",
        },
    )


def _wind_wave_note(location):
    """Shown only at the 3 locations where wave height and wind speed are
    only loosely linked (see LOW_WIND_WAVE_CORRELATION_LOCATIONS above) —
    a real, checked finding, not a caveat applied everywhere out of
    caution.
    """
    if location not in LOW_WIND_WAVE_CORRELATION_LOCATIONS:
        return None
    return _note_box(
        f"At {location}, wave height doesn't reliably reflect wind conditions "
        "(historically r≈0.35-0.40 here vs. ~0.61 Sri-Lanka-wide) — check the "
        "wind reading above even when the wave height alone looks calm.",
    )


def _window_note(forecast_df):
    """Calls out the calmest and roughest hour across the whole forecast
    horizon (now up to 8 days, from Open-Meteo — was 48h under SARIMA), so
    the chart above it doesn't have to be read by eye to answer 'when's
    the best time to go out'.
    """
    if forecast_df.empty:
        return None

    best = forecast_df.loc[forecast_df["wave_height"].idxmin()]
    worst = forecast_df.loc[forecast_df["wave_height"].idxmax()]
    days = max(1, round(len(forecast_df) / 24))

    def _stat(label, row, color):
        return html.Div(
            [
                html.Div(label, style={"fontSize": "11px", "fontWeight": "700", "color": color, "letterSpacing": "0.4px", "marginBottom": "6px"}),
                html.Div(
                    row["forecast_time"].strftime("%a %d %b, %I %p"),
                    style={"fontSize": "16px", "fontWeight": "750", "color": TEXT},
                ),
                html.Div(f"~{row['wave_height']:.1f} m", style={"fontSize": "12px", "color": MUTED, "marginTop": "2px"}),
            ],
            style={"flex": "1", "minWidth": "140px"},
        )

    return html.Div(
        [
            section_title(f"Next {days} days", "Calmest and roughest stretches in Open-Meteo's forecast for this location."),
            html.Div(
                [_stat("CALMEST", best, ACCENT_GREEN), _stat("ROUGHEST", worst, ACCENT_ORANGE)],
                style={"display": "flex", "gap": "24px", "flexWrap": "wrap"},
            ),
        ],
        style=CARD_STYLE,
    )


def _swell_breakdown_note():
    return _note_box(
        "Primary swell is usually the dominant driver of surfable wave energy; wind waves are locally "
        "wind-driven and choppier at short range; secondary swell (when the model resolves one) is a "
        "second wave train arriving from a different, more distant storm system. All three combine into "
        "the single wave-height number above.",
        color=ACCENT_TEAL, bg="#EAF7F5",
    )


def _note_box(text, color=ACCENT_ORANGE, bg="#FFF7E8"):
    return html.Div(
        text,
        style={
            "backgroundColor": bg, "padding": "12px 16px",
            "borderLeft": f"4px solid {color}", "borderRadius": "6px",
            "fontSize": "13px", "color": TEXT, "lineHeight": "1.6",
        },
    )


layout = html.Div(
    [
        html.Div(
            [
                html.Div(
                    [
                        html.Div(id="fisherman-hero"),
                        html.Div(
                            [
                                html.Div(
                                    "WAVE HEIGHT",
                                    style={
                                        "fontSize": "10px", "fontWeight": "700", "letterSpacing": "1px",
                                        "color": "#8EA6B0", "textAlign": "center", "marginBottom": "10px",
                                    },
                                ),
                                dcc.Graph(
                                    id="fisherman-gauge",
                                    config={"displayModeBar": False},
                                    style={"height": "190px", "width": "240px"},
                                ),
                            ],
                            style={"minWidth": "240px"},
                        ),
                    ],
                    style=HERO_STYLE,
                ),
                html.Div(
                    [
                        section_title("Last 7 days", "How wave conditions looked recently at this location — same data Emergency shows."),
                        html.Div(id="fisherman-day-strip", style={"display": "grid", "gridTemplateColumns": "repeat(7, minmax(0, 1fr))", "gap": "14px"}),
                    ],
                    style=CARD_STYLE,
                ),
                html.Div(style={"height": "8px"}),
                html.Div(id="fisherman-conditions-grid"),
                html.Div(id="fisherman-wind-wave-note", style={"marginTop": "16px"}),
            ],
            className=VERDICT_ZONE_CLASS,
        ),
        html.Div(style={"height": "8px"}),
        html.Div(
            [
                html.Div(id="fisherman-forecast-note", style={"marginBottom": "20px"}),
                chart_card(
                    "Wave height forecast",
                    "Open-Meteo's operational wave-model forecast for this location — not a model we fit ourselves.",
                    "fisherman-forecast", height=380,
                ),
                html.Div(style={"height": "20px"}),
                html.Div(id="fisherman-window-note"),
                html.Div(style={"height": "24px"}),
                chart_card(
                    "Swell & wind-wave breakdown",
                    "What's actually making up the wave-height number above — primary swell, secondary swell (when the model resolves one), and locally wind-driven waves.",
                    "fisherman-swell-breakdown", height=360,
                ),
                html.Div(style={"height": "12px"}),
                _swell_breakdown_note(),
                html.Div(style={"height": "24px"}),
                chart_card(
                    "Recent observed conditions",
                    "Real wave height and wind speed from the last 7 days (silver_hourly).",
                    "fisherman-recent-observed", height=360,
                ),
            ],
            className=DETAIL_ZONE_CLASS,
        ),
        html.Div(style={"height": "36px"}),
    ],
    style=PAGE_STYLE,
)


@callback(
    Output("fisherman-hero", "children"),
    Output("fisherman-gauge", "figure"),
    Output("fisherman-day-strip", "children"),
    Output("fisherman-conditions-grid", "children"),
    Output("fisherman-wind-wave-note", "children"),
    Output("fisherman-forecast-note", "children"),
    Output("fisherman-forecast", "figure"),
    Output("fisherman-window-note", "children"),
    Output("fisherman-swell-breakdown", "figure"),
    Output("fisherman-recent-observed", "figure"),
    Input("selected-location", "data"),
)
def update_fisherman_page(location):
    if not location:
        empty_hero = _hero_left(None, None, None, "")
        placeholder = _note_box("Choose a location above to see a forecast.")
        return empty_hero, _wave_gauge_figure(0, "#71828C"), [], None, None, placeholder, empty_chart(), None, empty_chart(), empty_chart()

    forecast_df = get_marine_forecast(location)
    observed_df = get_fisherman_silver(location, days_back=7)
    daily_df = get_emergency_data(location)

    # --------------------------------------------------------
    # Hero + gauge + conditions snapshot — from the latest real observed
    # row, not the forecast (the most recent actual reading is the more
    # honest answer to "right now" than a model output). The 7-day strip
    # and history sentence instead use gold_emergency_daily (daily max),
    # the same source Emergency itself reads from.
    # --------------------------------------------------------
    if not observed_df.empty:
        latest = observed_df.iloc[-1]
        wave_value = latest.get("wave_height")
        classification = _classify_wave(wave_value)
        history_note = (
            _history_context_text(daily_df["wave_height_max"], wave_value, location)
            if daily_df is not None and not daily_df.empty and "wave_height_max" in daily_df.columns
            else ""
        )
        hero = _hero_left(classification, wave_value, latest.get("timestamp"), history_note)
        gauge_fig = _wave_gauge_figure(wave_value, _classification_style(classification)[0])
        conditions_grid = _conditions_grid(latest)
    else:
        hero = _hero_left(None, None, None, "")
        gauge_fig = _wave_gauge_figure(0, "#71828C")
        conditions_grid = _conditions_grid(None)

    day_strip = _day_strip(daily_df)
    wind_wave_note = _wind_wave_note(location)
    window_note = _window_note(forecast_df)

    if forecast_df.empty:
        note = _note_box(
            f"No forecast available for {location} yet — the forecast pipeline "
            "(pipeline/fetch_marine_forecast.py) hasn't been run for this location. "
            "This is a data-availability gap, not a broken chart.",
        )
    else:
        generated = forecast_df["generated_at"].iloc[0]
        age = pd.Timestamp.now("UTC") - generated
        age_text = f"{int(age.total_seconds() / 3600)}h ago" if age.total_seconds() < 48 * 3600 else f"{int(age.total_seconds() / 86400)}d ago"
        note = _note_box(
            "Source: Open-Meteo Marine Weather Forecast — a blend of operational ocean/wave models "
            "(ECMWF WAM, NOAA GFS Wave, MeteoFrance MFWAM, DWD EWAM/GWAM), not a model we fit ourselves. "
            f"Forecast generated {age_text} — refreshed whenever the pipeline is re-run, not on every page load.",
            color=ACCENT_BLUE, bg="#EAF2FB",
        )

    if forecast_df.empty:
        forecast_fig = empty_chart("No forecast available for this location yet")
    else:
        forecast_fig = go.Figure()
        forecast_fig.add_trace(
            go.Scatter(
                x=forecast_df["forecast_time"], y=forecast_df["wave_height"],
                mode="lines", name="Forecast wave height (m)",
                line=dict(color=ACCENT_BLUE, width=3),
            )
        )
        forecast_fig.update_layout(
            margin=dict(l=50, r=20, t=10, b=45),
            yaxis_title="Wave height (m)",
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
        )

    if forecast_df.empty:
        swell_fig = empty_chart("No forecast available for this location yet")
    else:
        swell_fig = go.Figure()
        swell_fig.add_trace(
            go.Scatter(
                x=forecast_df["forecast_time"], y=forecast_df["swell_height"],
                mode="lines", name="Primary swell (m)",
                line=dict(color=ACCENT_BLUE, width=2.5),
            )
        )
        if forecast_df["secondary_swell_height"].notna().any():
            swell_fig.add_trace(
                go.Scatter(
                    x=forecast_df["forecast_time"], y=forecast_df["secondary_swell_height"],
                    mode="lines", name="Secondary swell (m)",
                    line=dict(color=ACCENT_PURPLE, width=2, dash="dot"),
                )
            )
        swell_fig.add_trace(
            go.Scatter(
                x=forecast_df["forecast_time"], y=forecast_df["wind_wave_height"],
                mode="lines", name="Wind waves (m)",
                line=dict(color=ACCENT_ORANGE, width=2),
            )
        )
        swell_fig.update_layout(
            margin=dict(l=50, r=20, t=10, b=45),
            yaxis_title="Height (m)",
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
        )

    observed_fig = go.Figure()
    if not observed_df.empty:
        observed_fig.add_trace(
            go.Scatter(x=observed_df["timestamp"], y=observed_df["wave_height"],
                       name="Observed wave height (m)", line=dict(color=ACCENT_BLUE, width=2))
        )
        observed_fig.add_trace(
            go.Scatter(x=observed_df["timestamp"], y=observed_df["wind_speed"],
                       name="Observed wind speed (km/h)", yaxis="y2", line=dict(color=ACCENT_PURPLE, width=2))
        )
        observed_fig.update_layout(
            margin=dict(l=50, r=60, t=10, b=45),
            yaxis=dict(title="Wave height (m)"),
            yaxis2=dict(title="Wind speed (km/h)", overlaying="y", side="right"),
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
        )
    else:
        observed_fig = empty_chart("No recent observed data for this location")

    return hero, gauge_fig, day_strip, conditions_grid, wind_wave_note, note, forecast_fig, window_note, swell_fig, observed_fig
