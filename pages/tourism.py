"""
pages/tourism.py — Tourism mode.

Real gold_tourism_daily columns (confirmed via information_schema.columns):
    daylight_hours_covered, date, wave_height_mean, wind_speed_mean,
    sea_surface_temp_mean, uv_index_mean, precipitation_sum,
    suitability_score, location_name

Same verdict/detail split as Emergency, for the same reason: a tourist
checking "is today good for the beach" doesn't want a suitability_score
line chart, they want a plain sentence and a few readable condition chips.
The trend charts and cross-location ranking are demoted to the detail zone.

suitability_score is still a first-draft placeholder formula (per the
project handoff) — every place it's shown says so, it is not presented as
an authoritative number.
"""

import dash
from dash import html, dcc, callback, Input, Output
import plotly.graph_objects as go
import plotly.express as px

from data_access import get_tourism_data

dash.register_page(__name__, path="/tourism", name="Tourism")

# suitability_score bands — same "first-draft, not settled" caveat as the
# score itself. Only used to pick a plain-language word, not a hard cutoff.
SCORE_BANDS = [
    (70, "Good beach day", "#2ecc71"),
    (40, "Fair — some conditions worth checking", "#f39c12"),
    (0, "Not ideal today", "#e74c3c"),
]


def _score_band(score):
    if score is None:
        return "conditions unknown", "#999"
    for threshold, label, color in SCORE_BANDS:
        if score >= threshold:
            return label, color
    return SCORE_BANDS[-1][1], SCORE_BANDS[-1][2]


def _uv_band(uv):
    # Standard WHO UV Index scale.
    if uv is None:
        return "—", "#999"
    if uv < 3:
        return "Low", "#2ecc71"
    if uv < 6:
        return "Moderate", "#f1c40f"
    if uv < 8:
        return "High", "#f39c12"
    if uv < 11:
        return "Very High", "#e74c3c"
    return "Extreme", "#9b59b6"


def _wave_band(wave):
    if wave is None:
        return "—"
    if wave < 0.5:
        return "Calm"
    if wave < 1.0:
        return "Gentle"
    if wave < 1.5:
        return "Choppy"
    return "Rough"


def _rain_band(precip):
    if precip is None:
        return "—"
    if precip < 1:
        return "Dry"
    if precip < 5:
        return "Light rain"
    return "Rainy"


def _condition_chip(icon, label, value_text, sub_color=None):
    return html.Div(
        [
            html.Div(icon, style={"fontSize": "22px", "marginBottom": "6px"}),
            html.Div(value_text, style={"fontSize": "15px", "fontWeight": "700"}),
            html.Div(label, style={"fontSize": "11px", "color": "#72838c"}),
        ],
        style={
            "flex": "1",
            "textAlign": "center",
            "padding": "14px 8px",
            "borderRadius": "8px",
            "background": "#ffffff",
            "border": "1px solid #dce5e9",
        },
    )


layout = html.Div(
    [
        # Verdict zone: plain-language beach verdict + readable condition
        # chips + a 7-day strip. No raw scores or line charts here.
        html.Div(
            [
                html.Div(id="tourism-verdict"),
                html.Div(
                    id="tourism-condition-chips",
                    style={"display": "flex", "gap": "10px", "marginTop": "1rem"},
                ),
                html.Div(id="tourism-day-strip", style={"marginTop": "1rem"}),
            ],
            className="cp-verdict-zone",
        ),
        # Detail zone: hidden until "Show details" is switched on.
        html.Div(
            [
                html.Div(
                    "Suitability score is a first-draft placeholder formula, "
                    "not a validated or authoritative metric \u2014 treat it "
                    "as a rough guide.",
                    style={
                        "backgroundColor": "#fff8e1", "padding": "0.5rem 1rem",
                        "borderLeft": "4px solid #f39c12", "marginBottom": "1rem",
                        "fontSize": "12px",
                    },
                ),
                html.H3("Suitability Score Trend"),
                dcc.Graph(id="tourism-suitability-timeseries"),
                html.Div(id="tourism-sst-note"),
                html.H3("Daylight-Hours Mean Conditions"),
                dcc.Graph(id="tourism-conditions"),
                html.H3("Ranked Comparison \u2014 All Locations, Latest Day"),
                dcc.Graph(id="tourism-ranked-comparison"),
            ],
            className="cp-detail-zone",
        ),
    ]
)


