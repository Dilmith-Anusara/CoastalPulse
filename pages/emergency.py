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
from design_system import (
    BG, CARD, TEXT, MUTED, BORDER, NAVY, NAVY_2, LIVE_COLOR, LIVE_BG,
    ACCENT_BLUE, ACCENT_PURPLE, ACCENT_PINK, ACCENT_ORANGE,
    PAGE_STYLE, HERO_STYLE, CARD_STYLE, VERDICT_ZONE_CLASS, DETAIL_ZONE_CLASS,
    section_title, metric_card, chart_card, day_pill, day_strip_grid, empty_chart,
)

# Emergency-specific chart-line accent aliases (kept as separate names for
# readability at call sites, pulled from the shared accent palette so the
# actual color values still live in one place).
WAVE_LINE = ACCENT_BLUE
WIND_LINE = ACCENT_PURPLE
GUST_LINE = ACCENT_PINK
PRESSURE_LINE = ACCENT_ORANGE

# ------------------------------------------------------------
# Shared classification styling — pulled from page_helpers so this
# page never re-defines Safe/Caution/Dangerous colors or copy on its
# own. If page_helpers.py doesn't yet export these two names, or
# exports them in a different shape, the fallback below keeps the
# page working with the same shape until you align it. TODO once
# you share page_helpers.py: delete the fallback and confirm the
# import matches exactly.
# ------------------------------------------------------------

_FALLBACK_CLASSIFICATION_COLORS = {
    "safe": {"color": "#18A673", "light": "#E8F7F1"},
    "caution": {"color": "#F59E0B", "light": "#FFF5DD"},
    "dangerous": {"color": "#E34D59", "light": "#FDEBED"},
    "unknown": {"color": "#71828C", "light": "#EEF2F4"},
}

_FALLBACK_EMERGENCY_VERDICT_TEXT = {
    "safe": "It's a good day to be near the coast. Conditions are calm.",
    "caution": "Take some care today — the sea is a little rough near this coast.",
    "dangerous": "Stay away from the coast right now. Conditions are dangerous.",
    "unknown": "We don't have a recent reading for this location.",
}

try:
    from page_helpers import CLASSIFICATION_COLORS, EMERGENCY_VERDICT_TEXT

    if not isinstance(CLASSIFICATION_COLORS, dict) or not isinstance(EMERGENCY_VERDICT_TEXT, dict):
        raise TypeError("page_helpers exports found but not in the expected dict shape")
except Exception as exc:
    print(f"[emergency.py] Could not use page_helpers styling ({exc}); using local fallback.")
    CLASSIFICATION_COLORS = _FALLBACK_CLASSIFICATION_COLORS
    EMERGENCY_VERDICT_TEXT = _FALLBACK_EMERGENCY_VERDICT_TEXT


def _lookup(mapping, raw_key):
    """Try a raw classification string against a mapping under a few
    common casings (page_helpers.py's real keys might be "Safe",
    "safe", or something else entirely). Returns None on a total miss
    instead of ever raising — callers fall back to a safe default.
    """
    if not isinstance(mapping, dict):
        return None
    for candidate in (raw_key, raw_key.lower(), raw_key.capitalize(), raw_key.upper()):
        if candidate in mapping:
            return mapping[candidate]
    return None


def classification_style(classification):
    """Single place that turns a raw classification string into
    (color, light_color, plain_language_sentence). Nothing else in
    this file should hardcode Safe/Caution/Dangerous colors or copy.
    Never raises, regardless of what page_helpers.py actually contains
    — falls back to the local defaults on any miss or shape mismatch.
    """
    raw = str(classification or "Unknown").strip()
    key = raw.lower()

    colors = _lookup(CLASSIFICATION_COLORS, raw)
    if colors is None:
        colors = _FALLBACK_CLASSIFICATION_COLORS.get(key, _FALLBACK_CLASSIFICATION_COLORS["unknown"])

    verdict = _lookup(EMERGENCY_VERDICT_TEXT, raw)
    if verdict is None:
        verdict = _FALLBACK_EMERGENCY_VERDICT_TEXT.get(key, _FALLBACK_EMERGENCY_VERDICT_TEXT["unknown"])

    # colors might be a plain hex string instead of a {"color","light"}
    # dict, depending on the real page_helpers.py shape — handle both.
    if isinstance(colors, dict):
        color = colors.get("color") or colors.get("light") or MUTED
        light = colors.get("light") or colors.get("color") or "#EEF2F4"
    else:
        color = colors or MUTED
        light = "#EEF2F4"

    return color, light, verdict


