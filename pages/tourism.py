"""
pages/tourism.py — Tourism mode.

Reuses Emergency's page pattern. Key differences per the handoff plan:
- Daylight-hours MEAN framing (06:00-18:00), NOT daily max — this is made
  visually explicit so it isn't misread as a worst-case number.
- Suitability score is flagged in the UI as a first-draft placeholder
  formula, not an authoritative metric.
- Cross-location ranked comparison view — more useful here than for
  Emergency, since Tourism is inherently about choosing WHERE to go.
- sea_surface_temp gaps for the 5 TOURISM_ONLY locations get an explicit
  explanatory note, never a blank panel.
"""

import dash
from dash import html, dcc, callback, Input, Output
import plotly.graph_objects as go
import plotly.express as px

from data_access import get_tourism_data

dash.register_page(__name__, path="/tourism", name="Tourism")

layout = html.Div(
    [
        html.H2("Tourism Mode"),
        html.P(
            "All metrics below are DAYLIGHT-HOURS (06:00\u201318:00) AVERAGES, "
            "not daily maximums \u2014 this view is about comfort/suitability, "
            "not worst-case risk.",
            style={"fontStyle": "italic", "color": "#555"},
        ),
        html.Div(
            "Suitability score is a first-draft placeholder formula, not a "
            "validated or authoritative metric \u2014 treat it as a rough guide.",
            style={
                "backgroundColor": "#fff8e1", "padding": "0.5rem 1rem",
                "borderLeft": "4px solid #f39c12", "marginBottom": "1rem",
            },
        ),
        dcc.Graph(id="tourism-suitability-timeseries"),
        html.Div(id="tourism-sst-note"),
        dcc.Graph(id="tourism-conditions"),
        html.H3("Ranked Comparison \u2014 All Locations, Latest Day"),
        dcc.Graph(id="tourism-ranked-comparison"),
    ]
)


@callback(
    Output("tourism-suitability-timeseries", "figure"),
    Output("tourism-sst-note", "children"),
    Output("tourism-conditions", "figure"),
    Input("selected-location", "data"),
)
def update_tourism_page(location):
    df = get_tourism_data(location)
    if df.empty:
        empty_fig = go.Figure()
        return empty_fig, html.Div(f"No data available for {location}."), empty_fig

    suit_fig = go.Figure()
    suit_fig.add_trace(
        go.Scatter(x=df["date"], y=df["suitability_score"], mode="lines", name="Suitability score")
    )
    suit_fig.update_layout(title="Suitability Score (0-100, first-draft formula)",
                            yaxis_title="score", yaxis_range=[0, 100])

    is_tourism_only = df["is_tourism_only"].iloc[0] if "is_tourism_only" in df.columns else False
    if is_tourism_only or df["sea_surface_temp_mean"].isna().any():
        sst_note = html.Div(
            f"Sea surface temperature isn't available for {location} "
            "(no marine data fetched for this location, or a temporary gap "
            "in the source archive) \u2014 not a data error.",
            style={"color": "#888", "fontStyle": "italic", "marginBottom": "1rem"},
        )
    else:
        sst_note = html.Div()

    conditions_fig = go.Figure()
    conditions_fig.add_trace(go.Scatter(x=df["date"], y=df["wave_height_mean"], name="Wave height (m)"))
    conditions_fig.add_trace(go.Scatter(x=df["date"], y=df["wind_speed_mean"], name="Wind speed (km/h)", yaxis="y2"))
    has_sst = "sea_surface_temp_mean" in df.columns and not df["sea_surface_temp_mean"].isna().all()
    if has_sst:
        conditions_fig.add_trace(
            go.Scatter(x=df["date"], y=df["sea_surface_temp_mean"], name="Sea surface temp (\u00b0C)", yaxis="y3")
        )
    conditions_fig.update_layout(
        title="Daylight-Hours Mean Conditions",
        yaxis=dict(title="meters", domain=[0, 0.86] if has_sst else [0, 1]),
        # wind speed (km/h) and sea surface temp (\u00b0C) are different units,
        # so each gets its own axis rather than sharing one secondary axis —
        # overlaying them together made the chart unreadable.
        yaxis2=dict(title="km/h", overlaying="y", side="right"),
        yaxis3=dict(
            title="\u00b0C", overlaying="y", side="right",
            anchor="free", position=1.0, showgrid=False,
        ) if has_sst else {},
        margin=dict(r=80) if has_sst else {},
    )

    return suit_fig, sst_note, conditions_fig


@callback(
    Output("tourism-ranked-comparison", "figure"),
    Input("selected-location", "data"),  # trigger refresh only
)
def update_ranked_comparison(_location):
    all_data = get_tourism_data(location=None)
    if all_data.empty:
        return go.Figure()

    latest_date = all_data["date"].max()
    latest = all_data[all_data["date"] == latest_date].sort_values(
        "suitability_score", ascending=False
    )

    fig = px.bar(
        latest, x="location_name", y="suitability_score",
        title=f"Suitability Score by Location \u2014 {latest_date.date()}",
        labels={"location_name": "Location", "suitability_score": "Score"},
    )
    return fig