"""
pages/fisherman.py — Fisherman mode.

Real forecast, no longer mocked: get_fisherman_forecast() (data_access.py)
now reads the `forecasts` table written by pipeline/build_forecasts.py — a
SARIMA model fit per location directly on silver_hourly's wave_height
series. See that script's docstring for the model order, why it isn't fit
inside this app, and the per-location backtest_rmse this page displays.

If the pipeline hasn't been run yet for the selected location (or ever),
get_fisherman_forecast() returns an empty DataFrame — this page says so
explicitly rather than showing an empty chart with no explanation.

Beyond the two charts, this page also answers the questions a fisherman
actually has, all derived from data already being fetched here (no new
pipeline work):
  - a go/no-go verdict based on the latest *observed* wave height (not the
    forecast — the most recent real reading is the more honest answer to
    "right now"), using the same Safe/Caution/Dangerous thresholds
    pipeline/build_gold.py's classify_wave_height() uses for Emergency;
  - a current-conditions snapshot (wind, swell, sea temp) from that same
    latest silver_hourly row;
  - the calmest/roughest hour in the 48h SARIMA forecast, so the chart
    doesn't have to be read by eye.
"""

import dash
from dash import html, callback, Input, Output
import plotly.graph_objects as go
import pandas as pd

from data_access import get_fisherman_forecast, get_fisherman_silver
from design_system import (
    PAGE_STYLE, TEXT, MUTED, CARD, BORDER, CARD_STYLE,
    ACCENT_BLUE, ACCENT_PURPLE, ACCENT_ORANGE, ACCENT_GREEN,
    section_title, metric_card, chart_card, empty_chart,
)
from page_helpers import CLASSIFICATION_COLORS

dash.register_page(__name__, path="/fisherman", name="Fisherman")

# Same thresholds as pipeline/build_gold.py's classify_wave_height() (the
# source of truth for Emergency's classification column) — duplicated here
# rather than imported since it's a small pipeline-side function, not a
# shared module; keep these in sync if that function's bands ever change.
WAVE_SAFE_MAX = 2.0
WAVE_CAUTION_MAX = 3.0

# Fishing-specific phrasing — Emergency's EMERGENCY_VERDICT_TEXT is written
# for "is it safe to swim/be near the coast", not "should a boat go out",
# so this page uses its own copy against the same classification labels
# and colors (CLASSIFICATION_COLORS, shared via page_helpers.py).
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


def _compass(degrees):
    """16-point compass label for a wind/swell/wave direction in degrees,
    since a raw '214°' means little to most readers but 'SW' does.
    """
    if degrees is None or pd.isna(degrees):
        return None
    idx = int((float(degrees) / 22.5) + 0.5) % 16
    return _COMPASS_POINTS[idx]


def _verdict_card(classification, wave_value, observed_time):
    color, light = _classification_style(classification)
    verdict_text = _FISHERMAN_VERDICT_TEXT.get(classification, _FISHERMAN_VERDICT_TEXT[None])
    wave_text = f"{wave_value:.2f} m" if wave_value is not None and pd.notna(wave_value) else "—"
    time_text = (
        "Latest reading: " + observed_time.strftime("%d %b, %H:%M")
        if observed_time is not None and pd.notna(observed_time)
        else ""
    )

    return html.Div(
        [
            html.Div(
                [
                    html.Span(
                        (classification or "UNKNOWN").upper(),
                        style={
                            "fontSize": "11px", "fontWeight": "800", "letterSpacing": "0.6px",
                            "backgroundColor": light, "color": color,
                            "padding": "6px 12px", "borderRadius": "20px",
                        },
                    ),
                    html.Span(
                        f"Wave height right now: {wave_text}",
                        style={"fontSize": "13px", "color": MUTED, "marginLeft": "14px"},
                    ),
                ],
                style={
                    "display": "flex", "alignItems": "center", "flexWrap": "wrap",
                    "rowGap": "8px", "marginBottom": "12px",
                },
            ),
            html.Div(verdict_text, style={"fontSize": "17px", "fontWeight": "650", "color": TEXT, "lineHeight": "1.6"}),
            html.Div(time_text, style={"fontSize": "11px", "color": MUTED, "marginTop": "10px"}) if time_text else None,
        ],
        style={
            "backgroundColor": CARD, "border": f"2px solid {color}", "borderRadius": "16px",
            "padding": "26px 28px", "boxShadow": "0 2px 8px rgba(15, 45, 58, 0.035)",
        },
    )


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

    wave_note = f"{wave_p:.0f}s period" if wave_p is not None else None
    if wave_dir is not None:
        wave_note = f"{wave_note} · from {_compass(wave_dir)}" if wave_note else f"From {_compass(wave_dir)}"

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
            "~", "Sea surface temp",
            f"{sst:.1f}" if sst is not None else "—",
            "°C" if sst is not None else "", ACCENT_ORANGE,
            note=wave_note if sst is not None else "Not measured at this location",
        ),
    ]
    return html.Div(
        cards,
        style={
            "display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(180px, 1fr))",
            "gap": "18px",
        },
    )


