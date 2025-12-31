#!/bin/bash
cd /Users/js/g9/scheduler

# Calculate tomorrow's date
TOMORROW=$(date -v+1d +%Y-%m-%d)

# Send tomorrow's briefing
/usr/bin/python3 exporters/telegram_briefing.py "$TOMORROW" >> /Users/js/g9/scheduler/logs/telegram_briefing.log 2>&1
