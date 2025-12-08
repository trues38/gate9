-- Add Korean translation columns to ingest_news table
ALTER TABLE ingest_news ADD COLUMN IF NOT EXISTS title_ko TEXT;
ALTER TABLE ingest_news ADD COLUMN IF NOT EXISTS summary_ko TEXT;
