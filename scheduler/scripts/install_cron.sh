#!/bin/bash
# Install crontab entries for G9 Schedule Manager

echo "Installing G9 Schedule Manager cron jobs..."

# Make scripts executable
chmod +x /opt/g9/scheduler/scripts/*.sh

# Add to crontab
(crontab -l 2>/dev/null; echo "") | crontab -

# Monthly collection (25th of each month, midnight KST = 15:00 UTC previous day)
(crontab -l 2>/dev/null; echo "0 15 24 * * /opt/g9/scheduler/scripts/run_monthly.sh") | crontab -

# Daily briefing (06:30 KST = 21:30 UTC previous day)
(crontab -l 2>/dev/null; echo "30 21 * * * /opt/g9/scheduler/scripts/run_daily.sh") | crontab -

# Weekly preview (Sunday 20:00 KST = Sunday 11:00 UTC)
(crontab -l 2>/dev/null; echo "0 11 * * 0 /opt/g9/scheduler/scripts/run_weekly.sh") | crontab -

echo "✅ Cron jobs installed!"
echo ""
echo "Current crontab:"
crontab -l
