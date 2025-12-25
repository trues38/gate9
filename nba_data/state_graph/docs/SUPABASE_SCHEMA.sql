-- ================================================================
-- NBA State Graph - Supabase Schema (Phase 1)
-- ================================================================
-- 설계 원칙:
-- 1. 모든 데이터는 날짜 기준 상태(State)로 저장
-- 2. Graph-friendly FK 구조
-- 3. Raw → Entity → Snapshot 단계 유지
-- ================================================================

-- ================================================================
-- 1. CORE ENTITIES (핵심 엔티티)
-- ================================================================

-- Teams 테이블
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    espn_id INTEGER UNIQUE NOT NULL,
    abbreviation VARCHAR(5) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    short_name VARCHAR(50),
    conference VARCHAR(20),  -- Eastern, Western
    division VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Players 테이블
CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    espn_id VARCHAR(20) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    jersey_number VARCHAR(5),
    position VARCHAR(10),
    team_id INTEGER REFERENCES teams(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Referees 테이블
CREATE TABLE IF NOT EXISTS referees (
    id SERIAL PRIMARY KEY,
    espn_id VARCHAR(20),
    full_name VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ================================================================
-- 2. RAW DATA TABLES (원본 데이터)
-- ================================================================

-- Raw Games (ESPN에서 수집한 원본 경기 데이터)
CREATE TABLE IF NOT EXISTS raw_games (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) UNIQUE NOT NULL,
    game_date DATE NOT NULL,
    raw_data JSONB NOT NULL,  -- ESPN Summary API 전체 응답
    collected_at TIMESTAMPTZ DEFAULT NOW()
);

-- Raw Rosters (날짜별 로스터 스냅샷)
CREATE TABLE IF NOT EXISTS raw_rosters (
    id SERIAL PRIMARY KEY,
    team_abbreviation VARCHAR(5) NOT NULL,
    roster_date DATE NOT NULL,
    raw_data JSONB NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team_abbreviation, roster_date)
);

-- ================================================================
-- 3. STATE TABLES (상태 테이블 - 핵심!)
-- ================================================================

-- Game States (경기 상태 스냅샷)
CREATE TABLE IF NOT EXISTS game_states (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL REFERENCES raw_games(game_id),
    game_date DATE NOT NULL,
    matchup VARCHAR(20) NOT NULL,  -- "PHI @ CHA"

    -- Home Team State
    home_team_abbr VARCHAR(5) NOT NULL,
    home_record VARCHAR(10),
    home_rest_days INTEGER,
    home_injuries JSONB,  -- ["LeBron James - Out", ...]
    home_lineup JSONB,    -- ["Player1", "Player2", ...]

    -- Away Team State
    away_team_abbr VARCHAR(5) NOT NULL,
    away_record VARCHAR(10),
    away_rest_days INTEGER,
    away_injuries JSONB,
    away_lineup JSONB,

    -- Game Meta
    referees JSONB,       -- ["Ref1", "Ref2", "Ref3"]
    state_notes JSONB,    -- ["GSW back-to-back", "Key player OUT"]

    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(game_id)
);

-- Team States (팀 일별 상태)
CREATE TABLE IF NOT EXISTS team_states (
    id SERIAL PRIMARY KEY,
    team_abbreviation VARCHAR(5) NOT NULL,
    state_date DATE NOT NULL,

    -- 순위/기록
    record VARCHAR(10),
    conference_rank INTEGER,

    -- 피로도 관련
    rest_days INTEGER,
    games_last_7_days INTEGER,
    travel_distance_km INTEGER,

    -- 부상 현황
    injuries JSONB,
    key_players_out TEXT[],

    -- 메타
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team_abbreviation, state_date)
);

