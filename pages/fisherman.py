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
"""

import dash
from dash import html, callback, Input, Output
import plotly.graph_objects as go
import pandas as pd

from data_access import get_fisherman_forecast, get_fisherman_silver
from design_system import PAGE_STYLE, TEXT, ACCENT_BLUE, ACCENT_PURPLE, ACCENT_ORANGE, chart_card, empty_chart

dash.register_page(__name__, path="/fisherman", name="Fisherman")

layout = html.Div(
    [
        html.Div(id="fisherman-forecast-note", style={"marginBottom": "20px"}),
        chart_card(
            "48-hour wave height forecast",
            "SARIMA model fit on this location's own hourly history — shaded band is the model's 95% prediction interval, not a guarantee.",
            "fisherman-forecast", height=380,
        ),
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
    Output("fisherman-forecast-note", "children"),
    Output("fisherman-forecast", "figure"),
    Output("fisherman-recent-observed", "figure"),
    Input("selected-location", "data"),
)
def update_fisherman_page(location):
    if not location:
        return _note_box("Choose a location above to see a forecast."), empty_chart(), empty_chart()

    forecast_df = get_fisherman_forecast(location)
    observed_df = get_fisherman_silver(location, days_back=7)

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

    return note, forecast_fig, observed_fig
