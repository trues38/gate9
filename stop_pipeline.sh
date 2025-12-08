#!/bin/bash

echo "🛑 Stopping News Pipeline..."

# Find PID of run_news_pipeline.py
PID=$(pgrep -f "run_news_pipeline.py")

if [ -z "$PID" ]; then
    echo "⚠️  Pipeline is not running."
else
    kill $PID
    echo "✅ Pipeline stopped (PID: $PID)."
fi
