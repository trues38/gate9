-- Add functional index for fast daily aggregation (Immutable for UTC)
CREATE INDEX IF NOT EXISTS idx_global_news_date_utc ON global_news_all (((published_at AT TIME ZONE 'UTC')::date));
