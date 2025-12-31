# G9 Schedule Manager

**Centralized schedule management system for NBA, Soccer, and Economic events**

Automatically collects schedules from multiple sources, stores in SQLite, and deploys to:
- Google Sheets (monthly/detail views)
- Google Calendar (with review task reminders)
- Markdown files (for pipeline consumption)
- Telegram (daily briefing)

---

## Features

### 📅 Data Collection
- **NBA**: ESPN API (free, no key required)
- **Soccer**: football-data.org (5 major leagues)
- **ECON**: Pre-configured calendar (CPI, NFP, FOMC, etc.)

### 📊 Export Targets
- **Google Sheets**: Multi-tab monthly overview
- **Google Calendar**: Color-coded events + review tasks
- **MD Files**: Daily/Weekly/Monthly markdown summaries
- **Telegram**: Morning briefing with day's schedule

### ⏰ Automation
- **Monthly**: Collect next month's schedule (runs on 25th)
- **Daily**: Send morning briefing (06:30 KST)
- **Weekly**: Preview next week (Sunday 20:00 KST)

---

## Quick Start

### 1. Install Dependencies

```bash
cd /opt/g9/scheduler
pip3 install -r requirements.txt
```

### 2. Initialize Database

```bash
python3 init_db.py
```

### 3. Configure Environment

```bash
cp .env.example .env
nano .env
```

**Required:**
- `FOOTBALL_API_KEY`: Get from [football-data.org](https://www.football-data.org/)
- `FRED_API_KEY`: Get from [FRED](https://fred.stlouisfed.org/docs/api/api_key.html)
- `TELEGRAM_BOT_TOKEN`: Create bot via [@BotFather](https://t.me/BotFather)

**Optional (for Google integration):**
- Follow [GOOGLE_SETUP_GUIDE.md](./GOOGLE_SETUP_GUIDE.md)

### 4. Get Telegram Chat ID

```bash
# Start a conversation with your bot, then run:
python3 exporters/telegram_briefing.py getchat
```

Copy the Chat ID to `.env`:
```
TELEGRAM_CHAT_ID=your_chat_id
```

### 5. Test Run

```bash
# Collect January 2025 schedule
python3 schedule_manager.py collect 2025 1

# Export to all platforms
python3 schedule_manager.py export 2025 1

# Send test briefing
python3 schedule_manager.py brief
```

---

## Usage

### Manual Commands

```bash
# Collect specific month
python3 schedule_manager.py collect <year> <month>

# Export to Google/MD/Telegram
python3 schedule_manager.py export <year> <month>

# Send daily briefing
python3 schedule_manager.py brief [date]

# Run automated jobs
python3 schedule_manager.py monthly
python3 schedule_manager.py daily
python3 schedule_manager.py weekly
```

### Automated (Cron)

```bash
# Install cron jobs
chmod +x scripts/*.sh
sudo bash scripts/install_cron.sh

# View scheduled jobs
crontab -l
```

**Cron Schedule:**
- **Monthly collection**: 25th @ 00:00 KST
- **Daily briefing**: Every day @ 06:30 KST
- **Weekly preview**: Sunday @ 20:00 KST

---

## Architecture

```
scheduler/
├── collectors/          # Data collection
│   ├── nba_collector.py
│   ├── soccer_collector.py
│   ├── econ_collector.py
│   └── econ_events.json
├── exporters/           # Output generation
│   ├── sheets_exporter.py
│   ├── calendar_exporter.py
│   ├── md_exporter.py
│   └── telegram_briefing.py
├── data/
│   └── schedules.db     # SQLite database
├── outputs/
│   ├── daily/           # MD files
│   ├── weekly/
│   └── monthly/
├── scripts/             # Cron scripts
│   ├── run_monthly.sh
│   ├── run_daily.sh
│   └── run_weekly.sh
├── schedule_manager.py  # Main orchestrator
└── init_db.py          # DB initialization
```

---

## Database Schema

### Tables
- `nba_games`: NBA schedule
- `soccer_games`: Soccer fixtures
- `econ_events`: Economic calendar
- `my_tasks`: Review task schedule
- `pipeline_log`: Report generation tracking

### Views
- `daily_overview`: Aggregated daily counts

---

## Google Sheets Output

### Tabs Created
1. **Monthly Overview**: Calendar view with counts
2. **NBA Detail**: All games with importance
3. **Soccer Detail**: All matches by league
4. **ECON Events**: Economic calendar
5. **Pipeline Log**: Report tracking

---

## Telegram Briefing Format

```
━━━━━━━━━━━━━━━━━━━━━━
📅 G9 Daily — 2025-01-15 (수)
━━━━━━━━━━━━━━━━━━━━━━

📊 ECON
└─ 🔴 CPI 발표 (22:30)

🏀 NBA (8경기)
├─ 🔥 Lakers vs Celtics (08:00)
├─ Warriors vs Suns (10:30)
└─ ... 6 more

⚽ SOCCER (5경기)
├─ 🔥 Arsenal vs Liverpool (22:00)
└─ ... 4 more

━━━━━━━━━━━━━━━━━━━━━━
⏰ 내 작업
├─ 06:30 ECON 검토
├─ 07:00 SOCCER 검토
└─ 20:00 NBA 검토

⚠️ CPI 발표 → 내일 변동성 주의
━━━━━━━━━━━━━━━━━━━━━━
```

---

## Deployment to VPS

### 1. Copy to VPS

```bash
# From local machine
rsync -avz /Users/js/g9/scheduler/ user@vps:/opt/g9/scheduler/
```

### 2. Install on VPS

```bash
# On VPS
cd /opt/g9/scheduler
pip3 install -r requirements.txt
python3 init_db.py

# Update .env with VPS paths
nano .env

# Install cron
sudo bash scripts/install_cron.sh
```

### 3. Test on VPS

```bash
python3 schedule_manager.py collect 2025 1
python3 schedule_manager.py brief
```

---

## Monitoring

### Cron Logs

```bash
tail -f /opt/g9/scheduler/data/cron.log
```

### Database Stats

```bash
sqlite3 data/schedules.db "SELECT * FROM daily_overview WHERE date >= date('now');"
```

---

## Troubleshooting

### Google API Errors
- Check [GOOGLE_SETUP_GUIDE.md](./GOOGLE_SETUP_GUIDE.md)
- Verify service account has Sheet/Calendar access
- Ensure APIs are enabled in Cloud Console

### Telegram Not Working
- Verify bot token and chat ID
- Run `python3 exporters/telegram_briefing.py getchat`
- Test: `curl https://api.telegram.org/bot<TOKEN>/getMe`

### Missing Data
- Check API keys are valid
- Review collector logs for errors
- Verify internet connectivity

### Cron Not Running
- Check cron service: `systemctl status cron`
- Verify script permissions: `chmod +x scripts/*.sh`
- Check paths in cron scripts match deployment location

---

## License

MIT

---

## Support

For issues or questions, contact the G9 team.
