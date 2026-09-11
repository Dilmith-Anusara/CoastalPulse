# pages/emergency.py

import dash
from dash import html, dcc, callback, Input, Output
import plotly.graph_objects as go
import pandas as pd

from data_access import (
    LOCATIONS,
    LOCATION_COORDS,
    get_emergency_data,
)


# ============================================================
# PAGE CONFIG
# ============================================================

dash.register_page(
    __name__,
    path="/emergency",
    name="Emergency",
)


# ============================================================
# DESIGN SYSTEM
# ============================================================

BG = "#F4F7F9"
CARD = "#FFFFFF"
TEXT = "#102A36"
MUTED = "#71828C"
BORDER = "#E4EBEF"

NAVY = "#0B202A"
NAVY_2 = "#123746"

GREEN = "#18A673"
GREEN_LIGHT = "#E8F7F1"

ORANGE = "#F59E0B"
ORANGE_LIGHT = "#FFF5DD"

RED = "#E34D59"
RED_LIGHT = "#FDEBED"

BLUE = "#2878C8"
BLUE_LIGHT = "#EAF3FC"

PURPLE = "#7757D6"


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def section_title(title, subtitle=None):
    children = [
        html.Div(
            title,
            style={
                "fontSize": "17px",
                "fontWeight": "700",
                "color": TEXT,
                "marginBottom": "4px",
            },
        )
    ]

    if subtitle:
        children.append(
            html.Div(
                subtitle,
                style={
                    "fontSize": "12px",
                    "color": MUTED,
                    "marginBottom": "18px",
                },
            )
        )

    return html.Div(children)


def metric_card(icon, label, value_id, unit, accent):
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        icon,
                        style={
                            "width": "38px",
                            "height": "38px",
                            "borderRadius": "10px",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "backgroundColor": f"{accent}15",
                            "color": accent,
                            "fontSize": "17px",
                            "fontWeight": "700",
                        },
                    ),
                    html.Div(
                        label,
                        style={
                            "fontSize": "12px",
                            "fontWeight": "600",
                            "color": MUTED,
                            "marginLeft": "10px",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "marginBottom": "13px",
                },
            ),
            html.Div(
                [
                    html.Span(
                        id=value_id,
                        style={
                            "fontSize": "27px",
                            "fontWeight": "750",
                            "color": TEXT,
                            "letterSpacing": "-0.5px",
                        },
                    ),
                    html.Span(
                        unit,
                        style={
                            "fontSize": "12px",
                            "fontWeight": "600",
                            "color": MUTED,
                            "marginLeft": "5px",
                        },
                    ),
                ]
            ),
        ],
        style={
            "backgroundColor": CARD,
            "border": f"1px solid {BORDER}",
            "borderRadius": "15px",
            "padding": "18px",
            "boxShadow": "0 2px 8px rgba(15, 45, 58, 0.035)",
        },
    )


def chart_card(title, subtitle, graph_id, height=400):
    return html.Div(
        [
            section_title(title, subtitle),
            dcc.Graph(
                id=graph_id,
                config={
                    "displayModeBar": False,
                    "responsive": True,
                },
                style={
                    "height": f"{height}px",
                },
            ),
        ],
        style={
            "backgroundColor": CARD,
            "border": f"1px solid {BORDER}",
            "borderRadius": "16px",
            "padding": "22px",
            "boxShadow": "0 2px 8px rgba(15, 45, 58, 0.035)",
        },
    )


# ============================================================
# EMPTY FIGURES
# ============================================================

def empty_chart(message="No data available"):
    fig = go.Figure()

    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(
            size=14,
            color=MUTED,
        ),
    )

    fig.update_layout(
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )

    return fig


