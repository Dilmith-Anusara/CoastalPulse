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
                           connection string instead (port 5432, host
                           ...pooler.supabase.com, username postgres.<ref>) —
                           IPv4-reachable, which the direct connection may not
                           be from a CI runner. Test this before the real
                           run; if it doesn't connect, it's almost certainly
                           this.

pip install requests supabase python-dotenv psycopg2-binary
"""

import os
import signal
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
# TEST MODE — set to True and run against ONE location first to confirm the
# alignment assertion (see build_silver_rows) holds before committing to the
# full 15-location / 18-month run. Flip back to False for the real run.
# ---------------------------------------------------------------------------

TEST_MODE = False
TEST_LOCATION = "Chilaw"  # multi-mode location — exercises marine_ocean too

if TEST_MODE:
    LOCATIONS = [loc for loc in LOCATIONS if loc["name"] == TEST_LOCATION]

# ---------------------------------------------------------------------------
# Date range — 2025 only for now, 2024 backfill is a separate later run.
#
# GLOBAL_END was previously a fixed date (2026-06-30) that stopped moving
# once written — every run after that date found every month chunk already
# "covered" (silver_chunk_covered) and skipped it, so the pipeline kept
# exiting successfully while silently fetching nothing new. inserted_at
# (the freshness badge's source) kept updating on unrelated backfill/rerun
# activity, so the badge looked fresh while the actual latest observation
# timestamp stayed frozen at June 30 — a real gap caught by checking the
# two against each other directly.
#
# Now computed fresh on every run instead. The 5-day buffer matches Open-
# Meteo's own documented reanalysis lag for the two sources this pipeline
# actually reads historically — archive-api's ERA5/ERA5-Land ("Daily with
# 5 days delay") and the Marine API's ERA5-Ocean ("Daily with 5 days
# delay"), per https://open-meteo.com/en/docs/historical-weather-api and
# .../marine-weather-api. A shorter buffer doesn't just risk an incomplete
# chunk — silver_chunk_covered() only checks that a row EXISTS for each
# hour, not that its values are non-null, so requesting days still inside
# the reanalysis window would write rows full of nulls that then look
# "already covered" forever and never get re-fetched once the real data
# is ready.
# ---------------------------------------------------------------------------

GLOBAL_START = date(2025, 1, 1)
GLOBAL_END = date.today() - timedelta(days=5)

# TIMEOUT was 90s, lowered to 30 after real GitHub Actions runs showed
# retries (each costing a full TIMEOUT wait + RETRY_DELAY before the next
# attempt) eating several minutes of the pipeline's timeout budget on a
# flaky connection to Open-Meteo. Measured directly first, not guessed:
# even a full month-chunk historical call (archive-api or marine-api,
# 15 locations x up to 31 days x several hourly variables) returns in
# ~1s under normal conditions — 30s still leaves ~30x headroom over that,
# so this only cuts the wait on requests that were already stuck, not on
# genuinely-slow-but-working ones. RETRIES is left alone (not lowered) —
# the retries themselves are the known-necessary part (GitHub runner IPs
# to Open-Meteo have documented transient flakiness, see fetch()'s
# docstring/usage), only the per-attempt wait was oversized. Worst case
# per fully-dead URL: 5 x (30 + 5) = 175s, down from 5 x (90 + 5) = 475s.
TIMEOUT = 30
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
    air_temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    weather_code DOUBLE PRECISION,
    cloud_cover DOUBLE PRECISION,
    apparent_temperature DOUBLE PRECISION,
    sunshine_duration DOUBLE PRECISION,
    wind_direction DOUBLE PRECISION,
    uv_index DOUBLE PRECISION,
    pm25 DOUBLE PRECISION,
    us_aqi DOUBLE PRECISION,
    inserted_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (location_name, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_silver_location_ts ON silver_hourly (location_name, timestamp);

-- Added after the initial run: these columns weren't part of the original
-- fetch, so CREATE TABLE IF NOT EXISTS alone won't add them to a table
-- that already exists in production. These statements are the actual
-- migration for the live table — additive only, existing rows just get
-- NULL here until the matching backfill_* function (below) patches them.
ALTER TABLE silver_hourly ADD COLUMN IF NOT EXISTS air_temperature DOUBLE PRECISION;
ALTER TABLE silver_hourly ADD COLUMN IF NOT EXISTS humidity DOUBLE PRECISION;
ALTER TABLE silver_hourly ADD COLUMN IF NOT EXISTS weather_code DOUBLE PRECISION;
ALTER TABLE silver_hourly ADD COLUMN IF NOT EXISTS cloud_cover DOUBLE PRECISION;
ALTER TABLE silver_hourly ADD COLUMN IF NOT EXISTS apparent_temperature DOUBLE PRECISION;
ALTER TABLE silver_hourly ADD COLUMN IF NOT EXISTS sunshine_duration DOUBLE PRECISION;
ALTER TABLE silver_hourly ADD COLUMN IF NOT EXISTS wind_direction DOUBLE PRECISION;
ALTER TABLE silver_hourly ADD COLUMN IF NOT EXISTS us_aqi DOUBLE PRECISION;
"""


