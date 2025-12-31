-- Soccer SQLite Schema v1.0
-- 정량 데이터 전용 (시계열, 통계, 오즈)
-- Common IDs: match_id, team_id, manager_id, referee_id, player_id

PRAGMA foreign_keys = ON;

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Teams (정적 정보만)
CREATE TABLE IF NOT EXISTS teams (
    team_id TEXT PRIMARY KEY,           -- Common ID (e.g., "arsenal", "barcelona")
    name TEXT NOT NULL,
    league TEXT NOT NULL,               -- EPL, LaLiga, Bundesliga, SerieA, Ligue1
    country TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Managers (정적 정보만)
CREATE TABLE IF NOT EXISTS managers (
    manager_id TEXT PRIMARY KEY,        -- Common ID (e.g., "arteta", "guardiola")
    name TEXT NOT NULL,
    nationality TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Referees (정적 정보만)
CREATE TABLE IF NOT EXISTS referees (
    referee_id TEXT PRIMARY KEY,        -- Common ID (e.g., "michael_oliver")
    name TEXT NOT NULL,
    country TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Players
CREATE TABLE IF NOT EXISTS players (
    player_id TEXT PRIMARY KEY,         -- Common ID (e.g., "saka_arsenal")
    name TEXT NOT NULL,
    team_id TEXT,
    position TEXT,                      -- GK, DEF, MID, FWD
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

-- =============================================================================
-- MATCH DATA (Core Quantitative)
-- =============================================================================

-- Matches (정량 결과)
CREATE TABLE IF NOT EXISTS matches (
    match_id TEXT PRIMARY KEY,          -- Common ID (e.g., "EPL_2024_arsenal_chelsea_20241215")
    date TEXT NOT NULL,
    league TEXT NOT NULL,
    season TEXT NOT NULL,               -- "2024-25"
    matchweek INTEGER,
    home_team_id TEXT NOT NULL,
    away_team_id TEXT NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    home_manager_id TEXT,
    away_manager_id TEXT,
    referee_id TEXT,
    venue TEXT,
    attendance INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (home_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (away_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (home_manager_id) REFERENCES managers(manager_id),
    FOREIGN KEY (away_manager_id) REFERENCES managers(manager_id),
    FOREIGN KEY (referee_id) REFERENCES referees(referee_id)
);

-- Match Stats (xG, Possession, etc.)
CREATE TABLE IF NOT EXISTS match_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    is_home INTEGER NOT NULL,           -- 1 = home, 0 = away

    -- xG 데이터 (Understat)
    xg REAL,
    xga REAL,                           -- xG Against
    npxg REAL,                          -- Non-penalty xG

    -- 기본 통계
    shots INTEGER,
    shots_on_target INTEGER,
    possession REAL,                    -- 0-100%
    passes INTEGER,
    pass_accuracy REAL,                 -- 0-100%

    -- 세트피스
    corners INTEGER,
    free_kicks INTEGER,

    -- 수비/파울
    fouls INTEGER,
    yellow_cards INTEGER,
    red_cards INTEGER,
    offsides INTEGER,

    -- 기타
    tackles INTEGER,
    interceptions INTEGER,
    saves INTEGER,

    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE(match_id, team_id)
);

-- =============================================================================
-- ODDS DATA
-- =============================================================================

-- Odds Snapshot (경기 시작 전 최종)
CREATE TABLE IF NOT EXISTS odds_closing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT NOT NULL,
    bookmaker TEXT DEFAULT 'pinnacle',

    -- 1X2
    home_win REAL,
    draw REAL,
    away_win REAL,

    -- Asian Handicap
    ah_line REAL,                       -- e.g., -0.5, -1.0, +0.5
    ah_home REAL,
    ah_away REAL,

    -- Over/Under
    ou_line REAL,                       -- e.g., 2.5, 3.0
    over REAL,
    under REAL,

    -- BTTS (Both Teams To Score)
    btts_yes REAL,
    btts_no REAL,

    recorded_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    UNIQUE(match_id, bookmaker)
);

-- Odds Movement (라인 변동 추적)
CREATE TABLE IF NOT EXISTS odds_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT NOT NULL,
    bookmaker TEXT DEFAULT 'pinnacle',
    recorded_at TEXT NOT NULL,

    -- 1X2
    home_win REAL,
    draw REAL,
    away_win REAL,

    -- Asian Handicap
    ah_line REAL,
    ah_home REAL,
    ah_away REAL,

    -- Over/Under
    ou_line REAL,
    over REAL,
    under REAL,

    FOREIGN KEY (match_id) REFERENCES matches(match_id)
);

-- =============================================================================
-- PLAYER PERFORMANCE
-- =============================================================================

-- Player Match Stats
CREATE TABLE IF NOT EXISTS player_match_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT NOT NULL,
    player_id TEXT NOT NULL,
    team_id TEXT NOT NULL,

    -- 출전
    started INTEGER DEFAULT 0,          -- 1 = starter, 0 = sub
    minutes_played INTEGER,

    -- 공격
    goals INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    shots INTEGER DEFAULT 0,
    shots_on_target INTEGER DEFAULT 0,
    xg REAL,
    xa REAL,                            -- xAssist

    -- 패스
    passes INTEGER,
    key_passes INTEGER,
    pass_accuracy REAL,

    -- 수비
    tackles INTEGER,
    interceptions INTEGER,
    clearances INTEGER,
    blocks INTEGER,

    -- 기타
    fouls_committed INTEGER DEFAULT 0,
    fouls_won INTEGER DEFAULT 0,
    yellow_card INTEGER DEFAULT 0,
    red_card INTEGER DEFAULT 0,

    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE(match_id, player_id)
);

-- =============================================================================
-- INJURIES & AVAILABILITY
-- =============================================================================

-- Current Injuries
CREATE TABLE IF NOT EXISTS injuries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    injury_type TEXT,                   -- "hamstring", "knee", "illness"
    status TEXT,                        -- "out", "doubtful", "questionable"
    expected_return TEXT,               -- date or "unknown"
    reported_at TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

-- =============================================================================
-- REFEREE STATISTICS (정량)
-- =============================================================================

-- Referee Season Stats
CREATE TABLE IF NOT EXISTS referee_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referee_id TEXT NOT NULL,
    season TEXT NOT NULL,
    league TEXT NOT NULL,

    matches_officiated INTEGER DEFAULT 0,

    -- 카드 통계
    yellow_cards_total INTEGER DEFAULT 0,
    red_cards_total INTEGER DEFAULT 0,
    yellow_per_match REAL,
    red_per_match REAL,

    -- 파울 통계
    fouls_per_match REAL,

    -- 페널티 통계
    penalties_given INTEGER DEFAULT 0,
    penalties_per_match REAL,

    -- 홈/어웨이 분포
    home_wins INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    away_wins INTEGER DEFAULT 0,

    -- 오버언더 경향
    avg_total_goals REAL,
    over_2_5_pct REAL,

    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (referee_id) REFERENCES referees(referee_id),
    UNIQUE(referee_id, season, league)
);

-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date);
CREATE INDEX IF NOT EXISTS idx_matches_league ON matches(league);
CREATE INDEX IF NOT EXISTS idx_matches_season ON matches(season);
CREATE INDEX IF NOT EXISTS idx_matches_home ON matches(home_team_id);
CREATE INDEX IF NOT EXISTS idx_matches_away ON matches(away_team_id);
CREATE INDEX IF NOT EXISTS idx_matches_referee ON matches(referee_id);

