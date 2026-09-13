"""
build_forecasts.py — CoastalPulse Fisherman forecasting.

Reads silver_hourly directly (no Gold table for Fisherman — the raw hourly
wave_height series IS the model input, there's nothing to pre-aggregate),
fits a SARIMA model per location, and writes a 48-hour-ahead wave_height
forecast to a new `forecasts` table. The dashboard (data_access.py's
get_fisherman_forecast) only ever reads that table — it never fits a model
itself, the same "batch job writes, dashboard just reads" split as
fetch_data.py -> silver_hourly and build_gold.py -> gold_*.

MODEL CHOICE (revised) — d=0, D=1, seasonal period m=24, (p,q) and (P,Q)
searched per COASTAL REGION:
The original order — (2,1,2)(0,0,0,24), grid-searched on Galle alone in
validation_scripts/interim.ipynb — turned out to be wrong everywhere, not
just under-verified elsewhere. Section 8 of
validation_scripts/eda_weather_indicators.ipynb ran real diagnostics
against all 15 locations and found, universally:
  - ACF at lag 24 of 0.80-0.92 (vs. a ~0.017 significance bound) — a real,
    strong daily cycle exists everywhere, on both coasts.
  - ADF says "stationary" (p<0.002) while KPSS says "non-stationary"
    (p=0.01, capped) at every location — the textbook signature of real
    seasonal structure, not a stochastic trend needing non-seasonal
    differencing.
  - The old model's own residuals still show significant 24h/48h
    autocorrelation everywhere (Ljung-Box p<=0.0046) — direct confirmation
    the missing seasonal term wasn't a Galle-specific quirk.
That evidence points at d=0 (ADF already says stationary, don't difference
away real structure) with D=1 seasonal differencing at m=24 (directly
targets the daily autocorrelation ADF can't see and the old model's
residuals confirm is still there) instead of the old non-seasonal d=1.

(p,q) and (P,Q) are grid-searched by AIC per coastal region (Southwest vs.
Northeast — see data_access.COAST_REGION; they're climatologically
opposite, so pooling them the way the original single order did isn't
appropriate) using one representative location each (Galle, Trincomalee)
on a 60-day window, then applied to every location in that region for the
real fit. This is still not a per-location search (15x grid searches
remains out of scope), but it's no longer a single Galle-only order
applied blind to a climatologically different coast, which is what the
Section 8 diagnostics actually flagged as the problem.

WHY NOT PERSIST THE MODEL ITSELF: refit from scratch on every run instead
of pickling/storing a trained model object. The serving side (Fisherman
page, deployed on Vercel) never needs the model — only this table's
output — so there's nowhere a persisted model would even need to be
loaded from, and refitting daily means the model always trains on the
latest conditions instead of going stale. This also keeps statsmodels out
of the Vercel deployment entirely (requirements-dev.txt only).
"""

import itertools
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

# Mirrors data_access.COAST_REGION exactly (see that module's own comment
# for the monsoon-climatology reasoning) — duplicated rather than imported
# because pipeline/ scripts don't depend on data_access.py (the dependency
# runs the other way: data_access.py depends on pipeline/, not vice versa,
# same reasoning build_gold.py already follows by deriving its own
# ALL_LOCATION_NAMES from fetch_data.LOCATIONS instead of importing it).
NORTHEAST_COAST = {"Trincomalee", "Batticaloa", "Arugam Bay", "Jaffna"}
COAST_REGION = {name: ("Northeast coast" if name in NORTHEAST_COAST else "Southwest coast") for name in ALL_LOCATION_NAMES}

# Fixed per the Section 8 diagnostics (see module docstring) — not searched.
D_ORDER = 0
D_SEASONAL = 1
SEASONAL_PERIOD = 24

# Small, AIC-selected per region rather than fixed globally.
SEARCH_P_RANGE = range(0, 3)
SEARCH_Q_RANGE = range(0, 3)
SEARCH_SEASONAL_P_RANGE = range(0, 2)
SEARCH_SEASONAL_Q_RANGE = range(0, 2)
SEARCH_WINDOW_HOURS = 24 * 60  # 60 days — same reasoning as interim.ipynb's 90-day search window, shortened since a seasonal search explores 4x more combinations

REGION_REPRESENTATIVE = {
    "Southwest coast": "Galle",
    "Northeast coast": "Trincomalee",
}

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
    # filter handles NaN observations as missing internally.
    return df["wave_height"].asfreq("h")


# ---------------------------------------------------------------------------
# Per-region seasonal order search
# ---------------------------------------------------------------------------

