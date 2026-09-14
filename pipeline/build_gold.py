"""
build_gold.py — CoastalPulse Gold layer

Reads from silver_hourly, writes two Gold tables:
  - gold_emergency_daily : daily MAX (not mean) of danger-relevant metrics,
                            classified against DMC-derived wave thresholds
  - gold_tourism_daily   : daylight-hours-only (06:00-18:00) MEAN, plus a
                            beach suitability score

Fisherman mode has no Gold table — SARIMA reads silver_hourly directly.
This is a separate, less-frequent-cadence script from fetch_data.py
(reads Silver, doesn't touch the source APIs).

*** COLUMN NAMES: all confirmed against the real silver_hourly schema. ***

Extended after the general-EDA pass (validation_scripts/eda_weather_indicators.ipynb)
to use the fields added to Silver in that same session: sea_level_height_max
in Emergency (closes the "no endpoint wired up yet" gap), and
humidity/apparent_temperature/air_temperature_max/cloud_cover/
dominant_weather_code/sunshine_hours/us_aqi in Tourism. apparent_temperature
is kept for the dashboard's "feels like" display; air_temperature_max is
kept separately because the HCI:Beach suitability formula needs raw
temperature (it does its own humidity adjustment — see
compute_suitability_score). weather_code went into Tourism but not
Emergency because EDA found zero thunderstorm codes anywhere in the dataset.

suitability_score is now HCI:Beach (Gunathilake et al. 2023), not an ad-hoc
formula — see compute_suitability_score's docstring for the citation.
"""

import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import math
from datetime import datetime

load_dotenv()

SUPABASE_DB_URL = os.environ["SUPABASE_DB_URL"]


def clean_value(v):
    """
    Convert pandas/numpy NaN to Python None before it reaches psycopg2.

    Root cause: pandas represents missing numeric data as float NaN, not
    None. psycopg2 correctly converts Python None -> SQL NULL, but passes
    float NaN through literally, so Postgres stores a real NaN value in the
    double precision column instead of NULL. `column IS NULL` does NOT match
    NaN (they're different things in Postgres), which silently breaks any
    downstream null-checking SQL that assumes IS NULL catches all missing
    values. Every value inserted via upsert_emergency/upsert_tourism must be
    run through this first.
    """
    if isinstance(v, float) and math.isnan(v):
        return None
    return v

# Wave height thresholds, reconstructed from Sri Lankan DoM advisory language
# (per handoff: not an official published table — flag this in the report)
WAVE_SAFE_MAX = 2.0       # < 2.0m -> Safe
WAVE_CAUTION_MAX = 3.0    # 2.0-3.0m -> Caution; > 3.0m -> Dangerous

DAYLIGHT_START_HOUR = 6
DAYLIGHT_END_HOUR = 18  # exclusive upper bound, i.e. 06:00-17:59 local


# ---------------------------------------------------------------------------
# Table setup
# ---------------------------------------------------------------------------