# Provisional wave-height bands used to draw the gauge. These match the
# reconstructed Gold-layer thresholds (Safe <2.0m, Caution 2.0-3.0m,
# Dangerous >3.0m) — not yet validated against real judgement, per the
# open item in the CoastalPulse handoff. Move this next to
# CLASSIFICATION_COLORS in page_helpers.py once it's settled so the
# gauge and the Gold-layer classification can't drift apart.
WAVE_GAUGE_MAX = 5.0
WAVE_SAFE_MAX = 2.0
WAVE_CAUTION_MAX = 3.0

# How many of the most recent days to plot in the trend charts. The Gold
# table holds ~1.5 years of history per location, but a 500+ point line
# chart is unreadable and isn't what "is it safe right now" needs — the
# rest of the history is used for HISTORY_MIN_ROWS-gated context below
# instead of being plotted.
CHART_WINDOW_DAYS = 30

# Minimum rows of history required before showing a rarity comparison —
# below this a percentile isn't meaningful.
HISTORY_MIN_ROWS = 30


def history_context_text(history_wave_series, current_wave, location_label):
    """One sentence putting today's wave height in the context of the
    full history for this location, instead of spending that history on
    an unreadable long line chart. Returns "" when there isn't enough
    history or data to say anything meaningful.
    """
    if current_wave is None or pd.isna(current_wave):
        return ""

    valid = history_wave_series.dropna()
    if len(valid) < HISTORY_MIN_ROWS:
        return ""

    percentile = (valid <= current_wave).mean() * 100

    if percentile >= 95:
        return f"This is among the roughest days recorded at {location_label} — higher than {percentile:.0f}% of days on record."
    if percentile >= 70:
        return f"Higher than {percentile:.0f}% of days recorded at {location_label}."
    if percentile <= 30:
        return f"Calmer than usual — lower than {100 - percentile:.0f}% of days recorded at {location_label}."
    return f"Fairly typical for {location_label} — around the middle of the range recorded here."


# ============================================================
# PAGE CONFIG
# ============================================================

dash.register_page(
    __name__,
    path="/emergency",
    name="Emergency",
)


# ============================================================
# EMERGENCY-SPECIFIC HELPERS (gauge, map hover text — not shared
# with other pages, so these stay local rather than going into
# design_system.py)
# ============================================================

def empty_gauge():
    fig = go.Figure(go.Indicator(mode="gauge", value=0))
    fig.update_layout(
        paper_bgcolor=CARD,
        margin=dict(l=20, r=20, t=20, b=0),
        height=180,
    )
    return fig


def empty_map():
    fig = go.Figure()

    fig.update_layout(
        map=dict(
            style="open-street-map",
            center=dict(lat=7.5, lon=80.7),
            zoom=6,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor=CARD,
    )

    return fig


def wave_gauge_figure(wave_value, status_color):
    """Wave-height gauge with Safe / Caution / Dangerous bands — the
    one number people can actually picture ("how big are the
    waves"), rather than a plain progress bar.
    """
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=float(wave_value) if pd.notna(wave_value) else 0,
            number={"suffix": " m", "font": {"size": 26, "color": "white"}},
            gauge={
                "axis": {
                    "range": [0, WAVE_GAUGE_MAX],
                    "tickcolor": "#8EA6B0",
                    "tickfont": {"color": "#8EA6B0", "size": 10},
                },
                "bar": {"color": status_color, "thickness": 0.42},
                "bgcolor": "rgba(255,255,255,0.06)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, WAVE_SAFE_MAX], "color": "rgba(24,166,115,0.55)"},
                    {"range": [WAVE_SAFE_MAX, WAVE_CAUTION_MAX], "color": "rgba(245,158,11,0.55)"},
                    {"range": [WAVE_CAUTION_MAX, WAVE_GAUGE_MAX], "color": "rgba(227,77,89,0.55)"},
                ],
            },
        )
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=16, r=16, t=16, b=8),
        height=190,
        font=dict(color="white"),
    )

    return fig


