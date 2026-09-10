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
try:
    from fetch_data import LOCATIONS, TOURISM_ONLY  # noqa: E402
except ImportError:
    # Fallback so this module can still be imported/tested standalone before
    # the pipeline/ folder is wired up in the same repo checkout. Keep this
    # in sync manually ONLY until the real import path is confirmed working —
    # this is exactly the kind of drift that caused the Gold-layer bug.
    LOCATIONS = [
        "Mirissa", "Hikkaduwa", "Unawatuna", "Bentota", "Arugam Bay",
        "Negombo", "Galle", "Trincomalee", "Chilaw", "Colombo",
        "Tangalle", "Batticaloa", "Jaffna", "Matara", "Puttalam",
    ]
    TOURISM_ONLY = {"Mirissa", "Hikkaduwa", "Unawatuna", "Bentota", "Arugam Bay"}

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
        start=pd.Timestamp.utcnow().floor("h"), periods=48, freq="h"
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