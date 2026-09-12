"""
design_system.py — shared visual tokens and layout components for every
CoastalPulse dashboard page (Emergency, Tourism, Fisherman, Overview).

This exists because Emergency and Tourism were built with two completely
different, hand-rolled style systems (different colors, card radii,
fonts, icon styles). Rather than copy-pasting one page's hex codes into
the other — which just reproduces the same "duplicated styling logic"
bug class the project's own handoff already flagged for classification
colors — both pages import their tokens and card components from here.

NOTE: this is layout/visual styling only. Business logic like
classification bands or suitability-score bands belongs in
page_helpers.py, not here.
"""

from dash import html, dcc
import plotly.graph_objects as go
import pandas as pd

# ------------------------------------------------------------
# Core tokens — shared by every page
# ------------------------------------------------------------

BG = "#F4F7F9"
CARD = "#FFFFFF"
TEXT = "#102A36"
MUTED = "#71828C"
BORDER = "#E4EBEF"

NAVY = "#0B202A"
NAVY_2 = "#123746"

LIVE_COLOR = "#18A673"
LIVE_BG = "#E8F7F1"

PAGE_FONT = "Inter, Arial, sans-serif"

# Generic accent palette for chart lines / icon tiles, decoupled from any
# one page's domain meaning (Emergency's wave/wind/gust/pressure and
# Tourism's condition chips both just pick colors from here).
ACCENT_BLUE = "#2878C8"
ACCENT_PURPLE = "#7757D6"
ACCENT_PINK = "#B03A6B"
ACCENT_ORANGE = "#F59E0B"
ACCENT_TEAL = "#1E8A8A"
ACCENT_GREEN = "#18A673"

# CSS class names used by app.py's global "Show details" mechanism —
# defined once here so every page wraps its content in the same classes.
VERDICT_ZONE_CLASS = "cp-verdict-zone"
DETAIL_ZONE_CLASS = "cp-detail-zone"

PAGE_STYLE = {
    "backgroundColor": BG,
    "minHeight": "100vh",
    "padding": "36px 44px",
    "fontFamily": PAGE_FONT,
    "boxSizing": "border-box",
}

HERO_STYLE = {
    "display": "flex",
    "justifyContent": "space-between",
    "alignItems": "center",
    "gap": "40px",
    "background": f"linear-gradient(135deg, {NAVY}, {NAVY_2})",
    "borderRadius": "18px",
    "padding": "36px 40px",
    "marginBottom": "24px",
    "boxShadow": "0 8px 24px rgba(11,32,42,0.12)",
}

CARD_STYLE = {
    "backgroundColor": CARD,
    "border": f"1px solid {BORDER}",
    "borderRadius": "16px",
    "padding": "28px",
    "boxShadow": "0 2px 8px rgba(15, 45, 58, 0.035)",
}


# ------------------------------------------------------------
# Shared components
# ------------------------------------------------------------

def section_title(title, subtitle=None):
    children = [
        html.Div(
            title,
            style={"fontSize": "17px", "fontWeight": "700", "color": TEXT, "marginBottom": "7px"},
        )
    ]
    if subtitle:
        children.append(
            html.Div(
                subtitle,
                style={"fontSize": "12px", "color": MUTED, "lineHeight": "1.6", "marginBottom": "22px"},
            )
        )
    return html.Div(children)


