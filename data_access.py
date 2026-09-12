"""
data_access.py — shared Supabase query layer for the CoastalPulse dashboard.

Every Dash page imports from HERE, never queries Supabase directly. This is
the same lesson learned twice already in this project (the import-path drift
between build_gold.py / validate_gold.py, and the LOCATIONS/TOURISM_ONLY
hardcoding bug) — centralize once, fix once.

Location lists are imported from pipeline/fetch_data.py (the single source
of truth), not redefined here.

Caching: functions are decorated with a no-op passthrough (`@cache_stub`) for
now. Wire in Flask-Caching once the app is running (dashboard build Step 6)
by replacing `cache_stub` with a real `@cache.memoize(timeout=300)` decorator
from a shared `cache = Cache(app)` instance. Keeping the decorator in place
now means adding real caching later is a one-line swap, not a refactor.
"""

import os
import sys
from pathlib import Path
from functools import wraps

import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

# --- Single source of truth for locations -----------------------------------
# pipeline/fetch_data.py lives one level up from this file's expected home
# (project root, alongside app.py). Adjust the relative path below if you
# place data_access.py somewhere else.
sys.path.insert(0, str(Path(__file__).resolve().parent / "pipeline"))

_FALLBACK_LOCATIONS = [
    {"name": "Mirissa", "lat": 5.948, "lon": 80.455},
    {"name": "Hikkaduwa", "lat": 6.139, "lon": 80.100},
    {"name": "Unawatuna", "lat": 5.999, "lon": 80.249},
    {"name": "Bentota", "lat": 6.421, "lon": 79.996},
    {"name": "Arugam Bay", "lat": 6.840, "lon": 81.836},
    {"name": "Negombo", "lat": 7.209, "lon": 79.855},
    {"name": "Galle", "lat": 6.030, "lon": 80.217},
    {"name": "Trincomalee", "lat": 8.587, "lon": 81.215},
    {"name": "Chilaw", "lat": 7.576, "lon": 79.796},
    {"name": "Colombo", "lat": 6.927, "lon": 79.861},
    {"name": "Tangalle", "lat": 6.025, "lon": 80.793},
    {"name": "Batticaloa", "lat": 7.717, "lon": 81.700},
    {"name": "Jaffna", "lat": 9.661, "lon": 80.013},
    {"name": "Matara", "lat": 5.948, "lon": 80.535},
    {"name": "Puttalam", "lat": 8.031, "lon": 79.828},
]
_FALLBACK_TOURISM_ONLY = {"Mirissa", "Hikkaduwa", "Unawatuna", "Bentota", "Arugam Bay"}

try:
    from fetch_data import LOCATIONS as _RAW_LOCATIONS, TOURISM_ONLY  # noqa: E402
except ImportError:
    # Fallback so this module can still be imported/tested standalone before
    # the pipeline/ folder is wired up in the same repo checkout. Keep this
    # in sync manually ONLY until the real import path is confirmed working —
    # this is exactly the kind of drift that caused the Gold-layer bug.
    _RAW_LOCATIONS = _FALLBACK_LOCATIONS
    TOURISM_ONLY = _FALLBACK_TOURISM_ONLY

# fetch_data.LOCATIONS holds real name + lat/lon per location (each entry a
# dict: {"name": ..., "lat": ..., "lon": ...}) — this is the single source
# of truth for BOTH the flat name list every page/dropdown uses AND the
# coordinates the Emergency map needs. Derive both from it here so nothing
# downstream has to know the underlying shape, and there's no second
# LOCATION_COORDS constant that can drift out of sync with the real list.
if _RAW_LOCATIONS and isinstance(_RAW_LOCATIONS[0], dict):
    LOCATIONS = [loc["name"] for loc in _RAW_LOCATIONS]
    LOCATION_COORDS = {loc["name"]: (loc["lat"], loc["lon"]) for loc in _RAW_LOCATIONS}
else:
    # Older flat-string shape (name-only) — no coordinates available from
    # fetch_data.py in this case, so fall back to placeholders and warn
    # loudly rather than silently mapping the Emergency map to the wrong
    # towns.
    LOCATIONS = _RAW_LOCATIONS
    print(
        "[data_access] WARNING: fetch_data.LOCATIONS has no lat/lon per "
        "entry — using placeholder coordinates for the Emergency map. "
        "Update fetch_data.py's LOCATIONS to the {name, lat, lon} dict "
        "format to fix this.",
        file=sys.stderr,
    )
    LOCATION_COORDS = {loc["name"]: (loc["lat"], loc["lon"]) for loc in _FALLBACK_LOCATIONS}

load_dotenv()

_SUPABASE_URL = os.environ.get("SUPABASE_URL")
_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

_client: Client | None = None


def get_client() -> Client:
    """Lazy singleton Supabase client (REST API key, not the direct
    Postgres connection string — that's SUPABASE_DB_URL, used only by
    build_gold.py / DDL work, not needed here)."""
    global _client
    if _client is None:
        if not _SUPABASE_URL or not _SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL / SUPABASE_KEY not set — check your .env file."
            )
        _client = create_client(_SUPABASE_URL, _SUPABASE_KEY)
    return _client


