"""
CoastalPulse
Coastal Intelligence & Decision Support Platform

Main application shell.

Expected pages:
    /
    /emergency
    /tourism
    /fisherman
"""

import dash
from dash import Dash, html, dcc, Input, Output, callback

from data_access import LOCATIONS


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

        .cp-live {
            display: flex;
            align-items: center;
            gap: 7px;

            color: #138a55;

            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.9px;
        }

        .cp-live-dot {
            width: 7px;
            height: 7px;

            border-radius: 50%;

            background: #16a765;

            box-shadow: 0 0 0 4px rgba(22, 167, 101, 0.10);
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

            .cp-live {
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
                html.Div(
                    [
                        html.Div(
                            className="cp-live-dot",
                        ),

                        html.Span(
                            "LIVE",
                        ),
                    ],
                    className="cp-live",
                ),

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
    className="cp-app",
)


# ============================================================
# LOCATION → SHARED STORE
# ============================================================

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
# KEEP DROPDOWN IN SYNC WITH SESSION STORE
# ============================================================

@callback(
    Output("location-dropdown", "value"),
    Input("selected-location", "data"),
)
def sync_location_dropdown(value):
    return value


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
# RUN
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)