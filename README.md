# CoastalPulse

A marine and coastal weather analytics dashboard for 15 locations around Sri
Lanka, built on a medallion (Bronze → Silver → Gold) data pipeline with
Supabase Postgres as the warehouse and a Dash app as the front end.

Live app: deployed on Vercel. Data pipeline: scheduled via GitHub Actions
(`.github/workflows/pipeline.yml`).

## Pages

| Page | What it shows |
|---|---|
| **Overview** | Sri-Lanka-wide snapshot — how many locations are Safe/Caution/Dangerous right now, the best current beach score, a map, and a per-location mode-picker. |
| **Emergency** | Per-location wave-height risk (Safe/Caution/Dangerous), last 7 days observed, and a forward-looking outlook strip from Open-Meteo's forecast. |
| **Tourism** | Per-location beach suitability score (HCI:Beach index, Gunathilake et al. 2023), last 7 days observed, and a forward-looking outlook strip. |
| **Fisherman** | Go/no-go verdict from the latest observed wave height, an 8-day wave-height forecast, and a swell/wind-wave breakdown (primary swell, secondary swell, wind waves) — all from Open-Meteo's live forecast. |
| **Analytics** | Cross-location trends split by monsoon coast, extremes, Emergency-vs-Tourism correlation, and a forecasting case study presenting a per-location SARIMA model (methodology, backtest RMSE vs. a naive baseline) — the "forecasting skill" demonstration for this project. |

## Architecture

**Bronze → Silver**: `pipeline/fetch_data.py` pulls historical/reanalysis
data from Open-Meteo (Marine, Forecast/Archive, and Air Quality APIs) for
all 15 locations, stages the raw JSON in `bronze_raw`, then writes parsed
hourly rows to `silver_hourly` and purges the Bronze rows. A 5-day buffer
is deliberate — Open-Meteo's own reanalysis data (ERA5/ERA5-Land,
ERA5-Ocean) lags real time by 5 days regardless of how often it's queried.

**Silver → Gold**: `pipeline/build_gold.py` aggregates `silver_hourly` into
two daily tables — `gold_emergency_daily` (daily max wave height +
Safe/Caution/Dangerous classification) and `gold_tourism_daily`
(daylight-hours mean of several indicators + HCI:Beach suitability score).

**Forecasts — two separate sources, two separate jobs**:
- `pipeline/fetch_marine_forecast.py` queries Open-Meteo's *live* forecast
  endpoints (not historical/reanalysis — a real physics-based operational
  blend: ECMWF WAM, NOAA GFS Wave, MeteoFrance MFWAM, DWD EWAM/GWAM) and
  writes `marine_forecasts` (hourly, up to 8 days — feeds Fisherman)
  plus `emergency_forecast_daily` / `tourism_forecast_daily` (daily
  aggregates built by reusing `build_gold.py`'s own classification/scoring
  functions — one source of truth for what "Dangerous" or "Good" means,
  whether the data is observed or forecast).
- `pipeline/build_forecasts.py` fits a SARIMA model per location directly
  on `silver_hourly`'s wave-height series, writes to `forecasts`. This is
  the Analytics page's case study, not a live user-facing forecast — a
  univariate autoregressive model has no storm/wind awareness and a much
  shorter useful horizon than Open-Meteo's operational models, so it isn't
  what Fisherman/Emergency/Tourism actually use for decisions.

**Reading path**: every page goes through `data_access.py` — no page
queries Supabase directly.

## Data freshness — read this before trusting "current" numbers

This is a scheduled batch pipeline, not a live feed:

- **Observed (Gold) data** carries Open-Meteo's own 5-day reanalysis lag
  *plus* however long since the last pipeline run — so "the latest
  recorded conditions" can genuinely be several days old, not today's
  weather. The dashboard's copy was deliberately written to say "latest
  recorded" / "currently" rather than "today" or "live" for this reason.
- **Forecast data** (Fisherman/Emergency/Tourism outlook) is fresher —
  Open-Meteo's own forecast models update every few hours — but this
  pipeline only fetches once a day, so the displayed forecast can be up to
  ~24h behind Open-Meteo's current one. Every forecast panel shows a
  "Forecast generated Xh/Xd ago" note computed from the real fetch
  timestamp, not a static claim.
- The header's "Updated Xh ago" badge reflects when the pipeline last ran
  (`silver_hourly.inserted_at`), not the age of the underlying observation
  — the two can diverge, which is exactly what the freshness copy above is
  trying not to paper over.

## Pipeline automation (GitHub Actions)

`.github/workflows/pipeline.yml`, two schedule triggers plus manual
dispatch:

- **Mon–Sat, 20:07 UTC**: `fetch_data.py` → `build_gold.py` →
  `fetch_marine_forecast.py` (fast, no SARIMA).
- **Sunday, 20:07 UTC**: same three, plus `build_forecasts.py` (SARIMA) —
  by far the slowest step (~38 min, since it refits on full history every
  run), run weekly rather than daily since it only feeds Analytics' case
  study, not a live decision page.
- **Manual run** (workflow_dispatch): always includes all four steps.

`timeout-minutes: 90` is deliberate headroom, not the expected runtime —
sized after measuring real step durations against Open-Meteo's occasional
retry-on-timeout behavior from GitHub-runner IPs.

## Database tables

| Table | Written by | Grain |
|---|---|---|
| `bronze_raw` | `fetch_data.py` | raw JSON, purged after promotion |
| `silver_hourly` | `fetch_data.py` | hourly, per location |
| `gold_emergency_daily` | `build_gold.py` | daily max, per location |
| `gold_tourism_daily` | `build_gold.py` | daily daylight-mean, per location |
| `marine_forecasts` | `fetch_marine_forecast.py` | hourly, up to 8 days ahead |
| `emergency_forecast_daily` | `fetch_marine_forecast.py` | daily, up to 8 days ahead |
| `tourism_forecast_daily` | `fetch_marine_forecast.py` | daily, up to 8 days ahead |
| `forecasts` | `build_forecasts.py` (SARIMA) | hourly, 48h ahead |

All forecast tables are delete-then-insert per location on every run — they
always hold exactly the latest forecast, never accumulate stale rows from a
previous run.

15 locations total; 5 of them (`TOURISM_ONLY` in `fetch_data.py`) skip the
sea-surface-temperature/ocean-current fetch — `sea_surface_temp_mean` is
null by design for these 5 in `gold_tourism_daily`, not a data gap.

## Running locally

1. `pip install -r requirements.txt` (dashboard) and, separately,
   `pip install -r requirements-pipeline.txt` if you need to run the
   pipeline scripts (adds `statsmodels`, kept out of the dashboard's own
   deps so Vercel's deployed function stays lean).
2. `.env` needs `SUPABASE_URL`, `SUPABASE_KEY` (REST API key — used by
   `data_access.py` and the dashboard), and `SUPABASE_DB_URL` (direct
   Postgres connection string — used only by the pipeline scripts for DDL
   and bulk upserts, never by the dashboard itself).
3. `python app.py`, open `http://127.0.0.1:8050`.

To run the pipeline manually instead of waiting for the schedule:

```
cd pipeline
python fetch_data.py
python build_gold.py
python fetch_marine_forecast.py
python build_forecasts.py   # slow (~38 min) — SARIMA, weekly in CI
```

## Deployment

Dashboard: Vercel (`vercel.json`, `app.py`'s `app = dash_app.server` as the
WSGI entry point). Pipeline: GitHub Actions, not Vercel — none of the
pipeline scripts run on the deployed dashboard.
