#!/bin/bash

##############################################
# NBA Betting Report Generator with Council Toggle
# Usage:
#   ./generate_report_with_council.sh HOME AWAY              # Stage 1 + 2 (Full)
#   ./generate_report_with_council.sh HOME AWAY --skip-council  # Stage 1 only
##############################################

set -e

# Parse arguments
SKIP_COUNCIL=false

if [ $# -lt 2 ]; then
    echo "Usage: $0 HOME_TEAM AWAY_TEAM [--skip-council]"
    echo ""
    echo "Examples:"
    echo "  $0 TOR GSW                  # Full pipeline (Stage 1 + 2)"
    echo "  $0 TOR GSW --skip-council   # Stage 1 only (skip AI Council)"
    exit 1
fi

HOME_TEAM=$1
AWAY_TEAM=$2

# Check for --skip-council flag
if [ $# -ge 3 ] && [ "$3" == "--skip-council" ]; then
    SKIP_COUNCIL=true
fi

echo "=========================================="
echo "NBA Betting Report Generator"
echo "=========================================="
echo ""
echo "Matchup: $AWAY_TEAM @ $HOME_TEAM"
echo "AI Council: $([ "$SKIP_COUNCIL" = true ] && echo "DISABLED" || echo "ENABLED")"
echo ""

# Check environment
if [ -z "$ODDS_API_KEY" ]; then
    echo "ERROR: ODDS_API_KEY not set"
    exit 1
fi

if [ "$SKIP_COUNCIL" = false ] && [ -z "$OPENROUTER_API_KEY" ]; then
    echo "ERROR: OPENROUTER_API_KEY not set (required for AI Council)"
    echo "Run: export OPENROUTER_API_KEY='sk-or-v1-...'"
    exit 1
fi

# ==========================================
# STAGE 1: Graph RAG + Odds → JSON Context
# ==========================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STAGE 1: Generating Base Report (Raw Data)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

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

# Find game - improved fuzzy matching
def team_matches(search_term, team_name):
    """Check if search_term matches team_name (handles abbreviations)"""
    search = search_term.upper()
    team = team_name.upper()

    # Direct substring match
    if search in team or team in search:
        return True

    # Check if search is abbreviation (e.g., "GSW" = "Golden State Warriors")
    if len(search) <= 5:
        words = team.split()
        # Try first letters of words
        initials = ''.join([w[0] for w in words if w])
        if search == initials:
            return True
        # Try matching any word
        if any(search in word for word in words):
            return True

    return False

found_game = None
for game in all_odds['games']:
    home_team = game['home_team']
    away_team = game['away_team']

    # Fuzzy match with abbreviation support
    if team_matches('$HOME_TEAM', home_team) and team_matches('$AWAY_TEAM', away_team):
        found_game = game
        break

if not found_game:
    print(f"❌ Game not found: $AWAY_TEAM @ $HOME_TEAM")
    sys.exit(1)

print(f"✓ Found: {found_game['away_team']} @ {found_game['home_team']}")

# Generate base report
report_text = generate_odds_only_report(found_game, adapter.extract_best_odds(found_game))

# Save report
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
reports_dir = '/Users/js/g9/nba_data/odds_reports'
os.makedirs(reports_dir, exist_ok=True)

report_file = f"{reports_dir}/report_{found_game['away_team'].replace(' ', '_')}_at_{found_game['home_team'].replace(' ', '_')}_{timestamp}.md"
with open(report_file, 'w') as f:
    f.write(report_text)

print(f"✓ Base report saved: {report_file}")

# Save RAW DATA context (no report text to save tokens)
best_odds = adapter.extract_best_odds(found_game)
context = {
    "metadata": {
        "generated_at": timestamp,
        "generator": "odds_report_v1",
        "stage1_complete": True
    },
    "game_info": {
        "home_team": found_game['home_team'],
        "away_team": found_game['away_team'],
        "timestamp": timestamp,
        "game_time": found_game['commence_time'],
        "game_id": found_game.get('id')
    },
    "odds": {
        "available": True,
        "moneyline": {
            "home": best_odds.get('h2h', {}).get('home'),
            "away": best_odds.get('h2h', {}).get('away')
        },
        "spreads": {
            "home": best_odds.get('spreads', {}).get('home'),
            "away": best_odds.get('spreads', {}).get('away')
        },
        "formatted_text": adapter.format_odds_for_report(found_game)
    },
    "team_stats": {
        "home": None,  # Graph RAG would populate this
        "away": None
    },
    "head_to_head": [],
    "graph_data_available": False,
    "main_report_file": report_file
}

# Save context JSON
json_file = f"{reports_dir}/context_{found_game['away_team'].replace(' ', '_')}_at_{found_game['home_team'].replace(' ', '_')}_{timestamp}.json"
with open(json_file, 'w') as f:
    json.dump(context, f, indent=2, ensure_ascii=False)

print(f"✓ Context JSON saved: {json_file}")
print(f"   → RAW DATA only (메인 리포트 텍스트 제외, 토큰 절약)")

# Save filepath for Stage 2
with open('/tmp/stage1_output.txt', 'w') as f:
    f.write(json_file)

EOF

if [ $? -ne 0 ]; then
    echo "❌ Stage 1 failed"
    exit 1
fi

CONTEXT_FILE=$(cat /tmp/stage1_output.txt)
echo ""
echo "✅ Stage 1 Complete"
echo ""

# ==========================================
# STAGE 2: AI Council (Optional)
# ==========================================

if [ "$SKIP_COUNCIL" = true ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "STAGE 2: SKIPPED (--skip-council flag)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Base report generated without AI Council."
    echo "To enable AI Council, run without --skip-council flag."
else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "STAGE 2: AI Council (5 Analysts)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    python3 ai_betting_council.py --context-file "$CONTEXT_FILE"

    if [ $? -ne 0 ]; then
        echo "❌ Stage 2 failed (AI Council)"
        echo "   Base report is still available"
        exit 1
    fi

    echo ""
    echo "✅ Stage 2 Complete (AI Council)"
fi

echo ""
echo "=========================================="
echo "✅ PIPELINE COMPLETE"
echo "=========================================="
echo ""
echo "Reports saved in: /Users/js/g9/nba_data/odds_reports/"
ls -lht /Users/js/g9/nba_data/odds_reports/ | grep -E "$(date +%Y%m%d)" | head -10
