"""
fetch_marine_forecast.py — CoastalPulse Fisherman forecast (Open-Meteo, not
SARIMA).

Queries Open-Meteo's live FORECAST endpoints (marine-api.open-meteo.com and
api.open-meteo.com, forecast_days=8 — no start_date/end_date, unlike
fetch_data.py's historical/reanalysis reads) and writes the result to a new
`marine_forecasts` table. This is what pages/fisherman.py now reads for its
forecast chart — real physics-based operational ocean/wave models (ECMWF
WAM, NOAA GFS Wave, MeteoFrance MFWAM, DWD EWAM/GWAM, blended by Open-Meteo),
not the per-location SARIMA fit in build_forecasts.py. SARIMA keeps running
unchanged (pipeline/build_forecasts.py) — its output now feeds the Analytics
page's forecasting case study instead of Fisherman.

FORECAST_DAYS = 8 is Open-Meteo Marine API's documented maximum horizon
(verified against https://open-meteo.com/en/docs/marine-weather-api, which
also confirms secondary_swell_wave_* has real data for Sri Lanka locations
but tertiary_swell_wave_* and wave_peak_period do not under the default
model blend here — spot-checked directly against a live API response for
Galle before deciding to include secondary swell and skip tertiary/peak
period rather than ship columns that would sit permanently null).

All 15 locations, unlike fetch_data.py's marine_ocean split — wave/swell
data doesn't depend on the sea-surface-temp/ocean-current fields the 5
TOURISM_ONLY locations skip, so there's no tourism-only branching here.

Table is delete+insert per location on every run (same reasoning as
build_forecasts.py's `forecasts` table): it should always hold exactly the
latest 8-day forecast, never accumulate stale future-dated rows from a
previous run.
"""

import os

from dotenv import load_dotenv
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from build_gold import _run_with_reconnect, clean_value
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
WIND_HOURLY_VARS = "wind_speed_10m,wind_gusts_10m,wind_direction_10m"


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
    wind = fetch("https://api.open-meteo.com/v1/forecast", {**common, "hourly": WIND_HOURLY_VARS})
    if not marine or not wind:
        return None
    return marine, wind


def build_forecast_rows(name, marine, wind):
    times = marine["hourly"]["time"]
    if wind["hourly"]["time"] != times:
        raise TimestampMismatchError(
            f"{name}: wind forecast hourly timestamps do not match marine forecast's "
            f"(lengths: {len(wind['hourly']['time'])} vs {len(times)}). Refusing to "
            "build rows for this location — would silently misalign data."
        )

    generated_at = pd.Timestamp.now(tz="UTC")
    mh, wh = marine["hourly"], wind["hourly"]
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
        })
    return rows


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
             wind_speed, wind_gust, wind_direction)
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
            wind_speed = EXCLUDED.wind_speed, wind_gust = EXCLUDED.wind_gust, wind_direction = EXCLUDED.wind_direction;
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
        marine, wind = result
        try:
            rows = build_forecast_rows(name, marine, wind)
        except TimestampMismatchError as e:
            print(f"  {e}")
            continue
        _run_with_reconnect(upsert_marine_forecast, name, rows)
        print(f"  wrote {len(rows)}h forecast ({len(rows) // 24}d)")

    print("\nDone.")


if __name__ == "__main__":
    main()
