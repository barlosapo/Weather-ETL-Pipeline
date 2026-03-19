# Live Weather Station Dashboard

A full-stack IoT data pipeline that ingests real-time weather data from a Davis Vantage Pro 2 station, pushes it to a cloud database, and serves a live public dashboard — all on free-tier infrastructure.
---
## What it does

- Reads live sensor data from a Davis Vantage Pro 2 weather station every few minutes
- Parses the station's HTML output and extracts temperature, humidity, wind speed, wind gust, dewpoint, rain totals, heat index, wind chill, and THW index
- Pushes the parsed data to a Supabase (PostgreSQL) backend via REST API
- Displays a live auto-refreshing dashboard hosted on GitHub Pages — no server required
- Logs a rolling wind history for trend analysis

---

## Architecture

```
Davis VP2 Station
      |
      | serial
      v
WeatherLink Software  (generates Current_Vantage_Pro.htm locally)
      |
      | file read
      v
weather_pusher.py  (Python — runs on local machine on a schedule)
      |
      | UPSERT via Supabase REST API
      v
Supabase (PostgreSQL)
   |-- weather_current   (single live row, id = 1)
   |-- weather_wind_log  (time-series, auto-pruned)
      |
      | JS fetch from browser
      v
GitHub Pages  (index.html — static, no backend needed)
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Hardware | Davis Vantage Pro 2 |
| Station software | WeatherLink |
| Data pipeline | Python 3, BeautifulSoup, Supabase Python client |
| Database | Supabase (PostgreSQL, free tier) |
| Frontend | Vanilla JS, HTML, CSS |
| Hosting | GitHub Pages |

---

## Key files

```
weather-station/
├── weather_pusher.py     # Core pipeline: parse → clean → push
├── index.html            # Live dashboard frontend
└── README.md
```

### `weather_pusher.py`

The heart of the system. Responsibilities:

1. **Parse** — reads `Current_Vantage_Pro.htm` using BeautifulSoup and maps HTML label text to database field names via a `label_map` dictionary
2. **Clean** — handles unit stripping, null values, and type coercion
3. **Push** — upserts the current reading to `weather_current` (always row id=1) and appends to `weather_wind_log`
4. **Prune** — trims old wind log entries to keep the table lean

### `index.html`

A single-file static dashboard. On load and on a polling interval it:

1. Calls the Supabase REST API directly from the browser using the public anon key
2. Selects `* from weather_current where id = 1`
3. Updates all DOM elements with the latest values

No build step, no framework, no server.

---

## Data fields

| Field | Description |
|---|---|
| `temperature` | Current air temperature |
| `humidity` | Relative humidity % |
| `dewpoint` | Dew point temperature |
| `wind` | Instantaneous wind speed |
| `wind_avg` | 10-minute average wind speed |
| `wind_gust` | 10-minute peak gust |
| `rain_today` | Rainfall accumulation today |
| `rain_rate` | Current rain rate |
| `rain_storm` | Storm total rainfall |
| `rain_monthly` | Monthly rainfall total |
| `rain_yearly` | Year-to-date rainfall |
| `wind_chill` | Wind chill temperature |
| `heat_index` | Heat index temperature |
| `thw_index` | Temperature-humidity-wind index |
| `barometer` | Barometric pressure |
| `station_time` | Timestamp from station |

---

## Database schema

```sql
-- Live reading (single row, always upserted)
CREATE TABLE weather_current (
  id           INTEGER PRIMARY KEY DEFAULT 1,
  temperature  TEXT,
  humidity     TEXT,
  dewpoint     TEXT,
  wind         TEXT,
  wind_avg     TEXT,
  wind_gust    TEXT,
  rain_today   TEXT,
  rain_rate    TEXT,
  rain_storm   TEXT,
  rain_monthly TEXT,
  rain_yearly  TEXT,
  wind_chill   TEXT,
  heat_index   TEXT,
  thw_index    TEXT,
  barometer    TEXT,
  station_time TEXT,
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Rolling wind history (pruned automatically)
CREATE TABLE weather_wind_log (
  id         BIGSERIAL PRIMARY KEY,
  wind_speed TEXT,
  logged_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Running locally

### Prerequisites

```bash
pip install supabase beautifulsoup4 requests
```

### Configuration

Create a `.env` file or set environment variables:

```
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_anon_key
HTM_PATH=C:\path\to\Current_Vantage_Pro.htm
```

### Run

```bash
python weather_pusher.py
```

Schedule with Windows Task Scheduler or cron to run every 5 minutes.

---

## Adapting to other stations

The pipeline is station-agnostic beyond the parser layer. To use a different station:

| Station type | What to change |
|---|---|
| Any station writing an HTML or CSV file | Update `label_map` in `weather_pusher.py` to match the new field names |
| Davis with WeatherLink Live | Replace BeautifulSoup parser with a `requests.get()` call to the local LAN API |
| Ambient Weather / Ecowitt | Replace pusher with a small Flask server that receives the station's POST |
| Any station with a public API | Poll the API instead of reading a local file |

Everything from Supabase onward — the schema, the frontend, the GitHub Pages hosting — stays identical regardless of station.

---

## Free tier infrastructure

This entire system runs at zero cost:

| Service | Free tier used | Limit |
|---|---|---|
| Supabase | ~5 MB database | 500 MB |
| Supabase | Unlimited API requests | Unlimited |
| GitHub Pages | Static hosting | Unlimited |

At one reading every 5 minutes, a full year of data consumes roughly 6 MB — well within free tier limits.

---

## Roadmap

- [ ] `weather_history` table for 7-day logging with downloadable export (XML / TXT)
- [ ] Barometer calibration (pending COM port resolution)
- [ ] Wind rose chart on dashboard
- [ ] Upgrade ingestion to WeatherLink Live API for cleaner data access
- [ ] Generalize pusher into a reusable package for arbitrary station types

---

## License

MIT
