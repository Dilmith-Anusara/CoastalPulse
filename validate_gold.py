"""
validate_gold.py — CoastalPulse Gold layer validation

Mirrors validate_silver.py's approach, adapted for two Gold tables:
  - gold_emergency_daily
  - gold_tourism_daily

Checks per table:
  1. Duplicate (location_name, date) rows — should be impossible given the
     PRIMARY KEY constraint, but verified anyway in case the table was ever
     manually altered.
  2. Coverage — for each location, are there gaps in the daily date sequence?
  3. hours_covered / daylight_hours_covered sanity — Emergency should be 24,
     Tourism should be 12; flags anything else (doesn't fail the run, since
     a real API gap upstream in Silver would legitimately produce <24).
  4. Null checks on core aggregate columns.
  5. Plausibility ranges on the aggregate values themselves (same corrected
     km/h-based bounds as validate_silver.py, since these are aggregates of
     the same underlying units).
  6. Emergency only: re-derives the Safe/Caution/Dangerous classification
     from wave_height_max and confirms it matches the stored classification
     — catches drift if WAVE_SAFE_MAX/WAVE_CAUTION_MAX ever change in
     build_gold.py without a table rebuild.
  7. Tourism only: suitability_score is within [0, 100].

Writes results to validation_report_gold.md alongside printing to stdout.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
import pandas as pd
from datetime import timedelta

# fetch_data.py lives in pipeline/, one level down from this script's location
# at the project root — add it to sys.path so `from fetch_data import ...`
# works regardless of the current working directory you run this from.
sys.path.insert(0, str(Path(__file__).resolve().parent / "pipeline"))

load_dotenv()
SUPABASE_DB_URL = os.environ["SUPABASE_DB_URL"]

# Same thresholds as build_gold.py — keep in sync manually, or import from
# build_gold if you want a single source of truth (see note at bottom).
WAVE_SAFE_MAX = 2.0
WAVE_CAUTION_MAX = 3.0

# Plausibility ranges — same corrected km/h-based bounds as validate_silver.py
# post-fix. Aggregates (max/mean) should always fall within the same bounds
# as the raw hourly values they're derived from.
PLAUSIBLE_RANGES = {
    "wave_height_max": (0, 15),       # metres — daily max, generous upper bound for storm conditions
    "wind_speed_max": (0, 150),       # km/h
    "wind_gust_max": (0, 220),        # km/h
    "pressure_min": (900, 1050),      # hPa
    "wave_height_mean": (0, 10),      # metres — daylight mean, tighter than daily max
    "wind_speed_mean": (0, 100),      # km/h
    "sea_surface_temp_mean": (15, 35),  # deg C, generous tropical range
    "uv_index_mean": (0, 16),
    "precipitation_sum": (0, 500),    # mm/day, generous for monsoon conditions
}

VALID_CLASSIFICATIONS = {"Safe", "Caution", "Dangerous"}


def load_table(conn, table_name: str) -> pd.DataFrame:
    df = pd.read_sql(f"SELECT * FROM {table_name} ORDER BY location_name, date;", conn)
    df["date"] = pd.to_datetime(df["date"])
    return df


def check_all_locations_present(df: pd.DataFrame, table_name: str, report: list):
    from fetch_data import LOCATIONS

    all_expected = {loc["name"] for loc in LOCATIONS}
    present = set(df["location_name"].unique())
    missing = all_expected - present

    if not missing:
        report.append(f"✅ {table_name}: all {len(all_expected)} locations from fetch_data.py's LOCATIONS are present.")
    else:
        report.append(
            f"❌ {table_name}: {len(missing)} location(s) from fetch_data.py's LOCATIONS have ZERO rows here "
            f"— likely means build_gold.py's location list doesn't include them: {sorted(missing)}"
        )


def check_duplicates(df: pd.DataFrame, table_name: str, report: list):
    dupes = df[df.duplicated(subset=["location_name", "date"], keep=False)]
    if dupes.empty:
        report.append(f"✅ {table_name}: no duplicate (location_name, date) rows.")
    else:
        report.append(f"❌ {table_name}: {len(dupes)} duplicate rows found (should be impossible — check for a dropped/recreated PRIMARY KEY):")
        report.append(dupes.to_string(index=False))


def check_coverage(df: pd.DataFrame, table_name: str, report: list):
    report.append(f"\n--- {table_name}: coverage per location ---")
    for location, group in df.groupby("location_name"):
        dates = group["date"].sort_values()
        expected_range = pd.date_range(dates.min(), dates.max(), freq="D")
        missing = expected_range.difference(dates)
        row_count = len(group)
        if len(missing) == 0:
            report.append(f"  {location}: {row_count} days, {dates.min().date()} to {dates.max().date()}, no gaps.")
        else:
            report.append(
                f"  {location}: {row_count} days, {dates.min().date()} to {dates.max().date()}, "
                f"⚠️ {len(missing)} missing date(s): {[d.date().isoformat() for d in missing[:10]]}"
                f"{' ...' if len(missing) > 10 else ''}"
            )


def check_hours_covered(df: pd.DataFrame, table_name: str, column: str, expected: int, report: list):
    off = df[df[column] != expected]
    if off.empty:
        report.append(f"✅ {table_name}: all rows have {column} == {expected}.")
    else:
        report.append(
            f"⚠️ {table_name}: {len(off)} row(s) with {column} != {expected} "
            f"(legitimate if the underlying Silver hour range had a gap — cross-check against "
            f"validate_silver.py's coverage report before treating as a Gold-layer bug):"
        )
        summary = off.groupby("location_name")[column].agg(["count", "min", "max"])
        report.append(summary.to_string())


def check_nulls(df: pd.DataFrame, table_name: str, columns: list, report: list):
    null_counts = df[columns].isnull().sum()
    null_counts = null_counts[null_counts > 0]
    if null_counts.empty:
        report.append(f"✅ {table_name}: no nulls in core aggregate columns.")
    else:
        report.append(f"⚠️ {table_name}: null counts found:")
        report.append(null_counts.to_string())


def check_plausible_ranges(df: pd.DataFrame, table_name: str, report: list):
    report.append(f"\n--- {table_name}: plausibility check ---")
    any_violation = False
    for column, (low, high) in PLAUSIBLE_RANGES.items():
        if column not in df.columns:
            continue
        violations = df[(df[column].notna()) & ((df[column] < low) | (df[column] > high))]
        if not violations.empty:
            any_violation = True
            report.append(f"❌ {column}: {len(violations)} row(s) outside [{low}, {high}]:")
            report.append(
                violations[["location_name", "date", column]].to_string(index=False)
            )
    if not any_violation:
        report.append(f"✅ {table_name}: all values within plausible ranges.")


def check_classification_consistency(df: pd.DataFrame, report: list):
    report.append(f"\n--- gold_emergency_daily: classification consistency ---")

    def expected_classification(wave_height_max):
        if pd.isna(wave_height_max):
            return None
        if wave_height_max < WAVE_SAFE_MAX:
            return "Safe"
        elif wave_height_max <= WAVE_CAUTION_MAX:
            return "Caution"
        else:
            return "Dangerous"

    df["_expected_classification"] = df["wave_height_max"].apply(expected_classification)
    mismatches = df[df["classification"] != df["_expected_classification"]]

    invalid_values = df[~df["classification"].isin(VALID_CLASSIFICATIONS) & df["classification"].notna()]
    if not invalid_values.empty:
        report.append(f"❌ {len(invalid_values)} row(s) with a classification value outside {VALID_CLASSIFICATIONS}:")
        report.append(invalid_values[["location_name", "date", "classification"]].to_string(index=False))

    if mismatches.empty:
        report.append("✅ all classification values match re-derived thresholds from wave_height_max.")
    else:
        report.append(
            f"❌ {len(mismatches)} row(s) where stored classification doesn't match "
            f"re-derived value from wave_height_max (WAVE_SAFE_MAX={WAVE_SAFE_MAX}, "
            f"WAVE_CAUTION_MAX={WAVE_CAUTION_MAX} — if you changed these in build_gold.py "
            f"since the table was last built, rerun build_gold.py to refresh):"
        )
        report.append(
            mismatches[["location_name", "date", "wave_height_max", "classification", "_expected_classification"]].to_string(index=False)
        )
    df.drop(columns=["_expected_classification"], inplace=True)


def check_suitability_score_range(df: pd.DataFrame, report: list):
    report.append(f"\n--- gold_tourism_daily: suitability_score range check ---")
    violations = df[(df["suitability_score"].notna()) & ((df["suitability_score"] < 0) | (df["suitability_score"] > 100))]
    if violations.empty:
        report.append("✅ all suitability_score values within [0, 100].")
    else:
        report.append(f"❌ {len(violations)} row(s) with suitability_score outside [0, 100]:")
        report.append(violations[["location_name", "date", "suitability_score"]].to_string(index=False))


def check_sea_surface_temp_null_pattern(tourism_df: pd.DataFrame, report: list):
    """
    sea_surface_temp comes from the marine_ocean API, which fetch_data.py's
    TOURISM_ONLY set deliberately skips. Nulls here are EXPECTED for those
    locations and NOT expected for anyone else.

    Uses fetch_data.py's TOURISM_ONLY directly (source of truth) rather than
    inferring membership by comparing gold_emergency_daily vs
    gold_tourism_daily — that inference broke once build_gold.py started
    running Emergency for all 15 locations instead of a hand-typed subset.
    """
    from fetch_data import TOURISM_ONLY

    report.append(f"\n--- gold_tourism_daily: sea_surface_temp_mean null pattern check ---")

    all_tourism_table_locations = set(tourism_df["location_name"].unique())
    tourism_only_locations = all_tourism_table_locations & TOURISM_ONLY
    shared_locations = all_tourism_table_locations - TOURISM_ONLY

    null_by_location = tourism_df[tourism_df["sea_surface_temp_mean"].isnull()].groupby("location_name").size()

    unexpected_nulls = null_by_location[null_by_location.index.isin(shared_locations)]
    expected_nulls = null_by_location[null_by_location.index.isin(tourism_only_locations)]

    report.append(f"TOURISM_ONLY locations (no marine_ocean fetch, per fetch_data.py): {sorted(tourism_only_locations)}")
    report.append(f"Non-TOURISM_ONLY locations (marine_ocean expected): {sorted(shared_locations)}")

    if not expected_nulls.empty:
        report.append(f"✅ {expected_nulls.sum()} null(s) confined to TOURISM_ONLY locations — expected:")
        report.append(expected_nulls.to_string())

    if unexpected_nulls.empty:
        report.append("✅ no unexpected nulls in non-TOURISM_ONLY locations.")
    else:
        report.append(
            f"⚠️ {unexpected_nulls.sum()} null(s) found in non-TOURISM_ONLY location(s) — small sparse gaps "
            f"are plausible (a source API hiccup on a given hour), but worth a quick look if the count is large "
            f"for any single location:"
        )
        report.append(unexpected_nulls.to_string())


def main():
    conn = psycopg2.connect(SUPABASE_DB_URL)
    report = []
    report.append("# CoastalPulse Gold Layer Validation Report\n")

    # --- Emergency ---
    emergency_df = load_table(conn, "gold_emergency_daily")
    report.append(f"\n## gold_emergency_daily ({len(emergency_df)} total rows, {emergency_df['location_name'].nunique()} locations)\n")
    check_all_locations_present(emergency_df, "gold_emergency_daily", report)
    check_duplicates(emergency_df, "gold_emergency_daily", report)
    check_coverage(emergency_df, "gold_emergency_daily", report)
    check_hours_covered(emergency_df, "gold_emergency_daily", "hours_covered", 24, report)
    check_nulls(
        emergency_df, "gold_emergency_daily",
        ["wave_height_max", "wind_speed_max", "wind_gust_max", "pressure_min", "classification"],
        report,
    )
    check_plausible_ranges(emergency_df, "gold_emergency_daily", report)
    check_classification_consistency(emergency_df, report)

    # --- Tourism ---
    tourism_df = load_table(conn, "gold_tourism_daily")
    report.append(f"\n## gold_tourism_daily ({len(tourism_df)} total rows, {tourism_df['location_name'].nunique()} locations)\n")
    check_all_locations_present(tourism_df, "gold_tourism_daily", report)
    check_duplicates(tourism_df, "gold_tourism_daily", report)
    check_coverage(tourism_df, "gold_tourism_daily", report)
    check_hours_covered(tourism_df, "gold_tourism_daily", "daylight_hours_covered", 12, report)
    check_nulls(
        tourism_df, "gold_tourism_daily",
        ["wave_height_mean", "wind_speed_mean", "uv_index_mean",
         "precipitation_sum", "suitability_score"],
        report,
    )
    # Note: sea_surface_temp_mean is deliberately excluded from the generic
    # null check above — it has its own dedicated check below, since nulls
    # there are expected for Tourism-only locations (see
    # check_sea_surface_temp_null_pattern) and a flat null-count warning
    # would just be noise.
    check_plausible_ranges(tourism_df, "gold_tourism_daily", report)
    check_suitability_score_range(tourism_df, report)
    check_sea_surface_temp_null_pattern(tourism_df, report)

    conn.close()

    output = "\n".join(str(line) for line in report)
    print(output)

    with open("validation_report_gold.md", "w", encoding="utf-8") as f:
        f.write(output)
    print("\n\nWritten to validation_report_gold.md")


if __name__ == "__main__":
    main()