"""
pages/overview.py — landing page at "/".

Structure, top to bottom, deliberately in this order:
    1. Hero — explains what CoastalPulse IS before showing any numbers.
       Not location-dependent; this is product framing, not data.
    2. Audience navigation cards — "which view is for me".
    3. Per-location snapshot — explicitly labeled as being about the
       selected location, not a national summary. All Gold data in this
       project is location-wise (gold_emergency_daily/gold_tourism_daily
       are keyed by location_name), so this section is honest about that
       scope rather than presenting itself as a Sri-Lanka-wide overview.

This is still a first pass, not the final Overview build — but it's a
real front page now, not just three bare navigation buttons.
"""

import dash
from dash import html, dcc, callback, Input, Output

from data_access import get_emergency_data, get_tourism_data, get_fisherman_forecast, LOCATIONS
from page_helpers import CLASSIFICATION_COLORS, EMERGENCY_VERDICT_TEXT, score_band

dash.register_page(__name__, path="/", name="Overview")


# ============================================================
# HERO
# ============================================================

def _stat_chip(value, label):
    return html.Div(
        [
            html.Div(value, style={
                "fontFamily": "'Space Grotesk', sans-serif",
                "fontSize": "20px", "fontWeight": "700", "color": "#0b202a",
            }),
            html.Div(label, style={"fontSize": "11px", "color": "#72838c"}),
        ],
        style={"textAlign": "left"},
    )


hero = html.Div(
    [
        html.Div(
            [
                html.H2(
                    "Coastal conditions, translated into a decision \u2014 "
                    "not a chart.",
                    style={
                        "fontFamily": "'Space Grotesk', sans-serif",
                        "fontSize": "26px", "fontWeight": "600",
                        "letterSpacing": "-0.5px", "margin": "0 0 10px 0",
                        "maxWidth": "640px", "lineHeight": "1.25",
                    },
                ),
                html.P(
                    "CoastalPulse pulls marine, weather, and air-quality data "
                    "for 15 locations along Sri Lanka's coast and turns it "
                    "into a plain answer for whoever's asking \u2014 a tourist "
                    "checking the beach, a resident tracking a storm, or a "
                    "fisherman deciding whether to go out.",
                    style={"fontSize": "13.5px", "color": "#72838c",
                           "maxWidth": "560px", "lineHeight": "1.6", "margin": "0"},
                ),
            ]
        ),
        html.Div(
            [
                _stat_chip("15", "Locations monitored"),
                _stat_chip("3", "Modes \u2014 Emergency, Tourism, Fisherman"),
                _stat_chip("Daily", "Data refresh"),
            ],
            style={"display": "flex", "gap": "36px", "marginTop": "22px"},
        ),
    ],
    style={
        "padding": "28px 30px",
        "background": "#ffffff",
        "border": "1px solid #dce5e9",
        "borderRadius": "10px",
        "marginBottom": "28px",
    },
)


# ============================================================
# AUDIENCE NAVIGATION CARDS
# ============================================================

_CARD_STYLE = {
    "display": "block",
    "padding": "24px",
    "border": "1px solid #dce5e9",
    "borderRadius": "8px",
    "background": "#ffffff",
    "textAlign": "left",
    "color": "#0b202a",
}

_CARD_TITLE_STYLE = {
    "fontFamily": "'Space Grotesk', sans-serif",
    "fontSize": "17px",
    "fontWeight": "600",
    "marginBottom": "6px",
}

_CARD_DESC_STYLE = {
    "fontSize": "13px",
    "color": "#72838c",
}


def _audience_card(emoji, title, description, href):
    return dcc.Link(
        html.Div(
            [
                html.Div(emoji, style={"fontSize": "26px", "marginBottom": "12px"}),
                html.Div(title, style=_CARD_TITLE_STYLE),
                html.Div(description, style=_CARD_DESC_STYLE),
            ],
            style=_CARD_STYLE,
            className="cp-card",
        ),
        href=href,
        style={"textDecoration": "none"},
    )


nav_cards = html.Div(
    [
        html.Div(
            "Not sure which view you need? Pick the one that matches you:",
            style={"marginBottom": "14px", "color": "#0b202a", "fontSize": "14px", "fontWeight": "600"},
        ),
        html.Div(
            [
                _audience_card(
                    "\U0001F3D6\uFE0F", "I'm visiting the beach",
                    "Beach conditions and whether today is a good day to go.",
                    "/tourism",
                ),
                _audience_card(
                    "\u26A0\uFE0F", "I live here",
                    "Current coastal risk and hazard status for your area.",
                    "/emergency",
                ),
                _audience_card(
                    "\U0001F41F", "I'm going fishing",
                    "Marine conditions and forecast for fishing decisions.",
                    "/fisherman",
                ),
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": "repeat(auto-fit, minmax(220px, 1fr))",
                "gap": "18px",
            },
        ),
    ],
    style={"marginBottom": "28px"},
)


