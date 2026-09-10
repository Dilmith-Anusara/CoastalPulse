"""
app.py — CoastalPulse dashboard entry point.

Multi-page Dash app (dash.register_page pattern). Each mode (Emergency,
Tourism, Fisherman) is a separate page under pages/. The selected location
is held in a dcc.Store with storage_type="session" so switching modes does
not reset which location you're looking at.

Run locally:
    pip install dash pandas supabase python-dotenv
    python app.py
"""

import dash
from dash import Dash, html, dcc, Input, Output, callback

from data_access import LOCATIONS

app = Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    suppress_callback_exceptions=True,
)
app.title = "CoastalPulse"

# --- Shared layout: nav bar + location selector + page container -----------

app.layout = html.Div(
    [
        dcc.Store(id="selected-location", storage_type="session", data=LOCATIONS[0]),
        html.Header(
            [
                html.H1("CoastalPulse", style={"margin": "0"}),
                html.Nav(
                    [
                        dcc.Link("Emergency", href="/", style={"marginRight": "1rem"}),
                        dcc.Link("Tourism", href="/tourism", style={"marginRight": "1rem"}),
                        dcc.Link("Fisherman", href="/fisherman"),
                    ],
                    style={"marginTop": "0.5rem"},
                ),
                html.Div(
                    [
                        html.Label("Location:", style={"marginRight": "0.5rem"}),
                        dcc.Dropdown(
                            id="location-dropdown",
                            options=[{"label": loc, "value": loc} for loc in LOCATIONS],
                            value=LOCATIONS[0],
                            clearable=False,
                            style={"width": "260px", "display": "inline-block"},
                        ),
                    ],
                    style={"marginTop": "1rem"},
                ),
            ],
            style={
                "padding": "1rem 2rem",
                "borderBottom": "1px solid #ddd",
                "marginBottom": "1rem",
            },
        ),
        html.Main(dash.page_container, style={"padding": "0 2rem"}),
    ]
)


# --- Sync the dropdown -> shared Store, so every page reads the same value --

@callback(
    Output("selected-location", "data"),
    Input("location-dropdown", "value"),
)
def sync_selected_location(value):
    return value


# --- Keep the dropdown in sync if a page changes the store directly --------
# (e.g. clicking a location marker on the Emergency map). Individual pages
# can add their own Output("location-dropdown", "value") callback for this;
# left as a placeholder comment rather than wired here to avoid a duplicate-
# output conflict until a page actually needs it.


if __name__ == "__main__":
    app.run(debug=True)