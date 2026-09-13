"""
design_system.py — shared visual tokens and layout components for every
CoastalPulse dashboard page (Emergency, Tourism, Fisherman, Analytics).

Overview and app.py's masthead were already restyled to the approved
"chart-paper" direction (navy masthead, cream paper, Fraunces/Public
Sans/IBM Plex Mono, hairline tide-table rows — see app.py's index_string
CSS for the canonical :root tokens this file mirrors). This file finishes
that migration for the other pages, replacing the earlier generic
SaaS-dashboard look it used to define: white rounded cards with soft
drop-shadows, a metric tile per stat with an emoji icon sitting in a
tinted colored square, and a different accent color per card ("rainbow
per tile"). That combination is one of the most recognizable
AI-generated-dashboard tells there is — the fix isn't more polish, it's
removing the decoration: no icon tiles, no per-card rainbow, no shadows,
mono numerals and hairline rules doing the work a card used to.

NOTE: this is layout/visual styling only. Business logic like
classification bands or suitability-score bands belongs in
page_helpers.py, not here.
"""

from dash import html, dcc
import plotly.graph_objects as go
import pandas as pd

# ------------------------------------------------------------
# Core tokens — mirrors app.py's CSS :root exactly (--navy, --paper,
# --paper-line, --teal, --slate, --ink) so Python-rendered styles (Dash
# callback outputs can't reference CSS custom properties directly) and
# CSS-rendered ones never drift apart.
# ------------------------------------------------------------

BG = "#F7F1E4"       # --paper
CARD = "#FFFFFF"
TEXT = "#16262C"     # --ink
MUTED = "#3A5A63"    # --slate
BORDER = "#E4DAC4"   # --paper-line

NAVY = "#0C2B3A"      # --navy
NAVY_2 = "#123B4C"    # a touch lighter — only for things that need subtle depth against navy; no gradients
TEAL = "#1E7F82"      # --teal
CORAL = "#D9622A"     # --coral — reserved for actual hazards/alerts, never decoration

LIVE_COLOR = "#4FAE7C"
LIVE_BG = "#E8F7F1"

PAGE_FONT = "Public Sans, Arial, sans-serif"
MONO_FONT = "IBM Plex Mono, monospace"

# Muted "chart pen" colors for distinguishing MULTIPLE DATA SERIES within
# one chart (e.g. wave vs. wind vs. gust vs. pressure on the same plot) —
# a legitimate, non-decorative use of color. This is a different thing
# from tinting a whole metric card by accent, which this file no longer
# does anywhere.
ACCENT_BLUE = "#3B6E8C"
ACCENT_TEAL = TEAL
ACCENT_ORANGE = "#C08A3E"
ACCENT_PINK = "#8C4A42"
ACCENT_PURPLE = "#5B6B8C"
ACCENT_GREEN = LIVE_COLOR

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

# Flat navy plate for an always-visible verdict — no gradient, no shadow,
# a restrained 4px radius (this is a plate sitting mid-page, not an
# edge-to-edge masthead like Overview's .cp-hero).
HERO_STYLE = {
    "display": "flex",
    "justifyContent": "space-between",
    "alignItems": "center",
    "gap": "40px",
    "backgroundColor": NAVY,
    "borderRadius": "4px",
    "padding": "36px 40px",
    "marginBottom": "24px",
}

# Matches Overview's .cp-card exactly: hairline border, small radius, no
# shadow — a chart is a bordered plate, not a floating card.
CARD_STYLE = {
    "backgroundColor": CARD,
    "border": f"1px solid {BORDER}",
    "borderRadius": "8px",
    "padding": "28px",
}


# ------------------------------------------------------------
# Shared components
# ------------------------------------------------------------

def section_title(title, subtitle=None):
    # Real <h3> (not a styled div) so it picks up app.py's global
    # `h1,h2,h3 { font-family: Fraunces }` rule for free — one less place
    # a heading style can drift from the rest of the app.
    children = [
        html.H3(
            title,
            style={"fontSize": "18px", "fontWeight": "500", "color": NAVY, "margin": "0 0 7px 0"},
        )
    ]
    if subtitle:
        children.append(
            html.Div(
                subtitle,
                style={"fontSize": "12.5px", "color": MUTED, "lineHeight": "1.6", "marginBottom": "22px"},
            )
        )
    return html.Div(children)


def badge_style(color):
    """Flat rectangular status badge — matches Overview's .cp-badge CSS
    class, reimplemented as a style dict for callback-driven Dash outputs
    (a CSS class alone can't carry a per-status color chosen at runtime).
    Not a rounded pill — pill badges read as a generic SaaS-notification
    default; a flat rectangle with a hairline inset ring reads closer to
    a chart-annotation tag.
    """
    return {
        "display": "inline-block",
        "backgroundColor": color,
        "color": "white",
        "padding": "3px 9px",
        "borderRadius": "2px",
        "fontSize": "11px",
        "fontWeight": "700",
        "textShadow": "0 1px 1px rgba(0,0,0,0.25)",
        "boxShadow": "inset 0 0 0 1px rgba(0,0,0,0.08)",
    }


