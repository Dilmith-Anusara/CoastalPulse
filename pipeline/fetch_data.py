"""
CoastalPulse — Bronze/Silver fetch pipeline
Run: python coastalpulse_pipeline.py

Requires in .env:
  SUPABASE_URL=...
  SUPABASE_KEY=...
  SUPABASE_DB_URL=...   <- NEW: direct Postgres connection string, needed only
                           for the one-time CREATE TABLE step (the anon/service
                           REST key can't run DDL). Get this from Supabase
                           dashboard -> Settings -> Database -> Connection
                           string -> URI. If your project only offers IPv6 on
                           the direct connection, use the "Session pooler"
                           connection string instead (port 6543) — same URI
                           format, just a different host/port. Test this
                           before the real run; if it doesn't connect, it's
                           almost certainly this.

pip install requests supabase python-dotenv psycopg2-binary
"""

import os
import time
from datetime import date, timedelta

import psycopg2
import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------

LOCATIONS = [
    {"name": "Mirissa",     "lat": 5.948,  "lon": 80.455},
    {"name": "Hikkaduwa",   "lat": 6.139,  "lon": 80.100},
    {"name": "Unawatuna",   "lat": 5.999,  "lon": 80.249},
    {"name": "Bentota",     "lat": 6.421,  "lon": 79.996},
    {"name": "Arugam Bay",  "lat": 6.840,  "lon": 81.836},
    {"name": "Negombo",     "lat": 7.209,  "lon": 79.855},
    {"name": "Galle",       "lat": 6.030,  "lon": 80.217},
    {"name": "Trincomalee", "lat": 8.587,  "lon": 81.215},
    {"name": "Chilaw",      "lat": 7.576,  "lon": 79.796},
    {"name": "Colombo",     "lat": 6.927,  "lon": 79.861},
    {"name": "Tangalle",    "lat": 6.025,  "lon": 80.793},
    {"name": "Batticaloa",  "lat": 7.717,  "lon": 81.700},
    {"name": "Jaffna",      "lat": 9.661,  "lon": 80.013},
    {"name": "Matara",      "lat": 5.948,  "lon": 80.535},
    {"name": "Puttalam",    "lat": 8.031,  "lon": 79.828},
]
TOURISM_ONLY = {"Mirissa", "Hikkaduwa", "Unawatuna", "Bentota", "Arugam Bay"}

# ---------------------------------------------------------------------------
# Date range — 2025 only for now, 2024 backfill is a separate later run
# ---------------------------------------------------------------------------

GLOBAL_START = date(2025, 1, 1)
GLOBAL_END = date(2026, 6, 30)

TIMEOUT = 90
RETRIES = 5
RETRY_DELAY = 5
SKIP_COVERAGE_THRESHOLD = 0.95  # tolerate up to 5% missing hours before re-fetching a chunk

DDL = """
CREATE TABLE IF NOT EXISTS bronze_raw (
    id BIGSERIAL PRIMARY KEY,
    location_name TEXT NOT NULL,
    api_source TEXT NOT NULL,
    raw_json JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS silver_hourly (
    location_name TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    wave_height DOUBLE PRECISION,
    wave_period DOUBLE PRECISION,
    wave_direction DOUBLE PRECISION,
    swell_height DOUBLE PRECISION,
    swell_period DOUBLE PRECISION,
    swell_direction DOUBLE PRECISION,
    wind_wave_height DOUBLE PRECISION,
    sea_surface_temp DOUBLE PRECISION,
    ocean_current_velocity DOUBLE PRECISION,
    ocean_current_direction DOUBLE PRECISION,
    sea_level_height DOUBLE PRECISION,
    wind_speed DOUBLE PRECISION,
    wind_gust DOUBLE PRECISION,
    precipitation DOUBLE PRECISION,
    atmospheric_pressure DOUBLE PRECISION,
    uv_index DOUBLE PRECISION,
    pm25 DOUBLE PRECISION,
    inserted_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (location_name, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_silver_location_ts ON silver_hourly (location_name, timestamp);
"""


def ensure_tables():
    """Create bronze_raw / silver_hourly if they don't exist yet. Idempotent."""
    conn = psycopg2.connect(SUPABASE_DB_URL)
    with conn.cursor() as cur:
        cur.execute(DDL)
        # Tables created via a direct connection aren't visible to PostgREST
        # (what supabase-py talks to) until its schema cache reloads. Without
        # this, a fresh table exists in Postgres but supabase-py calls against
        # it fail with PGRST205 "Could not find the table in the schema cache".
        cur.execute("NOTIFY pgrst, 'reload schema';")
    conn.commit()
    conn.close()
    print("Schema checked/created (schema cache reload signalled).")


# ---------------------------------------------------------------------------
# Month chunking
# ---------------------------------------------------------------------------

def month_chunks(start, end):
    cur = start
    while cur <= end:
        next_month = date(cur.year + 1, 1, 1) if cur.month == 12 else date(cur.year, cur.month + 1, 1)
        chunk_end = min(next_month - timedelta(days=1), end)
        yield cur, chunk_end
        cur = next_month


# ---------------------------------------------------------------------------
# Skip-if-exists (range-aware, not just location-level)
# ---------------------------------------------------------------------------

