"""
page_helpers.py — shared plain-language verdict logic.

Overview needs the same classification colors and suitability bands that
Emergency and Tourism already use, to show live mini-verdicts for each
mode. Centralizing here for the same reason LOCATIONS/TOURISM_ONLY live in
one place in data_access.py: the same threshold defined in two or three
files eventually drifts (exactly what happened with the Gold-layer
location lists) — one definition, imported everywhere.
"""

CLASSIFICATION_COLORS = {
    "Safe": "#2ecc71",
    "Caution": "#f39c12",
    "Dangerous": "#e74c3c",
}

EMERGENCY_VERDICT_TEXT = {
    "Safe": "safe conditions",
    "Caution": "rough conditions \u2014 take care",
    "Dangerous": "dangerous conditions \u2014 avoid the water",
}

# suitability_score bands — first-draft, not a settled formula (per the
# project handoff). Only used to pick a plain-language word, not a
# validated cutoff.
SCORE_BANDS = [
    (70, "Good beach day", "#2ecc71"),
    (40, "Fair \u2014 some conditions worth checking", "#f39c12"),
    (0, "Not ideal today", "#e74c3c"),
]


def score_band(score):
    """Returns (label, color) for a suitability_score value."""
    if score is None:
        return "conditions unknown", "#999"
    for threshold, label, color in SCORE_BANDS:
        if score >= threshold:
            return label, color
    return SCORE_BANDS[-1][1], SCORE_BANDS[-1][2]