-- Player States (선수 일별 상태)
CREATE TABLE IF NOT EXISTS player_states (
    id SERIAL PRIMARY KEY,
    player_espn_id VARCHAR(20) NOT NULL,
    player_name VARCHAR(100) NOT NULL,
    state_date DATE NOT NULL,

    -- 건강 상태
    injury_status VARCHAR(50),  -- Healthy, Day-To-Day, Out, etc.
    injury_type VARCHAR(100),

    -- 최근 퍼포먼스 (Phase 2에서 확장)
    -- last_5_games_avg JSONB,

    computed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(player_espn_id, state_date)
);

-- ================================================================
-- 4. RELATIONSHIP TABLES (관계 테이블)
-- ================================================================

-- Game-Referee 관계
CREATE TABLE IF NOT EXISTS game_referees (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    referee_id INTEGER REFERENCES referees(id),
    referee_name VARCHAR(100) NOT NULL,
    position_order INTEGER,  -- 1, 2, 3
    UNIQUE(game_id, referee_name)
);

-- Game-Player 관계 (라인업)
CREATE TABLE IF NOT EXISTS game_lineups (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    team_abbreviation VARCHAR(5) NOT NULL,
    player_name VARCHAR(100) NOT NULL,
    is_starter BOOLEAN DEFAULT FALSE,
    UNIQUE(game_id, team_abbreviation, player_name)
);

-- ================================================================
-- 5. INDEXES
-- ================================================================

-- 날짜 기반 조회 최적화
CREATE INDEX IF NOT EXISTS idx_game_states_date ON game_states(game_date);
CREATE INDEX IF NOT EXISTS idx_team_states_date ON team_states(state_date);
CREATE INDEX IF NOT EXISTS idx_player_states_date ON player_states(state_date);

-- 팀 기반 조회
CREATE INDEX IF NOT EXISTS idx_game_states_home ON game_states(home_team_abbr);
CREATE INDEX IF NOT EXISTS idx_game_states_away ON game_states(away_team_abbr);
CREATE INDEX IF NOT EXISTS idx_team_states_team ON team_states(team_abbreviation);

-- ================================================================
-- 6. HELPER VIEWS
-- ================================================================

-- 오늘 경기 상태 조회
CREATE OR REPLACE VIEW v_today_games AS
SELECT
    game_id,
    matchup,
    home_team_abbr,
    home_record,
    home_rest_days,
    away_team_abbr,
    away_record,
    away_rest_days,
    referees,
    state_notes
FROM game_states
WHERE game_date = CURRENT_DATE;

-- 팀별 최신 상태
CREATE OR REPLACE VIEW v_team_latest_state AS
SELECT DISTINCT ON (team_abbreviation)
    team_abbreviation,
    state_date,
    record,
    rest_days,
    injuries,
    key_players_out
FROM team_states
ORDER BY team_abbreviation, state_date DESC;

-- ================================================================
-- 7. SAMPLE DATA INSERT (테스트용)
-- ================================================================

/*
INSERT INTO teams (espn_id, abbreviation, display_name, conference, division) VALUES
(1, 'ATL', 'Atlanta Hawks', 'Eastern', 'Southeast'),
(2, 'BOS', 'Boston Celtics', 'Eastern', 'Atlantic'),
(13, 'LAL', 'Los Angeles Lakers', 'Western', 'Pacific'),
(9, 'GSW', 'Golden State Warriors', 'Western', 'Pacific');

-- Example Game State Insert
INSERT INTO game_states (
    game_id, game_date, matchup,
    home_team_abbr, home_record, home_rest_days, home_injuries, home_lineup,
    away_team_abbr, away_record, away_rest_days, away_injuries, away_lineup,
    referees, state_notes
) VALUES (
    '401736815', '2024-12-16', 'PHI @ CHA',
    'CHA', '7-19', 3, '["Grant Williams - Out"]'::jsonb, '["LaMelo Ball", "Miles Bridges"]'::jsonb,
    'PHI', '8-16', 3, '["Kelly Oubre Jr. - Out"]'::jsonb, '["Joel Embiid", "Paul George"]'::jsonb,
    '["Sean Wright", "Jason Goldenberg", "Michael Smith"]'::jsonb,
    '[]'::jsonb
);
*/
