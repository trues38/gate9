#!/bin/bash
# Weekly Preview Job
# Sends weekly preview every Sunday at 20:00 KST
# Cron: 0 11 * * 0 /opt/g9/scheduler/scripts/run_weekly.sh (11:00 UTC Sunday = 20:00 KST)

cd /opt/g9/scheduler
source .env

echo "$(date): Running weekly preview" >> data/cron.log

/usr/bin/python3 schedule_manager.py weekly >> data/cron.log 2>&1

echo "$(date): Weekly preview complete" >> data/cron.log