def ensure_gold_tables(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS gold_emergency_daily (
            location_name   TEXT NOT NULL,
            date            DATE NOT NULL,
            wave_height_max NUMERIC,
            wind_speed_max  NUMERIC,
            wind_gust_max   NUMERIC,
            pressure_min    NUMERIC,
            classification  TEXT,         -- 'Safe' | 'Caution' | 'Dangerous'
            hours_covered   INTEGER,      -- sanity check: should be 24
            sea_level_height_max NUMERIC,
            PRIMARY KEY (location_name, date)
        );

        CREATE TABLE IF NOT EXISTS gold_tourism_daily (
            location_name       TEXT NOT NULL,
            date                 DATE NOT NULL,
            wave_height_mean     NUMERIC,
            wind_speed_mean      NUMERIC,
            sea_surface_temp_mean NUMERIC,
            uv_index_mean        NUMERIC,
            precipitation_sum    NUMERIC,
            suitability_score    NUMERIC,  -- 0-100, see compute_suitability_score()
            daylight_hours_covered INTEGER, -- sanity check: should be 12
            humidity_mean            NUMERIC,
            apparent_temperature_mean NUMERIC,
            air_temperature_max      NUMERIC,
            cloud_cover_mean         NUMERIC,
            dominant_weather_code    NUMERIC,
            sunshine_hours_sum       NUMERIC,
            us_aqi_mean              NUMERIC,
            PRIMARY KEY (location_name, date)
        );
        """
    )
    conn.commit()
    cur.close()
    # Same PGRST205 schema-cache gotcha as Bronze/Silver setup — reload after DDL.
    # ADD COLUMN IF NOT EXISTS here too, same reason as Silver's migration:
    # CREATE TABLE IF NOT EXISTS alone won't add columns to tables that
    # already exist in production.
    cur = conn.cursor()
    cur.execute(
        """
        ALTER TABLE gold_emergency_daily ADD COLUMN IF NOT EXISTS sea_level_height_max NUMERIC;
        ALTER TABLE gold_tourism_daily ADD COLUMN IF NOT EXISTS humidity_mean NUMERIC;
        ALTER TABLE gold_tourism_daily ADD COLUMN IF NOT EXISTS apparent_temperature_mean NUMERIC;
        ALTER TABLE gold_tourism_daily ADD COLUMN IF NOT EXISTS air_temperature_max NUMERIC;
        ALTER TABLE gold_tourism_daily ADD COLUMN IF NOT EXISTS cloud_cover_mean NUMERIC;
        ALTER TABLE gold_tourism_daily ADD COLUMN IF NOT EXISTS dominant_weather_code NUMERIC;
        ALTER TABLE gold_tourism_daily ADD COLUMN IF NOT EXISTS sunshine_hours_sum NUMERIC;
        ALTER TABLE gold_tourism_daily ADD COLUMN IF NOT EXISTS us_aqi_mean NUMERIC;
        """
    )
    conn.commit()
    cur.close()
    cur = conn.cursor()
    cur.execute("NOTIFY pgrst, 'reload schema';")
    conn.commit()
    cur.close()


# ---------------------------------------------------------------------------
# Read Silver
# ---------------------------------------------------------------------------

def load_silver(conn, location_name: str) -> pd.DataFrame:
    query = """
        SELECT timestamp, wave_height, wind_speed, wind_gust, atmospheric_pressure,
               sea_surface_temp, uv_index, precipitation, sea_level_height,
               humidity, apparent_temperature, air_temperature, cloud_cover,
               weather_code, sunshine_duration, us_aqi
        FROM silver_hourly
        WHERE location_name = %s
        ORDER BY timestamp;
    """
    df = pd.read_sql(query, conn, params=(location_name,))
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["date"] = df["timestamp"].dt.date
    df["hour"] = df["timestamp"].dt.hour
    return df


# ---------------------------------------------------------------------------
# Emergency: daily max + DMC classification
# ---------------------------------------------------------------------------

def classify_wave_height(max_wave_height: float) -> str:
    if max_wave_height is None:
        return None
    if max_wave_height < WAVE_SAFE_MAX:
        return "Safe"
    elif max_wave_height <= WAVE_CAUTION_MAX:
        return "Caution"
    else:
        return "Dangerous"


def build_emergency_daily(df: pd.DataFrame, location_name: str) -> pd.DataFrame:
    grouped = df.groupby("date").agg(
        wave_height_max=("wave_height", "max"),
        wind_speed_max=("wind_speed", "max"),
        wind_gust_max=("wind_gust", "max"),
        pressure_min=("atmospheric_pressure", "min"),
        hours_covered=("timestamp", "count"),
        sea_level_height_max=("sea_level_height", "max"),
    ).reset_index()

    grouped["classification"] = grouped["wave_height_max"].apply(classify_wave_height)
    grouped["location_name"] = location_name
    return grouped[[
        "location_name", "date", "wave_height_max", "wind_speed_max",
        "wind_gust_max", "pressure_min", "classification", "hours_covered",
        "sea_level_height_max",
    ]]


# ---------------------------------------------------------------------------
# Tourism: daylight-hours-only mean + suitability score
# ---------------------------------------------------------------------------

# HCI:Beach rating tables — exact breakpoints from Gunathilake et al. 2023
# ("Performances of Holiday Climate Index (HCI) for Urban and Beach
# Destinations in Sri Lanka under Changing Climate", Climate 11(3):48),
# Table A1 — itself adapted from Scott, Rutty, Amelung & Tang (2016) and
# Rutty et al. (2020)'s original HCI:Beach. This is the same index applied
# by that paper directly to Sri Lankan beach destinations using real DoM
# climate data (1990-2018), giving published scores (26-61 for west/south
# coast beaches across monsoon seasons) to sanity-check against.
#
# Each (min, max, rate) band maps a raw value to a rating on a roughly
# -10..10 scale — negative ratings ARE part of the real table (extreme
# heat/cold/rain/wind score below zero, not just "0"), not a bug.
_TC_TABLE = [
    (-math.inf, 9.9, -10), (10, 14.99, -5), (15, 16.99, 0), (17, 17.99, 1),
    (18, 18.99, 2), (19, 19.99, 3), (20, 20.99, 4), (21, 21.99, 5),
    (22, 22.99, 6), (23, 25.99, 7), (26, 27.99, 9), (28, 30.99, 10),
    (31, 32.99, 9), (33, 33.99, 8), (34, 34.99, 7), (35, 35.99, 6),
    (36, 36.99, 5), (37, 37.99, 4), (38, 38.99, 2), (39, math.inf, 0),
]

_AESTHETIC_TABLE = [
    (0, 0.99, 8), (1, 14.99, 9), (15, 25.99, 10), (26, 35.99, 9),
    (36, 45.99, 8), (46, 55.99, 7), (56, 65.99, 6), (66, 75.99, 5),
    (76, 85.99, 4), (86, 95.99, 3), (96, 100, 2),
]

_PRECIPITATION_TABLE = [
    (0, 0.01, 10), (0.01, 2.99, 9), (3, 5.99, 8), (6, 8.99, 6),
    (9, 11.99, 4), (12, 24.99, 0), (25, math.inf, -1),
]

_WIND_TABLE = [
    (0, 0.59, 8), (0.6, 9.99, 10), (10, 19.99, 9), (20, 29.99, 8),
    (30, 39.99, 6), (40, 49.99, 3), (50, 69.99, 0), (70, math.inf, -10),
]


def _rate_from_table(value, table):
    if value is None or pd.isna(value):
        return None
    for lo, hi, rate in table:
        if lo <= value <= hi:
            return rate
    return table[0][2] if value < table[0][0] else table[-1][2]


def thermal_comfort_value(t_max: float, rh_mean: float) -> float:
    """TC per Scott/Rutty et al.'s humidex-style formula. T is daily MAX
    air temperature — deliberately NOT apparent_temperature, which would
    double-count humidity since this formula already does its own
    humidity adjustment. H is mean relative humidity (%)."""
    return t_max + (5 / 9) * (
        6.112 * 10 ** ((7.5 * t_max) / (237.7 + t_max)) * (rh_mean / 100) - 10
    )


def compute_suitability_score(row) -> float:
    """
    HCI:Beach = 2(TC) + 4(A) + 3(P) + W — see _TC_TABLE etc. above for the
    citation. Replaces the earlier ad-hoc placeholder formula (which
    scored wave height, wind, rain, and UV with hand-picked coefficients)
    with a cited, peer-reviewed methodology.

    The raw weighted sum can go as low as -25 (matching the paper's own
    "Dangerous" band, e.g. extreme heat + full cloud cover + heavy rain +
    high wind all scoring negative simultaneously); clamped to a 0 floor
    here since this column is documented/consumed elsewhere as 0-100.

    Returns None (not 0) when a required input is missing, rather than
    silently scoring on partial data — a missing day should show as
    "no score" on the dashboard, not a fake low score.
    """
    t_max = row["air_temperature_max"]
    rh_mean = row["humidity_mean"]
    cloud_mean = row["cloud_cover_mean"]
    precip_sum = row["precipitation_sum"]
    wind_mean = row["wind_speed_mean"]

    tc_rate = None
    if pd.notna(t_max) and pd.notna(rh_mean):
        tc_rate = _rate_from_table(thermal_comfort_value(t_max, rh_mean), _TC_TABLE)

    a_rate = _rate_from_table(cloud_mean, _AESTHETIC_TABLE)
    p_rate = _rate_from_table(precip_sum, _PRECIPITATION_TABLE)
    w_rate = _rate_from_table(wind_mean, _WIND_TABLE)

    if any(r is None for r in (tc_rate, a_rate, p_rate, w_rate)):
        return None

    raw_score = 2 * tc_rate + 4 * a_rate + 3 * p_rate + w_rate
    return round(max(raw_score, 0), 1)


def _mode_or_none(s: pd.Series):
    """Weather conditions aren't meaningfully averageable — the mode (most
    common code during daylight hours) answers "what did today mostly
    look like", which a mean of numeric codes would not."""
    m = s.mode()
    return m.iloc[0] if not m.empty else None


