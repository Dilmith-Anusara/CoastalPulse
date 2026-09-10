"""
pages/fisherman.py — Fisherman mode. CURRENTLY BLOCKED, not silently skipped.

SARIMA model (Phase 4) isn't built yet and the Forecasts table doesn't
exist. Per the handoff's parallel-track recommendation: this page's
layout/shell is built now against mocked 48h data (get_fisherman_forecast
in data_access.py) so the dashboard structure is complete and demoable,
and modeling work can happen in parallel with a teammate.

TO REPLACE THE MOCK: once the Forecasts table exists, swap
`get_fisherman_forecast()` in data_access.py for a real query, and remove
the "MOCK DATA" banner below. Nothing in this page's layout should need to
change — that's the point of centralizing the query in data_access.py.
"""

import dash
from dash import html, dcc, callback, Input, Output
import plotly.graph_objects as go

from data_access import get_fisherman_forecast, get_fisherman_silver

dash.register_page(__name__, path="/fisherman", name="Fisherman")

layout = html.Div(
    [
        html.H2("Fisherman Mode"),
        html.Div(
            "\u26a0\ufe0f MOCK DATA \u2014 SARIMA model and the Forecasts table "
            "are not built yet. Everything below is placeholder data shaped "
            "like the eventual real forecast, for layout purposes only.",
            style={
                "backgroundColor": "#fdecea", "padding": "0.75rem 1rem",
                "borderLeft": "4px solid #e74c3c", "marginBottom": "1.5rem",
                "fontWeight": "bold",
            },
        ),
        dcc.Graph(id="fisherman-forecast"),
        html.H3("Recent Observed Conditions (real data)"),
        dcc.Graph(id="fisherman-recent-observed"),
    ]
)


@callback(
    Output("fisherman-forecast", "figure"),
    Output("fisherman-recent-observed", "figure"),
    Input("selected-location", "data"),
)
def update_fisherman_page(location):
    forecast_df = get_fisherman_forecast(location)
    observed_df = get_fisherman_silver(location, days_back=7)

    forecast_fig = go.Figure()
    if not forecast_df.empty:
        forecast_fig.add_trace(
            go.Scatter(
                x=forecast_df["forecast_time"],
                y=forecast_df["wave_height_forecast"],
                mode="lines+markers",
                name="Forecast wave height (m) \u2014 MOCK",
                line=dict(dash="dot"),
            )
        )
    forecast_fig.update_layout(
        title=f"48h Wave Height Forecast \u2014 {location} (MOCK DATA)",
        yaxis_title="meters",
    )

    observed_fig = go.Figure()
    if not observed_df.empty:
        observed_fig.add_trace(
            go.Scatter(x=observed_df["timestamp"], y=observed_df["wave_height"], name="Observed wave height (m)")
        )
        observed_fig.add_trace(
            go.Scatter(x=observed_df["timestamp"], y=observed_df["wind_speed"], name="Observed wind speed (km/h)", yaxis="y2")
        )
    observed_fig.update_layout(
        title=f"Last 7 Days Observed \u2014 {location} (real silver_hourly data)",
        yaxis_title="meters",
        yaxis2=dict(overlaying="y", side="right"),
    )

    return forecast_fig, observed_fig