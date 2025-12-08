
    CREATE EXTENSION IF NOT EXISTS vector;

    CREATE TABLE IF NOT EXISTS antigravity_reports (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        date DATE NOT NULL,
        headline TEXT,
        pattern_ids TEXT[],
        final_thesis TEXT,
        dominant_narrative TEXT,
        strategy_bias TEXT,
        confirmed_signals TEXT[],
        weak_points TEXT[],
        counter_scenario TEXT,
        next_iteration_checklist TEXT[],
        embedding_text TEXT,
        embedding vector(3072),
        quality_score INTEGER,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
    );
    
    -- Create index for faster vector search
    CREATE INDEX IF NOT EXISTS antigravity_reports_embedding_idx ON antigravity_reports USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
    