def build_tourism_daily(df: pd.DataFrame, location_name: str) -> pd.DataFrame:
    daylight = df[(df["hour"] >= DAYLIGHT_START_HOUR) & (df["hour"] < DAYLIGHT_END_HOUR)]

    grouped = daylight.groupby("date").agg(
        wave_height_mean=("wave_height", "mean"),
        wind_speed_mean=("wind_speed", "mean"),
        sea_surface_temp_mean=("sea_surface_temp", "mean"),
        uv_index_mean=("uv_index", "mean"),
        precipitation_sum=("precipitation", "sum"),
        daylight_hours_covered=("timestamp", "count"),
        humidity_mean=("humidity", "mean"),
        apparent_temperature_mean=("apparent_temperature", "mean"),
        air_temperature_max=("air_temperature", "max"),
        cloud_cover_mean=("cloud_cover", "mean"),
        dominant_weather_code=("weather_code", _mode_or_none),
        sunshine_hours_sum=("sunshine_duration", lambda s: round(s.sum() / 3600, 2)),
        us_aqi_mean=("us_aqi", "mean"),
    ).reset_index()

    grouped["suitability_score"] = grouped.apply(compute_suitability_score, axis=1)
    grouped["location_name"] = location_name
    return grouped[[
        "location_name", "date", "wave_height_mean", "wind_speed_mean",
        "sea_surface_temp_mean", "uv_index_mean", "precipitation_sum",
        "suitability_score", "daylight_hours_covered",
        "humidity_mean", "apparent_temperature_mean", "air_temperature_max", "cloud_cover_mean",
        "dominant_weather_code", "sunshine_hours_sum", "us_aqi_mean",
    ]]


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------

