"""
CoastalPulse
Coastal Intelligence & Decision Support Platform

Main application shell.

Routes (fixed to match the nav — IMPORTANT for the pages step):
    /            -> pages/overview.py     (not built yet)
    /emergency   -> pages/emergency.py    (must register path="/emergency", NOT "/")
    /tourism     -> pages/tourism.py
    /fisherman   -> pages/fisherman.py

This app.py owns two contracts every page must honor:

1. ROUTING — see above. If a page registers the wrong path, the nav will
   look right but clicking it will 404 or land on the wrong content.

2. VERDICT / DETAIL SPLIT — the audience is tourists, residents, and
   fishermen, not statisticians. Nobody opening this at 5am wants to read
   a wave-height line chart against a dashed threshold line; they want
   "Go" or "Don't go, waves 2.8m." So every page's layout must put:
     - the plain-language status card / recommendation in a container
       with className="cp-verdict-zone" (ALWAYS visible)
     - charts, trends, and anything requiring interpretation in a
       container with className="cp-detail-zone" (hidden by default,
       revealed by the "Show details" switch in the header)
   This is enforced with a single CSS rule keyed off the app-root class,
   not per-page callbacks — so no page needs to reimplement show/hide
   logic, and it can't drift out of sync across pages the way the
   location lists did in the pipeline.
"""

import dash
from dash import Dash, html, dcc, Input, Output, State, callback

from data_access import LOCATIONS, get_last_updated


# ============================================================
# APP
# ============================================================

app = Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    suppress_callback_exceptions=True,
)

app.title = "CoastalPulse"


# ============================================================
# GLOBAL CSS
# ============================================================

