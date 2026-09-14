"""
fetch_marine_forecast.py — CoastalPulse Fisherman/Emergency/Tourism forecast
(Open-Meteo, not SARIMA).

Queries Open-Meteo's live FORECAST endpoints (marine-api.open-meteo.com and
api.open-meteo.com, forecast_days=8 — no start_date/end_date, unlike
fetch_data.py's historical/reanalysis reads) and writes the result to
`marine_forecasts` (hourly — what pages/fisherman.py reads for its forecast
chart), plus two small daily aggregates — `emergency_forecast_daily` and
`tourism_forecast_daily` — for Emergency's and Tourism's forward-looking
outlook strips. Real physics-based operational ocean/wave/weather models
(ECMWF WAM, NOAA GFS Wave, MeteoFrance MFWAM, DWD EWAM/GWAM, blended by
Open-Meteo), not the per-location SARIMA fit in build_forecasts.py. SARIMA
keeps running unchanged (pipeline/build_forecasts.py) — its output feeds
the Analytics page's forecasting case study instead.

The daily aggregates deliberately reuse pipeline/build_gold.py's own
classify_wave_height() / compute_suitability_score() functions rather than
reimplementing the thresholds/formula here — same reasoning as
build_forecasts.py already importing build_gold._run_with_reconnect: one
source of truth for what "Dangerous" or "Good" means, whether the
underlying data is observed (Gold) or forecast (here).

FORECAST_DAYS = 8 is Open-Meteo Marine API's documented maximum horizon
(verified against https://open-meteo.com/en/docs/marine-weather-api, which
also confirms secondary_swell_wave_* has real data for Sri Lanka locations
but tertiary_swell_wave_* and wave_peak_period do not under the default
model blend here — checked directly against live API responses for all 15
locations, not just one, before deciding to include secondary swell and
skip tertiary/peak period rather than ship columns that sit permanently
null everywhere). The weather variables added for Emergency/Tourism
(temperature, humidity, cloud cover, precipitation, surface pressure) were
checked the same way, across all 15 locations — all present everywhere.

All 15 locations, unlike fetch_data.py's marine_ocean split — wave/swell
data doesn't depend on the sea-surface-temp/ocean-current fields the 5
TOURISM_ONLY locations skip, so there's no tourism-only branching here.

Tables are delete+insert per location on every run (same reasoning as
build_forecasts.py's `forecasts` table): they should always hold exactly
the latest forecast, never accumulate stale future-dated rows from a
previous run.
"""

import os

from dotenv import load_dotenv
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from build_gold import (
    _run_with_reconnect, clean_value,
    classify_wave_height, compute_suitability_score,
    DAYLIGHT_START_HOUR, DAYLIGHT_END_HOUR,
)
from fetch_data import LOCATIONS, connect_with_hard_timeout, fetch

load_dotenv()

SUPABASE_DB_URL = os.environ["SUPABASE_DB_URL"]

ALL_LOCATION_NAMES = [loc["name"] for loc in LOCATIONS]

FORECAST_DAYS = 8

MARINE_HOURLY_VARS = (
    "wave_height,wave_period,wave_direction,"
    "sea_level_height_msl,"
    "swell_wave_height,swell_wave_period,swell_wave_direction,"
    "secondary_swell_wave_height,secondary_swell_wave_period,secondary_swell_wave_direction,"
    "wind_wave_height,wind_wave_period,wind_wave_direction"
)
# WIND_HOURLY_VARS was wind-only when this table fed only Fisherman.
# Extended for Emergency (surface_pressure, for gauge parity with its
# pressure_min display) and Tourism (temperature_2m, relative_humidity_2m,
# cloud_cover, precipitation — the exact inputs compute_suitability_score
# needs; wind_speed_10m already covers Tourism's wind input).
WEATHER_HOURLY_VARS = (
    "wind_speed_10m,wind_gusts_10m,wind_direction_10m,"
    "temperature_2m,relative_humidity_2m,cloud_cover,precipitation,surface_pressure"
)