def empty_map():
    fig = go.Figure()

    fig.update_layout(
        map=dict(
            style="open-street-map",
            center=dict(
                lat=7.5,
                lon=80.7,
            ),
            zoom=6,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor=CARD,
    )

    return fig


# ============================================================
# MAIN LAYOUT
# ============================================================

layout = html.Div(
    [
        # ----------------------------------------------------
        # TOP HEADER
        # ----------------------------------------------------

        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            "EMERGENCY MONITORING",
                            style={
                                "fontSize": "11px",
                                "fontWeight": "700",
                                "letterSpacing": "1.4px",
                                "color": "#6E8590",
                                "marginBottom": "6px",
                            },
                        ),
                        html.H1(
                            "Coastal Risk Monitor",
                            style={
                                "margin": "0",
                                "fontSize": "30px",
                                "fontWeight": "750",
                                "letterSpacing": "-0.7px",
                                "color": TEXT,
                            },
                        ),
                        html.Div(
                            "Monitor current marine conditions and identify potentially dangerous coastal conditions.",
                            style={
                                "fontSize": "13px",
                                "color": MUTED,
                                "marginTop": "7px",
                            },
                        ),
                    ]
                ),

                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    style={
                                        "width": "7px",
                                        "height": "7px",
                                        "borderRadius": "50%",
                                        "backgroundColor": GREEN,
                                        "marginRight": "7px",
                                    }
                                ),
                                html.Span(
                                    "LIVE DATA",
                                    style={
                                        "fontSize": "10px",
                                        "fontWeight": "750",
                                        "letterSpacing": "0.8px",
                                        "color": GREEN,
                                    },
                                ),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "padding": "9px 12px",
                                "backgroundColor": GREEN_LIGHT,
                                "borderRadius": "20px",
                                "marginRight": "12px",
                            },
                        ),

                        dcc.Dropdown(
                            id="emergency-location",
                            options=[
                                {
                                    "label": location,
                                    "value": location,
                                }
                                for location in LOCATIONS
                            ],
                            value=LOCATIONS[0] if LOCATIONS else None,
                            clearable=False,
                            style={
                                "width": "220px",
                                "fontSize": "13px",
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                    },
                ),
            ],
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "marginBottom": "25px",
                "gap": "20px",
            },
        ),

        # ----------------------------------------------------
        # HERO STATUS CARD
        # ----------------------------------------------------

        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            "CURRENT COASTAL STATUS",
                            style={
                                "fontSize": "10px",
                                "fontWeight": "750",
                                "letterSpacing": "1.4px",
                                "color": "#8EA6B0",
                                "marginBottom": "14px",
                            },
                        ),

                        html.Div(
                            [
                                html.Div(
                                    id="emergency-location-title",
                                    style={
                                        "fontSize": "25px",
                                        "fontWeight": "750",
                                        "color": "white",
                                    },
                                ),

                                html.Div(
                                    id="emergency-status-badge",
                                    style={
                                        "marginLeft": "12px",
                                    },
                                ),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "flexWrap": "wrap",
                            },
                        ),

                        html.Div(
                            id="emergency-verdict",
                            style={
                                "fontSize": "14px",
                                "lineHeight": "1.6",
                                "color": "#B8C9CF",
                                "marginTop": "10px",
                                "maxWidth": "650px",
                            },
                        ),

                        html.Div(
                            id="emergency-updated",
                            style={
                                "fontSize": "11px",
                                "color": "#718991",
                                "marginTop": "16px",
                            },
                        ),
                    ],
                    style={
                        "flex": "1",
                    },
                ),

                html.Div(
                    [
                        html.Div(
                            "RISK LEVEL",
                            style={
                                "fontSize": "10px",
                                "fontWeight": "700",
                                "letterSpacing": "1px",
                                "color": "#8EA6B0",
                                "marginBottom": "8px",
                            },
                        ),

                        html.Div(
                            id="emergency-risk-word",
                            style={
                                "fontSize": "31px",
                                "fontWeight": "800",
                                "color": "white",
                                "marginBottom": "12px",
                            },
                        ),

                        html.Div(
                            [
                                html.Div(
                                    id="emergency-risk-bar",
                                    style={
                                        "height": "7px",
                                        "borderRadius": "10px",
                                        "width": "100%",
                                        "backgroundColor": GREEN,
                                    },
                                )
                            ],
                            style={
                                "width": "180px",
                                "height": "7px",
                                "backgroundColor": "#263F49",
                                "borderRadius": "10px",
                            },
                        ),
                    ],
                    style={
                        "minWidth": "200px",
                        "textAlign": "right",
                    },
                ),
            ],
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "gap": "30px",
                "background": f"linear-gradient(135deg, {NAVY}, {NAVY_2})",
                "borderRadius": "18px",
                "padding": "27px 30px",
                "marginBottom": "18px",
                "boxShadow": "0 8px 24px rgba(11,32,42,0.12)",
            },
        ),

        # ----------------------------------------------------
        # METRIC CARDS
        # ----------------------------------------------------

        html.Div(
            [
                metric_card(
                    "≈",
                    "Maximum wave height",
                    "emergency-wave-value",
                    "m",
                    BLUE,
                ),
                metric_card(
                    "≋",
                    "Maximum wind speed",
                    "emergency-wind-value",
                    "km/h",
                    PURPLE,
                ),
                metric_card(
                    "P",
                    "Minimum pressure",
                    "emergency-pressure-value",
                    "hPa",
                    ORANGE,
                ),
                metric_card(
                    "◉",
                    "Observations",
                    "emergency-observation-value",
                    "",
                    GREEN,
                ),
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": "repeat(4, minmax(0, 1fr))",
                "gap": "14px",
                "marginBottom": "18px",
            },
        ),

        # ----------------------------------------------------
        # RECENT CONDITIONS
        # ----------------------------------------------------

        html.Div(
            [
                section_title(
                    "Recent conditions",
                    "Daily classification based on recorded marine conditions.",
                ),

                html.Div(
                    id="emergency-day-strip",
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(7, minmax(0, 1fr))",
                        "gap": "9px",
                    },
                ),
            ],
            style={
                "backgroundColor": CARD,
                "border": f"1px solid {BORDER}",
                "borderRadius": "16px",
                "padding": "22px",
                "marginBottom": "18px",
                "boxShadow": "0 2px 8px rgba(15, 45, 58, 0.035)",
            },
        ),

        # ----------------------------------------------------
        # WAVE CHART — FULL WIDTH
        # ----------------------------------------------------

        chart_card(
            "Wave height",
            "Maximum observed wave height over the selected period.",
            "emergency-wave-chart",
            height=390,
        ),

        html.Div(style={"height": "18px"}),

        # ----------------------------------------------------
        # WIND / PRESSURE CHART — FULL WIDTH
        # ----------------------------------------------------

        chart_card(
            "Wind and atmospheric pressure",
            "Observed maximum wind speed and minimum atmospheric pressure.",
            "emergency-wind-pressure-chart",
            height=390,
        ),

        html.Div(style={"height": "18px"}),

        # ----------------------------------------------------
        # MAP
        # ----------------------------------------------------

        html.Div(
            [
                section_title(
                    "Sri Lanka coastal risk map",
                    "Geographical distribution of recorded coastal conditions.",
                ),

                dcc.Graph(
                    id="emergency-map",
                    config={
                        "displayModeBar": False,
                        "responsive": True,
                    },
                    style={
                        "height": "560px",
                    },
                ),
            ],
            style={
                "backgroundColor": CARD,
                "border": f"1px solid {BORDER}",
                "borderRadius": "16px",
                "padding": "22px",
                "boxShadow": "0 2px 8px rgba(15, 45, 58, 0.035)",
            },
        ),

        html.Div(style={"height": "30px"}),

    ],
    style={
        "backgroundColor": BG,
        "minHeight": "100vh",
        "padding": "30px 34px",
        "fontFamily": "Inter, Arial, sans-serif",
        "boxSizing": "border-box",
    },
)


