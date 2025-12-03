-- Add new columns for news refinement
ALTER TABLE ingest_news 
ADD COLUMN IF NOT EXISTS category TEXT,
ADD COLUMN IF NOT EXISTS importance_score INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS is_refined BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS short_summary TEXT;

-- Index for faster filtering
CREATE INDEX IF NOT EXISTS idx_ingest_news_refined_score 
ON ingest_news (is_refined, importance_score);

-- Comment on columns
COMMENT ON COLUMN ingest_news.category IS 'LLM-classified category (ECONOMY, FINANCE, CRYPTO, etc.)';
COMMENT ON COLUMN ingest_news.importance_score IS 'LLM-rated importance (0-10)';
COMMENT ON COLUMN ingest_news.is_refined IS 'Whether the news has been processed by the refinement engine';
