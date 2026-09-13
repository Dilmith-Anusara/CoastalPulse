"""
pages/analytics.py — Analytics mode.

Not a per-location verdict page like Emergency/Tourism — this is the
"analytics" half of the course brief ("retrieve weather insights and
analytics"). Built around four real, checkable findings rather than a
single dropdown-driven line chart:

1. Regional monsoon split — Sri Lanka's Southwest and Northeast coasts run
   opposite wet seasons (Dept. of Meteorology climatology; see
   data_access.COAST_REGION). Pooling all 15 locations into one national
   average cancels that signal out, so the monthly trend is split by coast
   region instead.
2. Extremes — the single highest/lowest readings (which location, which
   day), not just the mean.
3. Emergency risk vs. Tourism suitability — since get_analytics_data()
   already joins both Gold tables on (location_name, date), this checks
   whether the two independently-computed verdicts actually move together.
4. Correlation — plus a plain-language callout of the strongest pairs
   instead of a bare, uninterpreted matrix.

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
from page_helpers import CLASSIFICATION_COLORS, SCORE_GOOD_MIN
from design_system import (
    CARD, TEXT, MUTED, BORDER, NAVY,
    ACCENT_BLUE, ACCENT_ORANGE, ACCENT_TEAL, ACCENT_PINK, ACCENT_PURPLE,
    PAGE_STYLE, CARD_STYLE,
    section_title, chart_card, empty_chart,
)

dash.register_page(__name__, path="/analytics", name="Analytics")

SUITABILITY_GOOD_MIN = SCORE_GOOD_MIN  # 60 — page_helpers.py's real "at least Good" cutoff, not positional SCORE_BANDS[0] (that's "Excellent" now that the dashboard shows all 5 HCI:Beach tiers)

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
COLUMN_LABELS = {col: name for name, (col, unit, color) in INDICATORS.items()}

CORRELATION_COLUMNS = [
    "air_temperature_max", "humidity_mean", "wind_speed_mean", "precipitation_sum",
    "pressure_min", "wave_height_max", "cloud_cover_mean", "uv_index_mean",
    "us_aqi_mean", "suitability_score",
]

REGION_COLORS = {"Southwest coast": ACCENT_ORANGE, "Northeast coast": ACCENT_BLUE}
RISK_ORDER = ["Safe", "Caution", "Dangerous"]


def _month_label(period_str):
    try:
        return pd.Period(period_str, freq="M").strftime("%b %Y")
    except Exception:
        return period_str


def _month_of_year(period_str):
    try:
        return pd.Period(period_str, freq="M").month
    except Exception:
        return None


def _extremes_list(df, col, unit, ascending, n=5):
    subset = df.dropna(subset=[col, "location_name", "date"]).sort_values(col, ascending=ascending).head(n)
    if subset.empty:
        return html.Div("No data.", style={"fontSize": "12px", "color": MUTED})
    rows = []
    for _, r in subset.iterrows():
        rows.append(
            html.Div(
                [
                    html.Span(f"{r['value_fmt']}{unit}", style={"fontWeight": "700", "color": TEXT, "marginRight": "8px"}),
                    html.Span(f"{r['location_name']} — {r['date'].strftime('%d %b %Y')}", style={"color": MUTED}),
                ],
                style={"fontSize": "12.5px", "padding": "7px 0", "borderBottom": f"1px solid {BORDER}"},
            )
        )
    return html.Div(rows)


def _caption_box(children, color=ACCENT_TEAL):
    return html.Div(
        children,
        style={
            "backgroundColor": "#EAF7F5", "padding": "12px 16px",
            "borderLeft": f"4px solid {color}", "borderRadius": "6px",
            "fontSize": "13px", "color": TEXT, "lineHeight": "1.6", "marginTop": "14px",
        },
    )


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

        chart_card(
            "Monthly pattern, split by coast",
            "Sri Lanka's Southwest and Northeast coasts run opposite monsoon seasons — pooling every "
            "location into one national average hides that. Each region is its own line here.",
            "analytics-monthly-chart", height=380,
        ),
        html.Div(id="analytics-monthly-caption"),
        html.Div(style={"height": "24px"}),

        chart_card(
            "How locations compare",
            "Mean value per location across the full date range, sorted low to high.",
            "analytics-location-chart", height=400,
        ),
        html.Div(id="analytics-location-caption"),
        html.Div(style={"height": "24px"}),

        html.Div(
            [
                section_title(
                    "Where and when has it been most extreme?",
                    "The single highest and lowest daily readings for the selected indicator, across all "
                    "15 locations and the full date range — means hide these.",
                ),
                html.Div(
                    [
                        html.Div(
                            [html.Div("Highest", style={"fontSize": "12px", "fontWeight": "700", "color": TEXT, "marginBottom": "6px"}),
                             html.Div(id="analytics-extremes-high")],
                            style={"flex": "1"},
                        ),
                        html.Div(
                            [html.Div("Lowest", style={"fontSize": "12px", "fontWeight": "700", "color": TEXT, "marginBottom": "6px"}),
                             html.Div(id="analytics-extremes-low")],
                            style={"flex": "1"},
                        ),
                    ],
                    style={"display": "flex", "gap": "32px", "flexWrap": "wrap"},
                ),
            ],
            style=CARD_STYLE,
        ),
        html.Div(style={"height": "24px"}),

        html.Div(
            [
                section_title(
                    "Do risk and suitability move together?",
                    "Emergency's wave-height classification and Tourism's HCI:Beach suitability score are computed "
                    "independently, from overlapping but different inputs — this checks whether they actually agree.",
                ),
                dcc.Graph(id="analytics-risk-chart", config={"displayModeBar": False}, style={"height": "280px"}),
                html.Div(id="analytics-risk-caption"),
            ],
            style=CARD_STYLE,
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
                html.Div(id="analytics-correlation-caption"),
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
    Output("analytics-monthly-caption", "children"),
    Output("analytics-location-chart", "figure"),
    Output("analytics-location-caption", "children"),
    Output("analytics-extremes-high", "children"),
    Output("analytics-extremes-low", "children"),
    Output("analytics-risk-chart", "figure"),
    Output("analytics-risk-caption", "children"),
    Output("analytics-correlation-chart", "figure"),
    Output("analytics-correlation-caption", "children"),
    Input("analytics-indicator", "value"),
    Input("selected-location", "data"),
)
def update_analytics(indicator_name, selected_location):
    empty_msg = html.Div("No data available.", style={"fontSize": "12px", "color": MUTED})
    try:
        df = get_analytics_data()
    except Exception:
        err = html.Div("We couldn't load analytics data right now.")
        return empty_chart(), err, empty_chart(), err, empty_msg, empty_msg, empty_chart(), err, empty_chart(), err

    if df is None or df.empty:
        return empty_chart(), empty_msg, empty_chart(), empty_msg, empty_msg, empty_msg, empty_chart(), empty_msg, empty_chart(), empty_msg

    col, unit, color = INDICATORS.get(indicator_name, list(INDICATORS.values())[0])
    if col not in df.columns:
        return empty_chart(), empty_msg, empty_chart(), empty_msg, empty_msg, empty_msg, empty_chart(), empty_msg, empty_chart(), empty_msg

    data = df.copy()
    data[col] = pd.to_numeric(data[col], errors="coerce")

    # --- Monthly trend, split by coast region ---
    regional = data.dropna(subset=[col, "coast_region"]).groupby(["coast_region", "month"])[col].mean().reset_index()
    monthly_fig = go.Figure()
    region_peaks = {}
    for region in ["Southwest coast", "Northeast coast"]:
        series = regional[regional["coast_region"] == region].set_index("month")[col].sort_index()
        if series.empty:
            continue
        labels = [_month_label(m) for m in series.index]
        monthly_fig.add_trace(go.Scatter(
            x=labels, y=series.values, mode="lines+markers", name=region,
            line=dict(color=REGION_COLORS[region], width=3), marker=dict(size=6, color=REGION_COLORS[region]),
        ))
        region_peaks[region] = series
    monthly_fig.update_layout(
        paper_bgcolor=CARD, plot_bgcolor=CARD, margin=dict(l=50, r=20, t=10, b=60),
        font=dict(family="Public Sans, Arial", color=TEXT, size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(showgrid=False, zeroline=False, showline=True, linecolor=BORDER, tickfont=dict(color=MUTED), tickangle=-35),
        yaxis=dict(title=f"{indicator_name} ({unit})" if unit else indicator_name, showgrid=True, gridcolor="#EDF1F3", tickfont=dict(color=MUTED)),
        hoverlabel=dict(bgcolor=NAVY, font_color="white"),
    )

    if "Southwest coast" in region_peaks and "Northeast coast" in region_peaks:
        sw, ne = region_peaks["Southwest coast"], region_peaks["Northeast coast"]
        sw_peak_month, ne_peak_month = sw.idxmax(), ne.idxmax()
        sw_moy, ne_moy = _month_of_year(sw_peak_month), _month_of_year(ne_peak_month)
        month_gap = min(abs(sw_moy - ne_moy), 12 - abs(sw_moy - ne_moy)) if sw_moy and ne_moy else None
        timing_note = (
            "different times of year — consistent with the Southwest and Northeast monsoons peaking months apart"
            if month_gap is not None and month_gap >= 3
            else "around the same time of year, so this indicator doesn't split strongly by monsoon region"
        )
        monthly_caption = _caption_box(
            f"Southwest coast peaks in {_month_label(sw_peak_month)} ({sw.max():.1f}{unit}); "
            f"Northeast coast peaks in {_month_label(ne_peak_month)} ({ne.max():.1f}{unit}) — {timing_note}."
        )
    else:
        monthly_caption = _caption_box("Not enough regional data to compare yet.")

    # --- Cross-location comparison ---
    by_location = data.groupby("location_name")[col].mean().dropna().sort_values()
    loc_colors = [color if name == selected_location else "#CFE3E3" for name in by_location.index]
    location_fig = go.Figure()
    if not by_location.empty:
        location_fig.add_trace(go.Bar(x=by_location.index, y=by_location.values, marker_color=loc_colors))
    location_fig.update_layout(
        paper_bgcolor=CARD, plot_bgcolor=CARD, margin=dict(l=50, r=20, t=10, b=90),
        font=dict(family="Public Sans, Arial", color=TEXT, size=11),
        xaxis=dict(showgrid=False, zeroline=False, tickangle=-45, tickfont=dict(color=MUTED)),
        yaxis=dict(title=f"{indicator_name} ({unit})" if unit else indicator_name, showgrid=True, gridcolor="#EDF1F3", tickfont=dict(color=MUTED)),
        hoverlabel=dict(bgcolor=NAVY, font_color="white"),
    )
    if len(by_location) >= 2:
        highest, lowest = by_location.index[-1], by_location.index[0]
        location_caption = _caption_box(
            f"{highest} runs highest on average ({by_location.iloc[-1]:.1f}{unit}); "
            f"{lowest} runs lowest ({by_location.iloc[0]:.1f}{unit})."
        )
    else:
        location_caption = _caption_box("Not enough data to compare locations yet.")

    # --- Extremes: single highest/lowest readings, not just means ---
    ext = data.dropna(subset=[col]).copy()
    ext["value_fmt"] = ext[col].map(lambda v: f"{v:.1f}")
    high_list = _extremes_list(ext, col, unit, ascending=False)
    low_list = _extremes_list(ext, col, unit, ascending=True)

    # --- Emergency risk vs. Tourism suitability cross-analysis ---
    risk_data = data.dropna(subset=["classification", "suitability_score"])
    risk_fig = go.Figure()
    risk_caption = empty_msg
    if not risk_data.empty:
        grp = risk_data.groupby("classification")["suitability_score"].mean()
        present = [c for c in RISK_ORDER if c in grp.index]
        risk_fig.add_trace(go.Bar(
            x=present, y=[grp[c] for c in present],
            marker_color=[CLASSIFICATION_COLORS[c] for c in present],
        ))
        risk_fig.update_layout(
            paper_bgcolor=CARD, plot_bgcolor=CARD, margin=dict(l=50, r=20, t=10, b=40),
            font=dict(family="Public Sans, Arial", color=TEXT, size=11),
            xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(color=MUTED)),
            yaxis=dict(title="Mean suitability score", range=[0, 100], showgrid=True, gridcolor="#EDF1F3", tickfont=dict(color=MUTED)),
            hoverlabel=dict(bgcolor=NAVY, font_color="white"),
        )
        if "Safe" in grp.index and "Dangerous" in grp.index:
            def pct_poor(cls):
                sub = risk_data[risk_data["classification"] == cls]["suitability_score"]
                return (sub < SUITABILITY_GOOD_MIN).mean() * 100
            safe_poor, danger_poor = pct_poor("Safe"), pct_poor("Dangerous")
            agree = danger_poor > safe_poor
            risk_caption = _caption_box(
                f"Safe-classified days average {grp['Safe']:.0f}/100 on suitability; Dangerous days average "
                f"{grp['Dangerous']:.0f}/100. {danger_poor:.0f}% of Dangerous days also score below "
                f"{SUITABILITY_GOOD_MIN}/100 (a below-par beach day), versus {safe_poor:.0f}% of Safe days — "
                + ("the two verdicts track the same underlying weather, not unrelated things."
                   if agree else
                   "surprisingly little difference, meaning the two scores capture largely independent risk.")
            )
    else:
        risk_caption = _caption_box("Not enough overlapping Emergency/Tourism data to compare yet.")

    # --- Correlation heatmap + plain-language top pairs ---
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
        font=dict(family="Public Sans, Arial", color=TEXT, size=10),
        xaxis=dict(tickangle=-45),
    )

    pairs = []
    cols = list(corr.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = corr.iloc[i, j]
            if pd.notna(r):
                pairs.append((cols[i], cols[j], r))
    pairs.sort(key=lambda p: abs(p[2]), reverse=True)
    notable = [p for p in pairs[:4] if abs(p[2]) >= 0.3]
    if notable:
        sentences = [
            f"{COLUMN_LABELS.get(a, a)} and {COLUMN_LABELS.get(b, b)} "
            f"{'rise and fall together' if r > 0 else 'move in opposite directions'} (r = {r:.2f})."
            for a, b, r in notable
        ]
        corr_caption = _caption_box("Strongest relationships: " + " ".join(sentences))
    else:
        corr_caption = _caption_box("No strong (|r| ≥ 0.3) relationships stand out among these indicators.")

    return (
        monthly_fig, monthly_caption,
        location_fig, location_caption,
        high_list, low_list,
        risk_fig, risk_caption,
        corr_fig, corr_caption,
    )
