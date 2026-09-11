"""
pages/overview.py — landing page at "/".

Restyled to the approved design direction (see
design_mockup/overview_direction.html): navy hero forming one continuous
masthead with app.py's header, an asymmetric audience legend list instead
of a uniform card grid, and the per-location snapshot rebuilt as a dense
tide-table row list instead of three separate cards.

Scope note on the snapshot: it shows THREE ROWS (Emergency / Tourism /
Fisherman) for the ONE selected location — not a table of multiple
locations. The mockup's placeholder table happened to show several
locations to demonstrate the visual style, but the real scope decision
from earlier in this project still holds: every Gold table here is
location-wise, so this section must not read as a Sri-Lanka-wide summary.

Colors for the badges (Safe/Caution/Dangerous, suitability bands) still
come from page_helpers.py unchanged, so Overview's meaning matches
Emergency/Tourism exactly even before those pages get the same visual
treatment.

DESIGN PASS (this revision): the hero graphic's coral position-dot was a
flat 2.5px circle competing on equal footing with five wave-contour
lines of similar visual weight, so it read as a stray mark rather than
an intentional "you are here" marker echoing the brand dot. Gave it a
soft halo (a larger, low-opacity circle underneath) — same motif used
for map pins — without adding motion or new elements. No structural
change.
"""

import dash
from dash import html, dcc, callback, Input, Output

from data_access import get_emergency_data, get_tourism_data, get_fisherman_forecast
from page_helpers import CLASSIFICATION_COLORS, EMERGENCY_VERDICT_TEXT, score_band

dash.register_page(__name__, path="/", name="Overview")


# ============================================================
# HERO
# ============================================================

def _stat(value, label):
    return html.Div(
        [
            html.Div(value, className="cp-stat-num"),
            html.Div(label, className="cp-stat-label"),
        ],
        className="cp-stat",
    )


# Chart-contour wave lines — echoes the tide-table aesthetic used below
# rather than a generic decorative wave illustration. A single coral dot
# marks a position on the chart, same motif as the brand mark in the header.
# The dot now carries a soft low-opacity halo underneath it so it reads as
# a deliberate "you are here" marker rather than a stray mark competing
# with the wave-contour lines around it.
_HERO_GRAPHIC = dcc.Markdown(
    """<svg viewBox="0 0 560 500" preserveAspectRatio="xMidYMid slice" style="width:100%;height:100%;">
<path d="M0,90 C70,60 140,120 210,90 C280,60 350,120 420,90 C470,70 520,95 560,85" fill="none" stroke="#2C5457" stroke-width="1" opacity="0.55"/>
<path d="M0,170 C80,135 150,205 230,170 C300,140 370,205 440,170 C490,150 530,175 560,165" fill="none" stroke="#2C5457" stroke-width="1" opacity="0.4"/>
<path d="M0,250 C90,210 160,285 240,250 C310,220 380,285 450,250 C495,232 530,255 560,245" fill="none" stroke="#2C5457" stroke-width="1" opacity="0.55"/>
<path d="M0,330 C75,295 145,360 220,330 C290,300 360,360 435,330 C480,312 525,332 560,325" fill="none" stroke="#2C5457" stroke-width="1" opacity="0.35"/>
<path d="M0,405 C85,368 155,435 235,405 C305,378 375,435 445,405 C490,388 528,408 560,400" fill="none" stroke="#2C5457" stroke-width="1" opacity="0.5"/>
<circle cx="330" cy="250" r="5.5" fill="#D9622A" opacity="0.18"/>
<circle cx="330" cy="250" r="2.5" fill="#D9622A"/>
</svg>""",
    dangerously_allow_html=True,
)

hero = html.Div(
    [
        html.Div(
            [
                html.Div("Coastal intelligence \u2014 Sri Lanka", className="cp-hero-kicker"),
                html.H1("Coastal conditions, read the way a chart reads them."),
                html.P(
                    "CoastalPulse turns marine, weather, and air-quality data "
                    "for 15 coastal locations into one answer for whoever's "
                    "asking \u2014 a tourist checking the beach, a resident "
                    "tracking a storm, a fisherman deciding whether to go out."
                ),
                html.Div(
                    [
                        _stat("15", "Locations monitored"),
                        _stat("3", "Emergency \u00b7 Tourism \u00b7 Fisherman"),
                        _stat("Daily", "Data refresh"),
                    ],
                    className="cp-stat-strip",
                ),
            ],
            className="cp-hero-inner",
        ),
        html.Div(_HERO_GRAPHIC, className="cp-hero-graphic"),
    ],
    className="cp-hero",
)