def _window_note(forecast_df):
    """Calls out the calmest and roughest hour in the 48h forecast, so
    the chart above it doesn't have to be read by eye to answer 'when's
    the best time to go out in the next couple of days'.
    """
    if forecast_df.empty:
        return None

    best = forecast_df.loc[forecast_df["wave_height_forecast"].idxmin()]
    worst = forecast_df.loc[forecast_df["wave_height_forecast"].idxmax()]

    def _stat(label, row, color):
        return html.Div(
            [
                html.Div(label, style={"fontSize": "11px", "fontWeight": "700", "color": color, "letterSpacing": "0.4px", "marginBottom": "6px"}),
                html.Div(
                    row["forecast_time"].strftime("%a %I %p"),
                    style={"fontSize": "16px", "fontWeight": "750", "color": TEXT},
                ),
                html.Div(f"~{row['wave_height_forecast']:.1f} m", style={"fontSize": "12px", "color": MUTED, "marginTop": "2px"}),
            ],
            style={"flex": "1", "minWidth": "140px"},
        )

    return html.Div(
        [
            section_title("Next 48 hours", "Calmest and roughest stretches in the forecast, from the same SARIMA model."),
            html.Div(
                [_stat("CALMEST", best, ACCENT_GREEN), _stat("ROUGHEST", worst, ACCENT_ORANGE)],
                style={"display": "flex", "gap": "24px", "flexWrap": "wrap"},
            ),
        ],
        style=CARD_STYLE,
    )


layout = html.Div(
    [
        html.Div(id="fisherman-verdict-card", style={"marginBottom": "20px"}),
        html.Div(id="fisherman-conditions-grid", style={"marginBottom": "24px"}),
        html.Div(id="fisherman-forecast-note", style={"marginBottom": "20px"}),
        chart_card(
            "48-hour wave height forecast",
            "SARIMA model fit on this location's own hourly history — shaded band is the model's 95% prediction interval, not a guarantee.",
            "fisherman-forecast", height=380,
        ),
        html.Div(style={"height": "20px"}),
        html.Div(id="fisherman-window-note"),
        html.Div(style={"height": "24px"}),
        chart_card(
            "Recent observed conditions",
            "Real wave height and wind speed from the last 7 days (silver_hourly).",
            "fisherman-recent-observed", height=360,
        ),
    ],
    style=PAGE_STYLE,
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


@callback(
    Output("fisherman-verdict-card", "children"),
    Output("fisherman-conditions-grid", "children"),
    Output("fisherman-forecast-note", "children"),
    Output("fisherman-forecast", "figure"),
    Output("fisherman-window-note", "children"),
    Output("fisherman-recent-observed", "figure"),
    Input("selected-location", "data"),
)
def update_fisherman_page(location):
    if not location:
        placeholder = _note_box("Choose a location above to see a forecast.")
        return None, None, placeholder, empty_chart(), None, empty_chart()

    forecast_df = get_fisherman_forecast(location)
    observed_df = get_fisherman_silver(location, days_back=7)

    # --------------------------------------------------------
    # Verdict + current-conditions snapshot — from the latest real
    # observed row, not the forecast (the most recent actual reading
    # is the more honest answer to "right now" than a model output).
    # --------------------------------------------------------
    if not observed_df.empty:
        latest = observed_df.iloc[-1]
        classification = _classify_wave(latest.get("wave_height"))
        verdict_card = _verdict_card(classification, latest.get("wave_height"), latest.get("timestamp"))
        conditions_grid = _conditions_grid(latest)
    else:
        verdict_card = _verdict_card(None, None, None)
        conditions_grid = _conditions_grid(None)

    window_note = _window_note(forecast_df)

    if forecast_df.empty:
        note = _note_box(
            f"No forecast available for {location} yet — the forecasting pipeline "
            "(pipeline/build_forecasts.py) hasn't been run for this location, or it "
            "didn't have enough history to fit a model. This is a data-availability "
            "gap, not a broken chart.",
        )
    else:
        rmse = forecast_df["backtest_rmse"].iloc[0]
        generated = forecast_df["generated_at"].iloc[0]
        age = pd.Timestamp.now("UTC") - generated
        age_text = f"{int(age.total_seconds() / 3600)}h ago" if age.total_seconds() < 48 * 3600 else f"{int(age.total_seconds() / 86400)}d ago"
        rmse_text = (
            f"Typical model error on recent held-out data: ±{rmse:.2f} m. "
            if pd.notna(rmse) else ""
        )
        note = _note_box(
            f"{rmse_text}Forecast generated {age_text} — refreshed whenever the forecasting "
            "pipeline is re-run, not on every page load.",
            color=ACCENT_BLUE, bg="#EAF2FB",
        )

    if forecast_df.empty:
        forecast_fig = empty_chart("No forecast available for this location yet")
    else:
        forecast_fig = go.Figure()
        forecast_fig.add_trace(
            go.Scatter(
                x=pd.concat([forecast_df["forecast_time"], forecast_df["forecast_time"][::-1]]),
                y=pd.concat([forecast_df["ci_high"], forecast_df["ci_low"][::-1]]),
                fill="toself", fillcolor="rgba(59,110,140,0.15)",
                line=dict(color="rgba(0,0,0,0)"), hoverinfo="skip",
                name="95% interval", showlegend=True,
            )
        )
        forecast_fig.add_trace(
            go.Scatter(
                x=forecast_df["forecast_time"], y=forecast_df["wave_height_forecast"],
                mode="lines+markers", name="Forecast wave height (m)",
                line=dict(color=ACCENT_BLUE, width=3), marker=dict(size=5, color=ACCENT_BLUE),
            )
        )
        forecast_fig.update_layout(
            margin=dict(l=50, r=20, t=10, b=45),
            yaxis_title="Wave height (m)",
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

    return verdict_card, conditions_grid, note, forecast_fig, window_note, observed_fig
