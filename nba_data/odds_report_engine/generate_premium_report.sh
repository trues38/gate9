#!/bin/bash

##############################################
# 2-Stage Premium Report Pipeline
# Stage 1: Graph RAG + Odds → JSON
# Stage 2: AI Council → Premium Report
##############################################

set -e

echo "=========================================="
echo "G9 Premium NBA Betting Report Generator"
echo "=========================================="
echo ""

# Check environment
if [ -z "$ODDS_API_KEY" ]; then
    echo "ERROR: ODDS_API_KEY not set"
    exit 1
fi

if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "ERROR: OPENROUTER_API_KEY not set"
    echo "Run: export OPENROUTER_API_KEY='sk-or-v1-...'"
    exit 1
fi

# Parse arguments
if [ $# -ne 2 ]; then
    echo "Usage: $0 HOME_TEAM AWAY_TEAM"
    echo "Example: $0 TOR GSW"
    exit 1
fi

HOME=$1
AWAY=$2

echo "🏀 Matchup: $AWAY @ $HOME"
echo ""

# ==========================================
# STAGE 1: Graph RAG + Odds Report
# ==========================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STAGE 1: Generating Base Report"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Generate base report (without Graph if Neo4j not available)
python3 << EOF
import sys
sys.path.insert(0, '.')

from odds_api_adapter import OddsAPIAdapter
from generate_sample_report import generate_odds_only_report
import json
import os
from datetime import datetime

# Get odds
adapter = OddsAPIAdapter()
all_odds = adapter.get_nba_odds()

if not all_odds['success']:
    print(f"❌ Failed to fetch odds: {all_odds.get('error')}")
    sys.exit(1)

# Find game
found_game = None
for game in all_odds['games']:
    home_team = game['home_team']
    away_team = game['away_team']

    # Fuzzy match
    if ('$HOME'.upper() in home_team.upper() or home_team.upper() in '$HOME'.upper()) and \
       ('$AWAY'.upper() in away_team.upper() or away_team.upper() in '$AWAY'.upper()):
        found_game = game
        break

if not found_game:
    print(f"❌ Game not found: $AWAY @ $HOME")
    sys.exit(1)

print(f"✓ Found: {found_game['away_team']} @ {found_game['home_team']}")

# Generate report
report_text = generate_odds_only_report(found_game, adapter.extract_best_odds(found_game))

# Save context JSON
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
context = {
    "game_info": {
        "home_team": found_game['home_team'],
        "away_team": found_game['away_team'],
        "timestamp": timestamp,
        "game_time": found_game['commence_time']
    },
    "odds": {
        "available": True,
        "formatted": adapter.format_odds_for_report(found_game),
        "best_odds": adapter.extract_best_odds(found_game)
    },
    "graph_analysis": {
        "available": False,
        "note": "Neo4j graph data not available in this run"
    },
    "main_report": {
        "text": report_text,
        "type": "odds_only"
    }
}

# Save
reports_dir = '/Users/js/g9/nba_data/odds_reports'
os.makedirs(reports_dir, exist_ok=True)

json_file = f"{reports_dir}/context_{found_game['away_team'].replace(' ', '_')}_at_{found_game['home_team'].replace(' ', '_')}_{timestamp}.json"
with open(json_file, 'w') as f:
    json.dump(context, f, indent=2, ensure_ascii=False)

print(f"✓ Context JSON saved: {json_file}")

# Save filepath for Stage 2
with open('/tmp/stage1_output.txt', 'w') as f:
    f.write(json_file)

EOF

if [ $? -ne 0 ]; then
    echo "❌ Stage 1 failed"
    exit 1
fi

# Get Stage 1 output file
CONTEXT_FILE=$(cat /tmp/stage1_output.txt)

echo ""
echo "✅ Stage 1 Complete: $CONTEXT_FILE"
echo ""

# ==========================================
# STAGE 2: AI Council Analysis
# ==========================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STAGE 2: AI Council (5 Analysts)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 ai_betting_council.py --context-file "$CONTEXT_FILE"

if [ $? -ne 0 ]; then
    echo "❌ Stage 2 failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ PIPELINE COMPLETE"
echo "=========================================="
echo ""
echo "Reports saved in: /Users/js/g9/nba_data/odds_reports/"
ls -lht /Users/js/g9/nba_data/odds_reports/ | head -10
