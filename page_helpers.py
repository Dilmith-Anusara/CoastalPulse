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
