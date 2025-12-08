-- 🚜 Agricultural Regime Engine - Database Schema

-- 1. Weather Data (Daily)
CREATE TABLE IF NOT EXISTS weather_daily (
    date DATE NOT NULL,
    region TEXT NOT NULL, -- e.g., 'Jeonnam', 'Gangwon'
    temp_avg FLOAT,
    rainfall FLOAT DEFAULT 0,
    sunshine FLOAT,
    humidity FLOAT,
    wind FLOAT,
    weather_api_raw JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (date, region)
);

-- 2. Crop Production (Daily Shipment)
CREATE TABLE IF NOT EXISTS crop_production_daily (
    date DATE NOT NULL,
    crop TEXT NOT NULL, -- 'onion', 'cabbage', 'potato', 'garlic'
    region TEXT NOT NULL,
    shipment_volume FLOAT, -- kg or ton
    production_index FLOAT,
    quality_grade TEXT,
    production_raw JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (date, crop, region)
);

-- 3. Crop Price (Daily Wholesale/Retail)
CREATE TABLE IF NOT EXISTS crop_price_daily (
    date DATE NOT NULL,
    crop TEXT NOT NULL,
    wholesale_price FLOAT,
    retail_price FLOAT,
    origin_market TEXT, -- e.g., 'Garak Market'
    price_raw JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (date, crop, origin_market)
);

-- 4. Crop News Headlines (RSS/Crawled)
CREATE TABLE IF NOT EXISTS crop_news_headlines (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date DATE NOT NULL,
    crop TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT UNIQUE,
    summary TEXT,
    extracted_keywords TEXT[],
    region TEXT,
    source TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Crop Events (AI Detected)
CREATE TABLE IF NOT EXISTS crop_events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date DATE NOT NULL,
    crop TEXT NOT NULL,
    event_type TEXT NOT NULL, -- 'Cold Wave', 'Pest', 'Policy', 'Import Surge'
    severity INTEGER CHECK (severity BETWEEN 1 AND 5),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Agri Regime Master (Final AI Output)
CREATE TABLE IF NOT EXISTS agri_regime_master (
    date DATE NOT NULL,
    crop TEXT NOT NULL,
    regime_label TEXT, -- e.g., 'Supply Shortage', 'Stable', 'Oversupply'
    narrative TEXT,
    drivers JSONB, -- Key factors driving the regime
    similarity_vector VECTOR(1536), -- For semantic search
    regime_raw JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (date, crop)
);

-- Enable RLS (Row Level Security)
ALTER TABLE weather_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE crop_production_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE crop_price_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE crop_news_headlines ENABLE ROW LEVEL SECURITY;
ALTER TABLE crop_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE agri_regime_master ENABLE ROW LEVEL SECURITY;

-- Public Read Access (For Dashboard)
CREATE POLICY "Public Read Weather" ON weather_daily FOR SELECT USING (true);
CREATE POLICY "Public Read Production" ON crop_production_daily FOR SELECT USING (true);
CREATE POLICY "Public Read Price" ON crop_price_daily FOR SELECT USING (true);
CREATE POLICY "Public Read News" ON crop_news_headlines FOR SELECT USING (true);
CREATE POLICY "Public Read Events" ON crop_events FOR SELECT USING (true);
CREATE POLICY "Public Read Agri Regime" ON agri_regime_master FOR SELECT USING (true);

-- Service Role Full Access (For Ingestion Scripts)
CREATE POLICY "Service Role Full Access Weather" ON weather_daily USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access Production" ON crop_production_daily USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access Price" ON crop_price_daily USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access News" ON crop_news_headlines USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access Events" ON crop_events USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access Agri Regime" ON agri_regime_master USING (true) WITH CHECK (true);
