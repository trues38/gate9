-- RPC function for Meta-RAG similarity search
-- Renamed output columns to avoid ambiguity with table columns

DROP FUNCTION IF EXISTS match_meta_fail(vector, float, int);

CREATE OR REPLACE FUNCTION match_meta_fail(
    query_embedding vector(3072),
    match_threshold float,
    match_count int
)
RETURNS TABLE (
    match_id uuid,
    match_origin_pattern_id text,
    match_fail_reason text,
    match_correction_rule text,
    match_regime_context text,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        g9_meta_rag.id,
        g9_meta_rag.origin_pattern_id,
        g9_meta_rag.fail_reason,
        g9_meta_rag.correction_rule,
        g9_meta_rag.regime_context,
        1 - (g9_meta_rag.embedding <=> query_embedding) as similarity
    FROM g9_meta_rag
    WHERE 1 - (g9_meta_rag.embedding <=> query_embedding) > match_threshold
    ORDER BY g9_meta_rag.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
