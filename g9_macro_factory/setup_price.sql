-- Run this in Supabase Dashboard SQL Editor

-- Create price_daily table if not exists
CREATE TABLE IF NOT EXISTS price_daily (
    ticker TEXT,
    date DATE,
    close FLOAT,
    open FLOAT,
    high FLOAT,
    low FLOAT,
    volume BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    PRIMARY KEY (ticker, date)
);

-- Add columns if missing (for existing table)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='price_daily' AND column_name='open') THEN
        ALTER TABLE price_daily ADD COLUMN open FLOAT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='price_daily' AND column_name='high') THEN
        ALTER TABLE price_daily ADD COLUMN high FLOAT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='price_daily' AND column_name='low') THEN
        ALTER TABLE price_daily ADD COLUMN low FLOAT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='price_daily' AND column_name='volume') THEN
        ALTER TABLE price_daily ADD COLUMN volume BIGINT;
    END IF;
END $$;
