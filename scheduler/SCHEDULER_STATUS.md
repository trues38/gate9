# G9 Scheduler System - Status Report

**Last Updated:** 2025-12-31

## ✅ System Components

### 1. NBA Schedule (25-26 Season)
- **Status:** ✅ Complete
- **Games:** 1,306 games
- **Period:** 2025-10-03 ~ 2026-04-13
- **Timezone:** KST (Korea Standard Time)
- **Collector:** `collectors/nba_collector.py`
- **Backfill:** `backfill_nba_season.py`

### 2. Soccer (Top 5 Leagues)
- **Status:** ✅ Partial (Dec-Jan only, API rate limited)
- **Matches:** 406 matches
- **Period:** 2025-12-01 ~ 2026-01-31
- **Leagues:**
  - EPL (Premier League): 105 matches
  - La Liga: 81 matches
  - Serie A: 101 matches
  - Bundesliga: 70 matches
  - Ligue 1: 49 matches
- **Timezone:** KST
- **Collector:** `collectors/soccer_collector.py`
- **Backfill:** `backfill_soccer_season.py`
- **API:** football-data.org (Free tier: 10 req/min limit)

### 3. ECON Events
- **Status:** ✅ Complete
- **Events:** 26 events
- **Period:** 2025-01-03 ~ 2026-06-17
- **Types:** NFP, CPI, FOMC, GDP, PCE
- **Impact:** All HIGH
- **Timezone:** KST
- **Source:** Hardcoded calendar in `collectors/econ_events.json`
- **Collector:** `collectors/econ_collector.py`

## ✅ Automation

### Daily Briefing
- **Time:** 22:00 KST (10 PM)
- **Content:** Tomorrow's full schedule (NBA + Soccer + ECON)
- **Script:** `send_daily_briefing.sh`
- **Cron:** `0 22 * * *`

### Task Reminders (30min before)
| Time | Task | Days | Script |
|------|------|------|--------|
| 06:00 | ECON Asia (weekday) / SOCCER (weekend) | Daily | `send_task_reminder.sh` |
| 06:30 | ECON Asia (weekend only) | Sat, Sun | `send_task_reminder.sh` |
| 19:30 | NBA review (if games exist) | Daily | `send_task_reminder.sh` |
| 20:00 | ECON US review | Daily | `send_task_reminder.sh` |

### Crontab
```bash
# Daily Briefing
0 22 * * * /Users/js/g9/scheduler/send_daily_briefing.sh

# Task Reminders
0 6 * * * /Users/js/g9/scheduler/send_task_reminder.sh
30 6 * * 0,6 /Users/js/g9/scheduler/send_task_reminder.sh
30 19 * * * /Users/js/g9/scheduler/send_task_reminder.sh
0 20 * * * /Users/js/g9/scheduler/send_task_reminder.sh
```

## 📊 Database

**Location:** `/Users/js/g9/scheduler/data/schedules.db`

### Tables
- `nba_games`: 1,306 rows
- `soccer_games`: 406 rows
- `econ_events`: 26 rows
- `my_tasks`: Custom tasks
- `pipeline_log`: Execution logs

### Schema
```sql
-- NBA Games
CREATE TABLE nba_games (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,           -- KST date
    time TEXT NOT NULL,           -- KST time
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    importance TEXT DEFAULT 'MID',
    status TEXT DEFAULT 'pending',
    season TEXT,
    notes TEXT
);

-- Soccer Games
CREATE TABLE soccer_games (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,           -- KST date
    time TEXT NOT NULL,           -- KST time
    league TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    importance TEXT DEFAULT 'MID',
    status TEXT DEFAULT 'pending',
    notes TEXT
);

-- ECON Events
CREATE TABLE econ_events (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,           -- KST date
    time TEXT NOT NULL,           -- KST time
    event_name TEXT NOT NULL,
    impact TEXT NOT NULL,
    country TEXT DEFAULT 'US',
    actual TEXT,
    forecast TEXT,
    previous TEXT,
    notes TEXT
);
```

## 🔧 Configuration

### Environment Variables (.env)
```
DB_PATH=/Users/js/g9/scheduler/data/schedules.db
TELEGRAM_BOT_TOKEN=<bot_token>
TELEGRAM_CHAT_ID=5991157652
FOOTBALL_API_KEY=9f8ffd2e830d441a97301cec9d52cf2b
FRED_API_KEY=<fred_key>
ESPN_API_BASE=https://site.api.espn.com/apis/site/v2/sports
```

### Telegram Bot
- **Bot:** @G9_state_bot
- **Chat ID:** 5991157652
- **API:** telegram.org/bot API

## 🌍 Timezone Handling

**Critical:** All dates and times are stored in **KST (Korea Standard Time, UTC+9)**

### NBA (US Games)
- Source: ESPN API provides UTC times
- Conversion: UTC → KST for both date and time
- Example: US 12/30 20:00 ET → KST 12/31 10:00

### Soccer (Europe Games)
- Source: football-data.org provides UTC times
- Conversion: UTC → KST for both date and time
- Example: London Sat 15:00 GMT → Seoul Sat 24:00 (Sun 00:00)

### ECON Events (US Markets)
- Hardcoded in KST
- NFP: 22:30 KST (US 08:30 ET)
- CPI: 22:30 KST (US 08:30 ET)
- FOMC: 04:00 KST (US 14:00 ET, previous day)

## 📝 Next Steps

### Immediate
- [ ] Monitor cron jobs for 24 hours
- [ ] Verify Telegram messages are sent correctly
- [ ] Check briefing format and content

### Short-term
- [ ] Expand soccer data (Feb-May 2026) when API rate limit resets
- [ ] Add more ECON events (retail sales, ISM, etc.)
- [ ] Add US/Korea holiday calendar

### Integration
- [ ] NBA analysis pipeline can query this DB for today's games
- [ ] Soccer analysis pipeline can query for matches
- [ ] Economic regime system can subscribe to ECON events

## 🔗 Usage for Other Pipelines

```python
import sqlite3
from datetime import datetime

# Get today's NBA games
db = sqlite3.connect('/Users/js/g9/scheduler/data/schedules.db')
cursor = db.cursor()

today = datetime.now().strftime('%Y-%m-%d')
cursor.execute("SELECT * FROM nba_games WHERE date = ?", (today,))
games = cursor.fetchall()

# Process games for analysis pipeline...
```

## 🎯 System Architecture

```
Cron Scheduler
    ↓
[22:00] Daily Briefing → Telegram
[06:00/06:30/19:30/20:00] Task Reminders → Telegram
    ↓
SQLite Database (Central Source of Truth)
    ↓
├── NBA Analysis Pipeline
├── Soccer Analysis Pipeline
└── Economic Regime System
```

---

**Status:** ✅ Production Ready
**Deployed:** 2025-12-31
**Maintained By:** G9 System