def connect_with_hard_timeout(db_url, seconds=20):
    """psycopg2's own connect_timeout only bounds the TCP-connect phase —
    NOT the DNS lookup before it, which can hang separately if a runner's
    resolver misbehaves. Observed directly: a GitHub Actions run sat stuck
    with zero output for 25+ minutes even with connect_timeout=15 already
    set, well past what that alone should have allowed.

    signal.alarm() forces a hard wall-clock bound regardless of which
    layer is actually stuck, by interrupting the blocking call outright.
    Unix-only (SIGALRM doesn't exist on Windows) — fine for GitHub
    Actions' ubuntu-latest runners, which is the only place this has ever
    hung; falls back to psycopg2's own connect_timeout alone on Windows,
    where this has always connected quickly.
    """
    if not hasattr(signal, "SIGALRM"):
        return psycopg2.connect(db_url, connect_timeout=seconds)

    def _on_alarm(signum, frame):
        raise TimeoutError(
            f"DB connection did not complete within {seconds}s (hard wall-clock "
            "timeout — likely a DNS or network hang that connect_timeout alone "
            "doesn't cover)."
        )

    previous_handler = signal.signal(signal.SIGALRM, _on_alarm)
    signal.alarm(seconds)
    try:
        return psycopg2.connect(db_url, connect_timeout=seconds)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)


def ensure_tables():
    """Create bronze_raw / silver_hourly if they don't exist yet. Idempotent."""
    conn = connect_with_hard_timeout(SUPABASE_DB_URL)
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
               {**common, "hourly": "wave_height,wave_period,wave_direction,sea_level_height_msl"})
    m2 = fetch("https://marine-api.open-meteo.com/v1/marine",
               {**common, "hourly": "swell_wave_height,swell_wave_direction,swell_wave_period,wind_wave_height"})
    m3 = None
    if not is_tourism_only:
        m3 = fetch("https://marine-api.open-meteo.com/v1/marine",
                   {**common, "hourly": "sea_surface_temperature,ocean_current_velocity,ocean_current_direction"})
    w = fetch("https://archive-api.open-meteo.com/v1/archive",
              {**common, "hourly": "wind_speed_10m,wind_gusts_10m,precipitation,surface_pressure,temperature_2m,relative_humidity_2m,weather_code,cloud_cover,apparent_temperature,sunshine_duration,wind_direction_10m"})
    aq = fetch("https://air-quality-api.open-meteo.com/v1/air-quality",
               {**common, "hourly": "uv_index,pm2_5,us_aqi"})

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

class TimestampMismatchError(Exception):
    """Raised when one of the joined API payloads doesn't share the same
    hourly timestamp array as marine_waves. Zipping by index in that case
    would silently pair wrong-hour values together, so we refuse instead."""
    pass


