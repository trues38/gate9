-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable Vector extension if not already enabled (for embedding)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS g9_intelligence_core (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    target_date DATE NOT NULL, -- 사건 발생일
    
    -- 1. 감지 (Signal)
    ticker VARCHAR(20) NOT NULL,
    sector VARCHAR(50),
    z_score FLOAT, -- 뉴스 폭발 강도
    macro_env JSONB, -- { "vix": 15, "rate": 4.2 ... }
    
    -- 2. 추론 (Reasoning)
    pattern_id VARCHAR(10), -- P-001 등
    strategy_type VARCHAR(20), -- Aggressive, Defensive 등
    confidence_score FLOAT, -- AI 확신도 (0.0 ~ 1.0)
    final_logic TEXT, -- 안티그래비티의 최종 논리
    
    -- 3. 결과 (Result - 백테스팅 후 업데이트됨)
    return_3d FLOAT, -- 3일 수익률
    return_7d FLOAT, -- 7일 수익률
    success_flag BOOLEAN, -- 성공 여부
    
    -- 4. 벡터 (Vector - RAG 검색용)
    embedding vector(1536) -- 상황+논리를 압축한 벡터
);

-- Index for faster vector search
-- CREATE INDEX ON g9_intelligence_core USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
