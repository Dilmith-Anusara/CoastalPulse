"""
pages/analytics.py — Analytics mode.

Not a per-location verdict page like Emergency/Tourism — this is the
"analytics" half of the course brief ("retrieve weather insights and
analytics"), turning the EDA notebook's own findings (seasonality,
cross-location comparison, correlations) into live, interactive charts
instead of leaving them in an offline notebook only a grader who opens
the .ipynb would ever see.

Reads get_analytics_data() (merged gold_emergency_daily + gold_tourism_daily),
not silver_hourly — see that function's docstring for why: Gold already
has daily-resolution versions of nearly every indicator this page needs,
at 8,190 rows instead of Silver's 196,560.
"""

import dash
from dash import html, dcc, callback, Input, Output
import plotly.graph_objects as go
import pandas as pd

from data_access import get_analytics_data
from design_system import (
    CARD, TEXT, MUTED, BORDER, NAVY,
    ACCENT_BLUE, ACCENT_ORANGE, ACCENT_TEAL, ACCENT_PINK, ACCENT_PURPLE,
    PAGE_STYLE, CARD_STYLE,
    section_title, chart_card, empty_chart,
)

dash.register_page(__name__, path="/analytics", name="Analytics")

# Indicator -> (Gold column, display unit, chart color). Deliberately
# sourced from Gold (daily resolution) — see get_analytics_data's
# docstring for why Silver isn't used here.
INDICATORS = {
    "Air temperature (daily max)": ("air_temperature_max", "°C", ACCENT_PINK),
    "Humidity (daylight mean)": ("humidity_mean", "%", ACCENT_BLUE),
    "Wind speed (daylight mean)": ("wind_speed_mean", "km/h", ACCENT_PURPLE),
    "Rainfall (daily total)": ("precipitation_sum", "mm", ACCENT_TEAL),
    "Atmospheric pressure (daily min)": ("pressure_min", "hPa", ACCENT_ORANGE),
    "Wave height (daily max)": ("wave_height_max", "m", ACCENT_BLUE),
    "Cloud cover (daylight mean)": ("cloud_cover_mean", "%", ACCENT_PURPLE),
    "UV index (daylight mean)": ("uv_index_mean", "", ACCENT_ORANGE),
    "Air quality — US AQI (daylight mean)": ("us_aqi_mean", "AQI", ACCENT_TEAL),
    "Beach suitability score": ("suitability_score", "/100", ACCENT_PINK),
}

CORRELATION_COLUMNS = [
    "air_temperature_max", "humidity_mean", "wind_speed_mean", "precipitation_sum",
    "pressure_min", "wave_height_max", "cloud_cover_mean", "uv_index_mean",
    "us_aqi_mean", "suitability_score",
]


def _month_label(period_str):
    try:
        return pd.Period(period_str, freq="M").strftime("%b %Y")
    except Exception:
        return period_str


# ============================================================
# LAYOUT
# ============================================================

layout = html.Div(
    [
        section_title(
            "Climate & marine analytics",
            "Trends, seasonality, and cross-location patterns across the full dataset — "
            "the analytical view behind the plain-language verdicts on Emergency and Tourism.",
        ),

        html.Div(
            [
                html.Label(
                    "Indicator",
                    style={"fontSize": "12px", "fontWeight": "600", "color": MUTED, "marginBottom": "6px", "display": "block"},
                ),
                dcc.Dropdown(
                    id="analytics-indicator",
                    options=[{"label": k, "value": k} for k in INDICATORS],
                    value=list(INDICATORS.keys())[0],
                    clearable=False,
                    style={"maxWidth": "420px"},
                ),
            ],
            style={"marginBottom": "24px"},
        ),

        html.Div(
            id="analytics-caption",
            style={
                "backgroundColor": "#EAF7F5", "padding": "12px 16px",
                "borderLeft": f"4px solid {ACCENT_TEAL}", "borderRadius": "6px",
                "fontSize": "13px", "color": TEXT, "lineHeight": "1.6", "marginBottom": "24px",
            },
        ),

        chart_card(
            "Monthly pattern — all locations pooled",
            "Mean value per month across the full date range. Reveals seasonality a single day's reading can't.",
            "analytics-monthly-chart", height=380,
        ),
        html.Div(style={"height": "24px"}),

        chart_card(
            "How locations compare",
            "Mean value per location across the full date range, sorted low to high.",
            "analytics-location-chart", height=400,
        ),
        html.Div(style={"height": "24px"}),

        html.Div(
            [
                section_title(
                    "How indicators relate to each other",
                    "Correlation across all locations and days — where two variables move together (or apart), "
                    "that's evidence for how the suitability score or emergency classification could use them.",
                ),
                dcc.Graph(id="analytics-correlation-chart", config={"displayModeBar": False}, style={"height": "480px"}),
            ],
            style=CARD_STYLE,
        ),
    ],
    style=PAGE_STYLE,
)


# ============================================================
# CALLBACK
# ============================================================