def silver_chunk_covered(location, chunk_start, chunk_end):
    resp = (
        supabase.table("silver_hourly")
        .select("timestamp", count="exact")
        .eq("location_name", location)
        .gte("timestamp", chunk_start.isoformat())
        .lte("timestamp", chunk_end.isoformat() + "T23:59:59")
        .execute()
    )
    count = resp.count or 0
    expected_hours = ((chunk_end - chunk_start).days + 1) * 24
    return count >= expected_hours * SKIP_COVERAGE_THRESHOLD


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch(url, params):
    for attempt in range(RETRIES):
        try:
            r = requests.get(url, params=params, timeout=TIMEOUT)
            data = r.json()
            if "hourly" not in data:
                print(f"    API error: {data}")
                return None
            return data
        except Exception as e:
            print(f"    Attempt {attempt + 1} failed: {e}")
            time.sleep(RETRY_DELAY)
    print("    All retries failed.")
    return None


def fetch_location_month(loc, chunk_start, chunk_end):
    name, lat, lon = loc["name"], loc["lat"], loc["lon"]
    is_tourism_only = name in TOURISM_ONLY
    common = dict(
        latitude=lat,
        longitude=lon,
        start_date=chunk_start.isoformat(),
        end_date=chunk_end.isoformat(),
        timezone="Asia/Colombo",
    )

    m1 = fetch("https://marine-api.open-meteo.com/v1/marine",
               {**common, "hourly": "wave_height,wave_period,wave_direction"})
    m2 = fetch("https://marine-api.open-meteo.com/v1/marine",
               {**common, "hourly": "swell_wave_height,swell_wave_direction,swell_wave_period,wind_wave_height"})
    m3 = None
    if not is_tourism_only:
        m3 = fetch("https://marine-api.open-meteo.com/v1/marine",
                   {**common, "hourly": "sea_surface_temperature,ocean_current_velocity,ocean_current_direction"})
    w = fetch("https://archive-api.open-meteo.com/v1/archive",
              {**common, "hourly": "wind_speed_10m,wind_gusts_10m,precipitation,surface_pressure"})
    aq = fetch("https://air-quality-api.open-meteo.com/v1/air-quality",
               {**common, "hourly": "uv_index,pm2_5"})

    required = [m1, m2, w, aq] if is_tourism_only else [m1, m2, m3, w, aq]
    if not all(required):
        return None
    return {"marine_waves": m1, "marine_swell": m2, "marine_ocean": m3, "weather": w, "air_quality": aq}


# ---------------------------------------------------------------------------
# Bronze
# ---------------------------------------------------------------------------

def save_bronze(location, payload_map):
    bronze_ids = []
    for source, payload in payload_map.items():
        if payload is None:
            continue
        resp = supabase.table("bronze_raw").insert({
            "location_name": location,
            "api_source": source,
            "raw_json": payload,
        }).execute()
        bronze_ids.append(resp.data[0]["id"])
    return bronze_ids


def purge_bronze(bronze_ids):
    if not bronze_ids:
        return
    supabase.table("bronze_raw").delete().in_("id", bronze_ids).execute()


# ---------------------------------------------------------------------------
# Silver
# ---------------------------------------------------------------------------

def build_silver_rows(name, payload_map):
    m1, m2, m3 = payload_map["marine_waves"], payload_map["marine_swell"], payload_map["marine_ocean"]
    w, aq = payload_map["weather"], payload_map["air_quality"]
    times = m1["hourly"]["time"]
    rows = []
    for i in range(len(times)):
        rows.append({
            "location_name": name,
            "timestamp": times[i],
            "wave_height": m1["hourly"]["wave_height"][i],
            "wave_period": m1["hourly"]["wave_period"][i],
            "wave_direction": m1["hourly"]["wave_direction"][i],
            "swell_height": m2["hourly"]["swell_wave_height"][i],
            "swell_period": m2["hourly"]["swell_wave_period"][i],
            "swell_direction": m2["hourly"]["swell_wave_direction"][i],
            "wind_wave_height": m2["hourly"]["wind_wave_height"][i],
            "sea_surface_temp": m3["hourly"]["sea_surface_temperature"][i] if m3 else None,
            "ocean_current_velocity": m3["hourly"]["ocean_current_velocity"][i] if m3 else None,
            "ocean_current_direction": m3["hourly"]["ocean_current_direction"][i] if m3 else None,
            "sea_level_height": None,  # no endpoint wired up yet — known gap, not a bug
            "wind_speed": w["hourly"]["wind_speed_10m"][i],
            "wind_gust": w["hourly"]["wind_gusts_10m"][i],
            "precipitation": w["hourly"]["precipitation"][i],
            "atmospheric_pressure": w["hourly"]["surface_pressure"][i],
            "uv_index": aq["hourly"]["uv_index"][i],
            "pm25": aq["hourly"]["pm2_5"][i],
        })
    return rows


def upsert_silver(rows):
    if not rows:
        return
    supabase.table("silver_hourly").upsert(rows, on_conflict="location_name,timestamp").execute()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    ensure_tables()

    for loc in LOCATIONS:
        name = loc["name"]
        print(f"\n=== {name} ===")
        for chunk_start, chunk_end in month_chunks(GLOBAL_START, GLOBAL_END):
            if silver_chunk_covered(name, chunk_start, chunk_end):
                print(f"  {chunk_start} to {chunk_end}: already in Silver, skipping")
                continue

            print(f"  Fetching {chunk_start} to {chunk_end}...")
            payload_map = fetch_location_month(loc, chunk_start, chunk_end)
            if payload_map is None:
                print(f"    FAILED for {name} {chunk_start} to {chunk_end} — skipping this chunk, will retry on next run")
                continue

            bronze_ids = save_bronze(name, payload_map)
            rows = build_silver_rows(name, payload_map)
            upsert_silver(rows)
            print(f"    Inserted {len(rows)} rows into Silver.")

            purge_bronze(bronze_ids)
            print(f"    Purged {len(bronze_ids)} Bronze records.")

    print("\nDone.")


if __name__ == "__main__":
    run()