-- G9 Schedule Manager SQLite Schema
-- Single Source of Truth for all schedules

-- NBA Games
CREATE TABLE IF NOT EXISTS nba_games (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    importance TEXT DEFAULT 'MID', -- HIGH, MID, LOW
    status TEXT DEFAULT 'pending',
    season TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Soccer Games
CREATE TABLE IF NOT EXISTS soccer_games (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    league TEXT NOT NULL, -- EPL, LaLiga, SerieA, Bundesliga, Ligue1
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    importance TEXT DEFAULT 'MID',
    status TEXT DEFAULT 'pending',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ECON Events
CREATE TABLE IF NOT EXISTS econ_events (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    event_name TEXT NOT NULL,
    impact TEXT NOT NULL, -- HIGH, MID, LOW
    country TEXT DEFAULT 'US',
    actual TEXT,
    forecast TEXT,
    previous TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- My Tasks (검토 작업 일정)
CREATE TABLE IF NOT EXISTS my_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    task_type TEXT NOT NULL, -- ECON, NBA, SOCCER
    domain TEXT NOT NULL,
    description TEXT,
    duration_minutes INTEGER DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pipeline Log (생성된 리포트 추적)
CREATE TABLE IF NOT EXISTS pipeline_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    domain TEXT NOT NULL, -- ECON, NBA, SOCCER
    dvss_score INTEGER,
    status TEXT DEFAULT 'pending',
    published INTEGER DEFAULT 0,
    report_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_nba_date ON nba_games(date);
CREATE INDEX IF NOT EXISTS idx_soccer_date ON soccer_games(date);
CREATE INDEX IF NOT EXISTS idx_econ_date ON econ_events(date);
CREATE INDEX IF NOT EXISTS idx_tasks_date ON my_tasks(date);
CREATE INDEX IF NOT EXISTS idx_pipeline_date ON pipeline_log(date);

-- Views for easy querying
CREATE VIEW IF NOT EXISTS daily_overview AS
SELECT
    date,
    (SELECT COUNT(*) FROM nba_games WHERE nba_games.date = d.date) as nba_count,
    (SELECT COUNT(*) FROM soccer_games WHERE soccer_games.date = d.date) as soccer_count,
    (SELECT COUNT(*) FROM econ_events WHERE econ_events.date = d.date) as econ_count,
    (SELECT GROUP_CONCAT(DISTINCT task_type) FROM my_tasks WHERE my_tasks.date = d.date) as my_tasks
FROM (
    SELECT DISTINCT date FROM nba_games
    UNION
    SELECT DISTINCT date FROM soccer_games
    UNION
    SELECT DISTINCT date FROM econ_events
) d
ORDER BY date;