@callback(
    Output("analytics-monthly-chart", "figure"),
    Output("analytics-location-chart", "figure"),
    Output("analytics-caption", "children"),
    Output("analytics-correlation-chart", "figure"),
    Input("analytics-indicator", "value"),
    Input("selected-location", "data"),
)
def update_analytics(indicator_name, selected_location):
    try:
        df = get_analytics_data()
    except Exception:
        return empty_chart(), empty_chart(), html.Div("We couldn't load analytics data right now."), empty_chart()

    if df is None or df.empty:
        return empty_chart(), empty_chart(), html.Div("No data available."), empty_chart()

    col, unit, color = INDICATORS.get(indicator_name, list(INDICATORS.values())[0])
    if col not in df.columns:
        return empty_chart(), empty_chart(), html.Div("No data for this indicator."), empty_chart()

    data = df.copy()
    data[col] = pd.to_numeric(data[col], errors="coerce")

    # --- Monthly trend, pooled across all locations ---
    monthly = data.groupby("month")[col].mean().dropna().sort_index()
    monthly_fig = go.Figure()
    if not monthly.empty:
        labels = [_month_label(m) for m in monthly.index]
        monthly_fig.add_trace(go.Scatter(
            x=labels, y=monthly.values, mode="lines+markers",
            line=dict(color=color, width=3), marker=dict(size=7, color=color),
        ))
    monthly_fig.update_layout(
        paper_bgcolor=CARD, plot_bgcolor=CARD, margin=dict(l=50, r=20, t=10, b=60),
        font=dict(family="Inter, Arial", color=TEXT, size=11),
        xaxis=dict(showgrid=False, zeroline=False, showline=True, linecolor=BORDER, tickfont=dict(color=MUTED), tickangle=-35),
        yaxis=dict(title=f"{indicator_name} ({unit})" if unit else indicator_name, showgrid=True, gridcolor="#EDF1F3", tickfont=dict(color=MUTED)),
        hoverlabel=dict(bgcolor=NAVY, font_color="white"),
    )

    # --- Cross-location comparison ---
    by_location = data.groupby("location_name")[col].mean().dropna().sort_values()
    loc_colors = [color if name == selected_location else "#CFE3E3" for name in by_location.index]
    location_fig = go.Figure()
    if not by_location.empty:
        location_fig.add_trace(go.Bar(x=by_location.index, y=by_location.values, marker_color=loc_colors))
    location_fig.update_layout(
        paper_bgcolor=CARD, plot_bgcolor=CARD, margin=dict(l=50, r=20, t=10, b=90),
        font=dict(family="Inter, Arial", color=TEXT, size=11),
        xaxis=dict(showgrid=False, zeroline=False, tickangle=-45, tickfont=dict(color=MUTED)),
        yaxis=dict(title=f"{indicator_name} ({unit})" if unit else indicator_name, showgrid=True, gridcolor="#EDF1F3", tickfont=dict(color=MUTED)),
        hoverlabel=dict(bgcolor=NAVY, font_color="white"),
    )

    # --- Caption: peak/trough month + highest/lowest location. This is
    # the "how to read a line plot" 4-step process (find the shape, find
    # peak/trough, check it against something real, check the swing
    # size) computed live instead of asked of the reader. ---
    caption_parts = []
    if len(monthly) >= 2:
        peak_month = monthly.idxmax()
        trough_month = monthly.idxmin()
        swing = monthly.max() - monthly.min()
        rel_swing = (swing / monthly.mean() * 100) if monthly.mean() else 0
        caption_parts.append(
            f"{indicator_name} peaks in {_month_label(peak_month)} ({monthly.max():.1f}{unit}) "
            f"and is lowest in {_month_label(trough_month)} ({monthly.min():.1f}{unit}) — "
            f"a swing of about {rel_swing:.0f}% relative to the average."
        )
    if len(by_location) >= 2:
        highest = by_location.index[-1]
        lowest = by_location.index[0]
        caption_parts.append(f"{highest} runs highest on average; {lowest} runs lowest.")
    caption = " ".join(caption_parts) if caption_parts else "Not enough data to summarize this indicator yet."

    # --- Correlation heatmap (independent of indicator selection) ---
    corr_cols = [c for c in CORRELATION_COLUMNS if c in data.columns]
    corr_data = data[corr_cols].apply(pd.to_numeric, errors="coerce")
    corr = corr_data.corr()
    corr_fig = go.Figure(data=go.Heatmap(
        z=corr.values, x=list(corr.columns), y=list(corr.columns),
        colorscale="RdBu", zmid=0, zmin=-1, zmax=1,
        text=corr.round(2).values, texttemplate="%{text}",
        hoverongaps=False,
    ))
    corr_fig.update_layout(
        paper_bgcolor=CARD, margin=dict(l=140, r=20, t=10, b=140),
        font=dict(family="Inter, Arial", color=TEXT, size=10),
        xaxis=dict(tickangle=-45),
    )

    return monthly_fig, location_fig, caption, corr_fig
