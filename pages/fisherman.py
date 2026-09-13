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
from design_system import PAGE_STYLE, CARD_STYLE, TEXT, MUTED, CORAL, note_box, section_title

dash.register_page(__name__, path="/fisherman", name="Fisherman")

layout = html.Div(
    [
        note_box(
            "MOCK DATA \u2014 the SARIMA forecasting model and the Forecasts table "
            "are not built yet. Everything below the observed-conditions chart "
            "is placeholder data shaped like the eventual real forecast, for "
            "layout purposes only.",
            tone="alert",
        ),
        html.Div(style={"height": "24px"}),
        html.Div(
            [
                section_title("48-hour wave height forecast", "Not real \u2014 see the notice above."),
                dcc.Graph(id="fisherman-forecast", config={"displayModeBar": False}),
            ],
            style=CARD_STYLE,
        ),
        html.Div(style={"height": "24px"}),
        html.Div(
            [
                section_title("Recent observed conditions", "Real data from the last 7 days."),
                dcc.Graph(id="fisherman-recent-observed", config={"displayModeBar": False}),
            ],
            style=CARD_STYLE,
        ),
    ],
    style=PAGE_STYLE,
)


@callback(
    Output("fisherman-forecast", "figure"),
    Output("fisherman-recent-observed", "figure"),
    Input("selected-location", "data"),
)
def update_fisherman_page(location):
    forecast_df = get_fisherman_forecast(location)
    observed_df = get_fisherman_silver(location, days_back=7)

    chart_layout = dict(
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        font=dict(family="Public Sans, Arial", color=TEXT, size=11),
        margin=dict(l=50, r=50, t=15, b=45),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1, font=dict(size=11, color=MUTED)),
    )

    forecast_fig = go.Figure()
    if not forecast_df.empty:
        forecast_fig.add_trace(
            go.Scatter(
                x=forecast_df["forecast_time"],
                y=forecast_df["wave_height_forecast"],
                mode="lines+markers",
                name="Forecast wave height (m) \u2014 MOCK",
                line=dict(dash="dot", color=CORAL),
            )
        )
    forecast_fig.update_layout(**chart_layout, yaxis=dict(title="Wave height (m)", gridcolor="#EDE6D3"))

    observed_fig = go.Figure()
    if not observed_df.empty:
        observed_fig.add_trace(
            go.Scatter(x=observed_df["timestamp"], y=observed_df["wave_height"], name="Observed wave height (m)")
        )
        observed_fig.add_trace(
            go.Scatter(x=observed_df["timestamp"], y=observed_df["wind_speed"], name="Observed wind speed (km/h)", yaxis="y2")
        )
    observed_fig.update_layout(
        **chart_layout,
        yaxis=dict(title="Wave height (m)", gridcolor="#EDE6D3"),
        yaxis2=dict(title="Wind speed (km/h)", overlaying="y", side="right"),
    )

    return forecast_fig, observed_fig