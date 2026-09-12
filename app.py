"""
CoastalPulse
Coastal Intelligence & Decision Support Platform

Main application shell — restyled to the approved design direction
(navy masthead, paper content, Fraunces / Public Sans / IBM Plex Mono),
replacing the earlier generic SaaS-dashboard look. Fraunces + Public Sans
replaced the original Source Serif 4 / IBM Plex Sans pairing, which read
as a generic AI-generated-dashboard default rather than something a
human designer picked.

Routes:
    /            -> pages/overview.py    (supplies its own hero — see below)
    /emergency   -> pages/emergency.py   (must register path="/emergency")
    /tourism     -> pages/tourism.py
    /fisherman   -> pages/fisherman.py

Two contracts every page must still honor (unchanged from before):

1. ROUTING — a page registering the wrong path will 404 or collide with
   another page even though the nav looks right.

2. VERDICT / DETAIL SPLIT — plain-language status goes in a container
   with className="cp-verdict-zone" (always visible); charts/trends go
   in className="cp-detail-zone" (hidden until the header's "Show
   details" switch is on). One CSS rule keyed off the app-root class
   controls this everywhere — no per-page show/hide logic.

NOTE on scope: only app.py and pages/overview.py have been restyled to
the new design direction so far. Emergency, Tourism, and Fisherman still
use the older look — they'll need the same treatment for the whole app
to feel consistent. The badge colors used here (Safe/Caution/Dangerous,
suitability bands) intentionally still come from page_helpers.py
unchanged, so Overview's colors match Emergency/Tourism's *meaning*
exactly even though the visual chrome around them hasn't caught up yet.

DESIGN PASS (this revision): fixed a handful of visual issues that
survived the initial restyle — dead hover state on audience rows, no
keyboard focus states anywhere, badge text contrast not guaranteed
against arbitrary classification colors, hero graphic potentially
colliding with hero copy at tablet widths, and hard-coded ALL-CAPS
strings in Python instead of letting CSS own that styling decision
(text-transform), which also keeps the underlying content sentence-case
for anything that reads the raw string (e.g. screen readers navigating
by text, or logging). No structural/behavioral changes.
"""

import os

import dash
from dash import Dash, html, dcc, Input, Output, State, callback

from data_access import LOCATIONS, get_last_updated


# ============================================================
# APP
# ============================================================

dash_app = Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    suppress_callback_exceptions=True,
)

dash_app.title = "CoastalPulse"

# WSGI entry point a production server runs instead of Dash's own dev
# server. Dash apps are Flask apps underneath. Named literally `app` (not
# `server`) because Vercel's zero-config Flask detection looks for a
# Flask instance named `app` in app.py — using that exact name avoids
# needing a custom pyproject.toml entrypoint, which pulled in a whole
# separate uv/PEP-621 dependency-resolution path we don't want (we
# already have requirements.txt as the single source of truth for deps).
app = dash_app.server


# ============================================================
# GLOBAL CSS
# ============================================================