def upsert_emergency(conn, df: pd.DataFrame):
    """Batched via execute_values instead of one cur.execute() per row —
    the row-by-row version measured at ~56s for a single location's 617
    rows (one network round-trip per row over the Supabase pooler), which
    extrapolated to ~14 minutes across 15 locations for this function
    alone. Bulk-inserting all rows in one round-trip does the same work
    in a fraction of a second — the DB work itself was never the
    bottleneck, the per-row round-trip count was.
    """
    if df.empty:
        return
    cur = conn.cursor()
    rows = [
        (
            clean_value(r["location_name"]), clean_value(r["date"]), clean_value(r["wave_height_max"]),
            clean_value(r["wind_speed_max"]), clean_value(r["wind_gust_max"]), clean_value(r["pressure_min"]),
            clean_value(r["classification"]), int(r["hours_covered"]),
            clean_value(r["sea_level_height_max"]),
        )
        for _, r in df.iterrows()
    ]
    execute_values(
        cur,
        """
        INSERT INTO gold_emergency_daily
            (location_name, date, wave_height_max, wind_speed_max,
             wind_gust_max, pressure_min, classification, hours_covered,
             sea_level_height_max)
        VALUES %s
        ON CONFLICT (location_name, date) DO UPDATE SET
            wave_height_max = EXCLUDED.wave_height_max,
            wind_speed_max = EXCLUDED.wind_speed_max,
            wind_gust_max = EXCLUDED.wind_gust_max,
            pressure_min = EXCLUDED.pressure_min,
            classification = EXCLUDED.classification,
            hours_covered = EXCLUDED.hours_covered,
            sea_level_height_max = EXCLUDED.sea_level_height_max;
        """,
        rows,
        page_size=1000,
    )
    conn.commit()
    cur.close()


