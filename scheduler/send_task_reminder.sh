#!/bin/bash
# 30분 후 작업 리마인더

cd /Users/js/g9/scheduler

# Get current time and day of week
CURRENT_HOUR=$(date +%H)
CURRENT_MIN=$(date +%M)
DAY_OF_WEEK=$(date +%u)  # 1=Mon, 7=Sun

# Determine what task is coming up
TASK=""

# Check which reminder this is
if [ "$CURRENT_HOUR" == "06" ] && [ "$CURRENT_MIN" == "00" ]; then
    # Weekend: SOCCER at 06:30
    if [ "$DAY_OF_WEEK" -ge 6 ]; then
        # Check if there are soccer games
        HAS_SOCCER=$(python3 -c "
import sqlite3
from datetime import datetime, timedelta
tomorrow = (datetime.now() + timedelta(days=0)).strftime('%Y-%m-%d')
conn = sqlite3.connect('data/schedules.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM soccer_games WHERE date = ?', (tomorrow,))
count = cursor.fetchone()[0]
print(count)
conn.close()
")
        if [ "$HAS_SOCCER" -gt 0 ]; then
            TASK="06:30 SOCCER 검토 ⚽"
        fi
    else
        # Weekday: ECON Asia at 06:30
        TASK="06:30 ECON Asia 검토"
    fi

elif [ "$CURRENT_HOUR" == "06" ] && [ "$CURRENT_MIN" == "30" ]; then
    # Weekend only: ECON Asia at 07:00
    if [ "$DAY_OF_WEEK" -ge 6 ]; then
        TASK="07:00 ECON Asia 검토"
    fi

elif [ "$CURRENT_HOUR" == "19" ] && [ "$CURRENT_MIN" == "30" ]; then
    # NBA at 20:00 (if games exist)
    HAS_NBA=$(python3 -c "
import sqlite3
from datetime import datetime
today = datetime.now().strftime('%Y-%m-%d')
conn = sqlite3.connect('data/schedules.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM nba_games WHERE date = ?', (today,))
count = cursor.fetchone()[0]
print(count)
conn.close()
")
    if [ "$HAS_NBA" -gt 0 ]; then
        TASK="20:00 NBA 검토 🏀"
    fi

elif [ "$CURRENT_HOUR" == "20" ] && [ "$CURRENT_MIN" == "00" ]; then
    TASK="20:30 ECON US 검토"
fi

# Send reminder if task exists
if [ -n "$TASK" ]; then
    /usr/bin/python3 exporters/send_quick_reminder.py "$TASK"
fi
