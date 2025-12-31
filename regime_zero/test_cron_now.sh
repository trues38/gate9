#!/bin/bash
# Quick Cron Test - runs immediately

# Use absolute path
LOG_FILE="/Users/js/g9/regime_zero/logs/cron_test.log"

# Create log directory if needed
mkdir -p /Users/js/g9/regime_zero/logs

{
    echo "================================================"
    echo "CRON TEST - $(date)"
    echo "================================================"
    echo "✅ Cron executed successfully!"
    echo "User: $(whoami)"
    echo "Working Directory: $(pwd)"
    echo "HOME: $HOME"
    echo "SHELL: $SHELL"
    echo ""

    # Test Python
    /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 --version 2>&1

    echo ""
    echo "✅ All cron permissions working!"
} >> "${LOG_FILE}" 2>&1