def metric_card(icon, label, value, unit="", accent=ACCENT_BLUE, note=None):
    """A single stat tile. `value` can be either:
      - a plain string/number to render immediately (e.g. Tourism's
        plain-language condition chips), or
      - a Dash component such as html.Span(id="some-id") whose children a
        callback fills in later (e.g. Emergency's live-updating cards).

    `note`, if given, is a short muted caption under the value (e.g. a
    plain-language band like "Choppy" alongside a raw "1.2 m" reading).
    """
    if isinstance(value, (str, int, float)):
        value_node = html.Span(
            str(value),
            style={"fontSize": "22px", "fontWeight": "750", "color": TEXT, "letterSpacing": "-0.4px"},
        )
    else:
        value_node = value

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
                        style={"fontSize": "12px", "fontWeight": "600", "color": MUTED, "marginLeft": "10px"},
                    ),
                ],
                style={"display": "flex", "alignItems": "center", "marginBottom": "18px"},
            ),
            html.Div(
                [
                    value_node,
                    html.Span(unit, style={"fontSize": "12px", "fontWeight": "600", "color": MUTED, "marginLeft": "6px"})
                    if unit
                    else None,
                ]
            ),
            html.Div(note, style={"fontSize": "11px", "color": MUTED, "marginTop": "8px"}) if note else None,
        ],
        style={
            "backgroundColor": CARD,
            "border": f"1px solid {BORDER}",
            "borderRadius": "15px",
            "padding": "24px",
            "boxShadow": "0 2px 8px rgba(15, 45, 58, 0.035)",
        },
    )


def chart_card(title, subtitle, graph_id, height=400):
    return html.Div(
        [
            section_title(title, subtitle),
            dcc.Graph(
                id=graph_id,
                config={"displayModeBar": False, "responsive": True},
                style={"height": f"{height}px"},
            ),
        ],
        style=CARD_STYLE,
    )


def day_pill(day_label, date_label, dot_color, bg_color, badge_text):
    """One tile in a 7-day strip — used by both Emergency (classification
    label) and Tourism (score-band label) so the strips look identical.
    """
    return html.Div(
        [
            html.Div(day_label, style={"fontSize": "11px", "fontWeight": "700", "color": TEXT, "marginBottom": "5px"}),
            html.Div(date_label, style={"fontSize": "10px", "color": MUTED, "marginBottom": "14px"}),
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
                    html.Span(badge_text, style={"fontSize": "10px", "fontWeight": "700", "color": dot_color}),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "padding": "6px 9px",
                    "borderRadius": "8px",
                    "backgroundColor": bg_color,
                    "width": "fit-content",
                },
            ),
        ],
        style={"padding": "16px", "border": f"1px solid {BORDER}", "borderRadius": "11px", "backgroundColor": "#FBFCFD"},
    )


def day_strip_grid(pills):
    return html.Div(
        pills,
        style={"display": "grid", "gridTemplateColumns": "repeat(7, minmax(0, 1fr))", "gap": "14px"},
    )


def empty_chart(message="No data available"):
    fig = go.Figure()
    fig.add_annotation(
        text=message, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
        font=dict(size=14, color=MUTED),
    )
    fig.update_layout(
        paper_bgcolor=CARD, plot_bgcolor=CARD,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig


def empty_map():
    fig = go.Figure()
    fig.update_layout(
        map=dict(style="open-street-map", center=dict(lat=7.5, lon=80.7), zoom=6),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor=CARD,
    )
    return fig


def stat_gauge_figure(value, value_max, bar_color, steps, suffix="", height=190):
    """Generic 0..value_max gauge with colored bands — used for any
    single-number visual indicator (Emergency's wave height, Tourism's
    suitability score) so both pages share one gauge implementation
    instead of two copies of the same go.Indicator boilerplate.

    `steps` is a list of {"range": [lo, hi], "color": "rgba(...)"} dicts
    — the band thresholds themselves are page-specific business judgment
    and stay in each page, only the rendering is shared here.
    """
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=float(value) if pd.notna(value) else 0,
            number={"suffix": suffix, "font": {"size": 26, "color": "white"}},
            gauge={
                "axis": {
                    "range": [0, value_max],
                    "tickcolor": "#8EA6B0",
                    "tickfont": {"color": "#8EA6B0", "size": 10},
                },
                "bar": {"color": bar_color, "thickness": 0.42},
                "bgcolor": "rgba(255,255,255,0.06)",
                "borderwidth": 0,
                "steps": steps,
            },
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=16, r=16, t=16, b=8),
        height=height,
        font=dict(color="white"),
    )
    return fig