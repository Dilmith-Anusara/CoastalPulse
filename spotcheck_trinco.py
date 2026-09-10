"""
Spot-check: Trincomalee's 72-hour frozen wave_height run (Apr 20-23, 2025).

Two checks:
1. Pull the raw silver_hourly rows for that window and print them —
   confirm the value really is frozen (not a display/rounding artifact)
   and see what it's frozen AT.
2. Re-fetch the same window directly from Open-Meteo's historical marine
   API and compare, since that's an independent source of truth outside
   your own pipeline.

Run this BEFORE trusting the Emergency Gold aggregation for that date range —
if it's genuinely bad/stale data, you may want to flag or interpolate it
before computing daily max wave_height for those 3 days.
"""

import os
from dotenv import load_dotenv
import psycopg2
import requests
from datetime import datetime

load_dotenv()

DB_CONN_STRING = os.environ["SUPABASE_DB_URL"]  # same as fetch_data.py uses

TRINCOMALEE_LAT = 8.587   # adjust to your actual stored coordinates
TRINCOMALEE_LON = 81.215
WINDOW_START = "2025-04-20"
WINDOW_END = "2025-04-23"


def check_stored_values():
    conn = psycopg2.connect(DB_CONN_STRING)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT timestamp, wave_height, wind_speed, wind_gust, atmospheric_pressure
        FROM silver_hourly
        WHERE location_name = %s
          AND timestamp >= %s
          AND timestamp < %s
        ORDER BY timestamp;
        """,
        ("Trincomalee", WINDOW_START, WINDOW_END),  # adjust location filter to your actual column/naming
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    print(f"\n--- Stored silver_hourly rows: Trincomalee {WINDOW_START} to {WINDOW_END} ---")
    frozen_value = None
    frozen_count = 0
    for ts, wave_height, wind_speed, wind_gust, pressure in rows:
        print(f"{ts}  wave_height={wave_height}  wind_speed={wind_speed}  wind_gust={wind_gust}  pressure={pressure}")
        if frozen_value is None:
            frozen_value = wave_height
        if wave_height == frozen_value:
            frozen_count += 1
    print(f"\nTotal rows: {len(rows)} | Rows matching first value ({frozen_value}): {frozen_count}")
    return rows


def check_openmeteo_source():
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": TRINCOMALEE_LAT,
        "longitude": TRINCOMALEE_LON,
        "hourly": "wave_height",
        "start_date": WINDOW_START,
        "end_date": WINDOW_END,
        "timezone": "UTC",
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    print(f"\n--- Live Open-Meteo marine API: same window ---")
    times = data["hourly"]["time"]
    heights = data["hourly"]["wave_height"]
    for t, h in zip(times, heights):
        print(f"{t}  wave_height={h}")

    return data


if __name__ == "__main__":
    stored = check_stored_values()
    live = check_openmeteo_source()
    print(
        "\nCompare the two printouts above:\n"
        "- If stored values match the live re-fetch closely -> the freeze is real "
        "(Open-Meteo's own model held that value for 72h) -> note it in limitations, no fix needed.\n"
        "- If stored values diverge from the live re-fetch -> likely a stale/bad fetch on your end "
        "-> consider re-pulling just this window before it feeds Gold's Emergency daily max."
    )