# ============================================================
# MAIN CALLBACK
# ============================================================

@callback(
    Output("emergency-status-badge", "children"),
    Output("emergency-status-badge", "style"),
    Output("emergency-location-title", "children"),
    Output("emergency-verdict", "children"),
    Output("emergency-updated", "children"),
    Output("emergency-risk-word", "children"),
    Output("emergency-risk-bar", "style"),
    Output("emergency-wave-value", "children"),
    Output("emergency-wind-value", "children"),
    Output("emergency-pressure-value", "children"),
    Output("emergency-observation-value", "children"),
    Output("emergency-day-strip", "children"),
    Output("emergency-wave-chart", "figure"),
    Output("emergency-wind-pressure-chart", "figure"),
    Input("emergency-location", "value"),
)
def update_emergency_page(location):

    # --------------------------------------------------------
    # Load data
    # --------------------------------------------------------

    try:
        df = get_emergency_data(location)

    except Exception:
        return (
            "ERROR",
            {
                "backgroundColor": RED_LIGHT,
                "color": RED,
                "padding": "7px 12px",
                "borderRadius": "20px",
                "fontSize": "11px",
                "fontWeight": "700",
            },
            location or "Unknown location",
            "Unable to load emergency monitoring data.",
            "Data could not be retrieved.",
            "UNKNOWN",
            {
                "height": "7px",
                "borderRadius": "10px",
                "width": "30%",
                "backgroundColor": RED,
            },
            "—",
            "—",
            "—",
            "0",
            [],
            empty_chart(),
            empty_chart(),
        )

    # --------------------------------------------------------
    # Validate data
    # --------------------------------------------------------

    if df is None or df.empty:
        return (
            "NO DATA",
            {
                "backgroundColor": "#EEF2F4",
                "color": MUTED,
                "padding": "7px 12px",
                "borderRadius": "20px",
                "fontSize": "11px",
                "fontWeight": "700",
            },
            location or "Unknown location",
            "No emergency observations are currently available for this location.",
            "No data available.",
            "NO DATA",
            {
                "height": "7px",
                "borderRadius": "10px",
                "width": "20%",
                "backgroundColor": MUTED,
            },
            "—",
            "—",
            "—",
            "0",
            [],
            empty_chart(),
            empty_chart(),
        )

    # --------------------------------------------------------
    # Prepare data
    # --------------------------------------------------------

    data = df.copy()

    if "date" in data.columns:
        data["date"] = pd.to_datetime(
            data["date"],
            errors="coerce",
        )

        data = data.sort_values("date")

    numeric_columns = [
        "wave_height_max",
        "wind_speed_max",
        "pressure_min",
    ]

    for col in numeric_columns:
        if col in data.columns:
            data[col] = pd.to_numeric(
                data[col],
                errors="coerce",
            )

    # --------------------------------------------------------
    # Current observation
    # --------------------------------------------------------

    current = data.iloc[-1]

    classification = str(
        current.get("classification", "Unknown")
    )

    wave = current.get("wave_height_max")
    wind = current.get("wind_speed_max")
    pressure = current.get("pressure_min")

    observation_count = len(data)

    # --------------------------------------------------------
    # Classification styling
    # --------------------------------------------------------

    if classification.lower() == "safe":

        status_color = GREEN
        status_light = GREEN_LIGHT
        verdict = (
            "Current conditions are within the monitored safe range."
        )
        risk_word = "SAFE"
        risk_width = "30%"

    elif classification.lower() == "caution":

        status_color = ORANGE
        status_light = ORANGE_LIGHT
        verdict = (
            "Marine conditions require caution. "
            "Continue monitoring changes in wave, wind and pressure."
        )
        risk_word = "CAUTION"
        risk_width = "60%"

    elif classification.lower() == "dangerous":

        status_color = RED
        status_light = RED_LIGHT
        verdict = (
            "Dangerous coastal conditions detected. "
            "Exercise extreme caution and follow relevant warnings."
        )
        risk_word = "DANGEROUS"
        risk_width = "90%"

    else:

        status_color = MUTED
        status_light = "#EEF2F4"
        verdict = (
            "The current classification is not available."
        )
        risk_word = "UNKNOWN"
        risk_width = "25%"

    badge = html.Span(
        classification.upper(),
        style={
            "fontSize": "10px",
            "fontWeight": "800",
            "letterSpacing": "0.6px",
        },
    )

    badge_style = {
        "backgroundColor": status_light,
        "color": status_color,
        "padding": "7px 12px",
        "borderRadius": "20px",
        "fontSize": "11px",
        "fontWeight": "700",
        "display": "inline-flex",
        "alignItems": "center",
    }

    risk_bar_style = {
        "height": "7px",
        "borderRadius": "10px",
        "width": risk_width,
        "backgroundColor": status_color,
    }

    # --------------------------------------------------------
    # Formatting helpers
    # --------------------------------------------------------

    wave_value = (
        f"{wave:.2f}"
        if pd.notna(wave)
        else "—"
    )

    wind_value = (
        f"{wind:.1f}"
        if pd.notna(wind)
        else "—"
    )

    pressure_value = (
        f"{pressure:.0f}"
        if pd.notna(pressure)
        else "—"
    )

    # --------------------------------------------------------
    # Updated text
    # --------------------------------------------------------

    if "date" in data.columns and pd.notna(current["date"]):

        updated_text = (
            "Latest observation: "
            + current["date"].strftime("%d %b %Y")
        )

    else:
        updated_text = "Latest observation available"

    # ========================================================
    # RECENT DAY STRIP
    # ========================================================

    recent = data.tail(7).copy()

    day_cards = []

    for _, row in recent.iterrows():

        row_classification = str(
            row.get("classification", "Unknown")
        )

        if row_classification.lower() == "safe":
            dot_color = GREEN
            bg_color = GREEN_LIGHT

        elif row_classification.lower() == "caution":
            dot_color = ORANGE
            bg_color = ORANGE_LIGHT

        elif row_classification.lower() == "dangerous":
            dot_color = RED
            bg_color = RED_LIGHT

        else:
            dot_color = MUTED
            bg_color = "#EEF2F4"

        if pd.notna(row.get("date")):
            day_label = row["date"].strftime("%a")
            date_label = row["date"].strftime("%d %b")
        else:
            day_label = "—"
            date_label = "—"

        day_cards.append(
            html.Div(
                [
                    html.Div(
                        day_label,
                        style={
                            "fontSize": "11px",
                            "fontWeight": "700",
                            "color": TEXT,
                            "marginBottom": "3px",
                        },
                    ),

                    html.Div(
                        date_label,
                        style={
                            "fontSize": "10px",
                            "color": MUTED,
                            "marginBottom": "9px",
                        },
                    ),

                    html.Div(
                        [
                            html.Div(
                                style={
                                    "width": "7px",
                                    "height": "7px",
                                    "borderRadius": "50%",
                                    "backgroundColor": dot_color,
                                    "marginRight": "6px",
                                }
                            ),
                            html.Span(
                                row_classification,
                                style={
                                    "fontSize": "10px",
                                    "fontWeight": "700",
                                    "color": dot_color,
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "padding": "5px 7px",
                            "borderRadius": "8px",
                            "backgroundColor": bg_color,
                            "width": "fit-content",
                        },
                    ),
                ],
                style={
                    "padding": "12px",
                    "border": f"1px solid {BORDER}",
                    "borderRadius": "11px",
                    "backgroundColor": "#FBFCFD",
                },
            )
        )

    # ========================================================
    # WAVE CHART
    # ========================================================

    wave_fig = go.Figure()

    if (
        "date" in data.columns
        and "wave_height_max" in data.columns
    ):

        wave_data = data.dropna(
            subset=["date", "wave_height_max"]
        )

        wave_fig.add_trace(
            go.Scatter(
                x=wave_data["date"],
                y=wave_data["wave_height_max"],
                mode="lines+markers",
                line=dict(
                    color=BLUE,
                    width=3,
                ),
                marker=dict(
                    size=7,
                    color=BLUE,
                ),
                fill="tozeroy",
                fillcolor="rgba(40,120,200,0.08)",
                hovertemplate=(
                    "<b>%{x|%d %b %Y}</b>"
                    "<br>Wave height: %{y:.2f} m"
                    "<extra></extra>"
                ),
            )
        )

        wave_fig.update_layout(
            paper_bgcolor=CARD,
            plot_bgcolor=CARD,
            margin=dict(
                l=45,
                r=20,
                t=10,
                b=45,
            ),
            font=dict(
                family="Inter, Arial",
                color=TEXT,
                size=11,
            ),
            xaxis=dict(
                title=None,
                showgrid=False,
                zeroline=False,
                showline=True,
                linecolor=BORDER,
                tickfont=dict(
                    color=MUTED,
                ),
            ),
            yaxis=dict(
                title="Wave height (m)",
                showgrid=True,
                gridcolor="#EDF1F3",
                zeroline=False,
                title_font=dict(
                    size=11,
                    color=MUTED,
                ),
                tickfont=dict(
                    color=MUTED,
                ),
            ),
            hoverlabel=dict(
                bgcolor=NAVY,
                font_color="white",
            ),
        )

    else:
        wave_fig = empty_chart()

    # ========================================================
    # WIND + PRESSURE CHART
    # ========================================================

    wind_pressure_fig = go.Figure()

    if (
        "date" in data.columns
        and "wind_speed_max" in data.columns
        and "pressure_min" in data.columns
    ):

        wp_data = data.dropna(
            subset=[
                "date",
                "wind_speed_max",
                "pressure_min",
            ]
        )

        # Wind
        wind_pressure_fig.add_trace(
            go.Scatter(
                x=wp_data["date"],
                y=wp_data["wind_speed_max"],
                mode="lines+markers",
                name="Wind speed",
                line=dict(
                    color=PURPLE,
                    width=3,
                ),
                marker=dict(
                    size=7,
                    color=PURPLE,
                ),
                hovertemplate=(
                    "<b>%{x|%d %b %Y}</b>"
                    "<br>Wind: %{y:.1f} km/h"
                    "<extra></extra>"
                ),
            )
        )

        # Pressure
        wind_pressure_fig.add_trace(
            go.Scatter(
                x=wp_data["date"],
                y=wp_data["pressure_min"],
                mode="lines+markers",
                name="Pressure",
                yaxis="y2",
                line=dict(
                    color=ORANGE,
                    width=3,
                ),
                marker=dict(
                    size=7,
                    color=ORANGE,
                ),
                hovertemplate=(
                    "<b>%{x|%d %b %Y}</b>"
                    "<br>Pressure: %{y:.0f} hPa"
                    "<extra></extra>"
                ),
            )
        )

        wind_pressure_fig.update_layout(
            paper_bgcolor=CARD,
            plot_bgcolor=CARD,
            margin=dict(
                l=50,
                r=65,
                t=15,
                b=50,
            ),
            font=dict(
                family="Inter, Arial",
                color=TEXT,
                size=11,
            ),
            xaxis=dict(
                showgrid=False,
                zeroline=False,
                showline=True,
                linecolor=BORDER,
                tickfont=dict(
                    color=MUTED,
                ),
            ),
            yaxis=dict(
                title="Wind speed (km/h)",
                showgrid=True,
                gridcolor="#EDF1F3",
                zeroline=False,
                title_font=dict(
                    size=11,
                    color=PURPLE,
                ),
                tickfont=dict(
                    color=MUTED,
                ),
            ),
            yaxis2=dict(
                title="Pressure (hPa)",
                overlaying="y",
                side="right",
                showgrid=False,
                zeroline=False,
                title_font=dict(
                    size=11,
                    color=ORANGE,
                ),
                tickfont=dict(
                    color=MUTED,
                ),
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.01,
                xanchor="right",
                x=1,
                font=dict(
                    size=11,
                    color=MUTED,
                ),
            ),
            hoverlabel=dict(
                bgcolor=NAVY,
                font_color="white",
            ),
        )

    else:
        wind_pressure_fig = empty_chart()

    # ========================================================
    # RETURN
    # ========================================================

    return (
        badge,
        badge_style,
        location or "Unknown location",
        verdict,
        updated_text,
        risk_word,
        risk_bar_style,
        wave_value,
        wind_value,
        pressure_value,
        str(observation_count),
        day_cards,
        wave_fig,
        wind_pressure_fig,
    )


# ============================================================
# MAP CALLBACK
# ============================================================

@callback(
    Output("emergency-map", "figure"),
    Input("emergency-location", "value"),
)
def update_emergency_map(selected_location):

    try:
        df = get_emergency_data()

    except Exception:
        return empty_map()

    if df is None or df.empty:
        return empty_map()

    data = df.copy()

    # --------------------------------------------------------
    # Latest observation for each location
    # --------------------------------------------------------

    if "date" in data.columns:
        data["date"] = pd.to_datetime(
            data["date"],
            errors="coerce",
        )

        data = data.sort_values("date")

        latest = (
            data.groupby("location_name", as_index=False)
            .tail(1)
            .copy()
        )

    else:
        latest = data.copy()

    # --------------------------------------------------------
    # Map figure
    # --------------------------------------------------------

    fig = go.Figure()

    for classification, color in [
        ("Safe", GREEN),
        ("Caution", ORANGE),
        ("Dangerous", RED),
    ]:

        group = latest[
            latest["classification"]
            .astype(str)
            .str.lower()
            == classification.lower()
        ].copy()

        if group.empty:
            continue

        lats = []
        lons = []
        names = []
        hover_text = []

        for _, row in group.iterrows():

            location_name = row.get(
                "location_name",
                "",
            )

            coords = LOCATION_COORDS.get(
                location_name
            )

            if coords is None:
                continue

            # Supports either:
            # (lat, lon)
            # or
            # {"lat": ..., "lon": ...}

            if isinstance(coords, dict):
                lat = coords.get("lat")
                lon = coords.get("lon")

            else:
                try:
                    lat, lon = coords
                except Exception:
                    continue

            if lat is None or lon is None:
                continue

            lats.append(lat)
            lons.append(lon)
            names.append(location_name)

            wave = row.get(
                "wave_height_max"
            )

            wind = row.get(
                "wind_speed_max"
            )

            pressure = row.get(
                "pressure_min"
            )

            hover_text.append(
                f"<b>{location_name}</b>"
                f"<br>Risk: {classification}"
                f"<br>Wave: "
                f"{wave:.2f} m"
                if pd.notna(wave)
                else
                f"<b>{location_name}</b>"
                f"<br>Risk: {classification}"
            )

        if not lats:
            continue

        fig.add_trace(
            go.Scattermap(
                lat=lats,
                lon=lons,
                mode="markers",
                name=classification,
                text=names,
                hovertext=hover_text,
                hoverinfo="text",
                marker=dict(
                    size=13,
                    color=color,
                    opacity=0.9,
                ),
            )
        )

    # --------------------------------------------------------
    # Highlight selected location
    # --------------------------------------------------------

    if selected_location in LOCATION_COORDS:

        coords = LOCATION_COORDS[
            selected_location
        ]

        if isinstance(coords, dict):
            lat = coords.get("lat")
            lon = coords.get("lon")
        else:
            lat, lon = coords

        if lat is not None and lon is not None:

            fig.add_trace(
                go.Scattermap(
                    lat=[lat],
                    lon=[lon],
                    mode="markers",
                    name="Selected location",
                    hoverinfo="skip",
                    marker=dict(
                        size=22,
                        color="#102A36",
                        opacity=0.22,
                    ),
                    showlegend=False,
                )
            )

            fig.add_trace(
                go.Scattermap(
                    lat=[lat],
                    lon=[lon],
                    mode="markers",
                    hoverinfo="skip",
                    marker=dict(
                        size=8,
                        color="#102A36",
                        opacity=1,
                    ),
                    showlegend=False,
                )
            )

    # --------------------------------------------------------
    # Map layout
    # --------------------------------------------------------

    fig.update_layout(
        map=dict(
            style="open-street-map",
            center=dict(
                lat=7.5,
                lon=80.7,
            ),
            zoom=6,
        ),
        margin=dict(
            l=0,
            r=0,
            t=0,
            b=0,
        ),
        paper_bgcolor=CARD,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=0.02,
            xanchor="left",
            x=0.02,
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor=BORDER,
            borderwidth=1,
            font=dict(
                size=11,
                color=TEXT,
            ),
        ),
    )

    return fig