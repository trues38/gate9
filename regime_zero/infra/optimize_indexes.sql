-- Create indexes to speed up dashboard filtering
-- We filter by: country, category, importance_score
-- We sort by: published_at DESC

-- 1. Index for default view (All countries, sorted by date)
CREATE INDEX IF NOT EXISTS idx_ingest_news_published_at ON ingest_news (published_at DESC);

-- 2. Index for filtering by Country + Score + Date
CREATE INDEX IF NOT EXISTS idx_ingest_news_country_score_date ON ingest_news (country, importance_score, published_at DESC);

-- 3. Index for filtering by Category + Score + Date
CREATE INDEX IF NOT EXISTS idx_ingest_news_category_score_date ON ingest_news (category, importance_score, published_at DESC);

-- 4. Composite index for Country + Category + Score + Date (Deep filtering)
CREATE INDEX IF NOT EXISTS idx_ingest_news_full_filter ON ingest_news (country, category, importance_score, published_at DESC);

-- 5. Text search index for Crypto (already exists usually, but ensuring)
CREATE INDEX IF NOT EXISTS idx_ingest_news_title_gin ON ingest_news USING gin(to_tsvector('english', title));