def cache_stub(fn):
    """No-op placeholder. Swap for cache.memoize(timeout=300) once
    Flask-Caching is wired into app.py (dashboard build Step 6)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapper


def _validate_location(location: str | None):
    if location is not None and location not in LOCATIONS:
        raise ValueError(
            f"Unknown location '{location}'. Must be one of {LOCATIONS}."
        )


# --- Data freshness -----------------------------------------------------------

@cache_stub
def get_last_updated() -> pd.Timestamp | None:
    """
    Most recent `inserted_at` timestamp across silver_hourly — the honest
    freshness signal for the header badge, replacing a decorative "LIVE"
    indicator. This pipeline is a scheduled batch job, not a real-time feed,
    so the UI should say "Updated 3h ago", not imply a live stream.

    Returns None (never raises) if Supabase isn't reachable/configured yet,
    so a bad connection degrades the badge, not the whole app.
    """
    try:
        resp = (
            get_client()
            .table("silver_hourly")
            .select("inserted_at")
            .order("inserted_at", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data:
            return pd.to_datetime(resp.data[0]["inserted_at"], utc=True)
    except Exception:
        pass
    return None


# --- Emergency mode -----------------------------------------------------------

@cache_stub
def get_emergency_data(location: str | None = None) -> pd.DataFrame:
    """
    Pulls from gold_emergency_daily: daily MAX wave/wind/pressure + DMC-style
    classification (Safe / Caution / Dangerous). If location is None,
    returns all 15 locations (current default — Emergency is not scoped to
    a subset; that's still an open question with the team, see handoff).
    """
    _validate_location(location)
    query = get_client().table("gold_emergency_daily").select("*")
    if location:
        query = query.eq("location_name", location)
    resp = query.order("date").execute()
    df = pd.DataFrame(resp.data)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


# --- Tourism mode ---------------------------------------------------------

@cache_stub
def get_tourism_data(location: str | None = None) -> pd.DataFrame:
    """
    Pulls from gold_tourism_daily: daylight-hours (06:00-18:00) MEAN metrics
    plus a first-draft suitability score. sea_surface_temp_mean will be null
    for the 5 TOURISM_ONLY locations (no marine_ocean fetch) — the UI layer
    is responsible for showing an explanatory note, not a blank panel.
    """
    _validate_location(location)
    query = get_client().table("gold_tourism_daily").select("*")
    if location:
        query = query.eq("location_name", location)
    resp = query.order("date").execute()
    df = pd.DataFrame(resp.data)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df["is_tourism_only"] = df["location_name"].isin(TOURISM_ONLY)
    return df


# --- Tourism mode: extras from silver_hourly --------------------------------

@cache_stub
def get_tourism_extras(location: str) -> dict:
    """
    Daylight-hours (06:00-18:00) means for silver_hourly columns that
    aren't in gold_tourism_daily but matter to a tourist deciding whether
    to go out today: air quality (pm25) and surf detail (swell height,
    swell period, wave period). Computed on the fly from the latest
    calendar day of raw hourly data rather than added to the Gold table,
    since these are supplementary "nice to know" fields, not part of the
    daily suitability formula.

    Returns {} if no rows are found (mirrors get_emergency_data /
    get_tourism_data returning an empty DataFrame rather than raising for
    that case) — callers still need to handle a real connection error via
    try/except, same as the other get_* functions here.
    """
    _validate_location(location)
    if not location:
        return {}

    resp = (
        get_client()
        .table("silver_hourly")
        .select("timestamp, pm25, swell_height, swell_period, wave_period")
        .eq("location_name", location)
        .order("timestamp", desc=True)
        .limit(48)
        .execute()
    )
    df = pd.DataFrame(resp.data)
    if df.empty:
        return {}

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    latest_date = df["timestamp"].dt.date.max()
    day_df = df[df["timestamp"].dt.date == latest_date]
    daylight_df = day_df[(day_df["timestamp"].dt.hour >= 6) & (day_df["timestamp"].dt.hour < 18)]
    if daylight_df.empty:
        daylight_df = day_df

    means = daylight_df.mean(numeric_only=True)
    return {
        "pm25_mean": means.get("pm25"),
        "swell_height_mean": means.get("swell_height"),
        "swell_period_mean": means.get("swell_period"),
        "wave_period_mean": means.get("wave_period"),
    }


# --- Fisherman mode ---------------------------------------------------------

@cache_stub
def get_fisherman_silver(location: str, days_back: int = 30) -> pd.DataFrame:
    """
    Pulls raw hourly data from silver_hourly for a single location — this
    feeds both the SARIMA model (Phase 4, in progress) and, later, the
    Forecasts table once it exists. `days_back` limits payload size; the
    full 546-day history isn't needed for a rolling forecast view.

    NOTE: no `air_temperature` column exists in silver_hourly (confirmed via
    information_schema.columns) — don't reference it here or in any page.
    """
    if not location:
        raise ValueError("get_fisherman_silver requires a single location.")
    _validate_location(location)

    resp = (
        get_client()
        .table("silver_hourly")
        .select("*")
        .eq("location_name", location)
        .order("timestamp", desc=True)
        .limit(days_back * 24)
        .execute()
    )
    df = pd.DataFrame(resp.data)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
    return df


@cache_stub
def get_fisherman_forecast(location: str) -> pd.DataFrame:
    """
    Placeholder for the Forecasts table (not yet built — blocked on SARIMA,
    Phase 4). Returns mocked 48h dummy data shaped like the eventual real
    query so the Fisherman dashboard page can be built and demoed now, per
    the handoff's parallel-track recommendation. SWAP THIS OUT for a real
    `.table("forecasts").select("*")...` query once the table exists —
    do not let this mock silently linger past that point.
    """
    _validate_location(location)
    horizon = pd.date_range(
        start=pd.Timestamp.now("UTC").floor("h"), periods=48, freq="h"
    )
    import numpy as np
    rng = np.random.default_rng(seed=hash(location) % (2**32))
    mock_wave = 1.0 + 0.5 * np.sin(np.linspace(0, 4 * np.pi, 48)) + rng.normal(0, 0.1, 48)
    return pd.DataFrame(
        {
            "location_name": location,
            "forecast_time": horizon,
            "wave_height_forecast": mock_wave.clip(min=0),
            "is_mocked": True,  # UI must surface this flag, not hide it
        }
    )