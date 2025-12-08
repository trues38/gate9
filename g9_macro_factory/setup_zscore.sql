-- Run this in Supabase Dashboard SQL Editor

-- 1. Create zscore_daily table
CREATE TABLE IF NOT EXISTS zscore_daily (
    date DATE PRIMARY KEY,
    count INT,
    z_score FLOAT, -- Legacy or Global
    z_year FLOAT,  -- (Month_Avg - Year_Avg) / Year_Std
    z_day_local FLOAT, -- (Day - Month_Avg) / Month_Std
    impact_score FLOAT, -- Hybrid Score: Z-Score * ln(1 + Count)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Add column if table exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='zscore_daily' AND column_name='impact_score') THEN
        ALTER TABLE zscore_daily ADD COLUMN impact_score FLOAT;
    END IF;
END $$;

-- 2. (Optional) Create run_sql function if missing
-- Note: This is a security risk if exposed to public. Only use in development.
DROP FUNCTION IF EXISTS run_sql(text);

CREATE OR REPLACE FUNCTION run_sql(query text)
RETURNS SETOF json
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY EXECUTE 'SELECT row_to_json(t) FROM (' || query || ') t';
EXCEPTION WHEN OTHERS THEN
    -- Return error as a JSON object (in a list)
    RETURN NEXT json_build_object('error', SQLERRM);
END;
$$;
