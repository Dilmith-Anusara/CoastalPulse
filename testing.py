import requests
from dotenv import load_dotenv
import os
import time
import sys

load_dotenv()

START, END = "2026-06-01", "2026-06-07"
TOURISM_ONLY = {"Mirissa", "Hikkaduwa", "Unawatuna", "Bentota", "Arugam Bay"}

TEST_LOCATIONS = [
    {"name": "Mirissa",  "lat": 5.948, "lon": 80.455},   # Tourism only
    {"name": "Galle",    "lat": 6.030, "lon": 80.217},   # all three modes
    {"name": "Chilaw",   "lat": 7.576, "lon": 79.796},   # Fisherman + Emergency
    {"name": "Tangalle", "lat": 6.025, "lon": 80.793},   # Fisherman only
    {"name": "Matara",   "lat": 5.948, "lon": 80.535},   # Emergency only
]

def fetch(url, hourly_vars, lat, lon, retries=3, timeout=60):
    for attempt in range(retries):
        try:
            t0 = time.time()
            r = requests.get(url, params={
                "latitude": lat, "longitude": lon,
                "hourly": hourly_vars,
                "start_date": START, "end_date": END,
                "timezone": "Asia/Colombo"
            }, timeout=timeout)
            elapsed = time.time() - t0
            data = r.json()
            if "hourly" not in data:
                print(f"    API error: {data}")
                return None, elapsed, 0
            size_bytes = sys.getsizeof(r.content)
            return data, elapsed, size_bytes
        except Exception as e:
            print(f"    Attempt {attempt+1} failed: {e}")
            time.sleep(3)
    return None, None, 0

def audit(label, data, keys, elapsed, size_bytes):
    """Report the actual go/no-go signals, not sample rows."""
    if data is None:
        print(f"    [{label}] FAIL — no data returned")
        return {"ok": False}

    times = data["hourly"]["time"]
    n = len(times)
    issues = []

    # 1. Null check across the FULL array, not a sample
    null_counts = {}
    for k in keys:
        vals = data["hourly"].get(k, [])
        nulls = sum(1 for v in vals if v is None)
        if nulls:
            null_counts[k] = nulls
    if null_counts:
        issues.append(f"nulls found: {null_counts}")

    # 2. Length consistency across variables within this endpoint
    lengths = {k: len(data["hourly"].get(k, [])) for k in keys}
    if len(set(lengths.values())) > 1:
        issues.append(f"inconsistent lengths: {lengths}")

    # 3. Sanity range checks (flag obviously broken values, don't hardcode full validation)
    for k in keys:
        vals = [v for v in data["hourly"].get(k, []) if v is not None]
        if vals and all(v == 0 for v in vals) and "uv" not in k and "precip" not in k:
            issues.append(f"{k} is all-zero — possible silent failure")

    status = "OK" if not issues else "REVIEW"
    print(f"    [{label}] {status} | {n} records | {elapsed:.1f}s | {size_bytes/1024:.1f} KB")
    if issues:
        for i in issues:
            print(f"        ⚠ {i}")

    return {"ok": not issues, "times": times, "n": n, "size_bytes": size_bytes}

results_summary = []

for loc in TEST_LOCATIONS:
    name, lat, lon = loc["name"], loc["lat"], loc["lon"]
    print(f"\n=== {name} ===")

    total_size = 0
    endpoint_times = {}

    m1, t1, s1 = fetch("https://marine-api.open-meteo.com/v1/marine",
                        "wave_height,wave_period,wave_direction", lat, lon)
    r1 = audit("marine_waves", m1, ["wave_height", "wave_period", "wave_direction"], t1, s1)
    total_size += s1

    m2, t2, s2 = fetch("https://marine-api.open-meteo.com/v1/marine",
                        "swell_wave_height,swell_wave_direction,swell_wave_period,wind_wave_height", lat, lon)
    r2 = audit("marine_swell", m2, ["swell_wave_height", "swell_wave_period", "wind_wave_height"], t2, s2)
    total_size += s2

    if name in TOURISM_ONLY:
        print("    [marine_ocean] skipped — tourism-only location")
        m3, r3 = None, {"ok": True, "times": None}
    else:
        m3, t3, s3 = fetch("https://marine-api.open-meteo.com/v1/marine",
                            "sea_surface_temperature,ocean_current_velocity,ocean_current_direction", lat, lon)
        r3 = audit("marine_ocean", m3, ["sea_surface_temperature", "ocean_current_velocity"], t3, s3)
        total_size += s3

    w, t4, s4 = fetch("https://archive-api.open-meteo.com/v1/archive",
                       "wind_speed_10m,wind_gusts_10m,precipitation,surface_pressure", lat, lon)
    r4 = audit("weather", w, ["wind_speed_10m", "wind_gusts_10m", "precipitation", "surface_pressure"], t4, s4)
    total_size += s4

    aq, t5, s5 = fetch("https://air-quality-api.open-meteo.com/v1/air-quality",
                        "uv_index,pm2_5", lat, lon)
    r5 = audit("air_quality", aq, ["uv_index", "pm2_5"], t5, s5)
    total_size += s5

    # Cross-endpoint alignment check — this is the real question, not eyeballing ranges
    time_arrays = [r["times"] for r in [r1, r2, r3, r4, r5] if r.get("times")]
    aligned = all(t == time_arrays[0] for t in time_arrays)
    print(f"    Cross-endpoint timestamp alignment: {'MATCH' if aligned else 'MISMATCH — DO NOT proceed to Silver script'}")
    print(f"    Total payload size for this location (7-day sample): {total_size/1024:.1f} KB")

    results_summary.append({
        "name": name,
        "aligned": aligned,
        "total_size_kb": total_size / 1024
    })

    time.sleep(2)

print("\n=== SUMMARY ===")
for r in results_summary:
    projected_full_range_mb = r["total_size_kb"] * (912 / 7) / 1024  # 912 days = 2024-01-01 to 2026-06-30
    print(f"{r['name']:12s} | aligned: {r['aligned']!s:6s} | 7-day size: {r['total_size_kb']:.1f} KB | "
          f"projected full-range: {projected_full_range_mb:.1f} MB")

print(f"\nProjected total across 15 locations (rough, using these 5 as proxy): "
      f"{sum(r['total_size_kb'] for r in results_summary)/len(results_summary) * (912/7) * 15 / 1024:.1f} MB")
print("Compare this against Supabase's 500MB free-tier cap before running the full loop.")