# ---------------------------------------------------------------------------
# Table setup
# ---------------------------------------------------------------------------

def ensure_marine_forecasts_table(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS marine_forecasts (
            location_name             TEXT NOT NULL,
            forecast_time             TIMESTAMPTZ NOT NULL,
            generated_at              TIMESTAMPTZ NOT NULL,
            wave_height                NUMERIC,
            wave_period                NUMERIC,
            wave_direction              NUMERIC,
            sea_level_height            NUMERIC,
            swell_height                NUMERIC,
            swell_period                NUMERIC,
            swell_direction             NUMERIC,
            secondary_swell_height      NUMERIC,
            secondary_swell_period      NUMERIC,
            secondary_swell_direction   NUMERIC,
            wind_wave_height            NUMERIC,
            wind_wave_period            NUMERIC,
            wind_wave_direction         NUMERIC,
            wind_speed                  NUMERIC,
            wind_gust                   NUMERIC,
            wind_direction               NUMERIC,
            PRIMARY KEY (location_name, forecast_time)
        );

        CREATE TABLE IF NOT EXISTS emergency_forecast_daily (
            location_name        TEXT NOT NULL,
            date                  DATE NOT NULL,
            generated_at          TIMESTAMPTZ NOT NULL,
            wave_height_max       NUMERIC,
            wind_speed_max        NUMERIC,
            wind_gust_max         NUMERIC,
            pressure_min          NUMERIC,
            classification        TEXT,
            hours_covered         INTEGER,
            sea_level_height_max  NUMERIC,
            PRIMARY KEY (location_name, date)
        );

        CREATE TABLE IF NOT EXISTS tourism_forecast_daily (
            location_name          TEXT NOT NULL,
            date                    DATE NOT NULL,
            generated_at            TIMESTAMPTZ NOT NULL,
            wave_height_mean        NUMERIC,
            wind_speed_mean         NUMERIC,
            precipitation_sum       NUMERIC,
            suitability_score       NUMERIC,
            daylight_hours_covered  INTEGER,
            humidity_mean           NUMERIC,
            air_temperature_max     NUMERIC,
            cloud_cover_mean        NUMERIC,
            PRIMARY KEY (location_name, date)
        );
        """
    )
    # Added after marine_forecasts already existed in production — additive
    # migration, same ALTER-TABLE-ADD-COLUMN-IF-NOT-EXISTS pattern
    # fetch_data.py/build_gold.py already use for this exact situation.
    cur.execute(
        """
        ALTER TABLE marine_forecasts ADD COLUMN IF NOT EXISTS air_temperature NUMERIC;
        ALTER TABLE marine_forecasts ADD COLUMN IF NOT EXISTS humidity NUMERIC;
        ALTER TABLE marine_forecasts ADD COLUMN IF NOT EXISTS cloud_cover NUMERIC;
        ALTER TABLE marine_forecasts ADD COLUMN IF NOT EXISTS precipitation NUMERIC;
        ALTER TABLE marine_forecasts ADD COLUMN IF NOT EXISTS surface_pressure NUMERIC;
        """
    )
    conn.commit()
    cur.close()
    cur = conn.cursor()
    cur.execute("NOTIFY pgrst, 'reload schema';")
    conn.commit()
    cur.close()


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

class TimestampMismatchError(Exception):
    """Same guard as fetch_data.py's build_silver_rows — refuse to zip two
    payloads by positional index if their hourly time arrays don't match
    exactly, rather than risk silently pairing wrong-hour values."""
    pass


def fetch_location_forecast(loc):
    common = dict(
        latitude=loc["lat"],
        longitude=loc["lon"],
        forecast_days=FORECAST_DAYS,
        timezone="Asia/Colombo",
    )
    marine = fetch("https://marine-api.open-meteo.com/v1/marine", {**common, "hourly": MARINE_HOURLY_VARS})
    weather = fetch("https://api.open-meteo.com/v1/forecast", {**common, "hourly": WEATHER_HOURLY_VARS})
    if not marine or not weather:
        return None
    return marine, weather


def build_forecast_rows(name, marine, weather):
    times = marine["hourly"]["time"]
    if weather["hourly"]["time"] != times:
        raise TimestampMismatchError(
            f"{name}: weather forecast hourly timestamps do not match marine forecast's "
            f"(lengths: {len(weather['hourly']['time'])} vs {len(times)}). Refusing to "
            "build rows for this location — would silently misalign data."
        )

    generated_at = pd.Timestamp.now(tz="UTC")
    mh, wh = marine["hourly"], weather["hourly"]
    rows = []
    for i in range(len(times)):
        rows.append({
            "location_name": name,
            "forecast_time": times[i],
            "generated_at": generated_at,
            "wave_height": mh["wave_height"][i],
            "wave_period": mh["wave_period"][i],
            "wave_direction": mh["wave_direction"][i],
            "sea_level_height": mh["sea_level_height_msl"][i],
            "swell_height": mh["swell_wave_height"][i],
            "swell_period": mh["swell_wave_period"][i],
            "swell_direction": mh["swell_wave_direction"][i],
            "secondary_swell_height": mh["secondary_swell_wave_height"][i],
            "secondary_swell_period": mh["secondary_swell_wave_period"][i],
            "secondary_swell_direction": mh["secondary_swell_wave_direction"][i],
            "wind_wave_height": mh["wind_wave_height"][i],
            "wind_wave_period": mh["wind_wave_period"][i],
            "wind_wave_direction": mh["wind_wave_direction"][i],
            "wind_speed": wh["wind_speed_10m"][i],
            "wind_gust": wh["wind_gusts_10m"][i],
            "wind_direction": wh["wind_direction_10m"][i],
            "air_temperature": wh["temperature_2m"][i],
            "humidity": wh["relative_humidity_2m"][i],
            "cloud_cover": wh["cloud_cover"][i],
            "precipitation": wh["precipitation"][i],
            "surface_pressure": wh["surface_pressure"][i],
        })
    return rows


# ---------------------------------------------------------------------------
# Daily aggregates for Emergency / Tourism — reuses build_gold.py's own
# classify_wave_height() / compute_suitability_score() rather than
# reimplementing them. Aggregated directly from the in-memory hourly `rows`
# (forecast_time as returned by Open-Meteo — naive Asia/Colombo local wall-
# clock strings, same convention silver_hourly's timestamps already use),
# not re-read from the DB, so date-bucketing stays in the same local-time
# frame the rest of this pipeline already assumes.
# ---------------------------------------------------------------------------

def build_emergency_forecast_daily(location_name, rows):
    df = pd.DataFrame(rows)
    df["forecast_time"] = pd.to_datetime(df["forecast_time"])
    df["date"] = df["forecast_time"].dt.date

    grouped = df.groupby("date").agg(
        wave_height_max=("wave_height", "max"),
        wind_speed_max=("wind_speed", "max"),
        wind_gust_max=("wind_gust", "max"),
        pressure_min=("surface_pressure", "min"),
        hours_covered=("forecast_time", "count"),
        sea_level_height_max=("sea_level_height", "max"),
    ).reset_index()

    grouped["classification"] = grouped["wave_height_max"].apply(classify_wave_height)
    grouped["location_name"] = location_name
    grouped["generated_at"] = df["generated_at"].iloc[0]
    return grouped


def build_tourism_forecast_daily(location_name, rows):
    df = pd.DataFrame(rows)
    df["forecast_time"] = pd.to_datetime(df["forecast_time"])
    df["date"] = df["forecast_time"].dt.date
    df["hour"] = df["forecast_time"].dt.hour
    daylight = df[(df["hour"] >= DAYLIGHT_START_HOUR) & (df["hour"] < DAYLIGHT_END_HOUR)]

    grouped = daylight.groupby("date").agg(
        wave_height_mean=("wave_height", "mean"),
        wind_speed_mean=("wind_speed", "mean"),
        precipitation_sum=("precipitation", "sum"),
        daylight_hours_covered=("forecast_time", "count"),
        humidity_mean=("humidity", "mean"),
        air_temperature_max=("air_temperature", "max"),
        cloud_cover_mean=("cloud_cover", "mean"),
    ).reset_index()

    grouped["suitability_score"] = grouped.apply(compute_suitability_score, axis=1)
    grouped["location_name"] = location_name
    grouped["generated_at"] = df["generated_at"].iloc[0]
    return grouped


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------

def upsert_marine_forecast(conn, location_name, rows):
    if not rows:
        return
    cur = conn.cursor()
    # Delete-then-insert, not ON CONFLICT alone — a location's rows should
    # always be exactly this run's 8-day forecast, not accumulate rows from
    # a shorter-horizon prior run at stale future timestamps.
    cur.execute("DELETE FROM marine_forecasts WHERE location_name = %s;", (location_name,))
    values = [
        (
            r["location_name"], r["forecast_time"], r["generated_at"],
            clean_value(r["wave_height"]), clean_value(r["wave_period"]), clean_value(r["wave_direction"]),
            clean_value(r["sea_level_height"]),
            clean_value(r["swell_height"]), clean_value(r["swell_period"]), clean_value(r["swell_direction"]),
            clean_value(r["secondary_swell_height"]), clean_value(r["secondary_swell_period"]), clean_value(r["secondary_swell_direction"]),
            clean_value(r["wind_wave_height"]), clean_value(r["wind_wave_period"]), clean_value(r["wind_wave_direction"]),
            clean_value(r["wind_speed"]), clean_value(r["wind_gust"]), clean_value(r["wind_direction"]),
            clean_value(r["air_temperature"]), clean_value(r["humidity"]), clean_value(r["cloud_cover"]),
            clean_value(r["precipitation"]), clean_value(r["surface_pressure"]),
        )
        for r in rows
    ]
    execute_values(
        cur,
        """
        INSERT INTO marine_forecasts
            (location_name, forecast_time, generated_at, wave_height, wave_period, wave_direction,
             sea_level_height, swell_height, swell_period, swell_direction,
             secondary_swell_height, secondary_swell_period, secondary_swell_direction,
             wind_wave_height, wind_wave_period, wind_wave_direction,
             wind_speed, wind_gust, wind_direction,
             air_temperature, humidity, cloud_cover, precipitation, surface_pressure)
        VALUES %s
        ON CONFLICT (location_name, forecast_time) DO UPDATE SET
            generated_at = EXCLUDED.generated_at,
            wave_height = EXCLUDED.wave_height, wave_period = EXCLUDED.wave_period, wave_direction = EXCLUDED.wave_direction,
            sea_level_height = EXCLUDED.sea_level_height,
            swell_height = EXCLUDED.swell_height, swell_period = EXCLUDED.swell_period, swell_direction = EXCLUDED.swell_direction,
            secondary_swell_height = EXCLUDED.secondary_swell_height, secondary_swell_period = EXCLUDED.secondary_swell_period,
            secondary_swell_direction = EXCLUDED.secondary_swell_direction,
            wind_wave_height = EXCLUDED.wind_wave_height, wind_wave_period = EXCLUDED.wind_wave_period,
            wind_wave_direction = EXCLUDED.wind_wave_direction,
            wind_speed = EXCLUDED.wind_speed, wind_gust = EXCLUDED.wind_gust, wind_direction = EXCLUDED.wind_direction,
            air_temperature = EXCLUDED.air_temperature, humidity = EXCLUDED.humidity, cloud_cover = EXCLUDED.cloud_cover,
            precipitation = EXCLUDED.precipitation, surface_pressure = EXCLUDED.surface_pressure;
        """,
        values,
        page_size=1000,
    )
    conn.commit()
    cur.close()


def upsert_emergency_forecast(conn, location_name, df: pd.DataFrame):
    if df.empty:
        return
    cur = conn.cursor()
    cur.execute("DELETE FROM emergency_forecast_daily WHERE location_name = %s;", (location_name,))
    values = [
        (
            r["location_name"], r["date"], r["generated_at"],
            clean_value(r["wave_height_max"]), clean_value(r["wind_speed_max"]), clean_value(r["wind_gust_max"]),
            clean_value(r["pressure_min"]), clean_value(r["classification"]), int(r["hours_covered"]),
            clean_value(r["sea_level_height_max"]),
        )
        for _, r in df.iterrows()
    ]
    execute_values(
        cur,
        """
        INSERT INTO emergency_forecast_daily
            (location_name, date, generated_at, wave_height_max, wind_speed_max,
             wind_gust_max, pressure_min, classification, hours_covered, sea_level_height_max)
        VALUES %s
        ON CONFLICT (location_name, date) DO UPDATE SET
            generated_at = EXCLUDED.generated_at,
            wave_height_max = EXCLUDED.wave_height_max, wind_speed_max = EXCLUDED.wind_speed_max,
            wind_gust_max = EXCLUDED.wind_gust_max, pressure_min = EXCLUDED.pressure_min,
            classification = EXCLUDED.classification, hours_covered = EXCLUDED.hours_covered,
            sea_level_height_max = EXCLUDED.sea_level_height_max;
        """,
        values,
        page_size=1000,
    )
    conn.commit()
    cur.close()


def upsert_tourism_forecast(conn, location_name, df: pd.DataFrame):
    if df.empty:
        return
    cur = conn.cursor()
    cur.execute("DELETE FROM tourism_forecast_daily WHERE location_name = %s;", (location_name,))
    values = [
        (
            r["location_name"], r["date"], r["generated_at"],
            clean_value(r["wave_height_mean"]), clean_value(r["wind_speed_mean"]), clean_value(r["precipitation_sum"]),
            clean_value(r["suitability_score"]), int(r["daylight_hours_covered"]),
            clean_value(r["humidity_mean"]), clean_value(r["air_temperature_max"]), clean_value(r["cloud_cover_mean"]),
        )
        for _, r in df.iterrows()
    ]
    execute_values(
        cur,
        """
        INSERT INTO tourism_forecast_daily
            (location_name, date, generated_at, wave_height_mean, wind_speed_mean, precipitation_sum,
             suitability_score, daylight_hours_covered, humidity_mean, air_temperature_max, cloud_cover_mean)
        VALUES %s
        ON CONFLICT (location_name, date) DO UPDATE SET
            generated_at = EXCLUDED.generated_at,
            wave_height_mean = EXCLUDED.wave_height_mean, wind_speed_mean = EXCLUDED.wind_speed_mean,
            precipitation_sum = EXCLUDED.precipitation_sum, suitability_score = EXCLUDED.suitability_score,
            daylight_hours_covered = EXCLUDED.daylight_hours_covered, humidity_mean = EXCLUDED.humidity_mean,
            air_temperature_max = EXCLUDED.air_temperature_max, cloud_cover_mean = EXCLUDED.cloud_cover_mean;
        """,
        values,
        page_size=1000,
    )
    conn.commit()
    cur.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    _run_with_reconnect(ensure_marine_forecasts_table)

    for loc in LOCATIONS:
        name = loc["name"]
        print(f"[MarineForecast] {name}...")
        result = fetch_location_forecast(loc)
        if result is None:
            print(f"  FAILED to fetch forecast for {name} — skipping")
            continue
        marine, weather = result
        try:
            rows = build_forecast_rows(name, marine, weather)
        except TimestampMismatchError as e:
            print(f"  {e}")
            continue
        _run_with_reconnect(upsert_marine_forecast, name, rows)

        emergency_df = build_emergency_forecast_daily(name, rows)
        _run_with_reconnect(upsert_emergency_forecast, name, emergency_df)

        tourism_df = build_tourism_forecast_daily(name, rows)
        _run_with_reconnect(upsert_tourism_forecast, name, tourism_df)

        print(f"  wrote {len(rows)}h forecast ({len(rows) // 24}d), "
              f"{len(emergency_df)} emergency days, {len(tourism_df)} tourism days")

    print("\nDone.")


if __name__ == "__main__":
    main()
