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
import plotly.graph_objects as go
import pandas as pd

from data_access import get_emergency_data, get_tourism_data, get_fisherman_forecast, LOCATION_COORDS
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
                        _stat(html.Span("\u2014", id="overview-stat-safe-value"), "Locations safe today"),
                        _stat(html.Span("\u2014", id="overview-stat-caution-value"), "Under caution or warning"),
                        _stat(html.Span("\u2014", id="overview-stat-best-value"), html.Span("Best beach score today", id="overview-stat-best-label")),
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
# TODAY ACROSS SRI LANKA — highlight line + status map. The page
# previously had no live data at all above the per-location snapshot,
# which is what made it feel like a marketing page rather than a
# dashboard. Both pieces are Sri-Lanka-wide (not tied to the selected
# location), so they're computed once per page load rather than
# re-fetched every time the header's location dropdown changes.
# ============================================================

highlight_banner = html.Div(
    html.Div(
        id="overview-highlight",
        style={
            "borderLeft": "3px solid var(--teal)",
            "paddingLeft": "16px",
            "fontSize": "14.5px",
            "lineHeight": "1.6",
            "color": "var(--ink)",
        },
    ),
    className="cp-section",
)

map_section = html.Div(
    [
        html.Div("Sri Lanka right now", className="cp-section-title"),
        html.Div("Every monitored location, colored by today's coastal risk.", className="cp-section-sub"),
        html.Div(
            dcc.Graph(id="overview-map", config={"displayModeBar": False, "responsive": True}, style={"height": "420px"}),
            className="cp-card",
            style={"padding": "10px", "overflow": "hidden"},
        ),
    ],
    className="cp-section",
)


def _empty_overview_map():
    fig = go.Figure()
    fig.update_layout(
        map=dict(style="open-street-map", center=dict(lat=7.5, lon=80.7), zoom=6),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#F7F1E4",
    )
    return fig


def _build_overview_map(latest_em):
    if latest_em is None or latest_em.empty:
        return _empty_overview_map()

    fig = go.Figure()
    for classification in ["Safe", "Caution", "Dangerous"]:
        color = CLASSIFICATION_COLORS.get(classification, "#999")
        group = latest_em[latest_em["classification"].astype(str).str.lower() == classification.lower()]
        lats, lons, names, hover = [], [], [], []
        for _, row in group.iterrows():
            loc = row.get("location_name", "")
            coords = LOCATION_COORDS.get(loc)
            if coords is None:
                continue
            lat, lon = coords if not isinstance(coords, dict) else (coords.get("lat"), coords.get("lon"))
            if lat is None or lon is None:
                continue
            lats.append(lat)
            lons.append(lon)
            names.append(loc)
            wave = row.get("wave_height_max")
            wave_text = f"<br>Wave: {wave:.2f} m" if pd.notna(wave) else ""
            hover.append(f"<b>{loc}</b><br>{classification}{wave_text}")
        if lats:
            fig.add_trace(go.Scattermap(
                lat=lats, lon=lons, mode="markers", name=classification,
                text=names, hovertext=hover, hoverinfo="text",
                marker=dict(size=12, color=color, opacity=0.9),
            ))

    fig.update_layout(
        map=dict(style="open-street-map", center=dict(lat=7.5, lon=80.7), zoom=6.2),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#F7F1E4",
        legend=dict(
            orientation="h", yanchor="bottom", y=0.02, xanchor="left", x=0.02,
            bgcolor="rgba(247,241,228,0.92)", bordercolor="#E4DAC4", borderwidth=1,
            font=dict(size=11, color="#16262C"),
        ),
    )
    return fig


def _build_highlight(safe, caution, dangerous, total, best_name, best_score):
    if not total:
        return "Live status is temporarily unavailable."

    if dangerous > 0:
        risk_text = (
            f"{dangerous} location{'s' if dangerous != 1 else ''} "
            f"{'are' if dangerous != 1 else 'is'} at Dangerous risk today — "
            "check Emergency mode before heading to the coast there."
        )
    elif caution > 0:
        risk_text = f"Conditions are calm at most locations, but {caution} {'are' if caution != 1 else 'is'} under Caution today."
    else:
        risk_text = f"All {total} monitored locations are Safe today."

    if best_name and best_score is not None and pd.notna(best_score):
        beach_text = f" {best_name} has today's best beach conditions, scoring {best_score:.0f}/100."
    else:
        beach_text = ""

    return risk_text + beach_text


# ============================================================
# MODE CARDS — shared by the audience picker below (Sri-Lanka-wide,
# static description + a live one-line stat) and the per-location
# snapshot further up (live badge/value only, no description). Both
# use the same .cp-mode-card/.cp-mode-grid CSS so the page reads as
# one card system, not a table and a separate list.
# ============================================================

MODE_CLASS = {"Emergency": "emergency", "Tourism": "tourism", "Fisherman": "fisherman"}