CREATE INDEX IF NOT EXISTS idx_match_stats_match ON match_stats(match_id);
CREATE INDEX IF NOT EXISTS idx_match_stats_team ON match_stats(team_id);

CREATE INDEX IF NOT EXISTS idx_odds_closing_match ON odds_closing(match_id);
CREATE INDEX IF NOT EXISTS idx_odds_history_match ON odds_history(match_id);
CREATE INDEX IF NOT EXISTS idx_odds_history_time ON odds_history(recorded_at);

CREATE INDEX IF NOT EXISTS idx_player_stats_match ON player_match_stats(match_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_player ON player_match_stats(player_id);

CREATE INDEX IF NOT EXISTS idx_injuries_player ON injuries(player_id);
CREATE INDEX IF NOT EXISTS idx_injuries_team ON injuries(team_id);
CREATE INDEX IF NOT EXISTS idx_injuries_status ON injuries(status);

CREATE INDEX IF NOT EXISTS idx_referee_stats_season ON referee_stats(season);

-- =============================================================================
-- MIGRATION LOG
-- =============================================================================

CREATE TABLE IF NOT EXISTS _migration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL,
    applied_at TEXT DEFAULT (datetime('now'))
);

INSERT INTO _migration_log (migration_name) VALUES ('v1.0_initial_schema');