def note_box(children, tone="default"):
    """A citation/disclaimer/insight callout. Deliberately just a hairline
    left rule over the page background, not a tinted rounded 'alert box'
    — that colored-background note card (soft yellow/teal fill, rounded
    corners) is one of the more recognizable AI-generated-dashboard
    tells, and Overview's own highlight banner never used it. `tone`
    picks the rule color only; the box never gets a background fill.
    """
    rule_color = {"default": BORDER, "alert": CORAL, "info": TEAL}.get(tone, BORDER)
    return html.Div(
        children,
        style={
            "borderLeft": f"3px solid {rule_color}",
            "paddingLeft": "16px",
            "fontSize": "13px",
            "color": TEXT,
            "lineHeight": "1.6",
        },
    )


def metric_card(icon, label, value, unit="", accent=ACCENT_TEAL, note=None):
    """A single reading, styled like a chart-annotation cell: a small-caps
    mono-ish label, a large IBM Plex Mono numeral, a hairline top rule.
    No card box, no shadow, no icon.

    `icon` is accepted for backward compatibility with existing call
    sites (Emergency/Tourism pass an emoji here) but deliberately never
    rendered — an emoji sitting in a tinted rounded square was the
    single biggest tell that this dashboard's look came from a
    generative-UI default rather than a considered design.

    `accent` now only tints a 2px left rule instead of an icon tile's
    background, so color stays a quiet signal rather than decoration —
    call sites can still pass a different accent per reading without it
    reading as an arbitrary rainbow.

    `value` can be either a plain string/number to render immediately, or
    a Dash component (e.g. html.Span(id=...)) a callback fills in later.
    """
    if isinstance(value, (str, int, float)):
        value_node = html.Span(
            str(value),
            style={
                "fontFamily": MONO_FONT, "fontSize": "21px", "fontWeight": "500",
                "color": NAVY, "letterSpacing": "-0.02em",
            },
        )
    else:
        value_node = value

    return html.Div(
        [
            html.Div(
                label,
                style={
                    "fontSize": "10.5px", "fontWeight": "600", "letterSpacing": "0.5px",
                    "textTransform": "uppercase", "color": MUTED, "marginBottom": "10px",
                },
            ),
            html.Div(
                [
                    value_node,
                    html.Span(unit, style={"fontSize": "11px", "color": MUTED, "marginLeft": "5px"}) if unit else None,
                ]
            ),
            html.Div(note, style={"fontSize": "11px", "color": MUTED, "marginTop": "7px"}) if note else None,
        ],
        style={
            "padding": "16px 18px",
            "borderLeft": f"2px solid {accent}",
            "borderTop": f"1px solid {BORDER}",
            "backgroundColor": CARD,
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
    """One column in a 7-day strip — a log-entry column (day, date, flat
    status badge) with a hairline left rule, not a bordered mini-card.
    `bg_color` is accepted for backward compatibility with existing call
    sites but no longer used as a background fill.
    """
    return html.Div(
        [
            html.Div(day_label, style={"fontSize": "10.5px", "fontWeight": "700", "letterSpacing": "0.3px", "textTransform": "uppercase", "color": TEXT, "marginBottom": "5px"}),
            html.Div(date_label, style={"fontFamily": MONO_FONT, "fontSize": "10.5px", "color": MUTED, "marginBottom": "14px"}),
            html.Span(badge_text, style=badge_style(dot_color)),
        ],
        style={"padding": "14px 14px 14px 12px", "borderLeft": f"1px solid {BORDER}"},
    )


def day_strip_grid(pills):
    return html.Div(
        pills,
        style={
            "display": "grid", "gridTemplateColumns": "repeat(7, minmax(0, 1fr))",
            "borderTop": f"1px solid {NAVY}",
        },
    )


def empty_chart(message="No data available"):
    fig = go.Figure()
    fig.add_annotation(
        text=message, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
        font=dict(size=14, color=MUTED, family=PAGE_FONT),
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
        paper_bgcolor=BG,
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
            number={"suffix": suffix, "font": {"size": 26, "color": "white", "family": MONO_FONT}},
            gauge={
                "axis": {
                    "range": [0, value_max],
                    "tickcolor": "#7C97A0",
                    "tickfont": {"color": "#7C97A0", "size": 10},
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
        font=dict(color="white", family=PAGE_FONT),
    )
    return fig
