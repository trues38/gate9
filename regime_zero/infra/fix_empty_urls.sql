-- 1. Remove rows with empty or NULL URLs (Invalid Data)
DELETE FROM ingest_news
WHERE url IS NULL OR url = '';

-- 2. Retry: Add Unique Constraint on URL
ALTER TABLE ingest_news 
ADD CONSTRAINT unique_news_url UNIQUE (url);
