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

# suitability_score is now HCI:Beach (Gunathilake et al. 2023, adapted from
# Scott/Rutty et al.'s Holiday Climate Index: Beach) — see
# pipeline/build_gold.py's compute_suitability_score for the formula and
# citation. These 3 dashboard-facing bands collapse that paper's own 5-tier
# scale (Impossible 0-19 / Unacceptable 20-39 / Marginal 40-59 / Good 60-79
# / Excellent 80-100): Not ideal = Impossible+Unacceptable, Fair = Marginal,
# Good = Good+Excellent.
SCORE_BANDS = [
    (60, "Good beach day", "#2ecc71"),
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