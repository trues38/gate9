-- OPTIMIZED DEDUPLICATION (Faster)

-- 1. Delete duplicates using CTE (Common Table Expression)
-- This is much faster than the previous method because it scans the table once.
WITH duplicates AS (
    SELECT id,
           ROW_NUMBER() OVER (
               PARTITION BY url 
               ORDER BY created_at DESC
           ) as row_num
    FROM ingest_news
    WHERE url IS NOT NULL  -- Safety check
)
DELETE FROM ingest_news
WHERE id IN (
    SELECT id FROM duplicates WHERE row_num > 1
);

-- 2. Add Unique Constraint (Run this AFTER the delete finishes)
ALTER TABLE ingest_news 
ADD CONSTRAINT unique_news_url UNIQUE (url);
