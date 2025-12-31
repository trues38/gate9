#!/bin/bash
# Monthly Schedule Collection
# Runs on 25th of each month to prepare next month
# Cron: 0 0 25 * * /opt/g9/scheduler/scripts/run_monthly.sh

cd /opt/g9/scheduler
source .env

echo "$(date): Running monthly collection" >> data/cron.log

/usr/bin/python3 schedule_manager.py monthly >> data/cron.log 2>&1

echo "$(date): Monthly collection complete" >> data/cron.log
