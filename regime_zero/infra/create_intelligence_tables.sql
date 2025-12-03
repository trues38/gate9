-- 1. Table for Regime Objects (Historical Analysis)
CREATE TABLE IF NOT EXISTS intelligence_regimes (
    date DATE PRIMARY KEY,
    regime_name TEXT NOT NULL,
    signature JSONB,
    historical_vibe TEXT,
    structural_reasoning TEXT,
    risks JSONB,
    upside JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Table for Consensus Reports (Daily Output)
CREATE TABLE IF NOT EXISTS intelligence_reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date DATE NOT NULL,
    type TEXT NOT NULL, -- 'Institutional' or 'Personal'
    content TEXT,
    consensus_signal JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(date, type)
);

-- 3. Enable RLS (Optional but recommended)
ALTER TABLE intelligence_regimes ENABLE ROW LEVEL SECURITY;
ALTER TABLE intelligence_reports ENABLE ROW LEVEL SECURITY;

-- 4. Allow public read access (for website)
CREATE POLICY "Public Read Regimes" ON intelligence_regimes FOR SELECT USING (true);
CREATE POLICY "Public Read Reports" ON intelligence_reports FOR SELECT USING (true);

-- 5. Allow service role full access
CREATE POLICY "Service Role Full Access Regimes" ON intelligence_regimes USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access Reports" ON intelligence_reports USING (true) WITH CHECK (true);