def build_silver_rows(name, payload_map):
    m1, m2, m3 = payload_map["marine_waves"], payload_map["marine_swell"], payload_map["marine_ocean"]
    w, aq = payload_map["weather"], payload_map["air_quality"]
    times = m1["hourly"]["time"]

    # --- Alignment check: every payload must share m1's exact hourly time
    # array before we zip them together by positional index. If any API
    # returned a partial/short response for the same requested date range,
    # this catches it loudly instead of silently mis-joining rows. ---
    to_check = [("marine_swell", m2), ("weather", w), ("air_quality", aq)]
    if m3 is not None:
        to_check.append(("marine_ocean", m3))

    for label, payload in to_check:
        other_times = payload["hourly"]["time"]
        if other_times != times:
            raise TimestampMismatchError(
                f"{name}: '{label}' hourly timestamps do not match 'marine_waves' "
                f"(lengths: {len(other_times)} vs {len(times)}). Refusing to build "
                f"Silver rows for this chunk — would silently misalign data."
            )

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
            "sea_level_height": m1["hourly"]["sea_level_height_msl"][i],
            "wind_speed": w["hourly"]["wind_speed_10m"][i],
            "wind_gust": w["hourly"]["wind_gusts_10m"][i],
            "precipitation": w["hourly"]["precipitation"][i],
            "atmospheric_pressure": w["hourly"]["surface_pressure"][i],
            "air_temperature": w["hourly"]["temperature_2m"][i],
            "humidity": w["hourly"]["relative_humidity_2m"][i],
            "weather_code": w["hourly"]["weather_code"][i],
            "cloud_cover": w["hourly"]["cloud_cover"][i],
            "apparent_temperature": w["hourly"]["apparent_temperature"][i],
            "sunshine_duration": w["hourly"]["sunshine_duration"][i],
            "wind_direction": w["hourly"]["wind_direction_10m"][i],
            "uv_index": aq["hourly"]["uv_index"][i],
            "pm25": aq["hourly"]["pm2_5"][i],
            "us_aqi": aq["hourly"]["us_aqi"][i],
        })
    return rows


def upsert_silver(rows):
    if not rows:
        return
    supabase.table("silver_hourly").upsert(rows, on_conflict="location_name,timestamp").execute()


# ---------------------------------------------------------------------------
# One-time backfill: air_temperature / humidity for rows fetched before
# these fields were added to fetch_location_month(). Re-queries ONLY the
# weather/archive endpoint (not marine or air-quality, which are
# unaffected) and does a partial upsert touching just these two columns —
# PostgREST's upsert only updates the columns present in the payload, so
# every other column on the existing row is left untouched. Not called
# from run()/__main__ — this is a separate one-off migration step, not
# part of the ongoing pipeline.
# ---------------------------------------------------------------------------

def backfill_chunk_covered(location, chunk_start, chunk_end):
    """Same shape as silver_chunk_covered, but counts rows where
    air_temperature is already populated — lets an interrupted or re-run
    backfill skip chunks it already patched instead of re-fetching them."""
    resp = (
        supabase.table("silver_hourly")
        .select("timestamp", count="exact")
        .eq("location_name", location)
        .gte("timestamp", chunk_start.isoformat())
        .lte("timestamp", chunk_end.isoformat() + "T23:59:59")
        .not_.is_("air_temperature", "null")
        .execute()
    )
    count = resp.count or 0
    expected_hours = ((chunk_end - chunk_start).days + 1) * 24
    return count >= expected_hours * SKIP_COVERAGE_THRESHOLD


def backfill_temperature_humidity():
    for loc in LOCATIONS:
        name = loc["name"]
        print(f"\n=== Backfilling {name} ===")
        for chunk_start, chunk_end in month_chunks(GLOBAL_START, GLOBAL_END):
            if backfill_chunk_covered(name, chunk_start, chunk_end):
                print(f"  {chunk_start} to {chunk_end}: already backfilled, skipping")
                continue

            print(f"  Fetching {chunk_start} to {chunk_end}...")
            common = dict(
                latitude=loc["lat"], longitude=loc["lon"],
                start_date=chunk_start.isoformat(), end_date=chunk_end.isoformat(),
                timezone="Asia/Colombo",
            )
            w = fetch("https://archive-api.open-meteo.com/v1/archive",
                      {**common, "hourly": "temperature_2m,relative_humidity_2m"})
            if w is None:
                print(f"    FAILED for {name} {chunk_start} to {chunk_end} — skipping, will retry on next run")
                continue

            times = w["hourly"]["time"]
            rows = [
                {
                    "location_name": name,
                    "timestamp": times[i],
                    "air_temperature": w["hourly"]["temperature_2m"][i],
                    "humidity": w["hourly"]["relative_humidity_2m"][i],
                }
                for i in range(len(times))
            ]
            upsert_silver(rows)
            print(f"    Patched {len(rows)} rows with air_temperature/humidity.")

    print("\nBackfill done.")


# ---------------------------------------------------------------------------
# One-time backfill: weather_code, cloud_cover, apparent_temperature,
# sunshine_duration, wind_direction, sea_level_height, us_aqi — six more
# fields added after the initial run. Unlike backfill_temperature_humidity
# above, this one DOES go through Bronze staging (save -> build -> upsert
# -> purge), matching run()'s pattern exactly, since it joins three
# separate API sources (marine, weather, air quality) that need the same
# alignment guarantee run() enforces for its own joins.
# ---------------------------------------------------------------------------