dash_app.index_string = """
<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link
        href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Public+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap"
        rel="stylesheet"
    >

    <style>

        /* ==================================================
           PALETTE / RESET

           Deep tide navy + chart-paper cream, ocean teal accent,
           warning coral — replaces the earlier generic cool-grey
           SaaS palette. See design_mockup/overview_direction.html
           for the approved reference.
        ================================================== */

        :root {
            --navy: #0C2B3A;
            --paper: #F7F1E4;
            --paper-line: #E4DAC4;
            --teal: #1E7F82;
            --teal-deep: #145558;
            --coral: #D9622A;
            --slate: #3A5A63;
            --ink: #16262C;
        }

        * {
            box-sizing: border-box;
        }

        html {
            background: var(--paper);
        }

        body {
            margin: 0;
            padding: 0;
            background: var(--paper);
            color: var(--ink);
            font-family: "Public Sans", Arial, sans-serif;
        }

        a {
            text-decoration: none;
        }

        button,
        input,
        select,
        textarea {
            font-family: inherit;
        }

        h1, h2, h3 {
            font-family: "Fraunces", serif;
            font-weight: 500;
        }


        /* ==================================================
           FOCUS STATES (app-wide)

           Nothing in the previous pass had a visible focus ring —
           nav links, the detail switch, the location dropdown all
           went silent on keyboard focus. Coral matches the brand
           mark / hero position-dot, so it reads as "here" rather
           than a generic browser blue.
        ================================================== */

        a:focus-visible,
        .cp-nav-link:focus-visible {
            outline: 2px solid var(--coral);
            outline-offset: 3px;
            border-radius: 2px;
        }

        .cp-switch:focus-visible {
            outline: 2px solid var(--coral);
            outline-offset: 3px;
        }

        .cp-location-dropdown .Select-control:focus-within {
            border-bottom-color: var(--coral) !important;
        }


        /* ==================================================
           APP
        ================================================== */

        .cp-app {
            min-height: 100vh;
            background: var(--paper);
        }


        /* ==================================================
           HEADER (masthead — navy, matches the hero below it
           on Overview so the two form one continuous dark
           zone rather than two disconnected bars)
        ================================================== */

        .cp-header {
            width: 100%;
            background: var(--navy);
            border-bottom: 1px solid rgba(255,255,255,0.1);

            display: flex;
            align-items: center;
            justify-content: space-between;

            padding: 16px 42px;

            position: sticky;
            top: 0;
            z-index: 1000;
        }


        /* ==================================================
           BRAND
        ================================================== */

        .cp-brand {
            display: flex;
            align-items: center;
            gap: 8px;

            font-family: "Fraunces", serif;
            font-weight: 600;
            font-size: 17px;
            color: var(--paper);
        }

        .cp-brand-mark {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--coral);
            display: inline-block;
        }


        /* ==================================================
           NAVIGATION
        ================================================== */

        .cp-navigation {
            display: flex;
            align-items: center;
            gap: 30px;
        }

        .cp-nav-link {
            font-size: 13px;
            font-weight: 500;
            color: #8FB8BA;

            padding-bottom: 4px;
            border-bottom: 2px solid transparent;

            transition: color 0.15s ease, border-color 0.15s ease;
        }

        .cp-nav-link:hover {
            color: var(--paper);
        }

        .cp-nav-link.active {
            color: var(--paper);
            font-weight: 600;
            border-bottom-color: var(--teal);
        }


        /* ==================================================
           HEADER RIGHT
        ================================================== */

        .cp-header-right {
            display: flex;
            align-items: center;
            gap: 24px;
        }


        /* ==================================================
           FRESHNESS INDICATOR
           A dot + mono readout, not a boxed pill — matches the
           understated masthead style. Only the dot color carries
           meaning (fresh/stale/unknown); text stays neutral.
        ================================================== */

        .cp-freshness {
            display: flex;
            align-items: center;
            gap: 6px;

            font-family: "IBM Plex Mono", monospace;
            font-size: 11px;
            color: #C9D6D4;
        }

        .cp-freshness-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
        }

        .cp-freshness-fresh .cp-freshness-dot { background: #4FAE7C; }
        .cp-freshness-stale .cp-freshness-dot { background: #E0A458; }
        .cp-freshness-unknown .cp-freshness-dot { background: #7A96A0; }


        /* ==================================================
           DETAIL TOGGLE
        ================================================== */

        .cp-detail-toggle {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .cp-detail-toggle-label {
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.4px;
            text-transform: uppercase;
            color: #8FB8BA;
        }

        .cp-switch {
            position: relative;

            width: 34px;
            height: 18px;

            border: none;
            border-radius: 999px;

            background: rgba(255,255,255,0.22);

            cursor: pointer;
            padding: 0;

            transition: background 0.15s ease;
        }

        .cp-switch.on {
            background: var(--teal);
        }

        .cp-switch::after {
            content: "";

            position: absolute;
            top: 2px;
            left: 2px;

            width: 14px;
            height: 14px;

            border-radius: 50%;
            background: #ffffff;

            transition: left 0.15s ease;
        }

        .cp-switch.on::after {
            left: 18px;
        }


        /* ==================================================
           LOCATION SELECTOR
           dcc.Dropdown's internals (react-select) restyled to a
           bare underlined control matching the masthead — not a
           bordered box. The flyout menu stays light for legibility
           regardless of the dark header.
        ================================================== */

        .cp-location-dropdown {
            min-width: 160px;
        }

        .cp-location-dropdown .Select-control {
            min-height: 30px !important;
            border: none !important;
            border-bottom: 1px solid rgba(255,255,255,0.4) !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            background: transparent !important;
        }

        .cp-location-dropdown .Select-placeholder,
        .cp-location-dropdown .Select-value-label {
            color: var(--paper) !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }

        .cp-location-dropdown .Select-menu-outer {
            background: var(--paper) !important;
            border: 1px solid var(--paper-line) !important;
            box-shadow: 0 8px 20px rgba(11,37,49,0.18) !important;
            z-index: 2000 !important;
        }

        .cp-location-dropdown .Select-option {
            color: var(--ink) !important;
            font-size: 13px !important;
        }


        /* ==================================================
           PAGE INTRO (kicker / title / description)
           Restyled to the new palette. Hidden entirely on
           Overview ("/"), which supplies its own hero instead —
           see update_page_context below.
        ================================================== */

        .cp-page {
            width: 100%;
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 0 60px;
        }

        .cp-page-intro {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;

            padding: 30px 42px 0;
            margin-bottom: 20px;
        }

        .cp-page-kicker {
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.4px;
            text-transform: uppercase;
            color: var(--teal-deep);
            margin-bottom: 6px;
        }

        .cp-page-title {
            margin: 0;
            font-size: 26px;
            color: var(--navy);
        }

        .cp-page-description {
            margin-top: 6px;
            color: var(--slate);
            font-size: 13px;
        }

        .cp-context {
            display: flex;
            align-items: center;
            gap: 10px;
            color: var(--slate);
            font-size: 11px;
        }

        .cp-context-divider {
            width: 3px;
            height: 3px;
            background: #B9AE94;
            border-radius: 50%;
        }


        /* ==================================================
           CONTENT
        ================================================== */

        .cp-content {
            width: 100%;
            padding: 0 42px;
        }


        /* ==================================================
           VERDICT / DETAIL ZONES (unchanged mechanism)
        ================================================== */

        .cp-verdict-zone {
            margin-bottom: 24px;
        }

        .cp-detail-zone {
            display: none;
        }

        .cp-app.detail-on .cp-detail-zone {
            display: block;
        }

        /* Divider between stacked sections inside a verdict zone
           (e.g. Overview's audience list -> snapshot table) so the
           page reads as distinct plates instead of one continuous
           scroll of paper-on-paper. */
        .cp-verdict-zone .cp-section + .cp-section,
        .cp-verdict-zone .cp-section {
            border-top: 1px solid var(--paper-line);
        }

        .cp-verdict-zone > .cp-section:first-child {
            border-top: none;
        }


        /* ==================================================
           SHARED CARD (still used by Emergency/Tourism until
           they're restyled — Overview uses its own classes below)
        ================================================== */

        .cp-card {
            background: #ffffff;
            border: 1px solid var(--paper-line);
            border-radius: 8px;
        }


        /* ==================================================
           OVERVIEW: HERO
        ================================================== */

        .cp-hero {
            background: var(--navy);
            color: var(--paper);
            padding: 40px 42px 36px;
            position: relative;
            overflow: hidden;
        }

        .cp-hero-inner {
            max-width: 560px;
            position: relative;
            z-index: 2;
        }

        .cp-hero-kicker {
            font-size: 12px;
            letter-spacing: 0.4px;
            text-transform: uppercase;
            color: #8FB8BA;
            margin-bottom: 14px;
        }

        .cp-hero h1 {
            font-size: 34px;
            line-height: 1.15;
            margin: 0 0 16px 0;
            color: var(--paper);
        }

        .cp-hero p {
            font-size: 14.5px;
            line-height: 1.65;
            color: #C9D6D4;
            margin: 0;
            font-family: "Public Sans", sans-serif;
        }

        .cp-hero-graphic {
            position: absolute;
            right: 0;
            top: 0;
            bottom: 0;
            width: 50%;
            /* Fade the graphic in from the right rather than hard-edging
               it against the hero copy — at tablet widths (650-1000px)
               the two were close enough to visually collide. */
            -webkit-mask-image: linear-gradient(to right, transparent, black 22%);
            mask-image: linear-gradient(to right, transparent, black 22%);
        }

        .cp-stat-strip {
            display: flex;
            border-top: 1px solid rgba(255,255,255,0.15);
            margin-top: 32px;
            padding-top: 22px;
            max-width: 560px;
            position: relative;
            z-index: 2;
        }

        .cp-stat { flex: 1; }

        .cp-stat-num {
            font-family: "IBM Plex Mono", monospace;
            font-size: 22px;
            font-weight: 500;
            color: var(--paper);
            letter-spacing: -0.02em;
            line-height: 1;
        }

        .cp-stat-label {
            font-size: 11px;
            color: #9CB9B8;
            margin-top: 6px;
            line-height: 1.3;
        }


        /* ==================================================
           OVERVIEW: AUDIENCE LIST (asymmetric legend rows,
           not a uniform SaaS card grid)
        ================================================== */

        .cp-section {
            padding: 36px 0;
        }

        .cp-section-title {
            font-size: 18px;
            margin: 0 0 4px 0;
            color: var(--navy);
        }

        .cp-section-sub {
            font-size: 13px;
            color: var(--slate);
            margin: 0 0 20px 0;
        }

        .cp-audience-list {
            border-top: 1px solid var(--navy);
        }

        .cp-audience-row {
            display: grid;
            grid-template-columns: 150px 1fr;
            gap: 28px;
            align-items: baseline;

            padding: 18px 12px;
            margin-left: -12px;
            border-bottom: 1px solid var(--paper-line);
            border-left: 3px solid transparent;

            color: var(--ink);

            transition: background 0.12s ease, border-left-color 0.12s ease;
        }

        .cp-audience-row:hover {
            background: #EFE7D4;
            border-left-color: var(--teal);
        }

        a:focus-visible > .cp-audience-row {
            background: #EFE7D4;
            border-left-color: var(--teal);
            outline: none;
        }

        .cp-audience-tag {
            font-size: 12px;
            font-weight: 600;
            color: var(--slate);
        }

        .cp-audience-row h3 {
            font-size: 16px;
            margin: 0;
            display: block;
        }

        .cp-audience-row p {
            font-size: 13px;
            color: var(--slate);
            line-height: 1.5;
            margin: 4px 0 0 0;
        }


        /* ==================================================
           OVERVIEW: SNAPSHOT (tide-table style — dense rows,
           mono numerals — for the ONE selected location; this is
           deliberately not a multi-location table, since every
           Gold table here is location-wise and this section
           should not read as a Sri-Lanka-wide summary)
        ================================================== */

        .cp-snapshot-header {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 4px;
        }

        .cp-snapshot-scope {
            font-size: 11px;
            color: #9AA8A6;
        }

        table.cp-tide {
            width: 100%;
            border-collapse: collapse;
            margin-top: 8px;
            font-size: 13.5px;
        }

        table.cp-tide thead th {
            text-align: left;
            font-weight: 600;
            font-size: 11px;
            color: var(--slate);
            padding: 0 14px 10px 0;
            border-bottom: 1px solid var(--navy);
        }

        table.cp-tide tbody td {
            padding: 13px 14px 13px 0;
            border-bottom: 1px solid var(--paper-line);
            vertical-align: middle;
        }

        .cp-badge {
            display: inline-block;
            font-size: 11px;
            font-weight: 600;
            padding: 3px 9px;
            border-radius: 2px;
            color: white;
            /* Badge colors come from CLASSIFICATION_COLORS / score_band(),
               which can land on lighter hexes (e.g. a caution amber) where
               flat white text loses contrast. A subtle text-shadow plus an
               inset ring keeps every badge legible without having to
               special-case individual colors. */
            text-shadow: 0 1px 1px rgba(0,0,0,0.25);
            box-shadow: inset 0 0 0 1px rgba(0,0,0,0.08);
        }

        .cp-mono {
            font-family: "IBM Plex Mono", monospace;
        }

        .cp-note-muted {
            font-size: 11.5px;
            color: #8A9AA2;
        }


        /* ==================================================
           RESPONSIVE
        ================================================== */

        @media (max-width: 1000px) {
            .cp-header {
                flex-wrap: wrap;
                gap: 14px;
                padding: 14px 22px;
            }
            .cp-navigation {
                order: 3;
                width: 100%;
                overflow-x: auto;
            }
            .cp-page-intro, .cp-hero, .cp-section, .cp-content {
                padding-left: 22px;
                padding-right: 22px;
            }
        }

        @media (max-width: 650px) {
            .cp-detail-toggle-label { display: none; }
            .cp-hero-graphic { display: none; }
            .cp-audience-row { grid-template-columns: 1fr; gap: 4px; }
        }

    </style>
</head>

<body>
    {%app_entry%}
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </footer>
</body>
</html>
"""


