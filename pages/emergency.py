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

from data_access import get_emergency_data, LOCATIONS

dash.register_page(__name__, path="/", name="Emergency")

CLASSIFICATION_COLORS = {
    "Safe": "#2ecc71",
    "Caution": "#f39c12",
    "Dangerous": "#e74c3c",
}

# Approximate coordinates for the map view. Fill these in from
# fetch_data.py's real LOCATIONS metadata if it stores lat/lon —
# these are placeholders only, replace before relying on the map.
LOCATION_COORDS = {
    "Mirissa": (5.9483, 80.4589), "Hikkaduwa": (6.1400, 80.1000),
    "Unawatuna": (6.0100, 80.2500), "Bentota": (6.4260, 79.9950),
    "Arugam Bay": (6.8400, 81.8360), "Negombo": (7.2080, 79.8380),
    "Galle": (6.0328, 80.2170), "Trincomalee": (8.5870, 81.2150),
    "Chilaw": (7.5750, 79.7950), "Colombo": (6.9271, 79.8612),
    "Tangalle": (6.0240, 80.7930), "Batticaloa": (7.7170, 81.7000),
    "Jaffna": (9.6650, 80.0080), "Matara": (5.9480, 80.5350),
    "Puttalam": (8.0360, 79.8280),
}

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
    if "atmospheric_pressure_max" in df.columns:
        wind_pressure_fig.add_trace(
            go.Scatter(
                x=df["date"], y=df["atmospheric_pressure_max"],
                name="Pressure max (hPa)", yaxis="y2",
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