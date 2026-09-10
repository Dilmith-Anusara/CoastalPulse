# CoastalPulse

Marine and coastal weather analytics dashboard for Sri Lanka, built for the DS4004 Big Data Analytics module, BSc Data Science, University of Colombo School of Computing.

CoastalPulse ingests hourly marine, weather, and air quality data for 15 coastal locations around Sri Lanka and serves it through three purpose-built dashboard modes:

- **Emergency** — daily peak wave height / wind / pressure, classified against DMC-derived danger thresholds
- **Tourism** — daylight-hours beach conditions and a suitability score, for planning a visit
- **Fisherman** — short-range (48h) forecast conditions for coastal fishing decisions

## Team

- Dilmith Yahathugoda (s16877)
- Dinusha Priyashan (s16798)
- Kavindu Perera (s16829)

## Project status

| Layer | Status |
|---|---|
| Bronze (raw ingestion) | ✅ Done, validated |
| Silver (hourly, cleaned) | ✅ Done, validated |
| Gold (daily aggregates) | ✅ Done, validated |
| Forecasts (SARIMA output) | 🔲 Not started |
| Dashboard | 🔲 Planned, not built |

## Architecture

Medallion architecture on top of Supabase (PostgreSQL):

```
Open-Meteo APIs (Marine, Historical Weather, Air Quality, Forecast)
        │
        ▼
   Bronze  (raw JSON per location/month, purged after Silver write)
        │
        ▼
   Silver  (silver_hourly — one row per location per hour, all sources joined)
        │
        ├──────────────────────┬─────────────────────┐
        ▼                      ▼                      ▼
  gold_emergency_daily   gold_tourism_daily      (Fisherman reads
  (daily MAX + DMC        (daylight-hours MEAN     silver_hourly
   classification)         + suitability score)     directly — no
                                                      Gold table)
```

Gold is intentionally split into two tables rather than one wide table, since Emergency and Tourism aggregate over genuinely different time windows (24h max vs. 06:00–18:00 mean).

## Data sources

Open-Meteo's free APIs: Marine (waves, swell, ocean current, sea surface temperature), Historical Weather (wind, precipitation, pressure), Air Quality (UV index, PM2.5), and Forecast (planned, for Fisherman mode).

## Locations

15 coastal locations across Sri Lanka. 5 are Tourism-only and skip the marine ocean current/temperature fetch (they don't need it and it reduces API load); the remaining 10 fetch the full data set.

Full list and coordinates live in `pipeline/fetch_data.py`'s `LOCATIONS` and `TOURISM_ONLY` — treated as the single source of truth across the whole pipeline, not duplicated elsewhere.

## Repository structure

```
Big Data Analytics/
├── pipeline/
│   ├── fetch_data.py         # Bronze → Silver ingestion pipeline
│   └── build_gold.py         # Silver → Gold aggregation
├── validation_scripts/
│   └── validate_gold.py      # Gold layer validation & report generation
├── spotcheck_trincomalee.py  # One-off spot-check against live Open-Meteo data
├── .env                      # Supabase credentials (not committed — see below)
├── .gitignore
└── README.md
```

## Setup

### Requirements

```
pip install requests supabase python-dotenv psycopg2-binary pandas
```

### Environment variables

Create a `.env` file in the project root (never commit this file):

```
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_KEY=<service_role key>
SUPABASE_DB_URL=postgresql://postgres:<password>@db.<your-project-ref>.supabase.co:5432/postgres
```

- `SUPABASE_URL` / `SUPABASE_KEY` — Project Settings → API in the Supabase dashboard. Use the `service_role` key for pipeline scripts (server-side, not exposed to any client).
- `SUPABASE_DB_URL` — Project Settings → Database → Connection string → URI. Needed for direct `psycopg2` access (schema DDL, raw queries) that the REST client can't do.

Make sure `.env` is listed in `.gitignore` before your first commit.

## Running the pipeline

```
python pipeline/fetch_data.py
```
Fetches all configured locations and date ranges, writes to Bronze, transforms into Silver, purges Bronze on success. Safe to re-run — skips date ranges already covered in Silver.

```
python pipeline/build_gold.py
```
Aggregates Silver into the two Gold tables. Safe to re-run — upserts on `(location_name, date)`, never duplicates.

```
python validation_scripts/validate_gold.py
```
Runs a full validation pass over both Gold tables (coverage, duplicates, plausibility ranges, classification consistency, null patterns) and writes `validation_report_gold.md`.

## Known limitations

- `sea_level_height` is not populated — no tide/storm-surge endpoint currently wired up. Emergency mode's danger classification is wave-height-based only and does not capture tidal flood risk.
- `sea_surface_temp` is unavailable by design for the 5 Tourism-only locations (no marine ocean fetch), plus one shared 12-day gap (Jan 30 – Feb 11, 2025) across the other 10 locations, likely a temporary upstream gap in Open-Meteo's marine reanalysis archive.
- The Emergency danger thresholds (Safe/Caution/Dangerous) are reconstructed from Sri Lankan DoM advisory language, not an official published table.
- Tourism's suitability score is a first-draft formula, not a specified or validated metric.
- 2024 data backfill is deliberately parked pending confirmed storage headroom against Supabase's free-tier cap.

## Roadmap

1. Analytical models — SARIMA (Fisherman), additive decomposition (Tourism), tree-ensemble (Emergency)
2. Forecasts table for SARIMA output
3. Dashboard (Dash/Plotly) — Emergency and Tourism modes first, Fisherman mode once forecasts exist
4. 2024 backfill, once storage is reconfirmed