# ============================================================
# AUDIENCE NAVIGATION (asymmetric legend list, not equal cards)
# ============================================================

def _audience_row(tag, title, description, href):
    return dcc.Link(
        html.Div(
            [
                html.Div(tag, className="cp-audience-tag"),
                html.Div([html.H3(title), html.P(description)]),
            ],
            className="cp-audience-row",
        ),
        href=href,
    )


nav_section = html.Div(
    [
        html.Div("Which view is for you", className="cp-section-title"),
        html.Div("Three ways to read the same coastline.", className="cp-section-sub"),
        html.Div(
            [
                _audience_row(
                    "Tourism", "Visiting the beach",
                    "Beach conditions and whether today is a good day to go.",
                    "/tourism",
                ),
                _audience_row(
                    "Emergency", "Living on the coast",
                    "Current risk and hazard status for your area.",
                    "/emergency",
                ),
                _audience_row(
                    "Fisherman", "Going out to fish",
                    "Marine conditions and forecast for the day ahead.",
                    "/fisherman",
                ),
            ],
            className="cp-audience-list",
        ),
    ],
    className="cp-section",
)


# ============================================================
# PER-LOCATION SNAPSHOT (tide-table style, one location, three
# rows — Emergency / Tourism / Fisherman)
# ============================================================

snapshot_section = html.Div(
    [
        html.Div(
            [
                html.Div(id="overview-snapshot-title", className="cp-section-title", style={"marginBottom": 0}),
                html.Div(id="overview-snapshot-scope", className="cp-snapshot-scope"),
            ],
            className="cp-snapshot-header",
        ),
        html.Div(
            "Location-specific \u2014 switch location in the header to see a different area.",
            className="cp-section-sub",
        ),
        html.Table(
            [
                html.Thead(html.Tr([html.Th("Mode"), html.Th("Status"), html.Th("Note")])),
                html.Tbody(id="overview-snapshot-rows"),
            ],
            className="cp-tide",
        ),
    ],
    className="cp-section",
)


layout = html.Div(
    [
        hero,
        nav_section,
        html.Div(snapshot_section, className="cp-verdict-zone"),
    ]
)


def _badge(text, color):
    return html.Span(text, className="cp-badge", style={"backgroundColor": color})


@callback(
    Output("overview-snapshot-title", "children"),
    Output("overview-snapshot-scope", "children"),
    Output("overview-snapshot-rows", "children"),
    Input("selected-location", "data"),
)
def update_overview_snapshot(location):
    if not location:
        return "Today's readings", "", []

    title = f"Today's readings \u2014 {location}"
    scope = "updated daily"
    rows = []

    # --- Emergency row --------------------------------------------------
    em_df = get_emergency_data(location)
    if not em_df.empty:
        latest = em_df.iloc[-1]
        status = latest.get("classification", "Unknown")
        color = CLASSIFICATION_COLORS.get(status, "#999")
        wave = latest.get("wave_height_max")
        note = EMERGENCY_VERDICT_TEXT.get(status, "conditions unknown")
        rows.append(
            html.Tr([
                html.Td("Emergency"),
                html.Td([
                    _badge(status, color), " ",
                    html.Span(f"{wave:.1f}m" if wave is not None else "\u2014", className="cp-mono cp-note-muted"),
                ]),
                html.Td(note, className="cp-note-muted"),
            ])
        )
    else:
        rows.append(html.Tr([html.Td("Emergency"), html.Td("No data"), html.Td("")]))

    # --- Tourism row ------------------------------------------------------
    tm_df = get_tourism_data(location)
    if not tm_df.empty:
        latest = tm_df.iloc[-1]
        score = latest.get("suitability_score")
        label, color = score_band(score)
        badge_text = f"{score:.0f}/100" if score is not None else "\u2014"
        rows.append(
            html.Tr([
                html.Td("Tourism"),
                html.Td(_badge(badge_text, color)),
                html.Td(label, className="cp-note-muted"),
            ])
        )
    else:
        rows.append(html.Tr([html.Td("Tourism"), html.Td("No data"), html.Td("")]))

    # --- Fisherman row (still mock data \u2014 say so) --------------------
    fc_df = get_fisherman_forecast(location)
    if not fc_df.empty:
        rows.append(
            html.Tr([
                html.Td("Fisherman"),
                html.Td(_badge("Preview", "#999")),
                html.Td("Forecast model not built yet \u2014 placeholder data.", className="cp-note-muted"),
            ])
        )
    else:
        rows.append(html.Tr([html.Td("Fisherman"), html.Td("No data"), html.Td("")]))

    return title, scope, rows