"""
pages/emergency.py — Emergency mode: cleanest data of the three modes
(validated Gold table, no open design questions on the metric itself),
so this page is built first to validate the whole plumbing.

Shows: current-status indicator, wave_height_max time series with the
2.0m / 3.0m threshold lines drawn in, secondary wind/pressure charts, and
a map of all 15 locations color-coded by current classification.
"""

import dash
from dash import html, dcc, callback, Input, Output
import plotly.graph_objects as go

from data_access import get_emergency_data, LOCATIONS, LOCATION_COORDS

dash.register_page(__name__, path="/", name="Emergency")

CLASSIFICATION_COLORS = {
    "Safe": "#2ecc71",
    "Caution": "#f39c12",
    "Dangerous": "#e74c3c",
}

# Coordinates now come from data_access.LOCATION_COORDS, which is derived
# from pipeline/fetch_data.py's LOCATIONS (single source of truth). Do not
# redefine coordinates here — that duplication is exactly what caused the
# LOCATIONS/TOURISM_ONLY drift bug data_access.py's docstring warns about.

layout = html.Div(
    [
        html.H2("Emergency Mode"),
        html.Div(id="emergency-status-indicator", style={"marginBottom": "1.5rem"}),
        dcc.Graph(id="emergency-wave-timeseries"),
        dcc.Graph(id="emergency-wind-pressure"),
        html.H3("All Locations — Current Classification"),
        dcc.Graph(id="emergency-map"),
    ]
)


@callback(
    Output("emergency-status-indicator", "children"),
    Output("emergency-wave-timeseries", "figure"),
    Output("emergency-wind-pressure", "figure"),
    Input("selected-location", "data"),
)
def update_emergency_page(location):
    df = get_emergency_data(location)

    if df.empty:
        empty_fig = go.Figure()
        return (
            html.Div(f"No data available for {location}.", style={"color": "red"}),
            empty_fig,
            empty_fig,
        )

    latest = df.iloc[-1]
    status = latest.get("classification", "Unknown")
    color = CLASSIFICATION_COLORS.get(status, "#999")

    indicator = html.Div(
        [
            html.Span(
                status,
                style={
                    "backgroundColor": color,
                    "color": "white",
                    "padding": "0.5rem 1rem",
                    "borderRadius": "4px",
                    "fontWeight": "bold",
                    "fontSize": "1.2rem",
                },
            ),
            html.Span(
                f"  {location} — as of {latest['date'].date()}",
                style={"marginLeft": "1rem"},
            ),
        ]
    )

    # Wave height with threshold lines. Thresholds are reconstructed from
    # DMC advisory language, not an official published table — say so if
    # this chart appears in the report.
    wave_fig = go.Figure()
    wave_fig.add_trace(
        go.Scatter(
            x=df["date"], y=df["wave_height_max"],
            mode="lines", name="Daily max wave height (m)",
        )
    )
    wave_fig.add_hline(y=2.0, line_dash="dash", line_color="orange",
                        annotation_text="Caution (2.0m)")
    wave_fig.add_hline(y=3.0, line_dash="dash", line_color="red",
                        annotation_text="Dangerous (3.0m)")
    wave_fig.update_layout(title="Daily Max Wave Height", yaxis_title="meters")

    wind_pressure_fig = go.Figure()
    wind_pressure_fig.add_trace(
        go.Scatter(x=df["date"], y=df["wind_speed_max"], name="Wind speed max (km/h)")
    )
    if "pressure_min" in df.columns:
        wind_pressure_fig.add_trace(
            go.Scatter(
                x=df["date"], y=df["pressure_min"],
                name="Pressure min (hPa)", yaxis="y2",
            )
        )
        wind_pressure_fig.update_layout(
            yaxis2=dict(overlaying="y", side="right", title="hPa")
        )
    wind_pressure_fig.update_layout(title="Wind & Pressure", yaxis_title="km/h")

    return indicator, wave_fig, wind_pressure_fig


@callback(
    Output("emergency-map", "figure"),
    Input("selected-location", "data"),  # trigger refresh; map itself shows all 15
)
def update_emergency_map(_location):
    all_data = get_emergency_data(location=None)
    if all_data.empty:
        return go.Figure()

    latest_per_loc = (
        all_data.sort_values("date").groupby("location_name").tail(1)
    )

    lats, lons, colors, texts = [], [], [], []
    for _, row in latest_per_loc.iterrows():
        coords = LOCATION_COORDS.get(row["location_name"])
        if not coords:
            continue
        lats.append(coords[0])
        lons.append(coords[1])
        status = row.get("classification", "Unknown")
        colors.append(CLASSIFICATION_COLORS.get(status, "#999"))
        texts.append(f"{row['location_name']}: {status}")

    fig = go.Figure(
        go.Scattermapbox(
            lat=lats, lon=lons, mode="markers",
            marker=dict(size=14, color=colors),
            text=texts, hoverinfo="text",
        )
    )
    fig.update_layout(
        mapbox=dict(style="open-street-map", center=dict(lat=7.5, lon=80.7), zoom=6),
        margin=dict(l=0, r=0, t=0, b=0),
    )
    return fig