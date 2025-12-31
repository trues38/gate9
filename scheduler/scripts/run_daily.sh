#!/bin/bash
# Daily Briefing Job
# Sends Telegram briefing every morning at 06:30 KST
# Cron: 30 21 * * * /opt/g9/scheduler/scripts/run_daily.sh (21:30 UTC = 06:30 KST)

cd /opt/g9/scheduler
source .env

echo "$(date): Running daily briefing" >> data/cron.log

/usr/bin/python3 schedule_manager.py daily >> data/cron.log 2>&1

echo "$(date): Daily briefing complete" >> data/cron.log
