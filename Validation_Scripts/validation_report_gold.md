# CoastalPulse Gold Layer Validation Report


## gold_emergency_daily (8190 total rows, 15 locations)

✅ gold_emergency_daily: all 15 locations from fetch_data.py's LOCATIONS are present.
✅ gold_emergency_daily: no duplicate (location_name, date) rows.

--- gold_emergency_daily: coverage per location ---
  Arugam Bay: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Batticaloa: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Bentota: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Chilaw: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Colombo: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Galle: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Hikkaduwa: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Jaffna: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Matara: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Mirissa: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Negombo: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Puttalam: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Tangalle: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Trincomalee: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Unawatuna: 546 days, 2025-01-01 to 2026-06-30, no gaps.
✅ gold_emergency_daily: all rows have hours_covered == 24.
✅ gold_emergency_daily: no nulls in core aggregate columns.

--- gold_emergency_daily: plausibility check ---
✅ gold_emergency_daily: all values within plausible ranges.

--- gold_emergency_daily: classification consistency ---
✅ all classification values match re-derived thresholds from wave_height_max.

## gold_tourism_daily (8190 total rows, 15 locations)

✅ gold_tourism_daily: all 15 locations from fetch_data.py's LOCATIONS are present.
✅ gold_tourism_daily: no duplicate (location_name, date) rows.

--- gold_tourism_daily: coverage per location ---
  Arugam Bay: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Batticaloa: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Bentota: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Chilaw: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Colombo: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Galle: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Hikkaduwa: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Jaffna: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Matara: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Mirissa: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Negombo: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Puttalam: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Tangalle: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Trincomalee: 546 days, 2025-01-01 to 2026-06-30, no gaps.
  Unawatuna: 546 days, 2025-01-01 to 2026-06-30, no gaps.
✅ gold_tourism_daily: all rows have daylight_hours_covered == 12.
✅ gold_tourism_daily: no nulls in core aggregate columns.

--- gold_tourism_daily: plausibility check ---
✅ gold_tourism_daily: all values within plausible ranges.

--- gold_tourism_daily: suitability_score range check ---
✅ all suitability_score values within [0, 100].

--- gold_tourism_daily: sea_surface_temp_mean null pattern check ---
TOURISM_ONLY locations (no marine_ocean fetch, per fetch_data.py): ['Arugam Bay', 'Bentota', 'Hikkaduwa', 'Mirissa', 'Unawatuna']
Non-TOURISM_ONLY locations (marine_ocean expected): ['Batticaloa', 'Chilaw', 'Colombo', 'Galle', 'Jaffna', 'Matara', 'Negombo', 'Puttalam', 'Tangalle', 'Trincomalee']
✅ 2730 null(s) confined to TOURISM_ONLY locations — expected:
location_name
Arugam Bay    546
Bentota       546
Hikkaduwa     546
Mirissa       546
Unawatuna     546
⚠️ 120 null(s) found in non-TOURISM_ONLY location(s) — small sparse gaps are plausible (a source API hiccup on a given hour), but worth a quick look if the count is large for any single location:
location_name
Batticaloa     12
Chilaw         12
Colombo        12
Galle          12
Jaffna         12
Matara         12
Negombo        12
Puttalam       12
Tangalle       12
Trincomalee    12