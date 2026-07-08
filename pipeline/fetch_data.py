import requests
from supabase import create_client
from dotenv import load_dotenv
import os
import time
import json

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

lat, lon, name = 6.93, 79.82, "Colombo"
START, END = "2025-01-01", "2026-06-30"

def fetch(url, hourly_vars, retries=5):
    for attempt in range(retries):
        try:
            r = requests.get(url, params={
                "latitude": lat,
                "longitude": lon,
                "hourly": hourly_vars,
                "start_date": START,
                "end_date": END,
                "timezone": "Asia/Colombo"
            }, timeout=60)
            data = r.json()
            if "hourly" not in data:
                print(f"  API error: {data}")
                return None
            return data
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            time.sleep(5)
    print("  All retries failed.")
    return None

print("Fetching marine batch 1 (waves)...")
m1 = fetch("https://marine-api.open-meteo.com/v1/marine",
           "wave_height,wave_period,wave_direction")

print("Fetching marine batch 2 (swell)...")
m2 = fetch("https://marine-api.open-meteo.com/v1/marine",
           "swell_wave_height,swell_wave_direction,swell_wave_period,wind_wave_height")

print("Fetching marine batch 3 (ocean)...")
m3 = fetch("https://marine-api.open-meteo.com/v1/marine",
           "sea_surface_temperature,ocean_current_velocity,ocean_current_direction")

print("Fetching weather...")
w = fetch("https://archive-api.open-meteo.com/v1/archive",
          "wind_speed_10m,wind_gusts_10m,precipitation,surface_pressure")

print("Fetching air quality...")
aq = fetch("https://air-quality-api.open-meteo.com/v1/air-quality",
           "uv_index,pm2_5")

if not all([m1, m2, m3, w, aq]):
    print("One or more API calls failed. Try again.")
    exit()

print("Saving to Bronze...")
supabase.table("bronze_raw").insert({
    "location_name": name,
    "api_source": "full_fetch",
    "raw_json": {
        "marine_waves": m1,
        "marine_swell": m2,
        "marine_ocean": m3,
        "weather": w,
        "air_quality": aq
    }
}).execute()

print("Parsing and saving to Silver...")
times = m1["hourly"]["time"]
rows = []

for i in range(len(times)):
    rows.append({
        "location_name":           name,
        "timestamp":               times[i],
        "wave_height":             m1["hourly"]["wave_height"][i],
        "wave_period":             m1["hourly"]["wave_period"][i],
        "wave_direction":          m1["hourly"]["wave_direction"][i],
        "swell_height":            m2["hourly"]["swell_wave_height"][i],
        "swell_period":            m2["hourly"]["swell_wave_period"][i],
        "swell_direction":         m2["hourly"]["swell_wave_direction"][i],
        "wind_wave_height":        m2["hourly"]["wind_wave_height"][i],
        "sea_surface_temp":        m3["hourly"]["sea_surface_temperature"][i],
        "ocean_current_velocity":  m3["hourly"]["ocean_current_velocity"][i],
        "ocean_current_direction": m3["hourly"]["ocean_current_direction"][i],
        "sea_level_height":        None,
        "wind_speed":              w["hourly"]["wind_speed_10m"][i],
        "wind_gust":               w["hourly"]["wind_gusts_10m"][i],
        "precipitation":           w["hourly"]["precipitation"][i],
        "atmospheric_pressure":    w["hourly"]["surface_pressure"][i],
        "uv_index":                aq["hourly"]["uv_index"][i],
        "pm25":                    aq["hourly"]["pm2_5"][i],
    })

supabase.table("silver_hourly").upsert(rows, on_conflict="location_name,timestamp").execute()
print(f"Done! Inserted {len(rows)} rows into Silver.")
print("Check your Supabase silver_hourly table.")

