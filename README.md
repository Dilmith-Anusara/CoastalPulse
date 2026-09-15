# CoastalPulse

A marine and coastal weather analytics dashboard for 15 locations around
Sri Lanka. It's built on a medallion (Bronze/Silver/Gold) data pipeline,
with Supabase Postgres as the database and a Dash app as the front end.

The dashboard is deployed on Vercel, and the data pipeline runs on a
schedule through GitHub Actions (`.github/workflows/pipeline.yml`).

## Pages

| Page | What it shows |
|---|---|
| **Overview** | A Sri-Lanka-wide snapshot: how many locations are currently Safe/Caution/Dangerous, the best beach score right now, a map, and a per-location picker. |
| **Emergency** | Per-location wave-height risk (Safe/Caution/Dangerous), the last 7 days observed, and a forward-looking outlook strip from Open-Meteo's forecast. |
| **Tourism** | Per-location beach suitability score (the HCI:Beach index, Gunathilake et al. 2023), the last 7 days observed, and a forward-looking outlook strip. |
| **Fisherman** | A go/no-go verdict based on the latest observed wave height, an 8-day wave-height forecast, and a swell/wind-wave breakdown (primary swell, secondary swell, wind waves), all from Open-Meteo's live forecast. |
| **Analytics** | Cross-location trends split by monsoon coast, extremes, an Emergency-vs-Tourism correlation check, and a forecasting case study built around a per-location SARIMA model (methodology, backtest RMSE vs. a naive baseline). This is the "forecasting skill" part of the project. |

## Architecture

**Bronze to Silver**: `pipeline/fetch_data.py` pulls historical/reanalysis
data from Open-Meteo (Marine, Forecast/Archive, and Air Quality APIs) for
all 15 locations. It stages the raw JSON in `bronze_raw`, then writes
parsed hourly rows to `silver_hourly` and clears out the Bronze rows once
that's done. There's a deliberate buffer here too, more on that below.

**Silver to Gold**: `pipeline/build_gold.py` aggregates `silver_hourly`
into two daily tables. `gold_emergency_daily` holds the daily max wave
height plus a Safe/Caution/Dangerous classification. `gold_tourism_daily`
holds the daylight-hours mean of several indicators plus an HCI:Beach
suitability score.

**Forecasts, two separate sources and two separate jobs**:
- `pipeline/fetch_marine_forecast.py` queries Open-Meteo's live forecast
  endpoints (not historical/reanalysis, a real physics-based operational
  blend of ECMWF WAM, NOAA GFS Wave, MeteoFrance MFWAM, and DWD EWAM/GWAM).
  It writes `marine_forecasts` (hourly, up to 8 days ahead, feeds
  Fisherman) plus `emergency_forecast_daily` and `tourism_forecast_daily`
  (daily aggregates, built by reusing `build_gold.py`'s own
  classification and scoring functions, so "Dangerous" or "Good" means the
  same thing whether the data is observed or forecast).
- `pipeline/build_forecasts.py` fits a SARIMA model per location, directly
  on `silver_hourly`'s wave-height series, and writes to `forecasts`. This
  feeds the Analytics page's case study, not a live user-facing forecast.
  A univariate autoregressive model has no storm/wind awareness and a much
  shorter useful horizon than Open-Meteo's operational models, so it isn't
  what Fisherman, Emergency, or Tourism actually use for decisions.

**Reading path**: every page goes through `data_access.py`. No page
queries Supabase directly.

## Data freshness, read this before trusting any "current" number

This is a scheduled batch pipeline, not a live feed.

Open-Meteo's own reanalysis data (ERA5/ERA5-Land, ERA5-Ocean) lags real
time by 5 days no matter how often it's queried, which is why the fetch
never asks for anything more recent than that. In practice the number you
actually see on the dashboard tends to run about a day further behind
still, closer to 6 days than 5. That extra day isn't Open-Meteo's fault,
it comes from how this project's own schedule lines up: the pipeline runs
late at night UTC, which lands in the early hours of the morning in Sri
Lanka (UTC+5:30), so by the time a Colombo-based user checks the dashboard
in the morning, the run that produced that data actually happened on the
UTC calendar day before. It's a real effect, confirmed against the
database directly, not just a guess.

