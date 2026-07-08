from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)

test_row = {
    "location_name": "Colombo",
    "api_source": "test",
    "raw_json": {"test": True}
}

result = supabase.table("bronze_raw").insert(test_row).execute()
print("Success! Connected to Supabase.")
print("Inserted row:", result.data)