def _mode_card(mode, children, href=None):
    card = html.Div(children, className=f"cp-mode-card {MODE_CLASS.get(mode, '')}".strip())
    if href:
        return dcc.Link(card, href=href, className="cp-mode-card-link")
    return card


# ============================================================
# AUDIENCE NAVIGATION — one card per mode, ordered to match the
# header nav (Emergency, Tourism, Fisherman). Each card carries a
# live one-line stat (filled by update_overview_live below) instead
# of being pure static marketing copy, so this section is real
# dashboard content, not just a list of links.
# ============================================================

def _audience_card(mode, title, description, href, stat_id):
    return _mode_card(
        mode,
        [
            html.Div(mode, className="cp-mode-card-tag"),
            html.H3(title),
            html.P(description, className="cp-mode-card-desc"),
            html.Div(id=stat_id, className="cp-mode-card-stat"),
        ],
        href=href,
    )


nav_section = html.Div(
    [
        html.Div("Which view is for you", className="cp-section-title"),
        html.Div("Three ways to read the same coastline.", className="cp-section-sub"),
        html.Div(
            [
                _audience_card(
                    "Emergency", "Living on the coast",
                    "Current risk and hazard status for your area.",
                    "/emergency", "overview-mode-stat-emergency",
                ),
                _audience_card(
                    "Tourism", "Visiting the beach",
                    "Beach conditions and whether today is a good day to go.",
                    "/tourism", "overview-mode-stat-tourism",
                ),
                _audience_card(
                    "Fisherman", "Going out to fish",
                    "Marine conditions and forecast for the day ahead.",
                    "/fisherman", "overview-mode-stat-fisherman",
                ),
            ],
            className="cp-mode-grid",
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
        html.Div(id="overview-snapshot-cards", className="cp-mode-grid"),
    ],
    className="cp-section",
)


layout = html.Div(
    [
        hero,
        highlight_banner,
        map_section,
        # Snapshot sits before the mode picker, not after — it answers
        # "what about MY location specifically" as the last big-picture
        # beat, so the audience nav that follows reads as the page's
        # actual call to action ("now go pick a mode") instead of being
        # undercut by a detail table appearing right after it.
        html.Div(snapshot_section, className="cp-verdict-zone"),
        nav_section,
    ]
)


def _badge(text, color):
    return html.Span(text, className="cp-badge", style={"backgroundColor": color})


# Same thresholds as pipeline/build_gold.py's classify_wave_height() / the
# local copies in pages/emergency.py and pages/fisherman.py — the forecasts
# table only stores the raw wave_height_forecast number, not a
# classification, so this row has to derive one the same way those pages do.
def _classify_wave(value):
    if value is None or pd.isna(value):
        return None
    if value < 2.0:
        return "Safe"
    if value <= 3.0:
        return "Caution"
    return "Dangerous"


# ============================================================
# LIVE STATS + MAP — Sri-Lanka-wide, so this fires once per page
# load (on the "/" route) rather than on every location change like
# update_overview_snapshot below does.
# ============================================================

@callback(
    Output("overview-stat-safe-value", "children"),
    Output("overview-stat-caution-value", "children"),
    Output("overview-stat-best-value", "children"),
    Output("overview-stat-best-label", "children"),
    Output("overview-highlight", "children"),
    Output("overview-map", "figure"),
    Output("overview-mode-stat-emergency", "children"),
    Output("overview-mode-stat-tourism", "children"),
    Output("overview-mode-stat-fisherman", "children"),
    Input("url", "pathname"),
)
def update_overview_live(pathname):
    if pathname not in ("/", None):
        return (dash.no_update,) * 9

    try:
        em_df = get_emergency_data()
    except Exception:
        em_df = pd.DataFrame()

    try:
        tm_df = get_tourism_data()
    except Exception:
        tm_df = pd.DataFrame()

    try:
        fc_df = get_fisherman_forecast()
    except Exception:
        fc_df = pd.DataFrame()

    latest_em = pd.DataFrame()
    if em_df is not None and not em_df.empty:
        em_df = em_df.copy()
        em_df["date"] = pd.to_datetime(em_df["date"], errors="coerce")
        latest_em = em_df.sort_values("date").groupby("location_name", as_index=False).tail(1)

    safe_count = caution_count = dangerous_count = total_count = 0
    if not latest_em.empty:
        cls = latest_em["classification"].astype(str).str.lower()
        safe_count = int((cls == "safe").sum())
        caution_count = int((cls == "caution").sum())
        dangerous_count = int((cls == "dangerous").sum())
        total_count = len(latest_em)

    best_name, best_score = None, None
    if tm_df is not None and not tm_df.empty:
        tm_df = tm_df.copy()
        tm_df["date"] = pd.to_datetime(tm_df["date"], errors="coerce")
        tm_df["suitability_score"] = pd.to_numeric(tm_df["suitability_score"], errors="coerce")
        latest_tm = tm_df.sort_values("date").groupby("location_name", as_index=False).tail(1)
        latest_tm = latest_tm.dropna(subset=["suitability_score"])
        if not latest_tm.empty:
            top = latest_tm.sort_values("suitability_score", ascending=False).iloc[0]
            best_name = top.get("location_name")
            best_score = top.get("suitability_score")

    safe_text = f"{safe_count}/{total_count}" if total_count else "—"
    caution_text = str(caution_count + dangerous_count) if total_count else "—"
    best_value_text = f"{best_score:.0f}" if best_score is not None and pd.notna(best_score) else "—"
    best_label_text = f"Best beach score today — {best_name}" if best_name else "Best beach score today"

    highlight = _build_highlight(safe_count, caution_count, dangerous_count, total_count, best_name, best_score)
    map_fig = _build_overview_map(latest_em)

    # --- Mode-picker live stats — one honest, real-data line per card,
    # instead of pure static marketing copy. ---------------------------
    mode_stat_emergency = (
        f"{safe_count}/{total_count} locations Safe today" if total_count else "Live status unavailable"
    )

    mode_stat_tourism = (
        f"Best today: {best_name} — {best_score:.0f}/100" if best_name else "Live suitability scores, 15 locations"
    )

    mode_stat_fisherman = "48h forecasts not generated yet"
    if fc_df is not None and not fc_df.empty:
        fc = fc_df.copy().sort_values(["location_name", "forecast_time"])
        earliest = fc.groupby("location_name", as_index=False).first()
        earliest["classification"] = earliest["wave_height_forecast"].apply(_classify_wave)
        n_safe = int((earliest["classification"] == "Safe").sum())
        n_total = len(earliest)
        mode_stat_fisherman = f"{n_safe}/{n_total} locations forecast Safe soon" if n_total else mode_stat_fisherman

    return (
        safe_text, caution_text, best_value_text, best_label_text, highlight, map_fig,
        mode_stat_emergency, mode_stat_tourism, mode_stat_fisherman,
    )


def _snapshot_card(mode, value_text, badge_text, badge_color, note_text, href):
    return _mode_card(
        mode,
        [
            html.Div(mode, className="cp-mode-card-tag"),
            html.Div(
                [
                    html.Span(value_text, className="cp-mode-card-value"),
                    _badge(badge_text, badge_color) if badge_text else None,
                ],
                className="cp-mode-card-headline",
            ),
            html.P(note_text, className="cp-mode-card-desc"),
        ],
        href=href,
    )


@callback(
    Output("overview-snapshot-title", "children"),
    Output("overview-snapshot-scope", "children"),
    Output("overview-snapshot-cards", "children"),
    Input("selected-location", "data"),
)
def update_overview_snapshot(location):
    if not location:
        return "Today's readings", "", []

    title = f"Today's readings \u2014 {location}"
    scope = "updated daily"
    cards = []

    # --- Emergency card ---------------------------------------------------
    em_df = get_emergency_data(location)
    if not em_df.empty:
        latest = em_df.iloc[-1]
        status = latest.get("classification", "Unknown")
        color = CLASSIFICATION_COLORS.get(status, "#999")
        wave = latest.get("wave_height_max")
        note = EMERGENCY_VERDICT_TEXT.get(status, "conditions unknown")
        wave_text = f"{wave:.1f}m" if wave is not None and pd.notna(wave) else "\u2014"
        cards.append(_snapshot_card("Emergency", wave_text, status, color, note, "/emergency"))
    else:
        cards.append(_snapshot_card("Emergency", "\u2014", None, None, "No data yet for this location.", "/emergency"))

    # --- Tourism card -------------------------------------------------------
    tm_df = get_tourism_data(location)
    if not tm_df.empty:
        latest = tm_df.iloc[-1]
        score = latest.get("suitability_score")
        label, color = score_band(score)
        value_text = f"{score:.0f}/100" if score is not None and pd.notna(score) else "\u2014"
        cards.append(_snapshot_card("Tourism", value_text, None, color, label, "/tourism"))
    else:
        cards.append(_snapshot_card("Tourism", "\u2014", None, None, "No data yet for this location.", "/tourism"))

    # --- Fisherman card (real SARIMA forecast, see pipeline/build_forecasts.py) ---
    fc_df = get_fisherman_forecast(location)
    if not fc_df.empty:
        next_hour = fc_df.iloc[0]
        wave = next_hour.get("wave_height_forecast")
        status = _classify_wave(wave)
        color = CLASSIFICATION_COLORS.get(status, "#999")
        wave_text = f"{wave:.1f}m" if wave is not None and pd.notna(wave) else "\u2014"
        forecast_time = next_hour.get("forecast_time")
        time_text = forecast_time.strftime("%H:%M") if forecast_time is not None and pd.notna(forecast_time) else ""
        note = f"48h wave forecast \u2014 next reading {time_text}" if time_text else "48h wave forecast"
        cards.append(_snapshot_card("Fisherman", wave_text, status, color, note, "/fisherman"))
    else:
        cards.append(_snapshot_card("Fisherman", "\u2014", None, None, "No forecast yet for this location.", "/fisherman"))

    return title, scope, cards