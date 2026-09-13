"""
build_forecasts.py — CoastalPulse Fisherman forecasting.

Reads silver_hourly directly (no Gold table for Fisherman — the raw hourly
wave_height series IS the model input, there's nothing to pre-aggregate),
fits a SARIMA model per location, and writes a 48-hour-ahead wave_height
forecast to a new `forecasts` table. The dashboard (data_access.py's
get_fisherman_forecast) only ever reads that table — it never fits a model
itself, the same "batch job writes, dashboard just reads" split as
fetch_data.py -> silver_hourly and build_gold.py -> gold_*.

MODEL CHOICE — order=(2,1,2), seasonal_order=(0,0,0,24):
Grid-searched by AIC over a small (p,d,q)(P,D,Q) space on Galle's hourly
wave_height (validation_scripts/interim.ipynb) and backtested across 5
holdout origins spanning the full year (Feb/Jun/Aug/Oct/Dec 2025), each
beating a naive persistence baseline (last observed value repeated) by
6.6-24.0% RMSE. The winning seasonal_order came back (0,0,0,24) — i.e. the
search found NO seasonal AR/I/MA terms worth their AIC cost at m=24; a
first-order difference already captured most of the hour-to-hour
structure. That's a real, if unintuitive, result from the search, not a
placeholder.

KNOWN LIMITATION: that order was only grid-searched for Galle. Re-running
a full grid search per location (15x) is expensive (the notebook's own
comment: "hourly SARIMAX with m=24 is expensive") and out of scope here —
this applies Galle's winning order to all 15 locations rather than
re-deriving it per location. To compensate, every location gets its own
backtest (not just Galle) before its live forecast is trusted, and the
resulting RMSE is stored alongside the forecast (see `backtest_rmse`) so
the dashboard can show real, per-location accuracy instead of assuming
the model performs the same everywhere. If a location's backtest RMSE is
much worse than Galle's, that's a sign it needs its own grid search later,
not that this pipeline is broken.

WHY NOT PERSIST THE MODEL ITSELF: refit from scratch on every run instead
of pickling/storing a trained model object. The serving side (Fisherman
page, deployed on Vercel) never needs the model — only this table's
output — so there's nowhere a persisted model would even need to be
loaded from, and refitting daily means the model always trains on the
latest conditions instead of going stale. This also keeps statsmodels out
of the Vercel deployment entirely (requirements-dev.txt only).
"""

import os
import warnings

from dotenv import load_dotenv
import numpy as np
import pandas as pd
import psycopg2
from statsmodels.tsa.statespace.sarimax import SARIMAX

from build_gold import _run_with_reconnect, clean_value
from fetch_data import LOCATIONS

warnings.filterwarnings("ignore")

load_dotenv()

SUPABASE_DB_URL = os.environ["SUPABASE_DB_URL"]

ALL_LOCATION_NAMES = [loc["name"] for loc in LOCATIONS]

ORDER = (2, 1, 2)
SEASONAL_ORDER = (0, 0, 0, 24)
FORECAST_HOURS = 48
MIN_HOURS_REQUIRED = 24 * 30  # ~1 month — below this a SARIMA fit isn't meaningful


# ---------------------------------------------------------------------------
# Table setup
# ---------------------------------------------------------------------------

