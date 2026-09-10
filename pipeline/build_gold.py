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

*** COLUMN NAMES: confirmed atmospheric_pressure (not "pressure") from real ***
*** silver_hourly schema. Other columns (wave_height, wind_speed, wind_gust, ***
*** air_temperature, uv_index, precipitation, location_name, timestamp) are ***
*** still assumptions pending an information_schema.columns check. ***
"""

import os
from dotenv import load_dotenv
import psycopg2
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
            PRIMARY KEY (location_name, date)
        );
        """
    )
    conn.commit()
    cur.close()
    # Same PGRST205 schema-cache gotcha as Bronze/Silver setup — reload after DDL
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
               sea_surface_temp, uv_index, precipitation
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
    ).reset_index()

    grouped["classification"] = grouped["wave_height_max"].apply(classify_wave_height)
    grouped["location_name"] = location_name
    return grouped[[
        "location_name", "date", "wave_height_max", "wind_speed_max",
        "wind_gust_max", "pressure_min", "classification", "hours_covered",
    ]]


# ---------------------------------------------------------------------------
# Tourism: daylight-hours-only mean + suitability score
# ---------------------------------------------------------------------------

def compute_suitability_score(row) -> float:
    """
    Placeholder 0-100 beach suitability formula. Not specified in the handoff —
    treat this as a first draft to refine, not a settled design decision.
    Penalizes rough seas, strong wind, rain, and extreme UV.
    Note: silver_hourly has no air_temperature column (never fetched from
    Weather API into Silver) — sea_surface_temp is used as a proxy signal
    but isn't currently scored in this formula; add a term here if you
    want water temperature to factor into the suitability score.
    """
    score = 100.0

    # Wave height penalty (calmer = better for tourism, unlike Emergency's danger framing)
    if pd.notna(row["wave_height_mean"]):
        score -= min(row["wave_height_mean"] * 15, 40)

    # Wind penalty (km/h, per the corrected Silver units)
    if pd.notna(row["wind_speed_mean"]):
        score -= min(max(row["wind_speed_mean"] - 15, 0) * 0.8, 25)

    # Rain penalty
    if pd.notna(row["precipitation_sum"]):
        score -= min(row["precipitation_sum"] * 5, 25)

    # UV: too high is a caution, not necessarily "bad", so a mild penalty only above 8
    if pd.notna(row["uv_index_mean"]) and row["uv_index_mean"] > 8:
        score -= min((row["uv_index_mean"] - 8) * 3, 10)

    return round(max(score, 0), 1)


def build_tourism_daily(df: pd.DataFrame, location_name: str) -> pd.DataFrame:
    daylight = df[(df["hour"] >= DAYLIGHT_START_HOUR) & (df["hour"] < DAYLIGHT_END_HOUR)]

    grouped = daylight.groupby("date").agg(
        wave_height_mean=("wave_height", "mean"),
        wind_speed_mean=("wind_speed", "mean"),
        sea_surface_temp_mean=("sea_surface_temp", "mean"),
        uv_index_mean=("uv_index", "mean"),
        precipitation_sum=("precipitation", "sum"),
        daylight_hours_covered=("timestamp", "count"),
    ).reset_index()

    grouped["suitability_score"] = grouped.apply(compute_suitability_score, axis=1)
    grouped["location_name"] = location_name
    return grouped[[
        "location_name", "date", "wave_height_mean", "wind_speed_mean",
        "sea_surface_temp_mean", "uv_index_mean", "precipitation_sum",
        "suitability_score", "daylight_hours_covered",
    ]]


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------

def upsert_emergency(conn, df: pd.DataFrame):
    cur = conn.cursor()
    for _, r in df.iterrows():
        cur.execute(
            """
            INSERT INTO gold_emergency_daily
                (location_name, date, wave_height_max, wind_speed_max,
                 wind_gust_max, pressure_min, classification, hours_covered)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (location_name, date) DO UPDATE SET
                wave_height_max = EXCLUDED.wave_height_max,
                wind_speed_max = EXCLUDED.wind_speed_max,
                wind_gust_max = EXCLUDED.wind_gust_max,
                pressure_min = EXCLUDED.pressure_min,
                classification = EXCLUDED.classification,
                hours_covered = EXCLUDED.hours_covered;
            """,
            (
                clean_value(r["location_name"]), clean_value(r["date"]), clean_value(r["wave_height_max"]),
                clean_value(r["wind_speed_max"]), clean_value(r["wind_gust_max"]), clean_value(r["pressure_min"]),
                clean_value(r["classification"]), int(r["hours_covered"]),
            ),
        )
    conn.commit()
    cur.close()


def upsert_tourism(conn, df: pd.DataFrame):
    cur = conn.cursor()
    for _, r in df.iterrows():
        cur.execute(
            """
            INSERT INTO gold_tourism_daily
                (location_name, date, wave_height_mean, wind_speed_mean,
                 sea_surface_temp_mean, uv_index_mean, precipitation_sum,
                 suitability_score, daylight_hours_covered)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (location_name, date) DO UPDATE SET
                wave_height_mean = EXCLUDED.wave_height_mean,
                wind_speed_mean = EXCLUDED.wind_speed_mean,
                sea_surface_temp_mean = EXCLUDED.sea_surface_temp_mean,
                uv_index_mean = EXCLUDED.uv_index_mean,
                precipitation_sum = EXCLUDED.precipitation_sum,
                suitability_score = EXCLUDED.suitability_score,
                daylight_hours_covered = EXCLUDED.daylight_hours_covered;
            """,
            (
                clean_value(r["location_name"]), clean_value(r["date"]), clean_value(r["wave_height_mean"]),
                clean_value(r["wind_speed_mean"]), clean_value(r["sea_surface_temp_mean"]),
                clean_value(r["uv_index_mean"]), clean_value(r["precipitation_sum"]),
                clean_value(r["suitability_score"]), int(r["daylight_hours_covered"]),
            ),
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

from fetch_data import LOCATIONS, TOURISM_ONLY

ALL_LOCATION_NAMES = [loc["name"] for loc in LOCATIONS]

EMERGENCY_LOCATIONS = ALL_LOCATION_NAMES
TOURISM_LOCATIONS = ALL_LOCATION_NAMES


def main():
    conn = psycopg2.connect(SUPABASE_DB_URL)
    ensure_gold_tables(conn)

    for location in EMERGENCY_LOCATIONS:
        print(f"[Emergency] Aggregating {location}...")
        silver_df = load_silver(conn, location)
        if silver_df.empty:
            print(f"  no silver rows for {location}, skipping")
            continue
        gold_df = build_emergency_daily(silver_df, location)
        upsert_emergency(conn, gold_df)
        print(f"  wrote {len(gold_df)} daily rows")

    for location in TOURISM_LOCATIONS:
        print(f"[Tourism] Aggregating {location}...")
        silver_df = load_silver(conn, location)
        if silver_df.empty:
            print(f"  no silver rows for {location}, skipping")
            continue
        gold_df = build_tourism_daily(silver_df, location)
        upsert_tourism(conn, gold_df)
        print(f"  wrote {len(gold_df)} daily rows")

    conn.close()
    print("\nDone. Spot-check a few rows against validation_report.md's known dates (e.g. Ditwah landfall) before trusting this.")


if __name__ == "__main__":
    main()