app.index_string = """
<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}

    <link
        rel="preconnect"
        href="https://fonts.googleapis.com"
    >
    <link
        rel="preconnect"
        href="https://fonts.gstatic.com"
        crossorigin
    >
    <link
        href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap"
        rel="stylesheet"
    >

    <style>

        /* ==================================================
           RESET
        ================================================== */

        * {
            box-sizing: border-box;
        }

        html {
            background: #f4f7f8;
        }

        body {
            margin: 0;
            padding: 0;
            background: #f4f7f8;
            color: #10212b;
            font-family: "DM Sans", Arial, sans-serif;
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


        /* ==================================================
           APP
        ================================================== */

        .cp-app {
            min-height: 100vh;
            background: #f4f7f8;
        }


        /* ==================================================
           HEADER
        ================================================== */

        .cp-header {
            height: 76px;
            width: 100%;
            background: #ffffff;
            border-bottom: 1px solid #dce5e9;

            display: flex;
            align-items: center;
            justify-content: space-between;

            padding: 0 38px;

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
            gap: 12px;
        }

        .cp-brand-mark {
            width: 34px;
            height: 34px;

            border-radius: 50%;

            background: #062b3a;

            display: flex;
            align-items: center;
            justify-content: center;

            color: #22c7df;
            font-size: 17px;
            font-weight: 700;
        }

        .cp-brand-name {
            font-family: "Space Grotesk", sans-serif;
            font-size: 19px;
            font-weight: 700;
            letter-spacing: -0.5px;
            color: #09212c;
        }

        .cp-brand-subtitle {
            margin-top: 1px;

            font-size: 8px;
            font-weight: 700;
            letter-spacing: 1.8px;

            color: #81939d;
        }


        /* ==================================================
           NAVIGATION
        ================================================== */

        .cp-navigation {
            position: absolute;
            left: 50%;
            transform: translateX(-50%);

            display: flex;
            align-items: center;
            gap: 5px;
        }

        .cp-nav-link {
            position: relative;

            padding: 9px 15px;

            color: #70818b;

            font-size: 13px;
            font-weight: 600;

            border-radius: 7px;

            transition:
                color 0.15s ease,
                background 0.15s ease;
        }

        .cp-nav-link:hover {
            color: #092b3a;
            background: #f0f5f6;
        }

        .cp-nav-link.active {
            color: #062b3a;
            background: #edf8fa;
        }

        .cp-nav-link.active::after {
            content: "";

            position: absolute;
            left: 15px;
            right: 15px;
            bottom: -13px;

            height: 2px;

            background: #11b6d1;
            border-radius: 2px;
        }


        /* ==================================================
           HEADER RIGHT
        ================================================== */

        .cp-header-right {
            display: flex;
            align-items: center;
            gap: 22px;
        }


        /* ==================================================
           FRESHNESS BADGE
           (replaces the old decorative "LIVE" dot — this is a
           scheduled batch pipeline, not a live stream, so the
           badge says how stale the data actually is)
        ================================================== */

        .cp-freshness {
            display: flex;
            align-items: center;
            gap: 7px;

            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.7px;

            padding: 6px 10px;
            border-radius: 5px;
        }

        .cp-freshness-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
        }

        .cp-freshness-fresh {
            color: #13734a;
            background: #edf8f2;
        }

        .cp-freshness-fresh .cp-freshness-dot {
            background: #16a765;
            box-shadow: 0 0 0 4px rgba(22, 167, 101, 0.10);
        }

        .cp-freshness-stale {
            color: #986000;
            background: #fff6e5;
        }

        .cp-freshness-stale .cp-freshness-dot {
            background: #e89a13;
        }

        .cp-freshness-unknown {
            color: #7a8b94;
            background: #f0f3f4;
        }

        .cp-freshness-unknown .cp-freshness-dot {
            background: #aab8be;
        }


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
            font-weight: 700;
            letter-spacing: 0.6px;
            color: #70818b;
        }

        .cp-switch {
            position: relative;

            width: 36px;
            height: 20px;

            border: none;
            border-radius: 999px;

            background: #cbd8dd;

            cursor: pointer;
            padding: 0;

            transition: background 0.15s ease;
        }

        .cp-switch.on {
            background: #11b6d1;
        }

        .cp-switch::after {
            content: "";

            position: absolute;
            top: 2px;
            left: 2px;

            width: 16px;
            height: 16px;

            border-radius: 50%;
            background: #ffffff;

            transition: left 0.15s ease;

            box-shadow: 0 1px 2px rgba(9, 35, 47, 0.25);
        }

        .cp-switch.on::after {
            left: 18px;
        }


        /* ==================================================
           LOCATION
        ================================================== */

        .cp-location {
            display: flex;
            flex-direction: column;
            gap: 3px;
        }

        .cp-location-label {
            font-size: 8px;
            font-weight: 700;
            letter-spacing: 1.1px;
            color: #83949d;
        }

        .cp-location-dropdown {
            min-width: 190px;
        }

        .cp-location-dropdown .Select-control {
            min-height: 34px !important;

            border: 1px solid #cbd8dd !important;
            border-radius: 6px !important;

            box-shadow: none !important;

            background: #ffffff !important;
        }

        .cp-location-dropdown .Select-placeholder,
        .cp-location-dropdown .Select-value-label {
            color: #24343d !important;
            font-size: 12px !important;
        }

        .cp-location-dropdown .Select-menu-outer {
            border: 1px solid #d4e0e4 !important;
            box-shadow: 0 8px 24px rgba(11, 37, 49, 0.10) !important;
            z-index: 2000 !important;
        }


        /* ==================================================
           PAGE
        ================================================== */

        .cp-page {
            width: 100%;
            max-width: 1540px;

            margin: 0 auto;

            padding: 34px 42px 60px;
        }


        /* ==================================================
           PAGE INTRO
        ================================================== */

        .cp-page-intro {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;

            margin-bottom: 28px;
        }

        .cp-page-kicker {
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1.5px;

            color: #1594aa;

            margin-bottom: 7px;
        }

        .cp-page-title {
            margin: 0;

            font-family: "Space Grotesk", sans-serif;

            font-size: 30px;
            line-height: 1.1;
            font-weight: 600;

            letter-spacing: -1px;

            color: #0b202a;
        }

        .cp-page-description {
            margin-top: 7px;

            color: #72838c;

            font-size: 13px;
        }


        /* ==================================================
           GLOBAL DATA CONTEXT
        ================================================== */

        .cp-context {
            display: flex;
            align-items: center;
            gap: 12px;

            color: #788991;

            font-size: 11px;
        }

        .cp-context-divider {
            width: 3px;
            height: 3px;

            background: #aab8be;

            border-radius: 50%;
        }


        /* ==================================================
           CONTENT
        ================================================== */

        .cp-content {
            width: 100%;
        }


        /* ==================================================
           VERDICT / DETAIL ZONES

           Every page puts its plain-language status card in
           cp-verdict-zone (always shown) and its charts in
           cp-detail-zone (hidden until the header switch is on).
           Toggling one class here controls every page — no
           per-page show/hide logic needed.
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


        /* ==================================================
           GENERAL CARDS
        ================================================== */

        .cp-card {
            background: #ffffff;

            border: 1px solid #dce5e9;
            border-radius: 8px;

            box-shadow:
                0 1px 2px rgba(9, 35, 47, 0.025);
        }


        /* ==================================================
           KPI / METRIC STYLE
        ================================================== */

        .cp-metric {
            padding: 20px 22px;
        }

        .cp-metric-label {
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 1.2px;

            color: #7a8b94;

            margin-bottom: 9px;
        }

        .cp-metric-value {
            font-family: "Space Grotesk", sans-serif;

            font-size: 28px;
            line-height: 1;

            font-weight: 600;

            color: #0a2530;
        }

        .cp-metric-unit {
            margin-left: 4px;

            font-size: 12px;
            font-weight: 500;

            color: #7a8b94;
        }

        .cp-metric-note {
            margin-top: 9px;

            font-size: 10px;
            color: #8a9aa2;
        }


        /* ==================================================
           SECTION HEADERS
        ================================================== */

        .cp-section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;

            margin-bottom: 13px;
        }

        .cp-section-title {
            font-family: "Space Grotesk", sans-serif;

            font-size: 15px;
            font-weight: 600;

            color: #102a35;
        }

        .cp-section-meta {
            font-size: 10px;
            color: #82929a;
        }


        /* ==================================================
           STATUS
        ================================================== */

        .cp-status {
            display: inline-flex;
            align-items: center;
            gap: 7px;

            padding: 7px 10px;

            border-radius: 5px;

            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.6px;
        }

        .cp-status-dot {
            width: 6px;
            height: 6px;

            border-radius: 50%;
        }

        .cp-status-normal {
            color: #13734a;
            background: #edf8f2;
        }

        .cp-status-normal .cp-status-dot {
            background: #18a765;
        }

        .cp-status-caution {
            color: #986000;
            background: #fff6e5;
        }

        .cp-status-caution .cp-status-dot {
            background: #e89a13;
        }

        .cp-status-danger {
            color: #a52828;
            background: #fff0f0;
        }

        .cp-status-danger .cp-status-dot {
            background: #dc4040;
        }


        /* ==================================================
           ERROR MESSAGE
        ================================================== */

        .cp-error {
            padding: 18px 20px;

            border: 1px solid #f0caca;
            border-radius: 7px;

            background: #fff8f8;

            color: #a33232;

            font-size: 12px;
        }


        /* ==================================================
           RESPONSIVE
        ================================================== */

        @media (max-width: 1000px) {

            .cp-navigation {
                position: static;
                transform: none;
            }

            .cp-header {
                height: auto;
                min-height: 76px;

                flex-wrap: wrap;

                gap: 15px;

                padding: 15px 25px;
            }

            .cp-navigation {
                order: 3;

                width: 100%;

                justify-content: center;
            }

            .cp-nav-link.active::after {
                bottom: -5px;
            }

            .cp-page {
                padding: 28px 25px 50px;
            }
        }


        @media (max-width: 650px) {

            .cp-header {
                padding: 14px 17px;
            }

            .cp-brand-subtitle {
                display: none;
            }

            .cp-header-right {
                gap: 10px;
            }

            .cp-detail-toggle-label {
                display: none;
            }

            .cp-location-dropdown {
                min-width: 145px;
            }

            .cp-page {
                padding: 24px 17px 40px;
            }

            .cp-page-title {
                font-size: 25px;
            }

            .cp-navigation {
                overflow-x: auto;
                justify-content: flex-start;
            }

            .cp-nav-link {
                white-space: nowrap;
            }
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
    """
    Create one navigation item.

    Active state is handled dynamically using the current URL.
    """
    return dcc.Link(
        label,
        href=href,
        id=f"nav-{page_id}",
        className="cp-nav-link",
    )


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
# BRAND
# ============================================================

brand = html.Div(
    [
        html.Div(
            "◒",
            className="cp-brand-mark",
        ),

        html.Div(
            [
                html.Div(
                    "CoastalPulse",
                    className="cp-brand-name",
                ),

                html.Div(
                    "COASTAL INTELLIGENCE",
                    className="cp-brand-subtitle",
                ),
            ]
        ),
    ],
    className="cp-brand",
)


# ============================================================
# FRESHNESS BADGE (replaces the fake "LIVE" dot)
# ============================================================
#
# This is a scheduled batch pipeline (Bronze -> Silver -> Gold), not a
# real-time feed. A pulsing "LIVE" dot next to data that's actually hours
# or a day old will erode trust the moment someone checks a timestamp.
# This badge shows how stale the data genuinely is, using the real
# MAX(inserted_at) from silver_hourly via data_access.get_last_updated().
#
# It refreshes on an interval rather than only at page load, so leaving
# the tab open doesn't show an increasingly wrong "just now".

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
    interval=5 * 60 * 1000,  # 5 minutes — matches the planned cache TTL
    n_intervals=0,
)


# ============================================================
# DETAIL TOGGLE
# ============================================================
#
# Default OFF: every page opens showing only its plain-language verdict
# (status card / recommendation). Switching this on reveals the
# cp-detail-zone containers — charts, trends, comparisons — for the
# smaller audience that wants to dig in (a resident tracking a storm,
# a fisherman planning several days out).

detail_mode_store = dcc.Store(id="detail-mode", storage_type="session", data=False)

detail_toggle = html.Div(
    [
        html.Span("SHOW DETAILS", className="cp-detail-toggle-label"),
        html.Button(id="detail-toggle-btn", className="cp-switch", n_clicks=0),
    ],
    className="cp-detail-toggle",
)


# ============================================================
# LOCATION SELECTOR
# ============================================================

location_selector = html.Div(
    [
        html.Div(
            "LOCATION",
            className="cp-location-label",
        ),

        dcc.Dropdown(
            id="location-dropdown",

            options=[
                {
                    "label": location,
                    "value": location,
                }
                for location in LOCATIONS
            ],

            value=LOCATIONS[0] if LOCATIONS else None,

            clearable=False,
            searchable=True,

            className="cp-location-dropdown",

            style={
                "width": "190px",
            },
        ),
    ],
    className="cp-location",
)


# ============================================================
# HEADER
# ============================================================

header = html.Header(
    [
        brand,

        navigation,

        html.Div(
            [
                freshness_badge,
                detail_toggle,
                location_selector,
            ],
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
# PAGE HEADER
# ============================================================

page_header = html.Div(
    [
        html.Div(
            [
                html.Div(
                    id="page-kicker",
                    className="cp-page-kicker",
                ),

                html.H1(
                    id="page-title",
                    className="cp-page-title",
                ),

                html.Div(
                    id="page-description",
                    className="cp-page-description",
                ),
            ]
        ),

        html.Div(
            [
                html.Span(
                    id="context-location",
                ),

                html.Div(
                    className="cp-context-divider",
                ),

                html.Span(
                    id="context-date",
                ),
            ],
            className="cp-context",
        ),
    ],
    className="cp-page-intro",
)


# ============================================================
# MAIN LAYOUT
# ============================================================

app.layout = html.Div(
    [
        # Shared state
        location_store,
        detail_mode_store,
        freshness_interval,

        # URL
        dcc.Location(
            id="url",
            refresh=False,
        ),

        # Application header
        header,

        # Main workspace
        html.Main(
            [
                page_header,

                html.Div(
                    dash.page_container,
                    className="cp-content",
                ),
            ],
            className="cp-page",
        ),
    ],
    id="app-root",
    className="cp-app",
)


# ============================================================
# LOCATION → SHARED STORE
# ============================================================
#
# One-way only: the dropdown is the single source of truth, the store is
# derived from it. A second callback that also wrote back from the store
# to the dropdown's value used to exist here — that created a cycle
# (dropdown -> store -> dropdown) which Dash's dependency graph rejects
# as a "Circular Dependency" error, exactly what you saw.
#
# If a future page needs to set the location some other way (e.g.
# clicking a marker on the Emergency map), have THAT page's callback
# target Output("location-dropdown", "value") directly — never re-add a
# callback that writes back to the dropdown from "selected-location",
# or the cycle returns.

@callback(
    Output("selected-location", "data"),
    Input("location-dropdown", "value"),
)
def sync_selected_location(value):
    """
    Store the selected location in session storage.

    All pages can access:
        State("selected-location", "data")
    """
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
        if name == current:
            return "cp-nav-link active"
        return "cp-nav-link"

    return (
        cls("overview"),
        cls("emergency"),
        cls("tourism"),
        cls("fisherman"),
    )


# ============================================================
# DYNAMIC PAGE CONTEXT
# ============================================================

@callback(
    Output("page-kicker", "children"),
    Output("page-title", "children"),
    Output("page-description", "children"),
    Input("url", "pathname"),
)
def update_page_context(pathname):

    if pathname == "/emergency":

        return (
            "EMERGENCY MONITORING",
            "Coastal risk",
            "Monitor hazardous marine conditions and emerging coastal threats.",
        )

    if pathname == "/tourism":

        return (
            "TOURISM INTELLIGENCE",
            "Coastal tourism",
            "Assess beach conditions and identify suitable coastal destinations.",
        )

    if pathname == "/fisherman":

        return (
            "FISHING INTELLIGENCE",
            "Fishing conditions",
            "Monitor marine conditions and identify safer fishing opportunities.",
        )

    return (
        "COASTAL SITUATION",
        "Coastal overview",
        "A live view of coastal conditions, risks and opportunities.",
    )


# ============================================================
# LOCATION CONTEXT
# ============================================================

@callback(
    Output("context-location", "children"),
    Input("selected-location", "data"),
)
def update_context_location(location):

    if not location:
        return "No location selected"

    return location


# ============================================================
# DATE CONTEXT
# ============================================================

@callback(
    Output("context-date", "children"),
    Input("url", "pathname"),
)
def update_context_date(pathname):

    # Deliberately kept generic here.
    #
    # Individual pages should display the actual observation
    # date/time from their dataset.
    #
    # This avoids pretending that the current browser date is
    # the date of the coastal observation.

    return "Coastal monitoring"


# ============================================================
# FRESHNESS BADGE (real data, not decorative)
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
        return (
            "cp-freshness-dot",
            "Freshness unknown",
            "cp-freshness cp-freshness-unknown",
        )

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

    # This is a daily batch pipeline — treat anything past ~36h as stale
    # rather than pretending it's current.
    state = "fresh" if hours < 36 else "stale"

    return (
        "cp-freshness-dot",
        label,
        f"cp-freshness cp-freshness-{state}",
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)