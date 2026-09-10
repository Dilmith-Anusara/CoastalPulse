"""
CoastalPulse — Silver layer validation
Run: python validate_silver.py

Writes a single Markdown report (validation_report.md by default) instead of
printing to the terminal — nothing is printed to stdout during a normal run.

NOTE ON UNITS: wind_speed and wind_gust are stored in km/h, not m/s.
fetch_data.py never sets Open-Meteo's `windspeed_unit` parameter, so the
Historical Weather API returns its default unit (km/h). Nothing about the
fetched data is wrong — it was only mislabeled/checked against the wrong
unit previously. PLAUSIBLE_RANGES and the printed labels below reflect km/h.

Checks one location's silver_hourly data against:
  1. Row coverage vs expected hourly count for the date range
  2. Timestamp gaps (missing hours) and duplicate timestamps
  3. Null discipline — zero-tolerance columns vs tourism-only ocean columns
     vs the known always-null sea_level_height placeholder
  4. Physical plausibility ranges per variable (catches unit/parsing bugs)
  5. Monsoon-season sanity check against the feasibility-analysis baselines
     already established for Mirissa (SW monsoon ~2.07m, NE monsoon ~1.52m,
     inter-monsoon baseline ~1.28m mean wave_height)
  6. Cross-variable physical consistency (gust >= sustained speed, combined
     sea height >= wind-wave component, directions within [0, 360))
  7. Statistical outlier detection (3x-IQR) per column — catches
     location-specific anomalies that pass the generic hard-bound check
  8. Frozen-value detection — flags long runs of an identical value, a
     known forecast/model artifact where data gets carried forward instead
     of updating
  9. Bronze purge confirmation — checks bronze_raw is actually empty for
     this location, rather than assuming the purge step worked
  10. Cross-variable confirmation of the known Cyclone Ditwah window
      (Nov 27-28, 2025) — a real storm should show a pressure drop
      alongside the wind_gust spike, not just the one variable

Uses SUPABASE_DB_URL directly (psycopg2) rather than supabase-py, since this
needs GROUP BY / gap analysis that the REST client doesn't do well.
"""

import io
import os
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

REPORT_PATH = "validation_report.md"

# ---------------------------------------------------------------------------
# Config — mirrors the fetch pipeline
# ---------------------------------------------------------------------------

TOURISM_ONLY = {"Mirissa", "Hikkaduwa", "Unawatuna", "Bentota", "Arugam Bay"}

GLOBAL_START = date(2025, 1, 1)
GLOBAL_END = date(2026, 6, 30)

ZERO_TOLERANCE_COLUMNS = [
    "wave_height", "wave_period", "wave_direction",
    "swell_height", "swell_period", "swell_direction", "wind_wave_height",
    "wind_speed", "wind_gust", "precipitation", "atmospheric_pressure",
    "uv_index", "pm25",
]
OCEAN_ONLY_COLUMNS = ["sea_surface_temp", "ocean_current_velocity", "ocean_current_direction"]
ALWAYS_NULL_COLUMNS = ["sea_level_height"]  # no endpoint wired up yet, documented gap

# (column, min, max) — generous physical bounds, flags parsing/unit errors, not weather itself.
# wind_speed / wind_gust bounds are in km/h (Open-Meteo's default unit — see module note above),
# set generously above Ditwah's real reported peak (~90 km/h sustained, ~85 km/h gust) to leave
# headroom for other/future storms without being so loose it stops catching real errors.
PLAUSIBLE_RANGES = {
    "wave_height": (0, 8),
    "wave_period": (0, 25),
    "wave_direction": (0, 360),
    "swell_height": (0, 8),
    "swell_period": (0, 25),
    "swell_direction": (0, 360),
    "wind_wave_height": (0, 6),
    "sea_surface_temp": (20, 34),
    "ocean_current_velocity": (0, 5),
    "ocean_current_direction": (0, 360),
    "wind_speed": (0, 150),   # km/h
    "wind_gust": (0, 220),    # km/h
    "precipitation": (0, 100),
    "atmospheric_pressure": (950, 1050),
    "uv_index": (0, 16),
    "pm25": (0, 500),
}

# Known feasibility-analysis baselines (mean wave_height, metres) for Mirissa,
# by season. Used only as a loose sanity check, not a hard pass/fail gate.
MIRISSA_SEASON_BASELINE = {
    "sw_monsoon": {"months": [5, 6, 7, 8, 9], "expected_mean": 2.07},
    "ne_monsoon": {"months": [12, 1, 2], "expected_mean": 1.52},
    "inter_monsoon": {"months": [3, 4, 10, 11], "expected_mean": 1.28},
}
SEASON_TOLERANCE = 0.35  # metres — loose, this is a sanity check not a strict re-test