@callback(
    Output("tourism-verdict", "children"),
    Output("tourism-condition-chips", "children"),
    Output("tourism-day-strip", "children"),
    Output("tourism-suitability-timeseries", "figure"),
    Output("tourism-sst-note", "children"),
    Output("tourism-conditions", "figure"),
    Input("selected-location", "data"),
)
def update_tourism_page(location):
    df = get_tourism_data(location)
    if df.empty:
        empty_fig = go.Figure()
        return (
            html.Div(f"No data available for {location}."),
            [], html.Div(), empty_fig, html.Div(), empty_fig,
        )

    latest = df.iloc[-1]
    score = latest.get("suitability_score")
    band_label, band_color = _score_band(score)

    verdict = html.Div(
        [
            html.Div(
                [
                    html.Span(
                        f"{score:.0f}/100" if score is not None else "\u2014",
                        style={
                            "backgroundColor": band_color, "color": "white",
                            "padding": "0.5rem 1rem", "borderRadius": "4px",
                            "fontWeight": "bold", "fontSize": "1.2rem",
                        },
                    ),
                    html.Span(
                        f"  as of {latest['date'].date()}",
                        style={"marginLeft": "1rem", "color": "#72838c"},
                    ),
                ]
            ),
            html.Div(
                f"{location}: {band_label}",
                style={"marginTop": "0.75rem", "fontSize": "1.05rem"},
            ),
        ]
    )

    wave_label = _wave_band(latest.get("wave_height_mean"))
    uv_label, _ = _uv_band(latest.get("uv_index_mean"))
    rain_label = _rain_band(latest.get("precipitation_sum"))
    sst = latest.get("sea_surface_temp_mean")

    chips = [
        _condition_chip("\U0001F30A", "Sea", wave_label),
        _condition_chip("\u2600\uFE0F", "UV Index", uv_label),
        _condition_chip("\U0001F327\uFE0F", "Rain", rain_label),
        _condition_chip(
            "\U0001F321\uFE0F", "Sea temp",
            f"{sst:.0f}\u00b0C" if sst is not None else "N/A",
        ),
    ]

    # 7-day strip, colored by suitability score band.
    recent = df.tail(7)
    day_chips = []
    for _, row in recent.iterrows():
        row_score = row.get("suitability_score")
        _, row_color = _score_band(row_score)
        day_chips.append(
            html.Div(
                [
                    html.Div(row["date"].strftime("%a"),
                              style={"fontSize": "11px", "fontWeight": "700", "color": "#72838c"}),
                    html.Div(row["date"].strftime("%d %b"),
                              style={"fontSize": "10px", "color": "#9aa8ae", "marginBottom": "6px"}),
                    html.Div(
                        f"{row_score:.0f}" if row_score is not None else "\u2014",
                        style={"fontSize": "15px", "fontWeight": "700", "color": "white"},
                    ),
                ],
                style={
                    "flex": "1", "textAlign": "center", "padding": "10px 6px",
                    "borderRadius": "6px", "background": row_color,
                },
            )
        )
    day_strip = html.Div(day_chips, style={"display": "flex", "gap": "6px"})

    # --- Detail-zone charts (unchanged purpose, just demoted) -----------

    suit_fig = go.Figure()
    suit_fig.add_trace(
        go.Scatter(x=df["date"], y=df["suitability_score"], mode="lines", name="Suitability score")
    )
    suit_fig.update_layout(title="Suitability Score (0-100, first-draft formula)",
                            yaxis_title="score", yaxis_range=[0, 100])

    is_tourism_only = df["is_tourism_only"].iloc[-1] if "is_tourism_only" in df.columns else False
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
    if "sea_surface_temp_mean" in df.columns:
        conditions_fig.add_trace(
            go.Scatter(x=df["date"], y=df["sea_surface_temp_mean"], name="Sea surface temp (\u00b0C)", yaxis="y2")
        )
    if "uv_index_mean" in df.columns:
        conditions_fig.add_trace(
            go.Scatter(x=df["date"], y=df["uv_index_mean"], name="UV index (mean)", yaxis="y2")
        )
    if "precipitation_sum" in df.columns:
        conditions_fig.add_trace(
            go.Bar(x=df["date"], y=df["precipitation_sum"], name="Precipitation (mm)", opacity=0.4)
        )
    conditions_fig.update_layout(
        title="Daylight-Hours Mean Conditions",
        yaxis_title="meters",
        yaxis2=dict(overlaying="y", side="right"),
    )

    return verdict, chips, day_strip, suit_fig, sst_note, conditions_fig


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