def backfill_extras_covered(location, chunk_start, chunk_end):
    """weather_code comes from the 'weather' source, fetched for every
    location regardless of tourism_only status — same reasoning as
    backfill_chunk_covered's use of air_temperature."""
    resp = (
        supabase.table("silver_hourly")
        .select("timestamp", count="exact")
        .eq("location_name", location)
        .gte("timestamp", chunk_start.isoformat())
        .lte("timestamp", chunk_end.isoformat() + "T23:59:59")
        .not_.is_("weather_code", "null")
        .execute()
    )
    count = resp.count or 0
    expected_hours = ((chunk_end - chunk_start).days + 1) * 24
    return count >= expected_hours * SKIP_COVERAGE_THRESHOLD


def backfill_marine_weather_extras():
    for loc in LOCATIONS:
        name = loc["name"]
        print(f"\n=== Backfilling extras for {name} ===")
        for chunk_start, chunk_end in month_chunks(GLOBAL_START, GLOBAL_END):
            if backfill_extras_covered(name, chunk_start, chunk_end):
                print(f"  {chunk_start} to {chunk_end}: already backfilled, skipping")
                continue

            print(f"  Fetching {chunk_start} to {chunk_end}...")
            common = dict(
                latitude=loc["lat"], longitude=loc["lon"],
                start_date=chunk_start.isoformat(), end_date=chunk_end.isoformat(),
                timezone="Asia/Colombo",
            )
            m = fetch("https://marine-api.open-meteo.com/v1/marine",
                      {**common, "hourly": "sea_level_height_msl"})
            w = fetch("https://archive-api.open-meteo.com/v1/archive",
                      {**common, "hourly": "weather_code,cloud_cover,apparent_temperature,sunshine_duration,wind_direction_10m"})
            aq = fetch("https://air-quality-api.open-meteo.com/v1/air-quality",
                       {**common, "hourly": "us_aqi"})

            if not all([m, w, aq]):
                print(f"    FAILED for {name} {chunk_start} to {chunk_end} — skipping, will retry on next run")
                continue

            payload_map = {"marine_sealevel": m, "weather_extras": w, "air_quality_aqi": aq}
            bronze_ids = save_bronze(name, payload_map)

            times = w["hourly"]["time"]
            mismatch = None
            for label, payload in [("marine_sealevel", m), ("air_quality_aqi", aq)]:
                other_times = payload["hourly"]["time"]
                if other_times != times:
                    mismatch = (
                        f"{name}: '{label}' hourly timestamps do not match 'weather_extras' "
                        f"(lengths: {len(other_times)} vs {len(times)})."
                    )
                    break

            if mismatch:
                print(f"    ALIGNMENT ERROR: {mismatch}")
                print(f"    Bronze kept (NOT purged) for {name} {chunk_start} to {chunk_end} for inspection.")
                continue

            rows = [
                {
                    "location_name": name,
                    "timestamp": times[i],
                    "sea_level_height": m["hourly"]["sea_level_height_msl"][i],
                    "weather_code": w["hourly"]["weather_code"][i],
                    "cloud_cover": w["hourly"]["cloud_cover"][i],
                    "apparent_temperature": w["hourly"]["apparent_temperature"][i],
                    "sunshine_duration": w["hourly"]["sunshine_duration"][i],
                    "wind_direction": w["hourly"]["wind_direction_10m"][i],
                    "us_aqi": aq["hourly"]["us_aqi"][i],
                }
                for i in range(len(times))
            ]
            upsert_silver(rows)
            print(f"    Patched {len(rows)} rows with weather/marine/AQI extras.")

            purge_bronze(bronze_ids)
            print(f"    Purged {len(bronze_ids)} Bronze records.")

    print("\nBackfill done.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    ensure_tables()

    if TEST_MODE:
        print(f"*** TEST_MODE is ON — running only {[l['name'] for l in LOCATIONS]} ***\n")

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

            try:
                rows = build_silver_rows(name, payload_map)
            except TimestampMismatchError as e:
                print(f"    ALIGNMENT ERROR: {e}")
                print(f"    Bronze kept (NOT purged) for {name} {chunk_start} to {chunk_end} for inspection.")
                continue

            upsert_silver(rows)
            print(f"    Inserted {len(rows)} rows into Silver.")

            purge_bronze(bronze_ids)
            print(f"    Purged {len(bronze_ids)} Bronze records.")

    print("\nDone.")


if __name__ == "__main__":
    run()