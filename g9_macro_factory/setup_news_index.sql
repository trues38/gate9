-- Add index to speed up news retrieval by date
CREATE INDEX IF NOT EXISTS idx_global_news_published_at ON global_news_all (published_at DESC);

-- Optional: Cluster table by index for faster range scans (Maintenance)
-- CLUSTER global_news_all USING idx_global_news_published_at;