Forecast data is fresher since Open-Meteo's own forecast models update
every few hours, but this pipeline only fetches once a day, so what's
displayed can be up to about 24 hours behind Open-Meteo's own current
forecast. Every forecast panel shows a real "Forecast generated Xh/Xd ago"
note computed from the actual fetch timestamp, not a static claim.

The header's "Updated Xh ago" badge reflects when the pipeline last ran
(`silver_hourly.inserted_at`), which isn't the same thing as how old the
underlying observation is. Those two numbers can and do diverge, and
that's exactly what the freshness copy across the dashboard is trying not
to paper over.

## Pipeline automation (GitHub Actions)

`.github/workflows/pipeline.yml` has two schedule triggers plus a manual
dispatch option.

- **Monday to Saturday, 20:07 UTC**: `fetch_data.py`, then `build_gold.py`,
  then `fetch_marine_forecast.py`. Fast, no SARIMA.
- **Sunday, 20:07 UTC**: the same three steps, plus `build_forecasts.py`
  (SARIMA). This one's the slowest by far, around 38 minutes since it
  refits on the full history every time, so it only runs weekly rather
  than daily. It only feeds Analytics' case study, not a live decision
  page, so there's no real need to run it every day.
- **Manual run** (workflow_dispatch): always runs all four steps.

`timeout-minutes: 90` is deliberate headroom, not the expected runtime.
It was sized after measuring how long each step actually takes and
accounting for Open-Meteo occasionally needing a retry from GitHub's
runner IPs.

## Database tables

| Table | Written by | Grain |
|---|---|---|
| `bronze_raw` | `fetch_data.py` | raw JSON, cleared out after promotion |
| `silver_hourly` | `fetch_data.py` | hourly, per location |
| `gold_emergency_daily` | `build_gold.py` | daily max, per location |
| `gold_tourism_daily` | `build_gold.py` | daily daylight-mean, per location |
| `marine_forecasts` | `fetch_marine_forecast.py` | hourly, up to 8 days ahead |
| `emergency_forecast_daily` | `fetch_marine_forecast.py` | daily, up to 8 days ahead |
| `tourism_forecast_daily` | `fetch_marine_forecast.py` | daily, up to 8 days ahead |
| `forecasts` | `build_forecasts.py` (SARIMA) | hourly, 48h ahead |

Every forecast table gets deleted and rewritten per location on each run,
so they always hold exactly the latest forecast and never build up stale
rows from a previous one.

There are 15 locations in total. 5 of them (`TOURISM_ONLY` in
`fetch_data.py`) skip the sea-surface-temperature/ocean-current fetch
entirely, so `sea_surface_temp_mean` is null by design for those 5 in
`gold_tourism_daily`. That's expected, not a data gap.

## Running locally

1. `pip install -r requirements.txt` for the dashboard, and separately
   `pip install -r requirements-pipeline.txt` if you need to run the
   pipeline scripts (this adds `statsmodels`, which is kept out of the
   dashboard's own dependencies so Vercel's deployed function stays lean).
2. Your `.env` needs `SUPABASE_URL` and `SUPABASE_KEY` (the REST API key,
   used by `data_access.py` and the dashboard), plus `SUPABASE_DB_URL`
   (the direct Postgres connection string, used only by the pipeline
   scripts for DDL and bulk upserts, never by the dashboard itself).
3. Run `python app.py` and open `http://127.0.0.1:8050`.

To run the pipeline manually instead of waiting for the schedule:

```
cd pipeline
python fetch_data.py
python build_gold.py
python fetch_marine_forecast.py
python build_forecasts.py   # slow, ~38 min, SARIMA, weekly in CI
```

## Deployment

The dashboard runs on Vercel (`vercel.json`, with `app.py`'s
`app = dash_app.server` as the WSGI entry point). The pipeline runs on
GitHub Actions only, none of the pipeline scripts run on the deployed
dashboard itself.
