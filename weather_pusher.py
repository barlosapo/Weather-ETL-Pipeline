#Honestly had to look up how to use BeautifulSoup and Supabase Python client docs 
#to get this working, but it's pretty straightforward once you see examples.


#Setup:
#  1. Copy .env.example to .env and fill in your values
#  2. Set HTM_PATH to the location of your WeatherLink HTML output file
#  3. Run on a schedule (Windows Task Scheduler / cron) every 5 minutes"

#Dependencies:
  #pip install supabase beautifulsoup4 python-dotenv

import os
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Path to the HTML file WeatherLink writes on your local machine
# Example (Windows): r"C:\WeatherLink\output\Current_Conditions.htm"
# Example (Linux/Mac): "/home/user/weatherlink/Current_Conditions.htm"
HTM_PATH = os.getenv("HTM_PATH", r"C:\path\to\your\Current_Vantage_Pro.htm")

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project-ref.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-anon-or-service-role-key")

# How many wind log entries to keep (approx. 7 days at 5-min intervals)
WIND_LOG_MAX_ROWS = 2016

#Supabase shi
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# LABELS YEAHHHHH
# Maps the label text in the WeatherLink HTML to Supabase column names.
# Adjust these if your WeatherLink template uses different label text.
# I had to double check these bc i am blind
label_map = {
    "Temperature":    
    "temperature",
    "Humidity":       
    "humidity",
    "Dewpoint":       
    "dewpoint",
    "Wind":           
    "wind",
    "10 Min Gust":    
    "wind_gust",
    "Barometer":      
    "barometer",
    "Today's Rain":   
    "rain_today",
    "Rain Rate":      
    "rain_rate",
    "Storm Total":    
    "rain_storm",
    "Monthly Rain":   
    "rain_monthly",
    "Yearly Rain":    
    "rain_yearly",
    "Wind Chill":     
    "wind_chill",
    "THW Index":      
    "thw_index",
    "Heat Index":     
    "heat_index",
}


def parse_htm(path: str) -> dict: #Parse the WeatherLink HTML file and return a dict of field -> value.

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")

    rows = soup.find_all("tr")
    data = {}

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        label_text = cells[0].get_text(strip=True)
        value_text = cells[1].get_text(strip=True)

        for html_label, db_field in label_map.items():
            if html_label.lower() in label_text.lower():
                data[db_field] = value_text
                break

    # Parse station time from the page title / header text
    # Adjust this regex if your WeatherLink template formats the date differently
    full_text = soup.get_text()
    time_match = re.search(r"(\d{2}/\d{2}/\d{2})\s+(\d{1,2}:\d{2}[ap])", full_text)
    if time_match:
        data["station_time"] = f"{time_match.group(1)} {time_match.group(2)}"

    return data


def extract_wind_speed(wind_str: str) -> str | None:

    #Extract numeric wind speed from a string like 'NE at 9.0 mph'.
    #Returns the speed as a string, or None if not parseable.

    if not wind_str:
        return None
    match = re.search(r"([\d.]+)\s*mph", wind_str, re.IGNORECASE)
    return match.group(1) if match else None


def push_to_supabase(data: dict) -> None:

    payload = {**data, "id": 1, "updated_at": datetime.now(timezone.utc).isoformat()}
    supabase.table("weather_current").upsert(payload).execute()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Pushed to weather_current")

    # Append to wind log and honestly im not fw this took everything in me to get bc i am kinda slow so shoutout claude
    wind_speed = extract_wind_speed(data.get("wind", ""))
    if wind_speed:
        supabase.table("weather_wind_log").insert({
            "wind_speed": wind_speed,
            "logged_at":  datetime.now(timezone.utc).isoformat(),
        }).execute()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Wind log: {wind_speed} mph")


#ngl everything after this i had a hard time with adjusting since it was previously made for a company case
#so i cleaned what i could and asked claude to finish, tested it, worked so here it is
def cleanup_wind_log() -> None:
    """
    Keep weather_wind_log trimmed to WIND_LOG_MAX_ROWS most recent entries.
    Runs a delete on the oldest rows when the table exceeds the limit.

    Note: if you set up pg_cron in Supabase this function is optional —
    pg_cron can handle pruning server-side on a schedule.
    """
    response = supabase.table("weather_wind_log") \
        .select("id", count="exact") \
        .execute()

    total = response.count or 0

    if total > WIND_LOG_MAX_ROWS:
        excess = total - WIND_LOG_MAX_ROWS
        oldest = supabase.table("weather_wind_log") \
            .select("id") \
            .order("logged_at", desc=False) \
            .limit(excess) \
            .execute()

        ids_to_delete = [row["id"] for row in oldest.data]
        if ids_to_delete:
            supabase.table("weather_wind_log") \
                .delete() \
                .in_("id", ids_to_delete) \
                .execute()
            print(f"[cleanup] Pruned {len(ids_to_delete)} old wind log entries")


def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Reading: {HTM_PATH}")

    if not os.path.exists(HTM_PATH):
        print(f"ERROR: HTML file not found at {HTM_PATH}")
        print("Check that WeatherLink is running and HTM_PATH is correct.")
        return

    data = parse_htm(HTM_PATH)

    if not data:
        print("WARNING: No data parsed. Check that label_map matches your WeatherLink template.")
        return

    print(f"  Fields extracted: {list(data.keys())}")

    push_to_supabase(data)
    cleanup_wind_log()

    print("Done.")


if __name__ == "__main__":
    main()
#YEAH WEATHER DATA MATHAFAKAS!!!!!!!!!!!
