# CoastalPulse Dashboard — Skeleton

This is dashboard build Steps 1-3 + the Fisherman shell (Step 5), per the
handoff plan. **All files compile and `data_access.py` smoke-tests clean**,
but nothing here has been run against your real Supabase instance yet.

## How to drop this into the existing repo

Your project folder is `Big Data Analytics/` with `pipeline/` and
`validation_scripts/` already in it. Add these new files at the project
root, alongside `pipeline/`:

```
Big Data Analytics/
├── .env                      (already exists)
├── pipeline/                 (already exists)
│   ├── fetch_data.py
│   └── build_gold.py
├── validation_scripts/       (already exists)
│   └── validate_gold.py
├── data_access.py            <- NEW
├── app.py                    <- NEW
├── requirements.txt          <- NEW
└── pages/                    <- NEW
    ├── emergency.py
    ├── tourism.py
    └── fisherman.py
```

## Before running

1. `pip install -r requirements.txt`
2. Confirm `.env` has `SUPABASE_URL` and `SUPABASE_KEY` (the REST API key —
   `data_access.py` never touches `SUPABASE_DB_URL`, that's only for
   `build_gold.py`'s direct psycopg2/DDL work).
3. **Check column names against your actual Gold tables.** I inferred
   `wave_height_max`, `wind_speed_max`, `atmospheric_pressure_max`,
   `classification` for `gold_emergency_daily`, and `wave_height_mean`,
   `wind_speed_mean`, `sea_surface_temp_mean`, `suitability_score` for
   `gold_tourism_daily` from the handoff's description of the aggregation
   logic — I don't have `build_gold.py`'s actual `SELECT`/column-alias
   output, so these names may not match exactly. If a page errors on
   `KeyError`, that's almost certainly the fix needed (check
   `information_schema.columns` the same way you did for `silver_hourly`).
4. **`LOCATION_COORDS` in `pages/emergency.py` are placeholder
   coordinates I filled in from general knowledge, not from your pipeline.**
   Replace with the real lat/lon your `fetch_data.py` uses per location
   (it must have them already, since it calls the Open-Meteo APIs) before
   trusting the map.
5. Run: `python app.py`, open `http://127.0.0.1:8050`.

## What's deliberately NOT done yet (per the plan, not an oversight)

- **Flask-Caching** (Step 6) — `data_access.py` has a `cache_stub` no-op
  decorator ready to swap for real memoization once the app is stable.
- **Fisherman's real data** — `get_fisherman_forecast()` returns clearly
  labeled mock data (`is_mocked: True`) until SARIMA + the `Forecasts`
  table exist. The page banner and mock flag are intentional, not bugs.
- **Emergency location scoping** — the map/data currently default to all
  15 locations, per the current safe default in `build_gold.py`. If the
  team resolves the open scoping question, filter in `get_emergency_data()`
  in one place, not per-page.
- **Deployment secrets** (Step 7) — untouched, still using local `.env`.

## Suggested order to actually test this

1. Run `app.py` and see if the Emergency page loads with your real data —
   this will surface any column-name mismatches immediately (see #3 above).
2. Fix column names in `pages/emergency.py` and `data_access.py` together.
3. Move to Tourism, same process.
4. Fisherman page should "just work" against the mock — no real data
   dependency to fix there yet.