-- G9 Meta-RAG (Failure Memory) Table
-- Stores failed strategies and correction rules to prevent future mistakes.

CREATE TABLE IF NOT EXISTS g9_meta_rag (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    origin_pattern_id TEXT, -- The pattern that failed (e.g., P-028)
    fail_reason TEXT,       -- Why it failed (e.g., "Priced-in", "Wrong Regime")
    correction_rule TEXT,   -- Rule to apply next time (e.g., "SKIP if Z < 2.0")
    regime_context TEXT,    -- Market regime when it failed (e.g., "Inflation")
    embedding VECTOR(3072), -- Embedding of the situation/pattern for similarity search
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_meta_rag_embedding ON g9_meta_rag USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
