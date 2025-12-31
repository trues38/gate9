# G9 Schedule Manager — Next Steps

## ✅ What's Complete

1. **Directory Structure**: Full hierarchy created
2. **Database**: SQLite initialized with schema
3. **Collectors**: NBA (ESPN), Soccer (football-data.org), ECON
4. **Exporters**: Google Sheets, Google Calendar, MD files, Telegram
5. **Orchestrator**: Main schedule_manager.py
6. **Cron Scripts**: Automated job runners
7. **Documentation**: README, Google setup guide

---

## 🔧 Configuration Needed

### 1. Telegram Chat ID

**Get your chat ID:**

```bash
cd /Users/js/g9/scheduler

# First, send a message to your bot: https://t.me/G9_state_bot
# Type anything, like: /start

# Then run:
python3 exporters/telegram_briefing.py getchat
```

**Update .env:**
```bash
TELEGRAM_CHAT_ID=your_chat_id_here
```

---

### 2. Google Service Account (Optional)

**If you want Google Sheets/Calendar integration:**

1. Follow guide: `GOOGLE_SETUP_GUIDE.md`
2. Download service account JSON
3. Save to: `credentials/google_service_account.json`
4. Create Google Sheet and share with service account
5. Update .env:
   ```
   GOOGLE_SHEET_ID=your_sheet_id
   GOOGLE_CALENDAR_ID=primary
   ```

**Skip for now?** System works without Google integration.

---

## 🧪 Test the System

### Test 1: Collect January 2025 Schedule

```bash
python3 schedule_manager.py collect 2025 1
```

**Expected output:**
- NBA games collected
- Soccer matches collected
- ECON events loaded

### Test 2: Export to MD Files

```bash
python3 schedule_manager.py export 2025 1
```

**Check outputs:**
```bash
ls -lh outputs/monthly/
ls -lh outputs/daily/
```

### Test 3: Send Telegram Briefing

```bash
# Make sure you've set TELEGRAM_CHAT_ID first!
python3 schedule_manager.py brief 2025-12-31
```

**Check your Telegram** for the briefing message.

---

## 🚀 Deploy to VPS

### Option 1: Manual Deployment

```bash
# From local machine
rsync -avz /Users/js/g9/scheduler/ root@141.164.35.214:/opt/g9/scheduler/

# On VPS
ssh root@141.164.35.214
cd /opt/g9/scheduler
pip3 install -r requirements.txt
python3 init_db.py

# Update .env with VPS paths
nano .env
# Change all /Users/js/g9/scheduler to /opt/g9/scheduler

# Test
python3 schedule_manager.py collect 2025 1
```

### Option 2: Docker Deployment (Recommended)

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "schedule_manager.py", "daily"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  scheduler:
    build: .
    volumes:
      - ./data:/app/data
      - ./outputs:/app/outputs
      - ./credentials:/app/credentials
    env_file:
      - .env
    restart: unless-stopped
```

---

## ⏰ Setup Automation

### Install Cron Jobs

```bash
cd /opt/g9/scheduler
chmod +x scripts/*.sh
sudo bash scripts/install_cron.sh
```

### Verify Cron

```bash
crontab -l
```

**Should show:**
- Monthly collection (25th @ midnight)
- Daily briefing (every day @ 06:30)
- Weekly preview (Sunday @ 20:00)

### Monitor Logs

```bash
tail -f /opt/g9/scheduler/data/cron.log
```

---

## 📊 Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| Database | ✅ Working | SQLite initialized |
| NBA Collector | ✅ Working | ESPN API tested |
| Soccer Collector | ⚠️ Not tested | Need API key validation |
| ECON Collector | ✅ Working | 2025 calendar loaded |
| MD Exporter | ✅ Working | Files generated |
| Telegram | ⚠️ Needs chat ID | Bot token configured |
| Google Sheets | ⏸️ Optional | Needs service account |
| Google Calendar | ⏸️ Optional | Needs service account |

---

## 🐛 Troubleshooting

### Telegram not working?

```bash
# Test bot token
curl https://api.telegram.org/bot8235545385:AAEu0TEUlqJnL6FHHj6q9CDnyCn2fg6TPNw/getMe

# Get chat ID
python3 exporters/telegram_briefing.py getchat
```

### Soccer API failing?

```bash
# Test football API key
curl -H "X-Auth-Token: 9f8ffd2e830d441a97301cec9d52cf2b" \
  https://api.football-data.org/v4/competitions/2021/matches
```

### Database queries?

```bash
sqlite3 data/schedules.db

# View ECON events
SELECT * FROM econ_events WHERE date >= date('now');

# View NBA games
SELECT * FROM nba_games WHERE date >= date('now');

# Daily overview
SELECT * FROM daily_overview WHERE date >= date('now');
```

---

## 📅 Recommended Next Actions

1. **Today**: Get Telegram Chat ID and test briefing
2. **Tomorrow**: Collect full January 2025 schedule
3. **This Week**: Setup Google integration (optional)
4. **Deploy**: Move to VPS and setup cron

---

## 🎯 Quick Commands Reference

```bash
# Collect schedule
python3 schedule_manager.py collect 2025 1

# Export everything
python3 schedule_manager.py export 2025 1

# Send briefing
python3 schedule_manager.py brief

# Run automated jobs
python3 schedule_manager.py monthly  # Monthly collection
python3 schedule_manager.py daily    # Daily briefing
python3 schedule_manager.py weekly   # Weekly preview

# Individual collectors
python3 collectors/nba_collector.py 20250115
python3 collectors/soccer_collector.py 2025-01-01 2025-01-31
python3 collectors/econ_collector.py 2025 1

# Individual exporters
python3 exporters/md_exporter.py daily 2025-01-15
python3 exporters/telegram_briefing.py 2025-01-15
```

---

## 📞 Need Help?

Check the logs:
```bash
tail -f data/cron.log
```

Re-read the docs:
```bash
cat README.md
cat GOOGLE_SETUP_GUIDE.md
```

---

**System is ready! Start with getting your Telegram Chat ID.**