def search_region_order(series: pd.Series) -> tuple:
    """AIC grid search over (p,q) x (P,Q) with d/D/m fixed per the Section 8
    diagnostics, on a recent window (full-history seasonal fits are slow
    enough that searching on the full series for every candidate isn't
    practical — same reasoning interim.ipynb used for the original search).
    Returns (order, seasonal_order) for the winning combination.
    """
    window = series.dropna().iloc[-SEARCH_WINDOW_HOURS:]

    best_aic = np.inf
    best_order = (1, D_ORDER, 0)
    best_seasonal = (0, D_SEASONAL, 0, SEASONAL_PERIOD)

    for p, q, P, Q in itertools.product(
        SEARCH_P_RANGE, SEARCH_Q_RANGE, SEARCH_SEASONAL_P_RANGE, SEARCH_SEASONAL_Q_RANGE
    ):
        order = (p, D_ORDER, q)
        seasonal_order = (P, D_SEASONAL, Q, SEASONAL_PERIOD)
        try:
            model = SARIMAX(
                window, order=order, seasonal_order=seasonal_order,
                enforce_stationarity=False, enforce_invertibility=False,
            )
            fitted = model.fit(disp=False, maxiter=50)
            if fitted.aic < best_aic:
                best_aic = fitted.aic
                best_order, best_seasonal = order, seasonal_order
        except Exception:
            continue

    return best_order, best_seasonal, best_aic


# ---------------------------------------------------------------------------
# Fit + backtest + forecast
# ---------------------------------------------------------------------------

def _fit_sarimax(train: pd.Series, order: tuple, seasonal_order: tuple):
    model = SARIMAX(
        train, order=order, seasonal_order=seasonal_order,
        enforce_stationarity=False, enforce_invertibility=False,
    )
    return model.fit(disp=False, maxiter=50)


def backtest_rmse(series: pd.Series, order: tuple, seasonal_order: tuple, holdout_hours: int = FORECAST_HOURS):
    """Fits on everything except the last `holdout_hours`, forecasts that
    window, and compares to both the real values and a naive persistence
    baseline. Returns (sarima_rmse, naive_rmse) or None if there isn't
    enough data.
    """
    clean = series.dropna()
    if len(clean) < MIN_HOURS_REQUIRED + holdout_hours:
        return None

    train, test = series.iloc[:-holdout_hours], series.iloc[-holdout_hours:]
    valid = test.notna().values
    if valid.sum() == 0 or train.dropna().empty:
        return None

    fitted = _fit_sarimax(train, order, seasonal_order)
    forecast = fitted.get_forecast(steps=holdout_hours).predicted_mean

    sarima_rmse = float(np.sqrt(np.mean((forecast.values[valid] - test.values[valid]) ** 2)))
    naive = np.full(holdout_hours, train.dropna().iloc[-1])
    naive_rmse = float(np.sqrt(np.mean((naive[valid] - test.values[valid]) ** 2)))
    return sarima_rmse, naive_rmse


def build_forecast_df(location_name: str, series: pd.Series, order: tuple, seasonal_order: tuple) -> pd.DataFrame:
    if series.dropna().shape[0] < MIN_HOURS_REQUIRED:
        return pd.DataFrame()

    bt = backtest_rmse(series, order, seasonal_order)
    sarima_rmse = bt[0] if bt else None

    # Refit on the FULL series (not the backtest's truncated train split) —
    # the live forecast should use every hour of history available.
    fitted = _fit_sarimax(series, order, seasonal_order)
    forecast = fitted.get_forecast(steps=FORECAST_HOURS)
    pred_mean = forecast.predicted_mean
    conf = forecast.conf_int()

    last_ts = series.index[-1]
    generated_at = pd.Timestamp.now(tz="UTC")
    model_label = f"SARIMA{order}x{seasonal_order}"

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
                "model_type": model_label,
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

    print("Searching seasonal order per coastal region (fixed d=0, D=1, m=24)...")
    region_orders = {}
    for region, rep_location in REGION_REPRESENTATIVE.items():
        print(f"[Search] {region} (using {rep_location})...")
        series = _run_with_reconnect(load_wave_series, rep_location)
        order, seasonal_order, aic = search_region_order(series)
        region_orders[region] = (order, seasonal_order)
        print(f"  best: order={order}, seasonal_order={seasonal_order}, AIC={aic:.1f}")

    for location in ALL_LOCATION_NAMES:
        region = COAST_REGION.get(location)
        order, seasonal_order = region_orders.get(region, list(region_orders.values())[0])
        print(f"[Forecast] {location} ({region}) using order={order}, seasonal_order={seasonal_order}...")
        try:
            series = _run_with_reconnect(load_wave_series, location)
            if series.dropna().empty:
                print("  no wave_height data, skipping")
                continue

            df = build_forecast_df(location, series, order, seasonal_order)
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

    print("\nDone. Compare backtest_rmse against the previous non-seasonal run's values to confirm this is actually an improvement, not just a different number.")


if __name__ == "__main__":
    main()
