-- Add translation columns
ALTER TABLE ingest_news 
ADD COLUMN IF NOT EXISTS title_ko TEXT,
ADD COLUMN IF NOT EXISTS summary_ko TEXT;

-- Comment
COMMENT ON COLUMN ingest_news.title_ko IS 'Korean translation of the title';
COMMENT ON COLUMN ingest_news.summary_ko IS 'Korean translation of the summary';
