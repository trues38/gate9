-- Enable pg_cron extension if not enabled
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule news ingestion every 30 minutes
-- Note: This assumes an Edge Function or HTTP endpoint exists to trigger the python script, 
-- OR we use pg_net to call an external webhook. 
-- Since the user asked to "codify" the existing setup, we assume a function call or similar.
-- For now, we'll define the job to call a Supabase Edge Function 'ingest-news'.

SELECT cron.schedule(
    'ingest-news-every-10-mins', -- Job name
    '*/10 * * * *',              -- Schedule (Every 10 mins)
    $$
    SELECT
      net.http_post(
          url:='https://PROJECT_REF.supabase.co/functions/v1/ingest-news',
          headers:='{"Content-Type": "application/json", "Authorization": "Bearer SERVICE_ROLE_KEY"}'::jsonb,
          body:='{}'::jsonb
      ) as request_id;
    $$
);

-- Schedule refinement every 10 minutes (to process newly ingested news)
SELECT cron.schedule(
    'refine-news-every-10-mins',
    '*/10 * * * *',
    $$
    SELECT
      net.http_post(
          url:='https://PROJECT_REF.supabase.co/functions/v1/refine-news',
          headers:='{"Content-Type": "application/json", "Authorization": "Bearer SERVICE_ROLE_KEY"}'::jsonb,
          body:='{}'::jsonb
      ) as request_id;
    $$
);