def ensure_forecasts_table(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS forecasts (
            location_name        TEXT NOT NULL,
            forecast_time        TIMESTAMPTZ NOT NULL,
            generated_at         TIMESTAMPTZ NOT NULL,
            wave_height_forecast NUMERIC,
            ci_low               NUMERIC,
            ci_high              NUMERIC,
            model_type           TEXT,
            backtest_rmse        NUMERIC,
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
# Read Silver
# ---------------------------------------------------------------------------

def load_wave_series(conn, location_name: str) -> pd.Series:
    query = """
        SELECT timestamp, wave_height
        FROM silver_hourly
        WHERE location_name = %s
        ORDER BY timestamp;
    """
    df = pd.read_sql(query, conn, params=(location_name,))
    if df.empty:
        return pd.Series(dtype=float)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp")
    # asfreq enforces a regular hourly index, exposing any gaps as explicit
    # NaN rather than silently compressing the series — SARIMAX's Kalman
    # filter handles NaN observations as missing internally, same as the
    # validated notebook approach (no interpolation/fill needed).
    return df["wave_height"].asfreq("h")


# ---------------------------------------------------------------------------
# Fit + backtest + forecast
# ---------------------------------------------------------------------------

def _fit_sarimax(train: pd.Series):
    model = SARIMAX(
        train, order=ORDER, seasonal_order=SEASONAL_ORDER,
        enforce_stationarity=False, enforce_invertibility=False,
    )
    return model.fit(disp=False, maxiter=50)


def backtest_rmse(series: pd.Series, holdout_hours: int = FORECAST_HOURS):
    """Fits on everything except the last `holdout_hours`, forecasts that
    window, and compares to both the real values and a naive persistence
    baseline — the same check validated on Galle across 5 holdout origins.
    Returns (sarima_rmse, naive_rmse) or None if there isn't enough data.
    """
    clean = series.dropna()
    if len(clean) < MIN_HOURS_REQUIRED + holdout_hours:
        return None

    train, test = series.iloc[:-holdout_hours], series.iloc[-holdout_hours:]
    valid = test.notna().values
    if valid.sum() == 0 or train.dropna().empty:
        return None

    fitted = _fit_sarimax(train)
    forecast = fitted.get_forecast(steps=holdout_hours).predicted_mean

    sarima_rmse = float(np.sqrt(np.mean((forecast.values[valid] - test.values[valid]) ** 2)))
    naive = np.full(holdout_hours, train.dropna().iloc[-1])
    naive_rmse = float(np.sqrt(np.mean((naive[valid] - test.values[valid]) ** 2)))
    return sarima_rmse, naive_rmse


def build_forecast_df(location_name: str, series: pd.Series) -> pd.DataFrame:
    if series.dropna().shape[0] < MIN_HOURS_REQUIRED:
        return pd.DataFrame()

    bt = backtest_rmse(series)
    sarima_rmse = bt[0] if bt else None

    # Refit on the FULL series (not the backtest's truncated train split) —
    # the live forecast should use every hour of history available.
    fitted = _fit_sarimax(series)
    forecast = fitted.get_forecast(steps=FORECAST_HOURS)
    pred_mean = forecast.predicted_mean
    conf = forecast.conf_int()

    last_ts = series.index[-1]
    generated_at = pd.Timestamp.now(tz="UTC")

    rows = []
    for i in range(FORECAST_HOURS):
        rows.append(
            {
                "location_name": location_name,
                "forecast_time": last_ts + pd.Timedelta(hours=i + 1),
                "generated_at": generated_at,
                # Wave height can't be negative — SARIMA's mean/CI are
                # unconstrained and can dip below zero at longer, less
                # certain horizons; clamp rather than show a nonsense value.
                "wave_height_forecast": max(0.0, float(pred_mean.iloc[i])),
                "ci_low": max(0.0, float(conf.iloc[i, 0])),
                "ci_high": max(0.0, float(conf.iloc[i, 1])),
                "model_type": "SARIMA",
                "backtest_rmse": sarima_rmse,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------

def upsert_forecasts(conn, location_name: str, df: pd.DataFrame):
    cur = conn.cursor()
    # A location's forecast table rows should always be exactly its latest
    # 48-hour run, not accumulate stale future-dated rows from prior runs —
    # delete then insert rather than relying on ON CONFLICT alone.
    cur.execute("DELETE FROM forecasts WHERE location_name = %s;", (location_name,))
    for _, r in df.iterrows():
        cur.execute(
            """
            INSERT INTO forecasts
                (location_name, forecast_time, generated_at, wave_height_forecast,
                 ci_low, ci_high, model_type, backtest_rmse)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (location_name, forecast_time) DO UPDATE SET
                generated_at = EXCLUDED.generated_at,
                wave_height_forecast = EXCLUDED.wave_height_forecast,
                ci_low = EXCLUDED.ci_low,
                ci_high = EXCLUDED.ci_high,
                model_type = EXCLUDED.model_type,
                backtest_rmse = EXCLUDED.backtest_rmse;
            """,
            (
                r["location_name"], r["forecast_time"], r["generated_at"],
                clean_value(r["wave_height_forecast"]), clean_value(r["ci_low"]),
                clean_value(r["ci_high"]), r["model_type"], clean_value(r["backtest_rmse"]),
            ),
        )
    conn.commit()
    cur.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    _run_with_reconnect(ensure_forecasts_table)

    for location in ALL_LOCATION_NAMES:
        print(f"[Forecast] {location}...")
        try:
            series = _run_with_reconnect(load_wave_series, location)
            if series.dropna().empty:
                print("  no wave_height data, skipping")
                continue

            df = build_forecast_df(location, series)
            if df.empty:
                print(f"  not enough history ({series.dropna().shape[0]} hourly obs), skipping")
                continue

            _run_with_reconnect(upsert_forecasts, location, df)
            rmse = df["backtest_rmse"].iloc[0]
            if rmse is not None:
                print(f"  wrote {len(df)}h forecast, backtest RMSE={rmse:.3f} m")
            else:
                print(f"  wrote {len(df)}h forecast (backtest skipped — not enough history)")
        except Exception as e:
            print(f"  FAILED for {location}: {e}")
            continue

    print("\nDone. Spot-check backtest_rmse per location — Galle's validated around 0.05-0.23m depending on season; a location wildly worse than that needs its own order re-search, not a bug fix here.")


if __name__ == "__main__":
    main()