def upsert_tourism(conn, df: pd.DataFrame):
    """Batched via execute_values — see upsert_emergency's docstring for
    why (measured ~38s row-by-row for one location's 617 rows)."""
    if df.empty:
        return
    cur = conn.cursor()
    rows = [
        (
            clean_value(r["location_name"]), clean_value(r["date"]), clean_value(r["wave_height_mean"]),
            clean_value(r["wind_speed_mean"]), clean_value(r["sea_surface_temp_mean"]),
            clean_value(r["uv_index_mean"]), clean_value(r["precipitation_sum"]),
            clean_value(r["suitability_score"]), int(r["daylight_hours_covered"]),
            clean_value(r["humidity_mean"]), clean_value(r["apparent_temperature_mean"]),
            clean_value(r["air_temperature_max"]), clean_value(r["cloud_cover_mean"]),
            clean_value(r["dominant_weather_code"]), clean_value(r["sunshine_hours_sum"]),
            clean_value(r["us_aqi_mean"]),
        )
        for _, r in df.iterrows()
    ]
    execute_values(
        cur,
        """
        INSERT INTO gold_tourism_daily
            (location_name, date, wave_height_mean, wind_speed_mean,
             sea_surface_temp_mean, uv_index_mean, precipitation_sum,
             suitability_score, daylight_hours_covered,
             humidity_mean, apparent_temperature_mean, air_temperature_max, cloud_cover_mean,
             dominant_weather_code, sunshine_hours_sum, us_aqi_mean)
        VALUES %s
        ON CONFLICT (location_name, date) DO UPDATE SET
            wave_height_mean = EXCLUDED.wave_height_mean,
            wind_speed_mean = EXCLUDED.wind_speed_mean,
            sea_surface_temp_mean = EXCLUDED.sea_surface_temp_mean,
            uv_index_mean = EXCLUDED.uv_index_mean,
            precipitation_sum = EXCLUDED.precipitation_sum,
            suitability_score = EXCLUDED.suitability_score,
            daylight_hours_covered = EXCLUDED.daylight_hours_covered,
            humidity_mean = EXCLUDED.humidity_mean,
            apparent_temperature_mean = EXCLUDED.apparent_temperature_mean,
            air_temperature_max = EXCLUDED.air_temperature_max,
            cloud_cover_mean = EXCLUDED.cloud_cover_mean,
            dominant_weather_code = EXCLUDED.dominant_weather_code,
            sunshine_hours_sum = EXCLUDED.sunshine_hours_sum,
            us_aqi_mean = EXCLUDED.us_aqi_mean;
        """,
        rows,
        page_size=1000,
    )
    conn.commit()
    cur.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# Location membership is derived directly from fetch_data.py's LOCATIONS /
