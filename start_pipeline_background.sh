#!/bin/bash

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if already running
if pgrep -f "run_news_pipeline.py" > /dev/null; then
    echo "⚠️  Pipeline is already running!"
    echo "To stop it, run: ./stop_pipeline.sh (I will create this for you)"
    exit 1
fi

echo "🚀 Starting News Pipeline in Background..."
echo "Logs will be saved to: $DIR/pipeline.log"

# Run with nohup
nohup python3 "$DIR/run_news_pipeline.py" > "$DIR/pipeline.log" 2>&1 &

echo "✅ Pipeline started! PID: $!"
echo "You can now close this terminal."