def get_conn():
    return psycopg2.connect(SUPABASE_DB_URL)


def section(title):
    print(f"\n{'='*70}\n{title}\n{'='*70}")


def validate_location(location_name):
    """Runs all checks for one location. All print() calls inside this
    function are captured by run_all() via redirect_stdout — nothing here
    reaches the real terminal."""
    is_tourism_only = location_name in TOURISM_ONLY
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    print(f"\n########## VALIDATING: {location_name} (tourism_only={is_tourism_only}) ##########")

    # -----------------------------------------------------------------
    # 1. Coverage
    # -----------------------------------------------------------------
    section("1. Row coverage")
    expected_hours = int((GLOBAL_END - GLOBAL_START).days + 1) * 24

    cur.execute("""
        SELECT COUNT(*) AS n, MIN(timestamp) AS min_ts, MAX(timestamp) AS max_ts,
               COUNT(DISTINCT timestamp) AS n_distinct
        FROM silver_hourly WHERE location_name = %s
    """, (location_name,))
    row = cur.fetchone()
    actual = row["n"]
    coverage_pct = 100 * actual / expected_hours if expected_hours else 0

    print(f"  Expected hours:  {expected_hours}")
    print(f"  Actual rows:     {actual}")
    print(f"  Coverage:        {coverage_pct:.2f}%")
    print(f"  Date range:      {row['min_ts']}  to  {row['max_ts']}")

    if row["n"] != row["n_distinct"]:
        print(f"  ⚠️  DUPLICATE TIMESTAMPS DETECTED: {row['n'] - row['n_distinct']} duplicate rows "
              f"(should be impossible given the PK — check upsert conflict target)")
    else:
        print("  ✓ No duplicate timestamps (row count == distinct timestamp count)")

    if coverage_pct < 95:
        print(f"  ⚠️  Coverage below 95% skip-threshold — this location would NOT be skipped on a re-run")
    else:
        print("  ✓ Coverage at or above the 95% skip-threshold used by the pipeline")

    # -----------------------------------------------------------------
    # 2. Gap analysis — actual missing hours, not just an aggregate count
    # -----------------------------------------------------------------
    section("2. Timestamp gap analysis")
    cur.execute("""
        SELECT timestamp FROM silver_hourly
        WHERE location_name = %s ORDER BY timestamp
    """, (location_name,))
    timestamps = [r["timestamp"] for r in cur.fetchall()]

    gaps = []
    for i in range(1, len(timestamps)):
        delta = timestamps[i] - timestamps[i - 1]
        if delta > timedelta(hours=1):
            missing_hours = int(delta.total_seconds() // 3600) - 1
            gaps.append((timestamps[i - 1], timestamps[i], missing_hours))

    if not gaps:
        print("  ✓ No gaps — fully contiguous hourly series")
    else:
        total_missing = sum(g[2] for g in gaps)
        print(f"  ⚠️  {len(gaps)} gap(s) found, {total_missing} missing hours total:")
        for start, end, hrs in gaps[:15]:
            print(f"      {start}  →  {end}   ({hrs} hours missing)")
        if len(gaps) > 15:
            print(f"      ... and {len(gaps) - 15} more gaps")
        # This note only applies to locations that actually fetch sea_surface_temp —
        # printing it unconditionally would be misleading for tourism-only locations,
        # where that column isn't fetched at all and can't be the cause of any gap.
        if not is_tourism_only:
            print("  Note: a nationwide 13-day sea_surface_temp gap (2025-01-29 to 2025-02-11) is a known,")
            print("  confirmed upstream issue, not a fetch bug, IF this location's gap(s) fall in that window.")
            print("  Check the gap dates above against that window before assuming it's the same cause.")

    # -----------------------------------------------------------------
    # 3. Null discipline
    # -----------------------------------------------------------------
    section("3. Null audit")

    null_check_cols = ZERO_TOLERANCE_COLUMNS + OCEAN_ONLY_COLUMNS + ALWAYS_NULL_COLUMNS
    null_counts = {}
    for col in null_check_cols:
        cur.execute(f"SELECT COUNT(*) AS n FROM silver_hourly WHERE location_name = %s AND {col} IS NULL",
                    (location_name,))
        null_counts[col] = cur.fetchone()["n"]

    print("  Zero-tolerance columns (wave/wind/swell/AQ) — should be 0 nulls:")
    for col in ZERO_TOLERANCE_COLUMNS:
        n = null_counts[col]
        pct = 100 * n / actual if actual else 0
        flag = "✓" if n == 0 else "⚠️ "
        print(f"    {flag} {col:<25} {n} nulls ({pct:.2f}%)")

    print("\n  Ocean-only columns (sea_surface_temp / current velocity / current direction):")
    if is_tourism_only:
        print("  This is a Tourism-only location — these should be 100% null (marine_ocean endpoint is")
        print("  deliberately skipped). Non-null values here would mean the tourism-only skip didn't")
        print("  apply correctly.")
        for col in OCEAN_ONLY_COLUMNS:
            n = null_counts[col]
            flag = "✓" if n == actual else "⚠️ "
            print(f"    {flag} {col:<25} {n}/{actual} null")
    else:
        print("  This location fetches marine_ocean data — ≤5% null tolerance applies (known SST gap):")
        for col in OCEAN_ONLY_COLUMNS:
            n = null_counts[col]
            pct = 100 * n / actual if actual else 0
            flag = "✓" if pct <= 5 else "⚠️ "
            print(f"    {flag} {col:<25} {n} nulls ({pct:.2f}%)")

    print(f"\n  sea_level_height: {null_counts['sea_level_height']}/{actual} null — expected, no endpoint wired up yet.")

    # -----------------------------------------------------------------
    # 4. Physical plausibility
    # -----------------------------------------------------------------
    section("4. Physical plausibility ranges")
    any_violation = False
    for col, (lo, hi) in PLAUSIBLE_RANGES.items():
        if is_tourism_only and col in OCEAN_ONLY_COLUMNS:
            continue  # structurally null, skip range check
        cur.execute(f"""
            SELECT COUNT(*) AS n, MIN({col}) AS min_v, MAX({col}) AS max_v
            FROM silver_hourly WHERE location_name = %s AND {col} IS NOT NULL AND ({col} < %s OR {col} > %s)
        """, (location_name, lo, hi))
        r = cur.fetchone()
        if r["n"] > 0:
            any_violation = True
            print(f"  ⚠️  {col}: {r['n']} rows outside plausible range [{lo}, {hi}] "
                  f"(observed min={r['min_v']}, max={r['max_v']})")
    if not any_violation:
        print("  ✓ All values within plausible physical ranges")

    # -----------------------------------------------------------------
    # 5. Monsoon-season sanity check (Mirissa only, for now)
    # -----------------------------------------------------------------
    if location_name == "Mirissa":
        section("5. Monsoon-season sanity check (vs feasibility-analysis baseline)")
        for season, info in MIRISSA_SEASON_BASELINE.items():
            months = info["months"]
            cur.execute("""
                SELECT AVG(wave_height) AS mean_wh, COUNT(*) AS n
                FROM silver_hourly
                WHERE location_name = %s AND EXTRACT(MONTH FROM timestamp) = ANY(%s)
            """, (location_name, months))
            r = cur.fetchone()
            observed = float(r["mean_wh"]) if r["mean_wh"] is not None else None
            expected = info["expected_mean"]
            if observed is None:
                print(f"  {season}: no data yet")
                continue
            diff = abs(observed - expected)
            flag = "✓" if diff <= SEASON_TOLERANCE else "⚠️ "
            print(f"  {flag} {season:<15} observed mean={observed:.2f}m  expected≈{expected}m  "
                  f"(diff={diff:.2f}m, n={r['n']} rows)")
        print("  Note: this is a loose sanity check (±0.35m tolerance), not a re-validation of the")
        print("  original feasibility analysis — large deviations are worth a closer look, small ones aren't.")
    else:
        section("5. Monsoon-season sanity check")
        print(f"  Skipped — no established feasibility-analysis baseline exists for {location_name} yet.")
        print("  Only Mirissa has a baseline from the interim feasibility work. Add one here once you have")
        print("  an independent reference to check against, otherwise this section has nothing to compare to.")

    # -----------------------------------------------------------------
    # 6. Cross-variable physical consistency
    # -----------------------------------------------------------------
    section("6. Cross-variable consistency")

    cur.execute("""
        SELECT COUNT(*) AS n FROM silver_hourly
        WHERE location_name = %s AND wind_gust IS NOT NULL AND wind_speed IS NOT NULL
              AND wind_gust < wind_speed
    """, (location_name,))
    n = cur.fetchone()["n"]
    flag = "✓" if n == 0 else "⚠️ "
    print(f"  {flag} wind_gust < wind_speed: {n} rows (gust should never be below sustained speed)")

    cur.execute("""
        SELECT COUNT(*) AS n FROM silver_hourly
        WHERE location_name = %s AND wave_height IS NOT NULL AND wind_wave_height IS NOT NULL
              AND wind_wave_height > wave_height + 0.3
    """, (location_name,))
    n = cur.fetchone()["n"]
    flag = "✓" if n == 0 else "⚠️ "
    print(f"  {flag} wind_wave_height > wave_height (+0.3m tolerance): {n} rows "
          f"(combined sea state should generally be >= its wind-wave component)")

    for col in ["wave_direction", "swell_direction"]:
        cur.execute(f"""
            SELECT COUNT(*) AS n FROM silver_hourly
            WHERE location_name = %s AND ({col} < 0 OR {col} >= 360)
        """, (location_name,))
        n = cur.fetchone()["n"]
        flag = "✓" if n == 0 else "⚠️ "
        print(f"  {flag} {col} outside [0, 360): {n} rows")

    # -----------------------------------------------------------------
    # 7. Statistical outliers (IQR method) — catches location-specific
    #    anomalies that pass the generic hard-bound check
    # -----------------------------------------------------------------
    section("7. Statistical outliers (IQR, 3x whisker)")
    iqr_cols = ["wave_height", "wave_period", "swell_height", "wind_speed", "wind_gust",
                "precipitation", "atmospheric_pressure", "uv_index", "pm25"]
    for col in iqr_cols:
        cur.execute(f"""
            SELECT
                percentile_cont(0.25) WITHIN GROUP (ORDER BY {col}) AS q1,
                percentile_cont(0.75) WITHIN GROUP (ORDER BY {col}) AS q3
            FROM silver_hourly WHERE location_name = %s AND {col} IS NOT NULL
        """, (location_name,))
        r = cur.fetchone()
        q1, q3 = r["q1"], r["q3"]
        if q1 is None:
            continue
        iqr = q3 - q1
        lo, hi = q1 - 3 * iqr, q3 + 3 * iqr
        cur.execute(f"""
            SELECT COUNT(*) AS n, MIN({col}) AS min_v, MAX({col}) AS max_v
            FROM silver_hourly WHERE location_name = %s AND {col} IS NOT NULL AND ({col} < %s OR {col} > %s)
        """, (location_name, lo, hi))
        r2 = cur.fetchone()
        pct = 100 * r2["n"] / actual if actual else 0
        note = "" if r2["n"] == 0 else f"  (range [{lo:.2f}, {hi:.2f}], observed min={r2['min_v']}, max={r2['max_v']})"
        flag = "✓" if pct < 1 else "⚠️ "
        print(f"  {flag} {col:<20} {r2['n']} outliers ({pct:.2f}%){note}")
    print("  Note: 3x-IQR is deliberately loose — flags statistical rarity, not necessarily errors.")
    print("  A real storm (like Ditwah) will show up here too; that's expected, not a failure.")
    print("  Note: precipitation is zero-inflated (most hours are 0mm), so its Q1/Q3 sit near zero and")
    print("  ordinary rain will register as a mathematical 'outlier' here — treat this column's result")
    print("  as noise, not a data quality signal, until a fixed physical threshold replaces IQR for it.")

    # -----------------------------------------------------------------
    # 8. Frozen-value detection (stale/carried-forward data artifact)
    # -----------------------------------------------------------------
    section("8. Frozen-value detection (stuck consecutive values)")
    FREEZE_RUN_THRESHOLD = 6  # hours
    freeze_cols = ["wave_height", "wind_speed", "atmospheric_pressure", "uv_index"]
    cur.execute("""
        SELECT timestamp, wave_height, wind_speed, atmospheric_pressure, uv_index
        FROM silver_hourly WHERE location_name = %s ORDER BY timestamp
    """, (location_name,))
    all_rows = cur.fetchall()
    any_frozen = False
    for col in freeze_cols:
        run_len = 1
        run_start = None
        max_run = 0
        max_run_start = None
        for i in range(1, len(all_rows)):
            if all_rows[i][col] == all_rows[i - 1][col] and all_rows[i][col] is not None:
                if run_len == 1:
                    run_start = all_rows[i - 1]["timestamp"]
                run_len += 1
            else:
                if run_len > max_run:
                    max_run, max_run_start = run_len, run_start
                run_len = 1
        if run_len > max_run:
            max_run, max_run_start = run_len, run_start
        if max_run >= FREEZE_RUN_THRESHOLD:
            any_frozen = True
            note = ""
            if col == "uv_index":
                note = "  (likely nighttime, uv_index=0 for ~12-14h every night — not necessarily stuck)"
            print(f"  ⚠️  {col}: longest identical-value run = {max_run} hours, starting {max_run_start}{note}")
        else:
            print(f"  ✓ {col}: longest identical-value run = {max_run} hours (below {FREEZE_RUN_THRESHOLD}h threshold)")
    if not any_frozen:
        print("  No frozen/stale-data runs detected.")

    # -----------------------------------------------------------------
    # 9. Bronze purge confirmation
    # -----------------------------------------------------------------
    section("9. Bronze purge confirmation")
    cur.execute("SELECT COUNT(*) AS n FROM bronze_raw WHERE location_name = %s", (location_name,))
    n = cur.fetchone()["n"]
    if n == 0:
        print(f"  ✓ bronze_raw has 0 rows for {location_name} — purge is working as designed")
    else:
        print(f"  ⚠️  bronze_raw still has {n} rows for {location_name} — purge may not be firing, "
              f"or these are from a chunk that failed after Bronze insert but before purge (see the note")
        print(f"      about crash-mid-chunk from earlier in this project — safe to manually delete these).")

    # -----------------------------------------------------------------
    # 10. Ditwah cross-variable confirmation (Nov 27-28 2025)
    # -----------------------------------------------------------------
    section("10. Known-event cross-check — Cyclone Ditwah (Nov 27-28, 2025)")
    cur.execute("""
        SELECT MIN(atmospheric_pressure) AS min_p, MAX(precipitation) AS max_precip,
               MAX(wave_height) AS max_wave, MAX(wind_gust) AS max_gust,
               AVG(atmospheric_pressure) AS avg_p_full
        FROM silver_hourly
        WHERE location_name = %s AND timestamp >= '2025-11-27' AND timestamp < '2025-11-29'
    """, (location_name,))
    event = cur.fetchone()
    cur.execute("""
        SELECT AVG(atmospheric_pressure) AS avg_p FROM silver_hourly WHERE location_name = %s
    """, (location_name,))
    baseline_p = cur.fetchone()["avg_p"]
    if event["min_p"] is not None:
        pressure_drop = float(baseline_p) - float(event["min_p"])
        print(f"  Nov 27-28 window: min pressure={event['min_p']} hPa (baseline avg={float(baseline_p):.1f} hPa, "
              f"drop={pressure_drop:.1f} hPa)")
        print(f"  Nov 27-28 window: max precipitation={event['max_precip']} mm, "
              f"max wave_height={event['max_wave']} m, max wind_gust={event['max_gust']} km/h")
        print(f"  Reference (independently reported, IMD/World Bank GRADE): Ditwah peak winds ~65-90 km/h")
        print(f"  sustained, gusts up to ~85 km/h at landfall. Compare this location's max_gust above")
        print(f"  against that range as a sanity check — values wildly above it are worth a closer look.")
        if pressure_drop > 3:
            print("  ✓ Pressure drop is consistent with a real storm system passing through")
        else:
            print("  ⚠️  Pressure barely moved — gust spike isn't corroborated by a pressure signature, "
                  "worth a second look")
    else:
        print("  No data found for this window — check date range coverage for this location.")

    cur.close()
    conn.close()


def run_all(locations, report_path=REPORT_PATH):
    """Runs validate_location() for each location, capturing all of its
    stdout output and writing it into one Markdown report file. Nothing is
    printed to the real terminal during this process. If a location crashes
    (e.g. no rows yet, or a DB error), that's recorded in its section instead
    of stopping the whole run."""
    report_parts = [
        "# CoastalPulse Silver Layer Validation Report",
        f"\nGenerated: {datetime.now().isoformat(timespec='seconds')}",
        f"\nLocations checked: {', '.join(locations)}",
        "\n**Units note:** wind_speed and wind_gust are stored in km/h "
        "(Open-Meteo's default — fetch_data.py does not override it).",
    ]

    for loc in locations:
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                validate_location(loc)
        except Exception as e:
            buf.write(f"\n\n!! VALIDATION CRASHED for {loc}: {e!r}\n")

        captured = buf.getvalue()
        report_parts.append(f"\n---\n\n## {loc}\n\n```text{captured}\n```")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_parts))


if __name__ == "__main__":
    # Add more location names here as you fetch them
    LOCATIONS_TO_VALIDATE = [
        "Mirissa",
        "Hikkaduwa",
        "Unawatuna",
        "Bentota",
        "Arugam Bay",
        "Negombo",
        "Galle",
        "Trincomalee",
        "Chilaw",
        "Colombo",
        "Tangalle",
        "Batticaloa",
        "Jaffna",
        "Matara",
        "Puttalam",
    ]
    run_all(LOCATIONS_TO_VALIDATE)