# ============================================================
# NAVIGATION
# ============================================================

def nav_link(label, href, page_id):
    return dcc.Link(label, href=href, id=f"nav-{page_id}", className="cp-nav-link")


navigation = html.Nav(
    [
        nav_link("Overview", "/", "overview"),
        nav_link("Emergency", "/emergency", "emergency"),
        nav_link("Tourism", "/tourism", "tourism"),
        nav_link("Fisherman", "/fisherman", "fisherman"),
    ],
    className="cp-navigation",
)


# ============================================================
# BRAND — simplified to match the mockup: a coral dot (the same
# "position marker" motif used on the hero's chart graphic and,
# later, the map) plus the serif wordmark. Dropped the old
# circular avatar mark + subtitle line, which the mockup doesn't
# use.
# ============================================================

brand = html.Div(
    [
        html.Span(className="cp-brand-mark"),
        html.Span("CoastalPulse"),
    ],
    className="cp-brand",
)


# ============================================================
# FRESHNESS INDICATOR
# ============================================================

freshness_badge = html.Div(
    [
        html.Div(id="freshness-dot", className="cp-freshness-dot"),
        html.Span(id="freshness-text", children="Checking data\u2026"),
    ],
    id="freshness-badge",
    className="cp-freshness cp-freshness-unknown",
)

