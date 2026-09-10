# CoastalPulse Silver Layer Validation Report

Generated: 2026-09-10T10:48:46

Locations checked: Mirissa, Hikkaduwa, Unawatuna, Bentota, Arugam Bay, Negombo, Galle, Trincomalee, Chilaw, Colombo, Tangalle, Batticaloa, Jaffna, Matara, Puttalam

**Units note:** wind_speed and wind_gust are stored in km/h (Open-Meteo's default — fetch_data.py does not override it).

---

## Mirissa

```text
########## VALIDATING: Mirissa (tourism_only=True) ##########

======================================================================
1. Row coverage
======================================================================
  Expected hours:  13104
  Actual rows:     13104
  Coverage:        100.00%
  Date range:      2025-01-01 00:00:00+00:00  to  2026-06-30 23:00:00+00:00
  ✓ No duplicate timestamps (row count == distinct timestamp count)
  ✓ Coverage at or above the 95% skip-threshold used by the pipeline

======================================================================
2. Timestamp gap analysis
======================================================================
  ✓ No gaps — fully contiguous hourly series

======================================================================
3. Null audit
======================================================================
  Zero-tolerance columns (wave/wind/swell/AQ) — should be 0 nulls:
    ✓ wave_height               0 nulls (0.00%)
    ✓ wave_period               0 nulls (0.00%)
    ✓ wave_direction            0 nulls (0.00%)
    ✓ swell_height              0 nulls (0.00%)
    ✓ swell_period              0 nulls (0.00%)
    ✓ swell_direction           0 nulls (0.00%)
    ✓ wind_wave_height          0 nulls (0.00%)
    ✓ wind_speed                0 nulls (0.00%)
    ✓ wind_gust                 0 nulls (0.00%)
    ✓ precipitation             0 nulls (0.00%)
    ✓ atmospheric_pressure      0 nulls (0.00%)
    ✓ uv_index                  0 nulls (0.00%)
    ✓ pm25                      0 nulls (0.00%)

  Ocean-only columns (sea_surface_temp / current velocity / current direction):
  This is a Tourism-only location — these should be 100% null (marine_ocean endpoint is
  deliberately skipped). Non-null values here would mean the tourism-only skip didn't
  apply correctly.
    ✓ sea_surface_temp          13104/13104 null
    ✓ ocean_current_velocity    13104/13104 null
    ✓ ocean_current_direction   13104/13104 null

  sea_level_height: 13104/13104 null — expected, no endpoint wired up yet.

======================================================================
4. Physical plausibility ranges
======================================================================
  ✓ All values within plausible physical ranges

======================================================================
5. Monsoon-season sanity check (vs feasibility-analysis baseline)
======================================================================
  ✓ sw_monsoon      observed mean=2.03m  expected≈2.07m  (diff=0.04m, n=5136 rows)
  ✓ ne_monsoon      observed mean=1.22m  expected≈1.52m  (diff=0.30m, n=3576 rows)
  ✓ inter_monsoon   observed mean=1.36m  expected≈1.28m  (diff=0.08m, n=4392 rows)
  Note: this is a loose sanity check (±0.35m tolerance), not a re-validation of the
  original feasibility analysis — large deviations are worth a closer look, small ones aren't.

======================================================================
6. Cross-variable consistency
======================================================================
  ⚠️  wind_gust < wind_speed: 20 rows (gust should never be below sustained speed)
  ✓ wind_wave_height > wave_height (+0.3m tolerance): 0 rows (combined sea state should generally be >= its wind-wave component)
  ✓ wave_direction outside [0, 360): 0 rows
  ✓ swell_direction outside [0, 360): 0 rows

======================================================================
7. Statistical outliers (IQR, 3x whisker)
======================================================================
  ✓ wave_height          0 outliers (0.00%)
  ✓ wave_period          0 outliers (0.00%)
  ✓ swell_height         0 outliers (0.00%)
  ✓ wind_speed           0 outliers (0.00%)
  ✓ wind_gust            0 outliers (0.00%)
  ⚠️  precipitation        947 outliers (7.23%)  (range [-0.60, 0.80], observed min=0.9, max=21.1)
  ✓ atmospheric_pressure 0 outliers (0.00%)
  ✓ uv_index             7 outliers (0.05%)  (range [-9.45, 12.60], observed min=12.65, max=13.3)
  ⚠️  pm25                 189 outliers (1.44%)  (range [-26.70, 54.50], observed min=54.6, max=79.6)
  Note: 3x-IQR is deliberately loose — flags statistical rarity, not necessarily errors.
  A real storm (like Ditwah) will show up here too; that's expected, not a failure.
  Note: precipitation is zero-inflated (most hours are 0mm), so its Q1/Q3 sit near zero and
  ordinary rain will register as a mathematical 'outlier' here — treat this column's result
  as noise, not a data quality signal, until a fixed physical threshold replaces IQR for it.

======================================================================
8. Frozen-value detection (stuck consecutive values)
======================================================================
  ⚠️  wave_height: longest identical-value run = 17 hours, starting 2025-05-04 20:00:00+00:00
  ✓ wind_speed: longest identical-value run = 3 hours (below 6h threshold)
  ✓ atmospheric_pressure: longest identical-value run = 4 hours (below 6h threshold)
  ⚠️  uv_index: longest identical-value run = 14 hours, starting 2025-01-02 17:00:00+00:00  (likely nighttime, uv_index=0 for ~12-14h every night — not necessarily stuck)

======================================================================
9. Bronze purge confirmation
======================================================================
  ✓ bronze_raw has 0 rows for Mirissa — purge is working as designed

======================================================================
10. Known-event cross-check — Cyclone Ditwah (Nov 27-28, 2025)
======================================================================
  Nov 27-28 window: min pressure=1003.6 hPa (baseline avg=1009.2 hPa, drop=5.6 hPa)
  Nov 27-28 window: max precipitation=12.2 mm, max wave_height=3.3 m, max wind_gust=70.6 km/h
  Reference (independently reported, IMD/World Bank GRADE): Ditwah peak winds ~65-90 km/h
  sustained, gusts up to ~85 km/h at landfall. Compare this location's max_gust above
  against that range as a sanity check — values wildly above it are worth a closer look.
  ✓ Pressure drop is consistent with a real storm system passing through

```

---

## Hikkaduwa

```text
########## VALIDATING: Hikkaduwa (tourism_only=True) ##########

======================================================================
1. Row coverage
======================================================================
  Expected hours:  13104
  Actual rows:     13104
  Coverage:        100.00%
  Date range:      2025-01-01 00:00:00+00:00  to  2026-06-30 23:00:00+00:00
  ✓ No duplicate timestamps (row count == distinct timestamp count)
  ✓ Coverage at or above the 95% skip-threshold used by the pipeline

======================================================================
2. Timestamp gap analysis
======================================================================
  ✓ No gaps — fully contiguous hourly series

======================================================================
3. Null audit
======================================================================
  Zero-tolerance columns (wave/wind/swell/AQ) — should be 0 nulls:
    ✓ wave_height               0 nulls (0.00%)
    ✓ wave_period               0 nulls (0.00%)
    ✓ wave_direction            0 nulls (0.00%)
    ✓ swell_height              0 nulls (0.00%)
    ✓ swell_period              0 nulls (0.00%)
    ✓ swell_direction           0 nulls (0.00%)
    ✓ wind_wave_height          0 nulls (0.00%)
    ✓ wind_speed                0 nulls (0.00%)
    ✓ wind_gust                 0 nulls (0.00%)
    ✓ precipitation             0 nulls (0.00%)
    ✓ atmospheric_pressure      0 nulls (0.00%)
    ✓ uv_index                  0 nulls (0.00%)
    ✓ pm25                      0 nulls (0.00%)

  Ocean-only columns (sea_surface_temp / current velocity / current direction):
  This is a Tourism-only location — these should be 100% null (marine_ocean endpoint is
  deliberately skipped). Non-null values here would mean the tourism-only skip didn't
  apply correctly.
    ✓ sea_surface_temp          13104/13104 null
    ✓ ocean_current_velocity    13104/13104 null
    ✓ ocean_current_direction   13104/13104 null

  sea_level_height: 13104/13104 null — expected, no endpoint wired up yet.

======================================================================
4. Physical plausibility ranges
======================================================================
  ✓ All values within plausible physical ranges

======================================================================
5. Monsoon-season sanity check
======================================================================
  Skipped — no established feasibility-analysis baseline exists for Hikkaduwa yet.
  Only Mirissa has a baseline from the interim feasibility work. Add one here once you have
  an independent reference to check against, otherwise this section has nothing to compare to.

======================================================================
6. Cross-variable consistency
======================================================================
  ⚠️  wind_gust < wind_speed: 29 rows (gust should never be below sustained speed)
  ✓ wind_wave_height > wave_height (+0.3m tolerance): 0 rows (combined sea state should generally be >= its wind-wave component)
  ✓ wave_direction outside [0, 360): 0 rows
  ✓ swell_direction outside [0, 360): 0 rows

======================================================================
7. Statistical outliers (IQR, 3x whisker)
======================================================================
  ✓ wave_height          0 outliers (0.00%)
  ✓ wave_period          0 outliers (0.00%)
  ✓ swell_height         0 outliers (0.00%)
  ✓ wind_speed           0 outliers (0.00%)
  ✓ wind_gust            0 outliers (0.00%)
  ⚠️  precipitation        1354 outliers (10.33%)  (range [-0.60, 0.80], observed min=0.9, max=19.7)
  ✓ atmospheric_pressure 0 outliers (0.00%)
  ✓ uv_index             0 outliers (0.00%)
  ✓ pm25                 44 outliers (0.34%)  (range [-18.80, 44.90], observed min=45.3, max=53.2)
  Note: 3x-IQR is deliberately loose — flags statistical rarity, not necessarily errors.
  A real storm (like Ditwah) will show up here too; that's expected, not a failure.
  Note: precipitation is zero-inflated (most hours are 0mm), so its Q1/Q3 sit near zero and
  ordinary rain will register as a mathematical 'outlier' here — treat this column's result
  as noise, not a data quality signal, until a fixed physical threshold replaces IQR for it.

======================================================================
8. Frozen-value detection (stuck consecutive values)
======================================================================
  ⚠️  wave_height: longest identical-value run = 21 hours, starting 2025-04-20 04:00:00+00:00
  ✓ wind_speed: longest identical-value run = 3 hours (below 6h threshold)
  ✓ atmospheric_pressure: longest identical-value run = 4 hours (below 6h threshold)
  ⚠️  uv_index: longest identical-value run = 14 hours, starting 2025-11-26 17:00:00+00:00  (likely nighttime, uv_index=0 for ~12-14h every night — not necessarily stuck)

======================================================================
9. Bronze purge confirmation
======================================================================
  ✓ bronze_raw has 0 rows for Hikkaduwa — purge is working as designed

======================================================================
10. Known-event cross-check — Cyclone Ditwah (Nov 27-28, 2025)
======================================================================
  Nov 27-28 window: min pressure=1004.8 hPa (baseline avg=1009.5 hPa, drop=4.7 hPa)
  Nov 27-28 window: max precipitation=9.5 mm, max wave_height=2.84 m, max wind_gust=68.0 km/h
  Reference (independently reported, IMD/World Bank GRADE): Ditwah peak winds ~65-90 km/h
  sustained, gusts up to ~85 km/h at landfall. Compare this location's max_gust above
  against that range as a sanity check — values wildly above it are worth a closer look.
  ✓ Pressure drop is consistent with a real storm system passing through

```

---

## Unawatuna

```text
########## VALIDATING: Unawatuna (tourism_only=True) ##########

======================================================================
1. Row coverage
======================================================================
  Expected hours:  13104
  Actual rows:     13104
  Coverage:        100.00%
  Date range:      2025-01-01 00:00:00+00:00  to  2026-06-30 23:00:00+00:00
  ✓ No duplicate timestamps (row count == distinct timestamp count)
  ✓ Coverage at or above the 95% skip-threshold used by the pipeline

======================================================================
2. Timestamp gap analysis
======================================================================
  ✓ No gaps — fully contiguous hourly series

======================================================================
3. Null audit
======================================================================
  Zero-tolerance columns (wave/wind/swell/AQ) — should be 0 nulls:
    ✓ wave_height               0 nulls (0.00%)
    ✓ wave_period               0 nulls (0.00%)
    ✓ wave_direction            0 nulls (0.00%)
    ✓ swell_height              0 nulls (0.00%)
    ✓ swell_period              0 nulls (0.00%)
    ✓ swell_direction           0 nulls (0.00%)
    ✓ wind_wave_height          0 nulls (0.00%)
    ✓ wind_speed                0 nulls (0.00%)
    ✓ wind_gust                 0 nulls (0.00%)
    ✓ precipitation             0 nulls (0.00%)
    ✓ atmospheric_pressure      0 nulls (0.00%)
    ✓ uv_index                  0 nulls (0.00%)
    ✓ pm25                      0 nulls (0.00%)

  Ocean-only columns (sea_surface_temp / current velocity / current direction):
  This is a Tourism-only location — these should be 100% null (marine_ocean endpoint is
  deliberately skipped). Non-null values here would mean the tourism-only skip didn't
  apply correctly.
    ✓ sea_surface_temp          13104/13104 null
    ✓ ocean_current_velocity    13104/13104 null
    ✓ ocean_current_direction   13104/13104 null

  sea_level_height: 13104/13104 null — expected, no endpoint wired up yet.

======================================================================
4. Physical plausibility ranges
======================================================================
  ✓ All values within plausible physical ranges

======================================================================
5. Monsoon-season sanity check
======================================================================
  Skipped — no established feasibility-analysis baseline exists for Unawatuna yet.
  Only Mirissa has a baseline from the interim feasibility work. Add one here once you have
  an independent reference to check against, otherwise this section has nothing to compare to.

======================================================================
6. Cross-variable consistency
======================================================================
  ⚠️  wind_gust < wind_speed: 24 rows (gust should never be below sustained speed)
  ✓ wind_wave_height > wave_height (+0.3m tolerance): 0 rows (combined sea state should generally be >= its wind-wave component)
  ✓ wave_direction outside [0, 360): 0 rows
  ✓ swell_direction outside [0, 360): 0 rows

======================================================================
7. Statistical outliers (IQR, 3x whisker)
======================================================================
  ✓ wave_height          0 outliers (0.00%)
  ✓ wave_period          0 outliers (0.00%)
  ✓ swell_height         0 outliers (0.00%)
  ✓ wind_speed           0 outliers (0.00%)
  ✓ wind_gust            0 outliers (0.00%)
  ⚠️  precipitation        974 outliers (7.43%)  (range [-0.60, 0.80], observed min=0.9, max=22.7)
  ✓ atmospheric_pressure 0 outliers (0.00%)
  ✓ uv_index             7 outliers (0.05%)  (range [-9.45, 12.60], observed min=12.65, max=13.3)
  ⚠️  pm25                 189 outliers (1.44%)  (range [-26.70, 54.50], observed min=54.6, max=79.6)
  Note: 3x-IQR is deliberately loose — flags statistical rarity, not necessarily errors.
  A real storm (like Ditwah) will show up here too; that's expected, not a failure.
  Note: precipitation is zero-inflated (most hours are 0mm), so its Q1/Q3 sit near zero and
  ordinary rain will register as a mathematical 'outlier' here — treat this column's result
  as noise, not a data quality signal, until a fixed physical threshold replaces IQR for it.

======================================================================
8. Frozen-value detection (stuck consecutive values)
======================================================================
  ⚠️  wave_height: longest identical-value run = 23 hours, starting 2025-03-24 14:00:00+00:00
  ✓ wind_speed: longest identical-value run = 4 hours (below 6h threshold)
  ✓ atmospheric_pressure: longest identical-value run = 4 hours (below 6h threshold)
  ⚠️  uv_index: longest identical-value run = 14 hours, starting 2025-01-02 17:00:00+00:00  (likely nighttime, uv_index=0 for ~12-14h every night — not necessarily stuck)

======================================================================
9. Bronze purge confirmation
======================================================================
  ✓ bronze_raw has 0 rows for Unawatuna — purge is working as designed

======================================================================
10. Known-event cross-check — Cyclone Ditwah (Nov 27-28, 2025)
======================================================================
  Nov 27-28 window: min pressure=1004.9 hPa (baseline avg=1009.9 hPa, drop=5.0 hPa)
  Nov 27-28 window: max precipitation=9.5 mm, max wave_height=3.12 m, max wind_gust=72.4 km/h
  Reference (independently reported, IMD/World Bank GRADE): Ditwah peak winds ~65-90 km/h
  sustained, gusts up to ~85 km/h at landfall. Compare this location's max_gust above
  against that range as a sanity check — values wildly above it are worth a closer look.
  ✓ Pressure drop is consistent with a real storm system passing through

```

---

## Bentota

```text
########## VALIDATING: Bentota (tourism_only=True) ##########

======================================================================
1. Row coverage
======================================================================
  Expected hours:  13104
  Actual rows:     13104
  Coverage:        100.00%
  Date range:      2025-01-01 00:00:00+00:00  to  2026-06-30 23:00:00+00:00
  ✓ No duplicate timestamps (row count == distinct timestamp count)
  ✓ Coverage at or above the 95% skip-threshold used by the pipeline

======================================================================
2. Timestamp gap analysis
======================================================================
  ✓ No gaps — fully contiguous hourly series

======================================================================
3. Null audit
======================================================================
  Zero-tolerance columns (wave/wind/swell/AQ) — should be 0 nulls:
    ✓ wave_height               0 nulls (0.00%)
    ✓ wave_period               0 nulls (0.00%)
    ✓ wave_direction            0 nulls (0.00%)
    ✓ swell_height              0 nulls (0.00%)
    ✓ swell_period              0 nulls (0.00%)
    ✓ swell_direction           0 nulls (0.00%)
    ✓ wind_wave_height          0 nulls (0.00%)
    ✓ wind_speed                0 nulls (0.00%)
    ✓ wind_gust                 0 nulls (0.00%)
    ✓ precipitation             0 nulls (0.00%)
    ✓ atmospheric_pressure      0 nulls (0.00%)
    ✓ uv_index                  0 nulls (0.00%)
    ✓ pm25                      0 nulls (0.00%)

  Ocean-only columns (sea_surface_temp / current velocity / current direction):
  This is a Tourism-only location — these should be 100% null (marine_ocean endpoint is
  deliberately skipped). Non-null values here would mean the tourism-only skip didn't
  apply correctly.
    ✓ sea_surface_temp          13104/13104 null
    ✓ ocean_current_velocity    13104/13104 null
    ✓ ocean_current_direction   13104/13104 null

  sea_level_height: 13104/13104 null — expected, no endpoint wired up yet.

======================================================================
4. Physical plausibility ranges
======================================================================
  ✓ All values within plausible physical ranges

======================================================================
5. Monsoon-season sanity check
======================================================================
  Skipped — no established feasibility-analysis baseline exists for Bentota yet.
  Only Mirissa has a baseline from the interim feasibility work. Add one here once you have
  an independent reference to check against, otherwise this section has nothing to compare to.

======================================================================
6. Cross-variable consistency
======================================================================
  ⚠️  wind_gust < wind_speed: 35 rows (gust should never be below sustained speed)
  ✓ wind_wave_height > wave_height (+0.3m tolerance): 0 rows (combined sea state should generally be >= its wind-wave component)
  ✓ wave_direction outside [0, 360): 0 rows
  ✓ swell_direction outside [0, 360): 0 rows

======================================================================
7. Statistical outliers (IQR, 3x whisker)
======================================================================
  ✓ wave_height          0 outliers (0.00%)
  ✓ wave_period          0 outliers (0.00%)
  ✓ swell_height         0 outliers (0.00%)
  ✓ wind_speed           5 outliers (0.04%)  (range [-20.10, 38.70], observed min=38.9, max=40.5)
  ✓ wind_gust            0 outliers (0.00%)
  ⚠️  precipitation        1258 outliers (9.60%)  (range [-0.60, 0.80], observed min=0.9, max=16.7)
  ✓ atmospheric_pressure 0 outliers (0.00%)
  ✓ uv_index             7 outliers (0.05%)  (range [-9.00, 12.00], observed min=12.05, max=12.9)
  ✓ pm25                 0 outliers (0.00%)
  Note: 3x-IQR is deliberately loose — flags statistical rarity, not necessarily errors.
  A real storm (like Ditwah) will show up here too; that's expected, not a failure.
  Note: precipitation is zero-inflated (most hours are 0mm), so its Q1/Q3 sit near zero and
  ordinary rain will register as a mathematical 'outlier' here — treat this column's result
  as noise, not a data quality signal, until a fixed physical threshold replaces IQR for it.

======================================================================
8. Frozen-value detection (stuck consecutive values)
======================================================================
  ⚠️  wave_height: longest identical-value run = 26 hours, starting 2026-02-27 07:00:00+00:00
  ✓ wind_speed: longest identical-value run = 3 hours (below 6h threshold)
  ✓ atmospheric_pressure: longest identical-value run = 4 hours (below 6h threshold)
  ⚠️  uv_index: longest identical-value run = 14 hours, starting 2025-01-11 17:00:00+00:00  (likely nighttime, uv_index=0 for ~12-14h every night — not necessarily stuck)

======================================================================
9. Bronze purge confirmation
======================================================================
  ✓ bronze_raw has 0 rows for Bentota — purge is working as designed

======================================================================
10. Known-event cross-check — Cyclone Ditwah (Nov 27-28, 2025)
======================================================================
  Nov 27-28 window: min pressure=1005.6 hPa (baseline avg=1010.0 hPa, drop=4.4 hPa)
  Nov 27-28 window: max precipitation=12.2 mm, max wave_height=3.26 m, max wind_gust=74.2 km/h
  Reference (independently reported, IMD/World Bank GRADE): Ditwah peak winds ~65-90 km/h
  sustained, gusts up to ~85 km/h at landfall. Compare this location's max_gust above
  against that range as a sanity check — values wildly above it are worth a closer look.
  ✓ Pressure drop is consistent with a real storm system passing through

```

---

## Arugam Bay

```text
########## VALIDATING: Arugam Bay (tourism_only=True) ##########

======================================================================
1. Row coverage
======================================================================
  Expected hours:  13104
  Actual rows:     13104
  Coverage:        100.00%
  Date range:      2025-01-01 00:00:00+00:00  to  2026-06-30 23:00:00+00:00
  ✓ No duplicate timestamps (row count == distinct timestamp count)
  ✓ Coverage at or above the 95% skip-threshold used by the pipeline

======================================================================
2. Timestamp gap analysis
======================================================================
  ✓ No gaps — fully contiguous hourly series

======================================================================
3. Null audit
======================================================================
  Zero-tolerance columns (wave/wind/swell/AQ) — should be 0 nulls:
    ✓ wave_height               0 nulls (0.00%)
    ✓ wave_period               0 nulls (0.00%)
    ✓ wave_direction            0 nulls (0.00%)
    ✓ swell_height              0 nulls (0.00%)
    ✓ swell_period              0 nulls (0.00%)
    ✓ swell_direction           0 nulls (0.00%)
    ✓ wind_wave_height          0 nulls (0.00%)
    ✓ wind_speed                0 nulls (0.00%)
    ✓ wind_gust                 0 nulls (0.00%)
    ✓ precipitation             0 nulls (0.00%)
    ✓ atmospheric_pressure      0 nulls (0.00%)
    ✓ uv_index                  0 nulls (0.00%)
    ✓ pm25                      0 nulls (0.00%)

  Ocean-only columns (sea_surface_temp / current velocity / current direction):
  This is a Tourism-only location — these should be 100% null (marine_ocean endpoint is
  deliberately skipped). Non-null values here would mean the tourism-only skip didn't
  apply correctly.
    ✓ sea_surface_temp          13104/13104 null
    ✓ ocean_current_velocity    13104/13104 null
    ✓ ocean_current_direction   13104/13104 null

  sea_level_height: 13104/13104 null — expected, no endpoint wired up yet.

======================================================================
4. Physical plausibility ranges
======================================================================
  ✓ All values within plausible physical ranges

======================================================================
5. Monsoon-season sanity check
======================================================================
  Skipped — no established feasibility-analysis baseline exists for Arugam Bay yet.
  Only Mirissa has a baseline from the interim feasibility work. Add one here once you have
  an independent reference to check against, otherwise this section has nothing to compare to.

======================================================================
6. Cross-variable consistency
======================================================================
  ⚠️  wind_gust < wind_speed: 11 rows (gust should never be below sustained speed)
  ✓ wind_wave_height > wave_height (+0.3m tolerance): 0 rows (combined sea state should generally be >= its wind-wave component)
  ✓ wave_direction outside [0, 360): 0 rows
  ✓ swell_direction outside [0, 360): 0 rows

======================================================================
7. Statistical outliers (IQR, 3x whisker)
======================================================================
  ✓ wave_height          0 outliers (0.00%)
  ✓ wave_period          0 outliers (0.00%)
  ✓ swell_height         0 outliers (0.00%)
  ✓ wind_speed           0 outliers (0.00%)
  ✓ wind_gust            0 outliers (0.00%)
  ⚠️  precipitation        1286 outliers (9.81%)  (range [-0.30, 0.40], observed min=0.5, max=24.9)
  ✓ atmospheric_pressure 0 outliers (0.00%)
  ✓ uv_index             0 outliers (0.00%)
  ⚠️  pm25                 223 outliers (1.70%)  (range [-16.10, 34.30], observed min=34.5, max=48.7)
  Note: 3x-IQR is deliberately loose — flags statistical rarity, not necessarily errors.
  A real storm (like Ditwah) will show up here too; that's expected, not a failure.
  Note: precipitation is zero-inflated (most hours are 0mm), so its Q1/Q3 sit near zero and
  ordinary rain will register as a mathematical 'outlier' here — treat this column's result
  as noise, not a data quality signal, until a fixed physical threshold replaces IQR for it.

======================================================================
8. Frozen-value detection (stuck consecutive values)
======================================================================
  ⚠️  wave_height: longest identical-value run = 30 hours, starting 2026-02-27 19:00:00+00:00
  ✓ wind_speed: longest identical-value run = 3 hours (below 6h threshold)
  ✓ atmospheric_pressure: longest identical-value run = 4 hours (below 6h threshold)
  ⚠️  uv_index: longest identical-value run = 13 hours, starting 2025-01-01 18:00:00+00:00  (likely nighttime, uv_index=0 for ~12-14h every night — not necessarily stuck)

======================================================================
9. Bronze purge confirmation
======================================================================
  ✓ bronze_raw has 0 rows for Arugam Bay — purge is working as designed

======================================================================
10. Known-event cross-check — Cyclone Ditwah (Nov 27-28, 2025)
======================================================================
  Nov 27-28 window: min pressure=1001.1 hPa (baseline avg=1009.3 hPa, drop=8.2 hPa)
  Nov 27-28 window: max precipitation=3.3 mm, max wave_height=1.58 m, max wind_gust=47.9 km/h
  Reference (independently reported, IMD/World Bank GRADE): Ditwah peak winds ~65-90 km/h
  sustained, gusts up to ~85 km/h at landfall. Compare this location's max_gust above
  against that range as a sanity check — values wildly above it are worth a closer look.
  ✓ Pressure drop is consistent with a real storm system passing through

```

---

## Negombo

```text
########## VALIDATING: Negombo (tourism_only=False) ##########

======================================================================
1. Row coverage
======================================================================
  Expected hours:  13104
  Actual rows:     13104
  Coverage:        100.00%
  Date range:      2025-01-01 00:00:00+00:00  to  2026-06-30 23:00:00+00:00
  ✓ No duplicate timestamps (row count == distinct timestamp count)
  ✓ Coverage at or above the 95% skip-threshold used by the pipeline

======================================================================
2. Timestamp gap analysis
======================================================================
  ✓ No gaps — fully contiguous hourly series

======================================================================
3. Null audit
======================================================================
  Zero-tolerance columns (wave/wind/swell/AQ) — should be 0 nulls:
    ✓ wave_height               0 nulls (0.00%)
    ✓ wave_period               0 nulls (0.00%)
    ✓ wave_direction            0 nulls (0.00%)
    ✓ swell_height              0 nulls (0.00%)
    ✓ swell_period              0 nulls (0.00%)
    ✓ swell_direction           0 nulls (0.00%)
    ✓ wind_wave_height          0 nulls (0.00%)
    ✓ wind_speed                0 nulls (0.00%)
    ✓ wind_gust                 0 nulls (0.00%)
    ✓ precipitation             0 nulls (0.00%)
    ✓ atmospheric_pressure      0 nulls (0.00%)
    ✓ uv_index                  0 nulls (0.00%)
    ✓ pm25                      0 nulls (0.00%)

  Ocean-only columns (sea_surface_temp / current velocity / current direction):
  This location fetches marine_ocean data — ≤5% null tolerance applies (known SST gap):
    ✓ sea_surface_temp          312 nulls (2.38%)
    ✓ ocean_current_velocity    0 nulls (0.00%)
    ✓ ocean_current_direction   0 nulls (0.00%)

  sea_level_height: 13104/13104 null — expected, no endpoint wired up yet.

======================================================================
4. Physical plausibility ranges
======================================================================
  ✓ All values within plausible physical ranges

======================================================================
5. Monsoon-season sanity check
======================================================================
  Skipped — no established feasibility-analysis baseline exists for Negombo yet.
  Only Mirissa has a baseline from the interim feasibility work. Add one here once you have
  an independent reference to check against, otherwise this section has nothing to compare to.

======================================================================
6. Cross-variable consistency
======================================================================
  ⚠️  wind_gust < wind_speed: 6 rows (gust should never be below sustained speed)
  ✓ wind_wave_height > wave_height (+0.3m tolerance): 0 rows (combined sea state should generally be >= its wind-wave component)
  ✓ wave_direction outside [0, 360): 0 rows
  ✓ swell_direction outside [0, 360): 0 rows

======================================================================
7. Statistical outliers (IQR, 3x whisker)
======================================================================
  ✓ wave_height          0 outliers (0.00%)
  ✓ wave_period          0 outliers (0.00%)
  ✓ swell_height         0 outliers (0.00%)
  ✓ wind_speed           4 outliers (0.03%)  (range [-18.00, 42.90], observed min=43.5, max=48.1)
  ✓ wind_gust            1 outliers (0.01%)  (range [-36.50, 92.30], observed min=94.0, max=94.0)
  ⚠️  precipitation        1669 outliers (12.74%)  (range [-0.30, 0.40], observed min=0.5, max=30.9)
  ✓ atmospheric_pressure 0 outliers (0.00%)
  ✓ uv_index             2 outliers (0.02%)  (range [-9.30, 12.40], observed min=12.5, max=12.65)
  ✓ pm25                 33 outliers (0.25%)  (range [-26.40, 61.10], observed min=61.2, max=91.3)
  Note: 3x-IQR is deliberately loose — flags statistical rarity, not necessarily errors.
  A real storm (like Ditwah) will show up here too; that's expected, not a failure.
  Note: precipitation is zero-inflated (most hours are 0mm), so its Q1/Q3 sit near zero and
  ordinary rain will register as a mathematical 'outlier' here — treat this column's result
  as noise, not a data quality signal, until a fixed physical threshold replaces IQR for it.

======================================================================
8. Frozen-value detection (stuck consecutive values)
======================================================================
  ⚠️  wave_height: longest identical-value run = 26 hours, starting 2025-03-30 04:00:00+00:00
  ✓ wind_speed: longest identical-value run = 4 hours (below 6h threshold)
  ✓ atmospheric_pressure: longest identical-value run = 4 hours (below 6h threshold)
  ⚠️  uv_index: longest identical-value run = 14 hours, starting 2025-10-20 17:00:00+00:00  (likely nighttime, uv_index=0 for ~12-14h every night — not necessarily stuck)

======================================================================
9. Bronze purge confirmation
======================================================================
  ✓ bronze_raw has 0 rows for Negombo — purge is working as designed

======================================================================
10. Known-event cross-check — Cyclone Ditwah (Nov 27-28, 2025)
======================================================================
  Nov 27-28 window: min pressure=1004.2 hPa (baseline avg=1009.0 hPa, drop=4.8 hPa)
  Nov 27-28 window: max precipitation=30.9 mm, max wave_height=3.3 m, max wind_gust=94.0 km/h
  Reference (independently reported, IMD/World Bank GRADE): Ditwah peak winds ~65-90 km/h
  sustained, gusts up to ~85 km/h at landfall. Compare this location's max_gust above
  against that range as a sanity check — values wildly above it are worth a closer look.
  ✓ Pressure drop is consistent with a real storm system passing through

```

---

## Galle

```text
########## VALIDATING: Galle (tourism_only=False) ##########

======================================================================
1. Row coverage
======================================================================
  Expected hours:  13104
  Actual rows:     13104
  Coverage:        100.00%
  Date range:      2025-01-01 00:00:00+00:00  to  2026-06-30 23:00:00+00:00
  ✓ No duplicate timestamps (row count == distinct timestamp count)
  ✓ Coverage at or above the 95% skip-threshold used by the pipeline

======================================================================
2. Timestamp gap analysis
======================================================================
  ✓ No gaps — fully contiguous hourly series

======================================================================
3. Null audit
======================================================================
  Zero-tolerance columns (wave/wind/swell/AQ) — should be 0 nulls:
    ✓ wave_height               0 nulls (0.00%)
    ✓ wave_period               0 nulls (0.00%)
    ✓ wave_direction            0 nulls (0.00%)
    ✓ swell_height              0 nulls (0.00%)
    ✓ swell_period              0 nulls (0.00%)
    ✓ swell_direction           0 nulls (0.00%)
    ✓ wind_wave_height          0 nulls (0.00%)
    ✓ wind_speed                0 nulls (0.00%)
    ✓ wind_gust                 0 nulls (0.00%)
    ✓ precipitation             0 nulls (0.00%)
    ✓ atmospheric_pressure      0 nulls (0.00%)
    ✓ uv_index                  0 nulls (0.00%)
    ✓ pm25                      0 nulls (0.00%)

  Ocean-only columns (sea_surface_temp / current velocity / current direction):
  This location fetches marine_ocean data — ≤5% null tolerance applies (known SST gap):
    ✓ sea_surface_temp          312 nulls (2.38%)
    ✓ ocean_current_velocity    0 nulls (0.00%)
    ✓ ocean_current_direction   0 nulls (0.00%)

  sea_level_height: 13104/13104 null — expected, no endpoint wired up yet.

======================================================================
4. Physical plausibility ranges
======================================================================
  ✓ All values within plausible physical ranges

======================================================================
5. Monsoon-season sanity check
======================================================================
  Skipped — no established feasibility-analysis baseline exists for Galle yet.
  Only Mirissa has a baseline from the interim feasibility work. Add one here once you have
  an independent reference to check against, otherwise this section has nothing to compare to.

======================================================================
6. Cross-variable consistency
======================================================================
  ⚠️  wind_gust < wind_speed: 37 rows (gust should never be below sustained speed)
  ✓ wind_wave_height > wave_height (+0.3m tolerance): 0 rows (combined sea state should generally be >= its wind-wave component)
  ✓ wave_direction outside [0, 360): 0 rows
  ✓ swell_direction outside [0, 360): 0 rows

======================================================================
7. Statistical outliers (IQR, 3x whisker)
======================================================================
  ✓ wave_height          0 outliers (0.00%)
  ✓ wave_period          0 outliers (0.00%)
  ✓ swell_height         0 outliers (0.00%)
  ✓ wind_speed           0 outliers (0.00%)
  ✓ wind_gust            0 outliers (0.00%)
  ⚠️  precipitation        1206 outliers (9.20%)  (range [-0.60, 0.80], observed min=0.9, max=27.2)
  ✓ atmospheric_pressure 0 outliers (0.00%)
  ✓ uv_index             7 outliers (0.05%)  (range [-9.45, 12.60], observed min=12.65, max=13.3)
  ⚠️  pm25                 189 outliers (1.44%)  (range [-26.70, 54.50], observed min=54.6, max=79.6)
  Note: 3x-IQR is deliberately loose — flags statistical rarity, not necessarily errors.
  A real storm (like Ditwah) will show up here too; that's expected, not a failure.
  Note: precipitation is zero-inflated (most hours are 0mm), so its Q1/Q3 sit near zero and
  ordinary rain will register as a mathematical 'outlier' here — treat this column's result
  as noise, not a data quality signal, until a fixed physical threshold replaces IQR for it.

======================================================================
8. Frozen-value detection (stuck consecutive values)
======================================================================
  ⚠️  wave_height: longest identical-value run = 23 hours, starting 2025-03-24 14:00:00+00:00
  ✓ wind_speed: longest identical-value run = 3 hours (below 6h threshold)
  ✓ atmospheric_pressure: longest identical-value run = 4 hours (below 6h threshold)
  ⚠️  uv_index: longest identical-value run = 14 hours, starting 2025-01-02 17:00:00+00:00  (likely nighttime, uv_index=0 for ~12-14h every night — not necessarily stuck)

======================================================================
9. Bronze purge confirmation
======================================================================
  ✓ bronze_raw has 0 rows for Galle — purge is working as designed

======================================================================
10. Known-event cross-check — Cyclone Ditwah (Nov 27-28, 2025)
======================================================================
  Nov 27-28 window: min pressure=1004.6 hPa (baseline avg=1009.5 hPa, drop=4.9 hPa)
  Nov 27-28 window: max precipitation=9.5 mm, max wave_height=3.12 m, max wind_gust=64.1 km/h
  Reference (independently reported, IMD/World Bank GRADE): Ditwah peak winds ~65-90 km/h
  sustained, gusts up to ~85 km/h at landfall. Compare this location's max_gust above
  against that range as a sanity check — values wildly above it are worth a closer look.
  ✓ Pressure drop is consistent with a real storm system passing through

```

---

## Trincomalee

```text
########## VALIDATING: Trincomalee (tourism_only=False) ##########

======================================================================
1. Row coverage
======================================================================
  Expected hours:  13104
  Actual rows:     13104
  Coverage:        100.00%
  Date range:      2025-01-01 00:00:00+00:00  to  2026-06-30 23:00:00+00:00
  ✓ No duplicate timestamps (row count == distinct timestamp count)
  ✓ Coverage at or above the 95% skip-threshold used by the pipeline

======================================================================
2. Timestamp gap analysis
======================================================================
  ✓ No gaps — fully contiguous hourly series

======================================================================
3. Null audit
======================================================================
  Zero-tolerance columns (wave/wind/swell/AQ) — should be 0 nulls:
    ✓ wave_height               0 nulls (0.00%)
    ✓ wave_period               0 nulls (0.00%)
    ✓ wave_direction            0 nulls (0.00%)
    ✓ swell_height              0 nulls (0.00%)
    ✓ swell_period              0 nulls (0.00%)
    ✓ swell_direction           0 nulls (0.00%)
    ✓ wind_wave_height          0 nulls (0.00%)
    ✓ wind_speed                0 nulls (0.00%)
    ✓ wind_gust                 0 nulls (0.00%)
    ✓ precipitation             0 nulls (0.00%)
    ✓ atmospheric_pressure      0 nulls (0.00%)
    ✓ uv_index                  0 nulls (0.00%)
    ✓ pm25                      0 nulls (0.00%)

  Ocean-only columns (sea_surface_temp / current velocity / current direction):
  This location fetches marine_ocean data — ≤5% null tolerance applies (known SST gap):
    ✓ sea_surface_temp          312 nulls (2.38%)
    ✓ ocean_current_velocity    0 nulls (0.00%)
    ✓ ocean_current_direction   0 nulls (0.00%)

  sea_level_height: 13104/13104 null — expected, no endpoint wired up yet.

======================================================================
4. Physical plausibility ranges
======================================================================
  ✓ All values within plausible physical ranges

======================================================================
5. Monsoon-season sanity check
======================================================================
  Skipped — no established feasibility-analysis baseline exists for Trincomalee yet.
  Only Mirissa has a baseline from the interim feasibility work. Add one here once you have
  an independent reference to check against, otherwise this section has nothing to compare to.

======================================================================
6. Cross-variable consistency
======================================================================
  ⚠️  wind_gust < wind_speed: 4 rows (gust should never be below sustained speed)
  ✓ wind_wave_height > wave_height (+0.3m tolerance): 0 rows (combined sea state should generally be >= its wind-wave component)
  ✓ wave_direction outside [0, 360): 0 rows
  ✓ swell_direction outside [0, 360): 0 rows

======================================================================
7. Statistical outliers (IQR, 3x whisker)
======================================================================
  ✓ wave_height          76 outliers (0.58%)  (range [-0.96, 1.84], observed min=1.86, max=3.12)
  ✓ wave_period          0 outliers (0.00%)
  ✓ swell_height         4 outliers (0.03%)  (range [-1.06, 1.74], observed min=1.78, max=2.08)
  ✓ wind_speed           4 outliers (0.03%)  (range [-21.20, 50.20], observed min=53.7, max=58.8)
  ✓ wind_gust            7 outliers (0.05%)  (range [-34.60, 91.40], observed min=92.2, max=104.8)
  ⚠️  precipitation        3242 outliers (24.74%)  (range [0.00, 0.00], observed min=0.1, max=35.1)
  ✓ atmospheric_pressure 0 outliers (0.00%)
  ✓ uv_index             1 outliers (0.01%)  (range [-9.60, 12.80], observed min=12.95, max=12.95)
  ⚠️  pm25                 191 outliers (1.46%)  (range [-17.60, 36.30], observed min=36.4, max=52.0)
  Note: 3x-IQR is deliberately loose — flags statistical rarity, not necessarily errors.
  A real storm (like Ditwah) will show up here too; that's expected, not a failure.
  Note: precipitation is zero-inflated (most hours are 0mm), so its Q1/Q3 sit near zero and
  ordinary rain will register as a mathematical 'outlier' here — treat this column's result
  as noise, not a data quality signal, until a fixed physical threshold replaces IQR for it.

======================================================================
8. Frozen-value detection (stuck consecutive values)
======================================================================
  ⚠️  wave_height: longest identical-value run = 72 hours, starting 2025-04-20 22:00:00+00:00
  ✓ wind_speed: longest identical-value run = 4 hours (below 6h threshold)
  ✓ atmospheric_pressure: longest identical-value run = 3 hours (below 6h threshold)
  ⚠️  uv_index: longest identical-value run = 14 hours, starting 2025-01-11 17:00:00+00:00  (likely nighttime, uv_index=0 for ~12-14h every night — not necessarily stuck)

======================================================================
9. Bronze purge confirmation
======================================================================
  ✓ bronze_raw has 0 rows for Trincomalee — purge is working as designed

======================================================================
10. Known-event cross-check — Cyclone Ditwah (Nov 27-28, 2025)
======================================================================
  Nov 27-28 window: min pressure=1000.6 hPa (baseline avg=1008.3 hPa, drop=7.7 hPa)
  Nov 27-28 window: max precipitation=35.1 mm, max wave_height=3.12 m, max wind_gust=104.8 km/h
  Reference (independently reported, IMD/World Bank GRADE): Ditwah peak winds ~65-90 km/h
  sustained, gusts up to ~85 km/h at landfall. Compare this location's max_gust above
  against that range as a sanity check — values wildly above it are worth a closer look.
  ✓ Pressure drop is consistent with a real storm system passing through

```

---

## Chilaw

```text
########## VALIDATING: Chilaw (tourism_only=False) ##########

======================================================================
1. Row coverage
======================================================================
  Expected hours:  13104
  Actual rows:     13104
  Coverage:        100.00%
  Date range:      2025-01-01 00:00:00+00:00  to  2026-06-30 23:00:00+00:00
  ✓ No duplicate timestamps (row count == distinct timestamp count)
  ✓ Coverage at or above the 95% skip-threshold used by the pipeline

======================================================================
2. Timestamp gap analysis
======================================================================
  ✓ No gaps — fully contiguous hourly series

======================================================================
3. Null audit
======================================================================
  Zero-tolerance columns (wave/wind/swell/AQ) — should be 0 nulls:
    ✓ wave_height               0 nulls (0.00%)
    ✓ wave_period               0 nulls (0.00%)
    ✓ wave_direction            0 nulls (0.00%)
    ✓ swell_height              0 nulls (0.00%)
    ✓ swell_period              0 nulls (0.00%)
    ✓ swell_direction           0 nulls (0.00%)
    ✓ wind_wave_height          0 nulls (0.00%)
    ✓ wind_speed                0 nulls (0.00%)
    ✓ wind_gust                 0 nulls (0.00%)
    ✓ precipitation             0 nulls (0.00%)
    ✓ atmospheric_pressure      0 nulls (0.00%)
    ✓ uv_index                  0 nulls (0.00%)
    ✓ pm25                      0 nulls (0.00%)

  Ocean-only columns (sea_surface_temp / current velocity / current direction):
  This location fetches marine_ocean data — ≤5% null tolerance applies (known SST gap):
    ✓ sea_surface_temp          312 nulls (2.38%)
    ✓ ocean_current_velocity    0 nulls (0.00%)
    ✓ ocean_current_direction   0 nulls (0.00%)

  sea_level_height: 13104/13104 null — expected, no endpoint wired up yet.

======================================================================
4. Physical plausibility ranges
======================================================================
  ✓ All values within plausible physical ranges

======================================================================
5. Monsoon-season sanity check
======================================================================
  Skipped — no established feasibility-analysis baseline exists for Chilaw yet.
  Only Mirissa has a baseline from the interim feasibility work. Add one here once you have
  an independent reference to check against, otherwise this section has nothing to compare to.

======================================================================
6. Cross-variable consistency
======================================================================
  ⚠️  wind_gust < wind_speed: 7 rows (gust should never be below sustained speed)
  ✓ wind_wave_height > wave_height (+0.3m tolerance): 0 rows (combined sea state should generally be >= its wind-wave component)
  ✓ wave_direction outside [0, 360): 0 rows
  ✓ swell_direction outside [0, 360): 0 rows

======================================================================
7. Statistical outliers (IQR, 3x whisker)
======================================================================
  ✓ wave_height          0 outliers (0.00%)
  ✓ wave_period          0 outliers (0.00%)
  ✓ swell_height         0 outliers (0.00%)
  ✓ wind_speed           5 outliers (0.04%)  (range [-16.70, 45.60], observed min=45.8, max=48.5)
  ✓ wind_gust            2 outliers (0.02%)  (range [-29.30, 86.90], observed min=89.6, max=93.6)
  ⚠️  precipitation        1452 outliers (11.08%)  (range [-0.30, 0.40], observed min=0.5, max=21.3)
  ✓ atmospheric_pressure 0 outliers (0.00%)
  ✓ uv_index             0 outliers (0.00%)
  ⚠️  pm25                 145 outliers (1.11%)  (range [-13.40, 38.40], observed min=38.4, max=52.9)
  Note: 3x-IQR is deliberately loose — flags statistical rarity, not necessarily errors.
  A real storm (like Ditwah) will show up here too; that's expected, not a failure.
  Note: precipitation is zero-inflated (most hours are 0mm), so its Q1/Q3 sit near zero and
  ordinary rain will register as a mathematical 'outlier' here — treat this column's result
  as noise, not a data quality signal, until a fixed physical threshold replaces IQR for it.

======================================================================
8. Frozen-value detection (stuck consecutive values)
======================================================================
  ⚠️  wave_height: longest identical-value run = 19 hours, starting 2026-02-23 14:00:00+00:00
  ✓ wind_speed: longest identical-value run = 3 hours (below 6h threshold)
  ✓ atmospheric_pressure: longest identical-value run = 4 hours (below 6h threshold)
  ⚠️  uv_index: longest identical-value run = 14 hours, starting 2025-10-20 17:00:00+00:00  (likely nighttime, uv_index=0 for ~12-14h every night — not necessarily stuck)

======================================================================
9. Bronze purge confirmation
======================================================================
  ✓ bronze_raw has 0 rows for Chilaw — purge is working as designed

======================================================================
10. Known-event cross-check — Cyclone Ditwah (Nov 27-28, 2025)
======================================================================
  Nov 27-28 window: min pressure=1003.7 hPa (baseline avg=1009.3 hPa, drop=5.6 hPa)
  Nov 27-28 window: max precipitation=17.2 mm, max wave_height=3.66 m, max wind_gust=93.6 km/h
  Reference (independently reported, IMD/World Bank GRADE): Ditwah peak winds ~65-90 km/h
  sustained, gusts up to ~85 km/h at landfall. Compare this location's max_gust above
  against that range as a sanity check — values wildly above it are worth a closer look.
  ✓ Pressure drop is consistent with a real storm system passing through

```

---

## Colombo

```text
########## VALIDATING: Colombo (tourism_only=False) ##########

======================================================================
1. Row coverage
======================================================================
  Expected hours:  13104
  Actual rows:     13104
  Coverage:        100.00%
  Date range:      2025-01-01 00:00:00+00:00  to  2026-06-30 23:00:00+00:00
  ✓ No duplicate timestamps (row count == distinct timestamp count)
  ✓ Coverage at or above the 95% skip-threshold used by the pipeline

======================================================================
2. Timestamp gap analysis
======================================================================
  ✓ No gaps — fully contiguous hourly series

======================================================================
3. Null audit
======================================================================
  Zero-tolerance columns (wave/wind/swell/AQ) — should be 0 nulls:
    ✓ wave_height               0 nulls (0.00%)
    ✓ wave_period               0 nulls (0.00%)
    ✓ wave_direction            0 nulls (0.00%)
    ✓ swell_height              0 nulls (0.00%)
    ✓ swell_period              0 nulls (0.00%)
    ✓ swell_direction           0 nulls (0.00%)
    ✓ wind_wave_height          0 nulls (0.00%)
    ✓ wind_speed                0 nulls (0.00%)
    ✓ wind_gust                 0 nulls (0.00%)
    ✓ precipitation             0 nulls (0.00%)
    ✓ atmospheric_pressure      0 nulls (0.00%)
    ✓ uv_index                  0 nulls (0.00%)
    ✓ pm25                      0 nulls (0.00%)

  Ocean-only columns (sea_surface_temp / current velocity / current direction):
  This location fetches marine_ocean data — ≤5% null tolerance applies (known SST gap):
    ✓ sea_surface_temp          312 nulls (2.38%)
    ✓ ocean_current_velocity    0 nulls (0.00%)
    ✓ ocean_current_direction   0 nulls (0.00%)

  sea_level_height: 13104/13104 null — expected, no endpoint wired up yet.

======================================================================
4. Physical plausibility ranges
======================================================================
  ✓ All values within plausible physical ranges

======================================================================
5. Monsoon-season sanity check
======================================================================
  Skipped — no established feasibility-analysis baseline exists for Colombo yet.
  Only Mirissa has a baseline from the interim feasibility work. Add one here once you have
  an independent reference to check against, otherwise this section has nothing to compare to.

======================================================================
6. Cross-variable consistency
======================================================================
  ⚠️  wind_gust < wind_speed: 9 rows (gust should never be below sustained speed)
  ✓ wind_wave_height > wave_height (+0.3m tolerance): 0 rows (combined sea state should generally be >= its wind-wave component)
  ✓ wave_direction outside [0, 360): 0 rows
  ✓ swell_direction outside [0, 360): 0 rows

======================================================================
7. Statistical outliers (IQR, 3x whisker)
======================================================================
  ✓ wave_height          0 outliers (0.00%)
  ✓ wave_period          0 outliers (0.00%)
  ✓ swell_height         0 outliers (0.00%)
  ✓ wind_speed           10 outliers (0.08%)  (range [-17.00, 36.20], observed min=36.4, max=41.9)
  ✓ wind_gust            0 outliers (0.00%)
  ⚠️  precipitation        1162 outliers (8.87%)  (range [-0.60, 0.80], observed min=0.9, max=20.4)
  ✓ atmospheric_pressure 0 outliers (0.00%)
  ✓ uv_index             5 outliers (0.04%)  (range [-8.70, 11.60], observed min=11.65, max=12.1)
  ✓ pm25                 3 outliers (0.02%)  (range [-36.00, 78.10], observed min=78.2, max=82.0)
  Note: 3x-IQR is deliberately loose — flags statistical rarity, not necessarily errors.
  A real storm (like Ditwah) will show up here too; that's expected, not a failure.
  Note: precipitation is zero-inflated (most hours are 0mm), so its Q1/Q3 sit near zero and
  ordinary rain will register as a mathematical 'outlier' here — treat this column's result
  as noise, not a data quality signal, until a fixed physical threshold replaces IQR for it.

======================================================================
8. Frozen-value detection (stuck consecutive values)
======================================================================
  ⚠️  wave_height: longest identical-value run = 27 hours, starting 2025-03-30 01:00:00+00:00
  ✓ wind_speed: longest identical-value run = 4 hours (below 6h threshold)
  ✓ atmospheric_pressure: longest identical-value run = 4 hours (below 6h threshold)
  ⚠️  uv_index: longest identical-value run = 14 hours, starting 2025-10-20 17:00:00+00:00  (likely nighttime, uv_index=0 for ~12-14h every night — not necessarily stuck)

======================================================================
9. Bronze purge confirmation
======================================================================
  ✓ bronze_raw has 0 rows for Colombo — purge is working as designed

======================================================================
10. Known-event cross-check — Cyclone Ditwah (Nov 27-28, 2025)
======================================================================
  Nov 27-28 window: min pressure=1004.8 hPa (baseline avg=1008.9 hPa, drop=4.1 hPa)
  Nov 27-28 window: max precipitation=20.4 mm, max wave_height=2.88 m, max wind_gust=82.1 km/h
  Reference (independently reported, IMD/World Bank GRADE): Ditwah peak winds ~65-90 km/h
  sustained, gusts up to ~85 km/h at landfall. Compare this location's max_gust above
  against that range as a sanity check — values wildly above it are worth a closer look.
  ✓ Pressure drop is consistent with a real storm system passing through

```

---

## Tangalle

```text
########## VALIDATING: Tangalle (tourism_only=False) ##########

======================================================================
1. Row coverage
======================================================================
  Expected hours:  13104
  Actual rows:     13104
  Coverage:        100.00%
  Date range:      2025-01-01 00:00:00+00:00  to  2026-06-30 23:00:00+00:00
  ✓ No duplicate timestamps (row count == distinct timestamp count)
  ✓ Coverage at or above the 95% skip-threshold used by the pipeline

======================================================================
2. Timestamp gap analysis
======================================================================
  ✓ No gaps — fully contiguous hourly series

======================================================================
3. Null audit
======================================================================
  Zero-tolerance columns (wave/wind/swell/AQ) — should be 0 nulls:
    ✓ wave_height               0 nulls (0.00%)
    ✓ wave_period               0 nulls (0.00%)
    ✓ wave_direction            0 nulls (0.00%)
    ✓ swell_height              0 nulls (0.00%)
    ✓ swell_period              0 nulls (0.00%)
    ✓ swell_direction           0 nulls (0.00%)
    ✓ wind_wave_height          0 nulls (0.00%)
    ✓ wind_speed                0 nulls (0.00%)
    ✓ wind_gust                 0 nulls (0.00%)
    ✓ precipitation             0 nulls (0.00%)
    ✓ atmospheric_pressure      0 nulls (0.00%)
    ✓ uv_index                  0 nulls (0.00%)
    ✓ pm25                      0 nulls (0.00%)

  Ocean-only columns (sea_surface_temp / current velocity / current direction):
  This location fetches marine_ocean data — ≤5% null tolerance applies (known SST gap):
    ✓ sea_surface_temp          312 nulls (2.38%)
    ✓ ocean_current_velocity    0 nulls (0.00%)
    ✓ ocean_current_direction   0 nulls (0.00%)

  sea_level_height: 13104/13104 null — expected, no endpoint wired up yet.

======================================================================
4. Physical plausibility ranges
======================================================================
  ✓ All values within plausible physical ranges

======================================================================
5. Monsoon-season sanity check
======================================================================
  Skipped — no established feasibility-analysis baseline exists for Tangalle yet.
  Only Mirissa has a baseline from the interim feasibility work. Add one here once you have
  an independent reference to check against, otherwise this section has nothing to compare to.

======================================================================
6. Cross-variable consistency
======================================================================
  ⚠️  wind_gust < wind_speed: 15 rows (gust should never be below sustained speed)
  ✓ wind_wave_height > wave_height (+0.3m tolerance): 0 rows (combined sea state should generally be >= its wind-wave component)
  ✓ wave_direction outside [0, 360): 0 rows
  ✓ swell_direction outside [0, 360): 0 rows

======================================================================
7. Statistical outliers (IQR, 3x whisker)
======================================================================
  ✓ wave_height          0 outliers (0.00%)
  ✓ wave_period          0 outliers (0.00%)
  ✓ swell_height         0 outliers (0.00%)
  ✓ wind_speed           0 outliers (0.00%)
  ✓ wind_gust            0 outliers (0.00%)
  ⚠️  precipitation        1091 outliers (8.33%)  (range [-0.30, 0.40], observed min=0.5, max=12.0)
  ✓ atmospheric_pressure 0 outliers (0.00%)
  ✓ uv_index             0 outliers (0.00%)
  ✓ pm25                 104 outliers (0.79%)  (range [-19.00, 41.90], observed min=42.0, max=54.7)
  Note: 3x-IQR is deliberately loose — flags statistical rarity, not necessarily errors.
  A real storm (like Ditwah) will show up here too; that's expected, not a failure.
  Note: precipitation is zero-inflated (most hours are 0mm), so its Q1/Q3 sit near zero and
  ordinary rain will register as a mathematical 'outlier' here — treat this column's result
  as noise, not a data quality signal, until a fixed physical threshold replaces IQR for it.

======================================================================
8. Frozen-value detection (stuck consecutive values)
======================================================================
  ⚠️  wave_height: longest identical-value run = 24 hours, starting 2025-03-27 13:00:00+00:00
  ✓ wind_speed: longest identical-value run = 3 hours (below 6h threshold)
  ✓ atmospheric_pressure: longest identical-value run = 3 hours (below 6h threshold)
  ⚠️  uv_index: longest identical-value run = 13 hours, starting 2025-01-01 18:00:00+00:00  (likely nighttime, uv_index=0 for ~12-14h every night — not necessarily stuck)

======================================================================
9. Bronze purge confirmation
======================================================================
  ✓ bronze_raw has 0 rows for Tangalle — purge is working as designed

======================================================================
10. Known-event cross-check — Cyclone Ditwah (Nov 27-28, 2025)
======================================================================
  Nov 27-28 window: min pressure=1001.3 hPa (baseline avg=1007.9 hPa, drop=6.6 hPa)
  Nov 27-28 window: max precipitation=7.3 mm, max wave_height=2.58 m, max wind_gust=71.3 km/h
  Reference (independently reported, IMD/World Bank GRADE): Ditwah peak winds ~65-90 km/h
  sustained, gusts up to ~85 km/h at landfall. Compare this location's max_gust above
  against that range as a sanity check — values wildly above it are worth a closer look.
  ✓ Pressure drop is consistent with a real storm system passing through

```

---

## Batticaloa

```text
########## VALIDATING: Batticaloa (tourism_only=False) ##########

======================================================================
1. Row coverage
======================================================================
  Expected hours:  13104
  Actual rows:     13104
  Coverage:        100.00%
  Date range:      2025-01-01 00:00:00+00:00  to  2026-06-30 23:00:00+00:00
  ✓ No duplicate timestamps (row count == distinct timestamp count)
  ✓ Coverage at or above the 95% skip-threshold used by the pipeline

======================================================================
2. Timestamp gap analysis
======================================================================
  ✓ No gaps — fully contiguous hourly series

======================================================================
3. Null audit
======================================================================
  Zero-tolerance columns (wave/wind/swell/AQ) — should be 0 nulls:
    ✓ wave_height               0 nulls (0.00%)
    ✓ wave_period               0 nulls (0.00%)
    ✓ wave_direction            0 nulls (0.00%)
    ✓ swell_height              0 nulls (0.00%)
    ✓ swell_period              0 nulls (0.00%)
    ✓ swell_direction           0 nulls (0.00%)
    ✓ wind_wave_height          0 nulls (0.00%)
    ✓ wind_speed                0 nulls (0.00%)
    ✓ wind_gust                 0 nulls (0.00%)
    ✓ precipitation             0 nulls (0.00%)
    ✓ atmospheric_pressure      0 nulls (0.00%)
    ✓ uv_index                  0 nulls (0.00%)
    ✓ pm25                      0 nulls (0.00%)

  Ocean-only columns (sea_surface_temp / current velocity / current direction):
  This location fetches marine_ocean data — ≤5% null tolerance applies (known SST gap):
    ✓ sea_surface_temp          312 nulls (2.38%)
    ✓ ocean_current_velocity    0 nulls (0.00%)
    ✓ ocean_current_direction   0 nulls (0.00%)

  sea_level_height: 13104/13104 null — expected, no endpoint wired up yet.

======================================================================
4. Physical plausibility ranges
======================================================================
  ✓ All values within plausible physical ranges

======================================================================
5. Monsoon-season sanity check
======================================================================
  Skipped — no established feasibility-analysis baseline exists for Batticaloa yet.
  Only Mirissa has a baseline from the interim feasibility work. Add one here once you have
  an independent reference to check against, otherwise this section has nothing to compare to.

======================================================================
6. Cross-variable consistency
======================================================================
  ⚠️  wind_gust < wind_speed: 40 rows (gust should never be below sustained speed)
  ✓ wind_wave_height > wave_height (+0.3m tolerance): 0 rows (combined sea state should generally be >= its wind-wave component)
  ✓ wave_direction outside [0, 360): 0 rows
  ✓ swell_direction outside [0, 360): 0 rows

======================================================================
7. Statistical outliers (IQR, 3x whisker)
======================================================================
  ✓ wave_height          104 outliers (0.79%)  (range [-0.62, 2.18], observed min=2.2, max=3.72)
  ✓ wave_period          0 outliers (0.00%)
  ✓ swell_height         87 outliers (0.66%)  (range [-0.54, 1.84], observed min=1.84, max=2.6)
  ✓ wind_speed           12 outliers (0.09%)  (range [-18.30, 35.60], observed min=37.1, max=46.3)
  ✓ wind_gust            5 outliers (0.04%)  (range [-34.10, 71.60], observed min=73.8, max=77.0)
  ⚠️  precipitation        1421 outliers (10.84%)  (range [-0.30, 0.40], observed min=0.5, max=18.7)
  ✓ atmospheric_pressure 0 outliers (0.00%)
  ✓ uv_index             1 outliers (0.01%)  (range [-9.75, 13.00], observed min=13.05, max=13.05)
  ✓ pm25                 72 outliers (0.55%)  (range [-19.10, 41.10], observed min=41.3, max=57.3)
  Note: 3x-IQR is deliberately loose — flags statistical rarity, not necessarily errors.
  A real storm (like Ditwah) will show up here too; that's expected, not a failure.
  Note: precipitation is zero-inflated (most hours are 0mm), so its Q1/Q3 sit near zero and
  ordinary rain will register as a mathematical 'outlier' here — treat this column's result
  as noise, not a data quality signal, until a fixed physical threshold replaces IQR for it.

======================================================================
8. Frozen-value detection (stuck consecutive values)
======================================================================
  ⚠️  wave_height: longest identical-value run = 40 hours, starting 2026-04-18 23:00:00+00:00
  ✓ wind_speed: longest identical-value run = 3 hours (below 6h threshold)
  ✓ atmospheric_pressure: longest identical-value run = 3 hours (below 6h threshold)
  ⚠️  uv_index: longest identical-value run = 14 hours, starting 2025-01-11 17:00:00+00:00  (likely nighttime, uv_index=0 for ~12-14h every night — not necessarily stuck)

======================================================================
9. Bronze purge confirmation
======================================================================
  ✓ bronze_raw has 0 rows for Batticaloa — purge is working as designed

======================================================================
10. Known-event cross-check — Cyclone Ditwah (Nov 27-28, 2025)
======================================================================
  Nov 27-28 window: min pressure=999.7 hPa (baseline avg=1008.5 hPa, drop=8.8 hPa)
  Nov 27-28 window: max precipitation=14.5 mm, max wave_height=3.72 m, max wind_gust=77.0 km/h
  Reference (independently reported, IMD/World Bank GRADE): Ditwah peak winds ~65-90 km/h
  sustained, gusts up to ~85 km/h at landfall. Compare this location's max_gust above
  against that range as a sanity check — values wildly above it are worth a closer look.
  ✓ Pressure drop is consistent with a real storm system passing through

```

---

## Jaffna

```text
########## VALIDATING: Jaffna (tourism_only=False) ##########

======================================================================
1. Row coverage
======================================================================
  Expected hours:  13104
  Actual rows:     13104
  Coverage:        100.00%
  Date range:      2025-01-01 00:00:00+00:00  to  2026-06-30 23:00:00+00:00
  ✓ No duplicate timestamps (row count == distinct timestamp count)
  ✓ Coverage at or above the 95% skip-threshold used by the pipeline

======================================================================
2. Timestamp gap analysis
======================================================================
  ✓ No gaps — fully contiguous hourly series

======================================================================
3. Null audit
======================================================================
  Zero-tolerance columns (wave/wind/swell/AQ) — should be 0 nulls:
    ✓ wave_height               0 nulls (0.00%)
    ✓ wave_period               0 nulls (0.00%)
    ✓ wave_direction            0 nulls (0.00%)
    ✓ swell_height              0 nulls (0.00%)
    ✓ swell_period              0 nulls (0.00%)
    ✓ swell_direction           0 nulls (0.00%)
    ✓ wind_wave_height          0 nulls (0.00%)
    ✓ wind_speed                0 nulls (0.00%)
    ✓ wind_gust                 0 nulls (0.00%)
    ✓ precipitation             0 nulls (0.00%)
    ✓ atmospheric_pressure      0 nulls (0.00%)
    ✓ uv_index                  0 nulls (0.00%)
    ✓ pm25                      0 nulls (0.00%)

  Ocean-only columns (sea_surface_temp / current velocity / current direction):
  This location fetches marine_ocean data — ≤5% null tolerance applies (known SST gap):
    ✓ sea_surface_temp          312 nulls (2.38%)
    ✓ ocean_current_velocity    0 nulls (0.00%)
    ✓ ocean_current_direction   0 nulls (0.00%)

  sea_level_height: 13104/13104 null — expected, no endpoint wired up yet.

======================================================================
4. Physical plausibility ranges
======================================================================
  ✓ All values within plausible physical ranges

======================================================================
5. Monsoon-season sanity check
======================================================================
  Skipped — no established feasibility-analysis baseline exists for Jaffna yet.
  Only Mirissa has a baseline from the interim feasibility work. Add one here once you have
  an independent reference to check against, otherwise this section has nothing to compare to.

======================================================================
6. Cross-variable consistency
======================================================================
  ⚠️  wind_gust < wind_speed: 7 rows (gust should never be below sustained speed)
  ✓ wind_wave_height > wave_height (+0.3m tolerance): 0 rows (combined sea state should generally be >= its wind-wave component)
  ✓ wave_direction outside [0, 360): 0 rows
  ✓ swell_direction outside [0, 360): 0 rows

======================================================================
7. Statistical outliers (IQR, 3x whisker)
======================================================================
  ✓ wave_height          0 outliers (0.00%)
  ✓ wave_period          0 outliers (0.00%)
  ✓ swell_height         9 outliers (0.07%)  (range [-0.34, 0.64], observed min=0.66, max=0.76)
  ✓ wind_speed           0 outliers (0.00%)
  ✓ wind_gust            0 outliers (0.00%)
  ⚠️  precipitation        2775 outliers (21.18%)  (range [0.00, 0.00], observed min=0.1, max=14.6)
  ✓ atmospheric_pressure 0 outliers (0.00%)
  ✓ uv_index             0 outliers (0.00%)
  ✓ pm25                 88 outliers (0.67%)  (range [-21.20, 43.90], observed min=44.0, max=56.9)
  Note: 3x-IQR is deliberately loose — flags statistical rarity, not necessarily errors.
  A real storm (like Ditwah) will show up here too; that's expected, not a failure.
  Note: precipitation is zero-inflated (most hours are 0mm), so its Q1/Q3 sit near zero and
  ordinary rain will register as a mathematical 'outlier' here — treat this column's result
  as noise, not a data quality signal, until a fixed physical threshold replaces IQR for it.

======================================================================
8. Frozen-value detection (stuck consecutive values)
======================================================================
  ⚠️  wave_height: longest identical-value run = 51 hours, starting 2025-11-07 22:00:00+00:00
  ✓ wind_speed: longest identical-value run = 4 hours (below 6h threshold)
  ✓ atmospheric_pressure: longest identical-value run = 4 hours (below 6h threshold)
  ⚠️  uv_index: longest identical-value run = 14 hours, starting 2025-11-23 17:00:00+00:00  (likely nighttime, uv_index=0 for ~12-14h every night — not necessarily stuck)

======================================================================
9. Bronze purge confirmation
======================================================================
  ✓ bronze_raw has 0 rows for Jaffna — purge is working as designed

======================================================================
10. Known-event cross-check — Cyclone Ditwah (Nov 27-28, 2025)
======================================================================
  Nov 27-28 window: min pressure=1004.3 hPa (baseline avg=1008.6 hPa, drop=4.3 hPa)
  Nov 27-28 window: max precipitation=12.9 mm, max wave_height=1.4 m, max wind_gust=76.0 km/h
  Reference (independently reported, IMD/World Bank GRADE): Ditwah peak winds ~65-90 km/h
  sustained, gusts up to ~85 km/h at landfall. Compare this location's max_gust above
  against that range as a sanity check — values wildly above it are worth a closer look.
  ✓ Pressure drop is consistent with a real storm system passing through

```

---

## Matara

```text
########## VALIDATING: Matara (tourism_only=False) ##########

======================================================================
1. Row coverage
======================================================================
  Expected hours:  13104
  Actual rows:     13104
  Coverage:        100.00%
  Date range:      2025-01-01 00:00:00+00:00  to  2026-06-30 23:00:00+00:00
  ✓ No duplicate timestamps (row count == distinct timestamp count)
  ✓ Coverage at or above the 95% skip-threshold used by the pipeline

======================================================================
2. Timestamp gap analysis
======================================================================
  ✓ No gaps — fully contiguous hourly series

======================================================================
3. Null audit
======================================================================
  Zero-tolerance columns (wave/wind/swell/AQ) — should be 0 nulls:
    ✓ wave_height               0 nulls (0.00%)
    ✓ wave_period               0 nulls (0.00%)
    ✓ wave_direction            0 nulls (0.00%)
    ✓ swell_height              0 nulls (0.00%)
    ✓ swell_period              0 nulls (0.00%)
    ✓ swell_direction           0 nulls (0.00%)
    ✓ wind_wave_height          0 nulls (0.00%)
    ✓ wind_speed                0 nulls (0.00%)
    ✓ wind_gust                 0 nulls (0.00%)
    ✓ precipitation             0 nulls (0.00%)
    ✓ atmospheric_pressure      0 nulls (0.00%)
    ✓ uv_index                  0 nulls (0.00%)
    ✓ pm25                      0 nulls (0.00%)

  Ocean-only columns (sea_surface_temp / current velocity / current direction):
  This location fetches marine_ocean data — ≤5% null tolerance applies (known SST gap):
    ✓ sea_surface_temp          312 nulls (2.38%)
    ✓ ocean_current_velocity    0 nulls (0.00%)
    ✓ ocean_current_direction   0 nulls (0.00%)

  sea_level_height: 13104/13104 null — expected, no endpoint wired up yet.

======================================================================
4. Physical plausibility ranges
======================================================================
  ✓ All values within plausible physical ranges

======================================================================
5. Monsoon-season sanity check
======================================================================
  Skipped — no established feasibility-analysis baseline exists for Matara yet.
  Only Mirissa has a baseline from the interim feasibility work. Add one here once you have
  an independent reference to check against, otherwise this section has nothing to compare to.

======================================================================
6. Cross-variable consistency
======================================================================
  ⚠️  wind_gust < wind_speed: 20 rows (gust should never be below sustained speed)
  ✓ wind_wave_height > wave_height (+0.3m tolerance): 0 rows (combined sea state should generally be >= its wind-wave component)
  ✓ wave_direction outside [0, 360): 0 rows
  ✓ swell_direction outside [0, 360): 0 rows

======================================================================
7. Statistical outliers (IQR, 3x whisker)
======================================================================
  ✓ wave_height          0 outliers (0.00%)
  ✓ wave_period          0 outliers (0.00%)
  ✓ swell_height         0 outliers (0.00%)
  ✓ wind_speed           0 outliers (0.00%)
  ✓ wind_gust            0 outliers (0.00%)
  ⚠️  precipitation        1530 outliers (11.68%)  (range [-0.30, 0.40], observed min=0.5, max=15.9)
  ✓ atmospheric_pressure 0 outliers (0.00%)
  ✓ uv_index             7 outliers (0.05%)  (range [-9.45, 12.60], observed min=12.65, max=13.3)
  ⚠️  pm25                 189 outliers (1.44%)  (range [-26.70, 54.50], observed min=54.6, max=79.6)
  Note: 3x-IQR is deliberately loose — flags statistical rarity, not necessarily errors.
  A real storm (like Ditwah) will show up here too; that's expected, not a failure.
  Note: precipitation is zero-inflated (most hours are 0mm), so its Q1/Q3 sit near zero and
  ordinary rain will register as a mathematical 'outlier' here — treat this column's result
  as noise, not a data quality signal, until a fixed physical threshold replaces IQR for it.

======================================================================
8. Frozen-value detection (stuck consecutive values)
======================================================================
  ⚠️  wave_height: longest identical-value run = 20 hours, starting 2025-06-02 23:00:00+00:00
  ✓ wind_speed: longest identical-value run = 3 hours (below 6h threshold)
  ✓ atmospheric_pressure: longest identical-value run = 4 hours (below 6h threshold)
  ⚠️  uv_index: longest identical-value run = 14 hours, starting 2025-01-02 17:00:00+00:00  (likely nighttime, uv_index=0 for ~12-14h every night — not necessarily stuck)

======================================================================
9. Bronze purge confirmation
======================================================================
  ✓ bronze_raw has 0 rows for Matara — purge is working as designed

======================================================================
10. Known-event cross-check — Cyclone Ditwah (Nov 27-28, 2025)
======================================================================
  Nov 27-28 window: min pressure=1003.2 hPa (baseline avg=1009.1 hPa, drop=5.9 hPa)
  Nov 27-28 window: max precipitation=11.4 mm, max wave_height=3.28 m, max wind_gust=69.5 km/h
  Reference (independently reported, IMD/World Bank GRADE): Ditwah peak winds ~65-90 km/h
  sustained, gusts up to ~85 km/h at landfall. Compare this location's max_gust above
  against that range as a sanity check — values wildly above it are worth a closer look.
  ✓ Pressure drop is consistent with a real storm system passing through

```

---

## Puttalam

```text
########## VALIDATING: Puttalam (tourism_only=False) ##########

======================================================================
1. Row coverage
======================================================================
  Expected hours:  13104
  Actual rows:     13104
  Coverage:        100.00%
  Date range:      2025-01-01 00:00:00+00:00  to  2026-06-30 23:00:00+00:00
  ✓ No duplicate timestamps (row count == distinct timestamp count)
  ✓ Coverage at or above the 95% skip-threshold used by the pipeline

======================================================================
2. Timestamp gap analysis
======================================================================
  ✓ No gaps — fully contiguous hourly series

======================================================================
3. Null audit
======================================================================
  Zero-tolerance columns (wave/wind/swell/AQ) — should be 0 nulls:
    ✓ wave_height               0 nulls (0.00%)
    ✓ wave_period               0 nulls (0.00%)
    ✓ wave_direction            0 nulls (0.00%)
    ✓ swell_height              0 nulls (0.00%)
    ✓ swell_period              0 nulls (0.00%)
    ✓ swell_direction           0 nulls (0.00%)
    ✓ wind_wave_height          0 nulls (0.00%)
    ✓ wind_speed                0 nulls (0.00%)
    ✓ wind_gust                 0 nulls (0.00%)
    ✓ precipitation             0 nulls (0.00%)
    ✓ atmospheric_pressure      0 nulls (0.00%)
    ✓ uv_index                  0 nulls (0.00%)
    ✓ pm25                      0 nulls (0.00%)

  Ocean-only columns (sea_surface_temp / current velocity / current direction):
  This location fetches marine_ocean data — ≤5% null tolerance applies (known SST gap):
    ✓ sea_surface_temp          312 nulls (2.38%)
    ✓ ocean_current_velocity    0 nulls (0.00%)
    ✓ ocean_current_direction   0 nulls (0.00%)

  sea_level_height: 13104/13104 null — expected, no endpoint wired up yet.

======================================================================
4. Physical plausibility ranges
======================================================================
  ✓ All values within plausible physical ranges

======================================================================
5. Monsoon-season sanity check
======================================================================
  Skipped — no established feasibility-analysis baseline exists for Puttalam yet.
  Only Mirissa has a baseline from the interim feasibility work. Add one here once you have
  an independent reference to check against, otherwise this section has nothing to compare to.

======================================================================
6. Cross-variable consistency
======================================================================
  ⚠️  wind_gust < wind_speed: 5 rows (gust should never be below sustained speed)
  ✓ wind_wave_height > wave_height (+0.3m tolerance): 0 rows (combined sea state should generally be >= its wind-wave component)
  ✓ wave_direction outside [0, 360): 0 rows
  ✓ swell_direction outside [0, 360): 0 rows

======================================================================
7. Statistical outliers (IQR, 3x whisker)
======================================================================
  ✓ wave_height          0 outliers (0.00%)
  ✓ wave_period          0 outliers (0.00%)
  ✓ swell_height         1 outliers (0.01%)  (range [-0.92, 2.44], observed min=2.52, max=2.52)
  ✓ wind_speed           0 outliers (0.00%)
  ✓ wind_gust            0 outliers (0.00%)
  ⚠️  precipitation        1080 outliers (8.24%)  (range [-0.30, 0.40], observed min=0.5, max=17.5)
  ✓ atmospheric_pressure 0 outliers (0.00%)
  ✓ uv_index             0 outliers (0.00%)
  ✓ pm25                 122 outliers (0.93%)  (range [-16.30, 36.90], observed min=37.0, max=51.6)
  Note: 3x-IQR is deliberately loose — flags statistical rarity, not necessarily errors.
  A real storm (like Ditwah) will show up here too; that's expected, not a failure.
  Note: precipitation is zero-inflated (most hours are 0mm), so its Q1/Q3 sit near zero and
  ordinary rain will register as a mathematical 'outlier' here — treat this column's result
  as noise, not a data quality signal, until a fixed physical threshold replaces IQR for it.

======================================================================
8. Frozen-value detection (stuck consecutive values)
======================================================================
  ⚠️  wave_height: longest identical-value run = 27 hours, starting 2025-03-06 19:00:00+00:00
  ✓ wind_speed: longest identical-value run = 3 hours (below 6h threshold)
  ✓ atmospheric_pressure: longest identical-value run = 4 hours (below 6h threshold)
  ⚠️  uv_index: longest identical-value run = 14 hours, starting 2025-11-27 17:00:00+00:00  (likely nighttime, uv_index=0 for ~12-14h every night — not necessarily stuck)

======================================================================
9. Bronze purge confirmation
======================================================================
  ✓ bronze_raw has 0 rows for Puttalam — purge is working as designed

======================================================================
10. Known-event cross-check — Cyclone Ditwah (Nov 27-28, 2025)
======================================================================
  Nov 27-28 window: min pressure=1003.0 hPa (baseline avg=1009.2 hPa, drop=6.2 hPa)
  Nov 27-28 window: max precipitation=17.5 mm, max wave_height=3.42 m, max wind_gust=85.7 km/h
  Reference (independently reported, IMD/World Bank GRADE): Ditwah peak winds ~65-90 km/h
  sustained, gusts up to ~85 km/h at landfall. Compare this location's max_gust above
  against that range as a sanity check — values wildly above it are worth a closer look.
  ✓ Pressure drop is consistent with a real storm system passing through

```