def map_hover_text(location_name, classification, wave):
    """Single place building map marker hover text — replaces the
    old inline ternary-with-implicit-concatenation, which worked but
    was easy to misread.
    """
    lines = [f"<b>{location_name}</b>", f"Risk: {classification}"]

    if pd.notna(wave):
        lines.append(f"Wave: {wave:.2f} m")

    return "<br>".join(lines)


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
                            "See if it's safe to go near the sea today.",
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
                            style={
                                "width": "7px",
                                "height": "7px",
                                "borderRadius": "50%",
                                "backgroundColor": LIVE_COLOR,
                                "marginRight": "7px",
                            }
                        ),
                        html.Span(
                            "LIVE DATA",
                            style={
                                "fontSize": "10px",
                                "fontWeight": "750",
                                "letterSpacing": "0.8px",
                                "color": LIVE_COLOR,
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "padding": "9px 12px",
                        "backgroundColor": LIVE_BG,
                        "borderRadius": "20px",
                    },
                ),
            ],
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "marginBottom": "34px",
                "gap": "24px",
            },
        ),

        # ----------------------------------------------------
        # VERDICT ZONE — always visible. Plain language + gauge +
        # 7-day strip. Nothing here requires reading a number.
        # ----------------------------------------------------
        html.Div(
            [
                # --- hero: sentence + gauge ---
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
                                        "marginBottom": "20px",
                                    },
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            id="emergency-location-title",
                                            style={
                                                "fontSize": "24px",
                                                "fontWeight": "750",
                                                "color": "white",
                                            },
                                        ),
                                        html.Div(
                                            id="emergency-status-badge",
                                            style={"marginLeft": "14px"},
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "flexWrap": "wrap",
                                        "rowGap": "10px",
                                    },
                                ),
                                html.Div(
                                    id="emergency-verdict",
                                    style={
                                        "fontSize": "18px",
                                        "fontWeight": "600",
                                        "lineHeight": "1.7",
                                        "color": "white",
                                        "marginTop": "18px",
                                        "maxWidth": "480px",
                                    },
                                ),
                                html.Div(
                                    id="emergency-history-note",
                                    style={
                                        "fontSize": "13px",
                                        "lineHeight": "1.6",
                                        "color": "#B8C9CF",
                                        "marginTop": "10px",
                                        "maxWidth": "480px",
                                    },
                                ),
                                html.Div(
                                    id="emergency-updated",
                                    style={
                                        "fontSize": "11px",
                                        "color": "#718991",
                                        "marginTop": "22px",
                                    },
                                ),
                            ],
                            style={"flex": "1"},
                        ),
                        html.Div(
                            [
                                html.Div(
                                    "WAVE HEIGHT",
                                    style={
                                        "fontSize": "10px",
                                        "fontWeight": "700",
                                        "letterSpacing": "1px",
                                        "color": "#8EA6B0",
                                        "textAlign": "center",
                                        "marginBottom": "10px",
                                    },
                                ),
                                dcc.Graph(
                                    id="emergency-gauge",
                                    config={"displayModeBar": False},
                                    style={"height": "190px", "width": "240px"},
                                ),
                            ],
                            style={"minWidth": "240px"},
                        ),
                    ],
                    style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center",
                        "gap": "40px",
                        "background": f"linear-gradient(135deg, {NAVY}, {NAVY_2})",
                        "borderRadius": "18px",
                        "padding": "36px 40px",
                        "marginBottom": "24px",
                        "boxShadow": "0 8px 24px rgba(11,32,42,0.12)",
                    },
                ),

                # --- 7-day plain-language strip ---
                html.Div(
                    [
                        section_title(
                            "Last 7 days",
                            "How conditions looked recently at this location.",
                        ),
                        html.Div(
                            id="emergency-day-strip",
                            style={
                                "display": "grid",
                                "gridTemplateColumns": "repeat(7, minmax(0, 1fr))",
                                "gap": "14px",
                            },
                        ),
                    ],
                    style={
                        "backgroundColor": CARD,
                        "border": f"1px solid {BORDER}",
                        "borderRadius": "16px",
                        "padding": "28px",
                        "boxShadow": "0 2px 8px rgba(15, 45, 58, 0.035)",
                    },
                ),
            ],
            className="cp-verdict-zone",
        ),

        html.Div(style={"height": "8px"}),

        # ----------------------------------------------------
        # DETAIL ZONE — hidden until the header's global "Show
        # details" switch is on (app.py toggles this purely via
        # the shared .cp-detail-zone CSS class — no per-page
        # show/hide logic, same mechanism Tourism uses). Raw
        # metric cards, both charts, and the map: the part meant
        # for people who want the underlying data, not the
        # default view.
        # ----------------------------------------------------
        html.Div(
            [
                html.Div(
                    [
                        metric_card("≈", "Maximum wave height", html.Span(id="emergency-wave-value"), "m", WAVE_LINE),
                        metric_card("≋", "Maximum wind speed", html.Span(id="emergency-wind-value"), "km/h", WIND_LINE),
                        metric_card("↯", "Maximum wind gust", html.Span(id="emergency-gust-value"), "km/h", GUST_LINE),
                        metric_card("P", "Minimum pressure", html.Span(id="emergency-pressure-value"), "hPa", PRESSURE_LINE),
                        metric_card("◉", "Days recorded", html.Span(id="emergency-observation-value"), "", LIVE_COLOR),
                    ],
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(auto-fit, minmax(180px, 1fr))",
                        "gap": "18px",
                        "marginBottom": "24px",
                    },
                ),

                chart_card(
                    "Wave height — last 30 days",
                    "Maximum observed wave height per day. Full history is used for the comparison note above, not plotted here.",
                    "emergency-wave-chart",
                    height=390,
                ),

                html.Div(style={"height": "24px"}),

                chart_card(
                    "Wind and pressure — last 30 days",
                    "Maximum wind speed and gust, and minimum atmospheric pressure.",
                    "emergency-wind-pressure-chart",
                    height=390,
                ),

                html.Div(style={"height": "24px"}),

                html.Div(
                    [
                        section_title(
                            "Sri Lanka coastal risk map",
                            "Geographical distribution of recorded coastal conditions.",
                        ),
                        dcc.Graph(
                            id="emergency-map",
                            config={"displayModeBar": False, "responsive": True},
                            style={"height": "560px"},
                        ),
                    ],
                    style={
                        "backgroundColor": CARD,
                        "border": f"1px solid {BORDER}",
                        "borderRadius": "16px",
                        "padding": "28px",
                        "boxShadow": "0 2px 8px rgba(15, 45, 58, 0.035)",
                    },
                ),
            ],
            className="cp-detail-zone",
        ),

        html.Div(style={"height": "36px"}),
    ],
    style={
        "backgroundColor": BG,
        "minHeight": "100vh",
        "padding": "36px 44px",
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
    Output("emergency-history-note", "children"),
    Output("emergency-updated", "children"),
    Output("emergency-gauge", "figure"),
    Output("emergency-wave-value", "children"),
    Output("emergency-wind-value", "children"),
    Output("emergency-gust-value", "children"),
    Output("emergency-pressure-value", "children"),
    Output("emergency-observation-value", "children"),
    Output("emergency-day-strip", "children"),
    Output("emergency-wave-chart", "figure"),
    Output("emergency-wind-pressure-chart", "figure"),
    Input("selected-location", "data"),
)
def update_emergency_page(location):

    # --------------------------------------------------------
    # No location selected yet (shared store not initialized) —
    # same guard as tourism.py's update_tourism_page.
    # --------------------------------------------------------
    if not location:
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
            "Choose a location",
            "Pick a location above to see coastal conditions.",
            "",
            "",
            empty_gauge(),
            "—",
            "—",
            "—",
            "—",
            "0",
            [],
            empty_chart(),
            empty_chart(),
        )

    # --------------------------------------------------------
    # Load data
    # --------------------------------------------------------
    try:
        df = get_emergency_data(location)
    except Exception:
        color, light, _ = classification_style("unknown")
        return (
            "ERROR",
            {
                "backgroundColor": light,
                "color": color,
                "padding": "7px 12px",
                "borderRadius": "20px",
                "fontSize": "11px",
                "fontWeight": "700",
            },
            location or "Unknown location",
            "We couldn't load data for this location right now.",
            "",
            "Data could not be retrieved.",
            empty_gauge(),
            "—",
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
        color, light, verdict = classification_style("unknown")
        return (
            "NO DATA",
            {
                "backgroundColor": light,
                "color": color,
                "padding": "7px 12px",
                "borderRadius": "20px",
                "fontSize": "11px",
                "fontWeight": "700",
            },
            location or "Unknown location",
            verdict,
            "",
            "No data available.",
            empty_gauge(),
            "—",
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
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
        data = data.sort_values("date")

    for col in ["wave_height_max", "wind_speed_max", "wind_gust_max", "pressure_min"]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    # --------------------------------------------------------
    # Current observation
    # --------------------------------------------------------
    current = data.iloc[-1]
    classification = str(current.get("classification", "Unknown"))

    wave = current.get("wave_height_max")
    wind = current.get("wind_speed_max")
    gust = current.get("wind_gust_max")
    pressure = current.get("pressure_min")

    observation_count = len(data)

    status_color, status_light, verdict = classification_style(classification)

    # Full history (before the chart window is applied below) used only
    # for the rarity comparison — this is the actual use of the ~1.5
    # years of data, instead of plotting all of it on one unreadable line.
    history_note = (
        history_context_text(data["wave_height_max"], wave, location or "this location")
        if "wave_height_max" in data.columns
        else ""
    )

    badge = html.Span(
        classification.upper(),
        style={"fontSize": "10px", "fontWeight": "800", "letterSpacing": "0.6px"},
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

    gauge_fig = wave_gauge_figure(wave, status_color)

    # --------------------------------------------------------
    # Formatting helpers
    # --------------------------------------------------------
    wave_value = f"{wave:.2f}" if pd.notna(wave) else "—"
    wind_value = f"{wind:.1f}" if pd.notna(wind) else "—"
    gust_value = f"{gust:.1f}" if pd.notna(gust) else "—"
    pressure_value = f"{pressure:.0f}" if pd.notna(pressure) else "—"

    if "date" in data.columns and pd.notna(current["date"]):
        updated_text = "Latest observation: " + current["date"].strftime("%d %b %Y")
    else:
        updated_text = "Latest observation available"

    # ========================================================
    # RECENT DAY STRIP — shared day_pill component (same visual
    # language as Tourism's 7-day strip)
    # ========================================================
    recent = data.tail(7).copy()
    day_cards = []

    for _, row in recent.iterrows():
        row_classification = str(row.get("classification", "Unknown"))
        dot_color, bg_color, _ = classification_style(row_classification)

        if pd.notna(row.get("date")):
            day_label = row["date"].strftime("%a")
            date_label = row["date"].strftime("%d %b")
        else:
            day_label = "—"
            date_label = "—"

        day_cards.append(day_pill(day_label, date_label, dot_color, bg_color, row_classification))

    # ========================================================
    # WAVE CHART — last CHART_WINDOW_DAYS only (full history is used
    # for the rarity comparison above instead)
    # ========================================================
    chart_data = data.tail(CHART_WINDOW_DAYS)

    if "date" in chart_data.columns and "wave_height_max" in chart_data.columns:
        wave_data = chart_data.dropna(subset=["date", "wave_height_max"])

        wave_fig = go.Figure()
        wave_fig.add_trace(
            go.Scatter(
                x=wave_data["date"],
                y=wave_data["wave_height_max"],
                mode="lines+markers",
                line=dict(color=WAVE_LINE, width=3),
                marker=dict(size=7, color=WAVE_LINE),
                fill="tozeroy",
                fillcolor="rgba(40,120,200,0.08)",
                hovertemplate="<b>%{x|%d %b %Y}</b><br>Wave height: %{y:.2f} m<extra></extra>",
            )
        )
        wave_fig.update_layout(
            paper_bgcolor=CARD,
            plot_bgcolor=CARD,
            margin=dict(l=45, r=20, t=10, b=45),
            font=dict(family="Inter, Arial", color=TEXT, size=11),
            xaxis=dict(showgrid=False, zeroline=False, showline=True, linecolor=BORDER, tickfont=dict(color=MUTED)),
            yaxis=dict(
                title="Wave height (m)",
                showgrid=True,
                gridcolor="#EDF1F3",
                zeroline=False,
                title_font=dict(size=11, color=MUTED),
                tickfont=dict(color=MUTED),
            ),
            hoverlabel=dict(bgcolor=NAVY, font_color="white"),
        )
    else:
        wave_fig = empty_chart()

    # ========================================================
    # WIND + GUST + PRESSURE CHART — same recent window as the wave chart
    # ========================================================
    if all(col in chart_data.columns for col in ["date", "wind_speed_max", "pressure_min"]):
        wp_data = chart_data.dropna(subset=["date", "wind_speed_max", "pressure_min"])

        wind_pressure_fig = go.Figure()
        wind_pressure_fig.add_trace(
            go.Scatter(
                x=wp_data["date"],
                y=wp_data["wind_speed_max"],
                mode="lines+markers",
                name="Wind speed",
                line=dict(color=WIND_LINE, width=3),
                marker=dict(size=7, color=WIND_LINE),
                hovertemplate="<b>%{x|%d %b %Y}</b><br>Wind: %{y:.1f} km/h<extra></extra>",
            )
        )
        if "wind_gust_max" in wp_data.columns and wp_data["wind_gust_max"].notna().any():
            wind_pressure_fig.add_trace(
                go.Scatter(
                    x=wp_data["date"],
                    y=wp_data["wind_gust_max"],
                    mode="lines",
                    name="Wind gust",
                    line=dict(color=GUST_LINE, width=2, dash="dot"),
                    hovertemplate="<b>%{x|%d %b %Y}</b><br>Gust: %{y:.1f} km/h<extra></extra>",
                )
            )
        wind_pressure_fig.add_trace(
            go.Scatter(
                x=wp_data["date"],
                y=wp_data["pressure_min"],
                mode="lines+markers",
                name="Pressure",
                yaxis="y2",
                line=dict(color=PRESSURE_LINE, width=3),
                marker=dict(size=7, color=PRESSURE_LINE),
                hovertemplate="<b>%{x|%d %b %Y}</b><br>Pressure: %{y:.0f} hPa<extra></extra>",
            )
        )
        wind_pressure_fig.update_layout(
            paper_bgcolor=CARD,
            plot_bgcolor=CARD,
            margin=dict(l=50, r=65, t=15, b=50),
            font=dict(family="Inter, Arial", color=TEXT, size=11),
            xaxis=dict(showgrid=False, zeroline=False, showline=True, linecolor=BORDER, tickfont=dict(color=MUTED)),
            yaxis=dict(
                title="Wind speed (km/h)",
                showgrid=True,
                gridcolor="#EDF1F3",
                zeroline=False,
                title_font=dict(size=11, color=WIND_LINE),
                tickfont=dict(color=MUTED),
            ),
            yaxis2=dict(
                title="Pressure (hPa)",
                overlaying="y",
                side="right",
                showgrid=False,
                zeroline=False,
                title_font=dict(size=11, color=PRESSURE_LINE),
                tickfont=dict(color=MUTED),
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1, font=dict(size=11, color=MUTED)),
            hoverlabel=dict(bgcolor=NAVY, font_color="white"),
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
        history_note,
        updated_text,
        gauge_fig,
        wave_value,
        wind_value,
        gust_value,
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
    Input("selected-location", "data"),
)
def update_emergency_map(selected_location):

    try:
        df = get_emergency_data()
    except Exception:
        return empty_map()

    if df is None or df.empty:
        return empty_map()

    data = df.copy()

    if "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
        data = data.sort_values("date")
        latest = data.groupby("location_name", as_index=False).tail(1).copy()
    else:
        latest = data.copy()

    fig = go.Figure()

    for classification in ["Safe", "Caution", "Dangerous"]:
        color, _, _ = classification_style(classification)

        group = latest[latest["classification"].astype(str).str.lower() == classification.lower()].copy()
        if group.empty:
            continue

        lats, lons, names, hover_text = [], [], [], []

        for _, row in group.iterrows():
            location_name = row.get("location_name", "")
            coords = LOCATION_COORDS.get(location_name)

            if coords is None:
                continue

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
            hover_text.append(map_hover_text(location_name, classification, row.get("wave_height_max")))

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
                marker=dict(size=13, color=color, opacity=0.9),
            )
        )

    if selected_location in LOCATION_COORDS:
        coords = LOCATION_COORDS[selected_location]
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
                    marker=dict(size=22, color="#102A36", opacity=0.22),
                    showlegend=False,
                )
            )
            fig.add_trace(
                go.Scattermap(
                    lat=[lat],
                    lon=[lon],
                    mode="markers",
                    hoverinfo="skip",
                    marker=dict(size=8, color="#102A36", opacity=1),
                    showlegend=False,
                )
            )

    fig.update_layout(
        map=dict(style="open-street-map", center=dict(lat=7.5, lon=80.7), zoom=6),
        margin=dict(l=0, r=0, t=0, b=0),
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
            font=dict(size=11, color=TEXT),
        ),
    )

    return fig