freshness_interval = dcc.Interval(
    id="freshness-interval",
    interval=5 * 60 * 1000,
    n_intervals=0,
)


# ============================================================
# DETAIL TOGGLE
# ============================================================

detail_mode_store = dcc.Store(id="detail-mode", storage_type="session", data=False)

detail_toggle = html.Div(
    [
        html.Span("Show details", className="cp-detail-toggle-label"),
        html.Button(id="detail-toggle-btn", className="cp-switch", n_clicks=0),
    ],
    className="cp-detail-toggle",
)


# ============================================================
# LOCATION SELECTOR
# ============================================================

location_selector = dcc.Dropdown(
    id="location-dropdown",
    options=[{"label": loc, "value": loc} for loc in LOCATIONS],
    value=LOCATIONS[0] if LOCATIONS else None,
    clearable=False,
    searchable=True,
    className="cp-location-dropdown",
    style={"width": "170px"},
)


# ============================================================
# HEADER
# ============================================================

header = html.Header(
    [
        brand,
        navigation,
        html.Div(
            [freshness_badge, detail_toggle, location_selector],
            className="cp-header-right",
        ),
    ],
    className="cp-header",
)


# ============================================================
# SHARED LOCATION STORE
# ============================================================

location_store = dcc.Store(
    id="selected-location",
    storage_type="session",
    data=LOCATIONS[0] if LOCATIONS else None,
)


