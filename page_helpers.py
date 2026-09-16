"""
page_helpers.py — shared plain-language verdict logic.

Overview needs the same classification colors and suitability bands that
Emergency and Tourism already use, to show live mini-verdicts for each
mode. Centralizing here for the same reason LOCATIONS/TOURISM_ONLY live in
one place in data_access.py: the same threshold defined in two or three
files eventually drifts (exactly what happened with the Gold-layer
location lists) — one definition, imported everywhere.
"""

import pandas as pd

CLASSIFICATION_COLORS = {
    "Safe": "#2ecc71",
    "Caution": "#f39c12",
    "Dangerous": "#e74c3c",
}

EMERGENCY_VERDICT_TEXT = {
    "Safe": "safe conditions",
    "Caution": "rough conditions — take care",
    "Dangerous": "dangerous conditions — avoid the water",
}

# suitability_score is HCI:Beach (Gunathilake et al. 2023, adapting Scott/
# Rutty et al.'s Holiday Climate Index: Beach) — see
# pipeline/build_gold.py's compute_suitability_score for the formula and
# citation. Shows the paper's own published 5-tier scale in full (Impossible
# 0-19 / Unacceptable 20-39 / Marginal 40-59 / Good 60-79 / Excellent
# 80-100) instead of collapsing it to 3 dashboard bands as before.
#
# Collapsing to 3 bands didn't remove the hard cutoffs at 40/60 — those are
# the paper's own real boundaries, not something CoastalPulse chose, so a
# score of 59 vs. 60 was always going to land in different bands no matter
# how many total tiers exist. What collapsing DID do was hide that 40/60
# come from a real published source rather than an app-specific choice, and
# lump a 60/100 day in with a 99/100 day under one "Good" label. Showing the
# real 5 tiers fixes both without touching either boundary's actual value.
SCORE_BANDS = [
    (80, "Excellent beach day", "#18A673"),
    (60, "Good beach day", "#2ecc71"),
    (40, "Marginal — some conditions worth checking", "#f39c12"),
    (20, "Unacceptable for most visitors", "#e67e22"),
    (0, "Impossible — not a viable beach day", "#e74c3c"),
]

# The paper's real "at least Good" cutoff, named explicitly rather than
# read positionally off SCORE_BANDS[0] — SCORE_BANDS[0] stopped meaning
# "the Good threshold" the moment Excellent became its own tier above it.
# pages/analytics.py's Emergency-vs-Tourism cross-analysis depends on this
# specific value, not on however many tiers SCORE_BANDS happens to have.
SCORE_GOOD_MIN = 60


def score_band(score):
    """Returns (label, color) for a suitability_score value."""
    if score is None:
        return "conditions unknown", "#999"
    for threshold, label, color in SCORE_BANDS:
        if score >= threshold:
            return label, color
    return SCORE_BANDS[-1][1], SCORE_BANDS[-1][2]


# UV Index — WHO's internationally standard exposure-category thresholds
# and color scale (who.int UV Index guide), not an app-specific choice.
# tourism.py used to have these thresholds as a text-only local function;
# centralized here (with color added) so a metric card backed by a real
# external standard can be colored the same way Emergency's Safe/Caution/
# Dangerous classification already is, instead of a neutral generic accent.
UV_BANDS = [
    (11, "Extreme", "#8e44ad"),
    (8, "Very High", "#e74c3c"),
    (6, "High", "#e67e22"),
    (3, "Moderate", "#f1c40f"),
    (0, "Low", "#2ecc71"),
]


def uv_band(value):
    """Returns (label, color) for a uv_index value."""
    if value is None or pd.isna(value):
        return "—", "#999"
    for threshold, label, color in UV_BANDS:
        if value >= threshold:
            return label, color
    return UV_BANDS[-1][1], UV_BANDS[-1][2]


# Air quality — official US EPA AQI bands and their standard colors
# (airnow.gov), applied to Open-Meteo's us_aqi (a real computed EPA index
# combining PM2.5/PM10/ozone/NO2/SO2/CO). Same reasoning as UV_BANDS above:
# an external, sourced standard, not an invented severity scale.
AQI_BANDS = [
    (301, "Hazardous", "#7e0023"),
    (201, "Very unhealthy", "#8e44ad"),
    (151, "Unhealthy", "#e74c3c"),
    (101, "Unhealthy for sensitive groups", "#e67e22"),
    (51, "Moderate", "#f1c40f"),
    (0, "Good", "#2ecc71"),
]


def aqi_band(value):
    """Returns (label, color) for a us_aqi value."""
    if value is None or pd.isna(value):
        return "—", "#999"
    for threshold, label, color in AQI_BANDS:
        if value >= threshold:
            return label, color
    return AQI_BANDS[-1][1], AQI_BANDS[-1][2]


# Minimum rows of history before a percentile comparison is meaningful —
# same reasoning as Emergency/Tourism's own hero-note functions, which
# each independently defined a HISTORY_MIN_ROWS = 30 before this existed.
HISTORY_MIN_ROWS = 30


def value_percentile_note(value, history_series, noun="reading", min_rows=HISTORY_MIN_ROWS):
    """Plain-language comparison of `value` against this location's own
    full recorded history for the same metric — for metrics with no
    established safety or suitability scale (wind speed, wind gust,
    pressure, sea level anomaly, "feels like" temperature, humidity, sea
    surface temperature, sunshine hours), this gives a bare number some
    real context without inventing a severity band that doesn't exist.
    Direction-neutral by design (just "higher/lower than the record for
    this place"), not a good/bad judgment — unlike score_band/uv_band/
    aqi_band, nothing here claims a value is dangerous or unhealthy.

    Returns "" if there isn't enough history or the value is missing,
    same fail-quiet convention as the rest of this module.
    """
    if value is None or pd.isna(value):
        return ""
    valid = history_series.dropna()
    if len(valid) < min_rows:
        return ""
    percentile = (valid <= value).mean() * 100
    if percentile >= 95:
        return f"Among the highest {noun} recorded here"
    if percentile >= 70:
        return f"Higher than {percentile:.0f}% of {noun} recorded here"
    if percentile <= 5:
        return f"Among the lowest {noun} recorded here"
    if percentile <= 30:
        return f"Lower than {100 - percentile:.0f}% of {noun} recorded here"
    return "Typical for this location"