# ============================================================
# PER-LOCATION SNAPSHOT
# ============================================================
# Explicitly scoped: every Gold table in this project is keyed by
# location_name, so there is no real "all of Sri Lanka" number to show
# here honestly. This section is titled and worded to make clear it's
# about the one selected location, not a national summary.

def _mini_verdict_card(icon, title, badge_text, badge_color, sentence, href):
    return dcc.Link(
        html.Div(
            [
                html.Div(
                    [
                        html.Span(icon, style={"fontSize": "18px", "marginRight": "8px"}),
                        html.Span(title, style={"fontWeight": "600", "fontSize": "13px"}),
                    ],
                    style={"marginBottom": "10px"},
                ),
                html.Span(
                    badge_text,
                    style={
                        "backgroundColor": badge_color, "color": "white",
                        "padding": "3px 10px", "borderRadius": "4px",
                        "fontSize": "11px", "fontWeight": "700",
                    },
                ),
                html.Div(sentence, style={"marginTop": "8px", "fontSize": "12.5px", "color": "#4a5a63"}),
            ],
            style={**_CARD_STYLE, "padding": "18px"},
            className="cp-card",
        ),
        href=href,
        style={"textDecoration": "none"},
    )


snapshot_section = html.Div(
    [
        html.Div(
            id="overview-snapshot-title",
            style={"fontSize": "14px", "fontWeight": "600", "marginBottom": "4px"},
        ),
        html.Div(
            "Location-specific \u2014 switch location above to see a different area.",
            style={"fontSize": "11px", "color": "#9aa8ae", "marginBottom": "14px"},
        ),
        html.Div(
            id="overview-snapshot-cards",
            style={
                "display": "grid",
                "gridTemplateColumns": "repeat(auto-fit, minmax(220px, 1fr))",
                "gap": "14px",
            },
        ),
    ]
)


layout = html.Div(
    [
        hero,
        nav_cards,
        html.Div(snapshot_section, className="cp-verdict-zone"),
    ]
)


@callback(
    Output("overview-snapshot-title", "children"),
    Output("overview-snapshot-cards", "children"),
    Input("selected-location", "data"),
)
def update_overview_snapshot(location):
    if not location:
        return "Today's snapshot", []

    title = f"Today's snapshot \u2014 {location}"
    cards = []

    # --- Emergency mini-verdict --------------------------------------
    em_df = get_emergency_data(location)
    if not em_df.empty:
        latest = em_df.iloc[-1]
        status = latest.get("classification", "Unknown")
        color = CLASSIFICATION_COLORS.get(status, "#999")
        sentence = EMERGENCY_VERDICT_TEXT.get(status, "conditions unknown")
        cards.append(_mini_verdict_card("\u26A0\uFE0F", "Emergency", status, color, sentence, "/emergency"))
    else:
        cards.append(_mini_verdict_card("\u26A0\uFE0F", "Emergency", "No data", "#999", "", "/emergency"))

    # --- Tourism mini-verdict ------------------------------------------
    tm_df = get_tourism_data(location)
    if not tm_df.empty:
        latest = tm_df.iloc[-1]
        score = latest.get("suitability_score")
        label, color = score_band(score)
        badge = f"{score:.0f}/100" if score is not None else "\u2014"
        cards.append(_mini_verdict_card("\U0001F3D6\uFE0F", "Tourism", badge, color, label, "/tourism"))
    else:
        cards.append(_mini_verdict_card("\U0001F3D6\uFE0F", "Tourism", "No data", "#999", "", "/tourism"))

    # --- Fisherman mini-verdict (still mock data — say so) --------------
    fc_df = get_fisherman_forecast(location)
    if not fc_df.empty:
        cards.append(
            _mini_verdict_card(
                "\U0001F41F", "Fisherman", "Preview", "#999",
                "Forecast model not built yet \u2014 showing placeholder data.",
                "/fisherman",
            )
        )
    else:
        cards.append(_mini_verdict_card("\U0001F41F", "Fisherman", "No data", "#999", "", "/fisherman"))

    return title, cards