# ============================================================
# PAGE INTRO (hidden on Overview — see update_page_context)
# ============================================================

page_header = html.Div(
    [
        html.Div(
            [
                html.Div(id="page-kicker", className="cp-page-kicker"),
                html.H1(id="page-title", className="cp-page-title"),
                html.Div(id="page-description", className="cp-page-description"),
            ]
        ),
        html.Div(
            [
                html.Span(id="context-location"),
                html.Div(className="cp-context-divider"),
                html.Span(id="context-date"),
            ],
            className="cp-context",
        ),
    ],
    id="page-intro",
    className="cp-page-intro",
)


# ============================================================
# MAIN LAYOUT
# ============================================================

dash_app.layout = html.Div(
    [
        location_store,
        detail_mode_store,
        freshness_interval,
        dcc.Location(id="url", refresh=False),
        header,
        html.Main(
            [
                page_header,
                html.Div(dash.page_container, className="cp-content"),
            ],
            className="cp-page",
        ),
    ],
    id="app-root",
    className="cp-app",
)


# ============================================================
# LOCATION → SHARED STORE (one-way only — see prior notes on
# why a store->dropdown callback here would cause a circular
# dependency; never re-add one)
# ============================================================

@callback(
    Output("selected-location", "data"),
    Input("location-dropdown", "value"),
)
def sync_selected_location(value):
    return value


# ============================================================
# DETAIL TOGGLE → SHARED STORE
# ============================================================

@callback(
    Output("detail-mode", "data"),
    Input("detail-toggle-btn", "n_clicks"),
    State("detail-mode", "data"),
    prevent_initial_call=True,
)
def toggle_detail_mode(_n_clicks, current):
    return not current


@callback(
    Output("app-root", "className"),
    Output("detail-toggle-btn", "className"),
    Input("detail-mode", "data"),
)
def apply_detail_mode(is_on):
    base_class = "cp-app detail-on" if is_on else "cp-app"
    switch_class = "cp-switch on" if is_on else "cp-switch"
    return base_class, switch_class