# TOURISM_ONLY — NOT hardcoded here. This fixes two real bugs found via
# validate_gold.py:
#   1. Arugam Bay was wrongly guessed as "shared multi-mode" in an earlier
#      version of this file. It's actually Tourism-only per fetch_data.py's
#      TOURISM_ONLY set (skips marine_ocean by design) — its 100% null
#      sea_surface_temp_mean in gold_tourism_daily is correct, not a bug.
#   2. Tangalle, Matara, and Puttalam were missing from both hardcoded lists
#      entirely — they have real Silver data but never got Gold rows built.
#
# Default below: Emergency and Tourism both run for ALL 15 locations, since
# the underlying metrics each mode needs (wave_height, wind_speed,
# precipitation, uv_index) are fetched for every location regardless of the
# TOURISM_ONLY flag — that flag only ever controls whether marine_ocean
# (sea_surface_temp / ocean_current) gets fetched, not mode eligibility.
# If your product design actually restricts Emergency mode to a subset of
# locations, narrow ALL_LOCATION_NAMES below for EMERGENCY_LOCATIONS
# specifically — this default errs toward not silently dropping locations.

from fetch_data import LOCATIONS, TOURISM_ONLY, connect_with_hard_timeout

ALL_LOCATION_NAMES = [loc["name"] for loc in LOCATIONS]

EMERGENCY_LOCATIONS = ALL_LOCATION_NAMES
TOURISM_LOCATIONS = ALL_LOCATION_NAMES


def _run_with_reconnect(fn, *args, retries=3):
    """A single long-lived connection across all 15 locations x 2 modes
    (~15-20 minutes of row-by-row upserts) was observed dropping mid-run
    with 'server closed the connection unexpectedly' — a transient
    Supabase pooler timeout, not a data problem (everything before the
    drop had already committed successfully). Retrying with a fresh
    connection is simpler and more robust than trying to keep one
    connection alive for the whole run.
    """
    for attempt in range(retries):
        # Hard wall-clock timeout, not just connect_timeout — see
        # fetch_data.connect_with_hard_timeout's docstring for why
        # connect_timeout alone wasn't enough (a DNS-level hang isn't
        # bounded by it).
        conn = connect_with_hard_timeout(SUPABASE_DB_URL)
        try:
            # If THIS connection dies mid-transaction like the last run
            # did, don't let the orphaned backend sit "idle in
            # transaction" indefinitely holding locks that block a future
            # run's ALTER TABLE (exactly what happened: a crashed upsert
            # blocked ensure_gold_tables() for 14+ minutes until manually
            # found and killed via pg_terminate_backend). Let Postgres
            # clean up after itself instead.
            with conn.cursor() as c:
                c.execute("SET idle_in_transaction_session_timeout = '30s';")
            conn.commit()
            result = fn(conn, *args)
            conn.close()
            return result
        except psycopg2.OperationalError as e:
            conn.close()
            if attempt == retries - 1:
                raise
            print(f"  connection dropped ({e}); retrying ({attempt + 2}/{retries})...")


def main():
    _run_with_reconnect(ensure_gold_tables)

    for location in EMERGENCY_LOCATIONS:
        print(f"[Emergency] Aggregating {location}...")
        silver_df = _run_with_reconnect(load_silver, location)
        if silver_df.empty:
            print(f"  no silver rows for {location}, skipping")
            continue
        gold_df = build_emergency_daily(silver_df, location)
        _run_with_reconnect(upsert_emergency, gold_df)
        print(f"  wrote {len(gold_df)} daily rows")

    for location in TOURISM_LOCATIONS:
        print(f"[Tourism] Aggregating {location}...")
        silver_df = _run_with_reconnect(load_silver, location)
        if silver_df.empty:
            print(f"  no silver rows for {location}, skipping")
            continue
        gold_df = build_tourism_daily(silver_df, location)
        _run_with_reconnect(upsert_tourism, gold_df)
        print(f"  wrote {len(gold_df)} daily rows")

    print("\nDone. Spot-check a few rows against validation_report.md's known dates (e.g. Ditwah landfall) before trusting this.")


if __name__ == "__main__":
    main()