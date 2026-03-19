-- schema.sql
-- Run this in the Supabase SQL editor to set up the required tables.
-- Project Settings > SQL Editor > New query > paste and run.

-- ── Live conditions table ─────────────────────────────────────────────────────
-- Always contains exactly one row (id = 1), upserted on every push.
CREATE TABLE IF NOT EXISTS weather_current (
    id           INTEGER PRIMARY KEY DEFAULT 1,
    temperature  TEXT,
    humidity     TEXT,
    dewpoint     TEXT,
    wind         TEXT,
    wind_avg     TEXT,
    wind_gust    TEXT,
    barometer    TEXT,
    rain_today   TEXT,
    rain_rate    TEXT,
    rain_storm   TEXT,
    rain_monthly TEXT,
    rain_yearly  TEXT,
    wind_chill   TEXT,
    thw_index    TEXT,
    heat_index   TEXT,
    station_time TEXT,
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ── Wind log table ────────────────────────────────────────────────────────────
-- Rolling time-series of wind speed readings.
-- Pruned by weather_pusher.py or by the pg_cron job below.
CREATE TABLE IF NOT EXISTS weather_wind_log (
    id         BIGSERIAL PRIMARY KEY,
    wind_speed TEXT,
    logged_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── Optional: 7-day history table ────────────────────────────────────────────
-- Uncomment to enable historical logging with download support.
-- CREATE TABLE IF NOT EXISTS weather_history (
--     id          BIGSERIAL PRIMARY KEY,
--     logged_at   TIMESTAMPTZ DEFAULT NOW(),
--     temperature TEXT,
--     humidity    TEXT,
--     wind_avg    TEXT,
--     wind_gust   TEXT,
--     rain_today  TEXT,
--     barometer   TEXT
-- );

-- ── Row Level Security ────────────────────────────────────────────────────────
-- Allow public read access (anon role).
-- The anon key in index.html can read but not write.
ALTER TABLE weather_current  ENABLE ROW LEVEL SECURITY;
ALTER TABLE weather_wind_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read - weather_current"
    ON weather_current FOR SELECT
    USING (true);

CREATE POLICY "Public read - weather_wind_log"
    ON weather_wind_log FOR SELECT
    USING (true);

-- weather_pusher.py writes using the service role key (bypasses RLS)
-- so no INSERT/UPDATE policy is needed for the anon role.

-- ── Optional: pg_cron auto-purge ─────────────────────────────────────────────
-- Uncomment to have Supabase automatically prune old wind log entries daily.
-- Requires pg_cron extension (enabled by default on Supabase).
--
-- SELECT cron.schedule(
--   'purge-old-wind-log',
--   '0 3 * * *',
--   $$
--     DELETE FROM weather_wind_log
--     WHERE logged_at < NOW() - INTERVAL '7 days';
--   $$
-- );