# ============================================================
# ACTIVE NAVIGATION
# ============================================================

@callback(
    Output("nav-overview", "className"),
    Output("nav-emergency", "className"),
    Output("nav-tourism", "className"),
    Output("nav-fisherman", "className"),
    Input("url", "pathname"),
)
def update_active_navigation(pathname):
    if pathname == "/" or pathname is None:
        current = "overview"
    elif pathname.startswith("/emergency"):
        current = "emergency"
    elif pathname.startswith("/tourism"):
        current = "tourism"
    elif pathname.startswith("/fisherman"):
        current = "fisherman"
    else:
        current = "overview"

    def cls(name):
        return "cp-nav-link active" if name == current else "cp-nav-link"

    return cls("overview"), cls("emergency"), cls("tourism"), cls("fisherman")


# ============================================================
# PAGE INTRO CONTENT — and visibility. Hidden entirely on "/"
# since Overview supplies its own hero inside pages/overview.py;
# showing both would duplicate the framing.
#
# Content strings are sentence-case; ALL-CAPS presentation for the
# kicker is handled purely in CSS (text-transform: uppercase on
# .cp-page-kicker), matching how .cp-hero-kicker and
# .cp-detail-toggle-label already work. Keeps the raw string
# sentence-case for anything that reads the text directly.
# ============================================================

@callback(
    Output("page-kicker", "children"),
    Output("page-title", "children"),
    Output("page-description", "children"),
    Output("page-intro", "style"),
    Input("url", "pathname"),
)
def update_page_context(pathname):
    if pathname == "/" or pathname is None:
        return "", "", "", {"display": "none"}

    if pathname == "/emergency":
        content = (
            "Emergency monitoring",
            "Coastal risk",
            "Monitor hazardous marine conditions and emerging coastal threats.",
        )
    elif pathname == "/tourism":
        content = (
            "Tourism intelligence",
            "Coastal tourism",
            "Assess beach conditions and identify suitable coastal destinations.",
        )
    elif pathname == "/fisherman":
        content = (
            "Fishing intelligence",
            "Fishing conditions",
            "Monitor marine conditions and identify safer fishing opportunities.",
        )
    else:
        content = ("Coastal situation", "Coastal overview", "")

    return content[0], content[1], content[2], {"display": "flex"}


# ============================================================
# LOCATION CONTEXT
# ============================================================

@callback(
    Output("context-location", "children"),
    Input("selected-location", "data"),
)
def update_context_location(location):
    return location if location else "No location selected"


# ============================================================
# DATE CONTEXT
# ============================================================

@callback(
    Output("context-date", "children"),
    Input("url", "pathname"),
)
def update_context_date(pathname):
    # Deliberately generic — individual pages show their own real
    # observation date/time from their dataset.
    return "Coastal monitoring"


# ============================================================
# FRESHNESS INDICATOR (real data, not decorative)
# ============================================================

@callback(
    Output("freshness-dot", "className"),
    Output("freshness-text", "children"),
    Output("freshness-badge", "className"),
    Input("freshness-interval", "n_intervals"),
)
def update_freshness_badge(_n_intervals):
    last_updated = get_last_updated()

    if last_updated is None:
        return "cp-freshness-dot", "Freshness unknown", "cp-freshness cp-freshness-unknown"

    import pandas as pd

    age = pd.Timestamp.now("UTC") - last_updated
    hours = age.total_seconds() / 3600

    if hours < 1:
        minutes = int(age.total_seconds() / 60)
        label = f"Updated {minutes}m ago" if minutes > 0 else "Updated just now"
    elif hours < 48:
        label = f"Updated {int(hours)}h ago"
    else:
        label = f"Updated {int(hours / 24)}d ago"

    state = "fresh" if hours < 36 else "stale"

    return "cp-freshness-dot", label, f"cp-freshness cp-freshness-{state}"


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    # debug=True (Dash's dev server, with hot reload + the debug UI) is for
    # local development only. Production runs through Vercel's Python
    # runtime instead, which imports this module for `app` (the Flask/WSGI
    # object) and never executes this block at all — this guard is a
    # second layer of protection in case something ever does invoke
    # `python app.py` on a server.
    debug_mode = os.environ.get("DASH_DEBUG", "false").lower() == "true"
    dash_app.run(debug=debug_mode)