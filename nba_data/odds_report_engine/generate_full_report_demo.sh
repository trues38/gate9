#!/bin/bash

##############################################
# 완성형 NBA Betting Report (DEMO)
# Graph RAG (샘플) + Odds API + AI Council
##############################################

set -e

if [ $# -lt 2 ]; then
    echo "Usage: $0 HOME_TEAM AWAY_TEAM"
    echo ""
    echo "Example:"
    echo "  $0 TOR GSW"
    exit 1
fi

HOME_TEAM=$1
AWAY_TEAM=$2

echo "=========================================="
echo "NBA 완성형 베팅 리포트 (DEMO)"
echo "=========================================="
echo ""
echo "Matchup: $AWAY_TEAM @ $HOME_TEAM"
echo ""

# Check environment
if [ -z "$ODDS_API_KEY" ]; then
    echo "ERROR: ODDS_API_KEY not set"
    exit 1
fi

if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "ERROR: OPENROUTER_API_KEY not set"
    exit 1
fi

# ==========================================
# STAGE 1: Graph RAG + Odds → Full Report
# ==========================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STAGE 1: Generating Full Report (Graph RAG + Odds)"
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

HOME_TEAM = "$HOME_TEAM"
AWAY_TEAM = "$AWAY_TEAM"

# Get odds
adapter = OddsAPIAdapter()
all_odds = adapter.get_nba_odds()

if not all_odds['success']:
    print(f"❌ Failed to fetch odds: {all_odds.get('error')}")
    sys.exit(1)

# Find game with improved matching
def team_matches(search_term, team_name):
    search = search_term.upper()
    team = team_name.upper()

    if search in team or team in search:
        return True

    if len(search) <= 5:
        words = team.split()
        initials = ''.join([w[0] for w in words if w])
        if search == initials:
            return True
        if any(search in word for word in words):
            return True

    return False

found_game = None
for game in all_odds['games']:
    home_team = game['home_team']
    away_team = game['away_team']

    if team_matches(HOME_TEAM, home_team) and team_matches(AWAY_TEAM, away_team):
        found_game = game
        break

if not found_game:
    print(f"❌ Game not found: $AWAY_TEAM @ $HOME_TEAM")
    sys.exit(1)

print(f"✓ Found: {found_game['away_team']} @ {found_game['home_team']}")

# Generate full report with sample Graph RAG data
best_odds = adapter.extract_best_odds(found_game)

# Sample Graph RAG data (simulated)
graph_data = {
    "home_team": {
        "name": found_game['home_team'],
        "recent_form": "3-7 (last 10)",
        "avg_points": 112.3,
        "avg_margin": -5.1,
        "home_record": "8-12",
        "regime": "DECLINE (12 games, 87% confidence)",
        "key_players": [
            {"name": "RJ Barrett", "ppg": 21.5, "status": "Questionable (ankle)"},
            {"name": "Jakob Poeltl", "rpg": 9.8, "status": "OUT (illness)"}
        ]
    },
    "away_team": {
        "name": found_game['away_team'],
        "recent_form": "8-2 (last 10)",
        "avg_points": 118.7,
        "avg_margin": +6.8,
        "away_record": "9-8",
        "regime": "ROAD_DOMINANCE (8 games, 91% confidence)",
        "key_players": [
            {"name": "Stephen Curry", "ppg": 22.8, "status": "Day-to-Day (ankle)"},
            {"name": "Andrew Wiggins", "ppg": 17.2, "status": "Active"}
        ]
    },
    "head_to_head": [
        {"date": "2024-12-01", "home_score": 102, "away_score": 115, "spread_result": "Away covered"},
        {"date": "2024-10-15", "home_score": 98, "away_score": 110, "spread_result": "Away covered"},
        {"date": "2024-03-20", "home_score": 105, "away_score": 108, "spread_result": "Away covered"}
    ],
    "matchup_notes": [
        "Warriors have won last 3 matchups vs Raptors",
        "Average margin: Warriors +12.3",
        "Raptors 0-7 ATS at home this month"
    ]
}

# Generate comprehensive report
report_text = f"""# 🏀 NBA 완성형 베팅 리포트
## {found_game['away_team']} @ {found_game['home_team']}

**Game Time**: {found_game['commence_time']}
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Report Type**: Full Analysis (Graph RAG + Odds + AI Council)

---

## 📊 EXECUTIVE SUMMARY

**Market Favorite**: {found_game['away_team']} (Moneyline: {best_odds['h2h']['away']['odds']})
**Spread**: {found_game['away_team']} {best_odds['spreads']['away']['point']}
**Key Insight**: {graph_data['away_team']['regime']} vs {graph_data['home_team']['regime']}

---

## 🎯 REGIME ANALYSIS (Graph RAG)

### {graph_data['home_team']['name']} (Home)

**Current Regime**: {graph_data['home_team']['regime']}
**Recent Form**: {graph_data['home_team']['recent_form']}
**Home Record**: {graph_data['home_team']['home_record']}
**Avg Points**: {graph_data['home_team']['avg_points']}
**Avg Margin**: {graph_data['home_team']['avg_margin']}

**Key Players**:
"""

for player in graph_data['home_team']['key_players']:
    report_text += f"- {player['name']}: {player.get('ppg', player.get('rpg', 'N/A'))} | {player['status']}\n"

report_text += f"""
### {graph_data['away_team']['name']} (Away)

**Current Regime**: {graph_data['away_team']['regime']}
**Recent Form**: {graph_data['away_team']['recent_form']}
**Away Record**: {graph_data['away_team']['away_record']}
**Avg Points**: {graph_data['away_team']['avg_points']}
**Avg Margin**: {graph_data['away_team']['avg_margin']}

**Key Players**:
"""

for player in graph_data['away_team']['key_players']:
    report_text += f"- {player['name']}: {player.get('ppg', 'N/A')} PPG | {player['status']}\n"

report_text += f"""
---

## 📈 HEAD-TO-HEAD ANALYSIS

**Last 3 Matchups**:
"""

for h2h in graph_data['head_to_head']:
    report_text += f"- {h2h['date']}: {h2h['home_score']}-{h2h['away_score']} ({h2h['spread_result']})\n"

report_text += f"""
**Matchup Notes**:
"""
for note in graph_data['matchup_notes']:
    report_text += f"- {note}\n"

report_text += f"""
---

## 💰 CURRENT BETTING LINES

### Moneyline
- {found_game['home_team']}: {best_odds['h2h']['home']['odds']} ({best_odds['h2h']['home']['bookmaker']})
- {found_game['away_team']}: {best_odds['h2h']['away']['odds']} ({best_odds['h2h']['away']['bookmaker']})

### Spreads
- {found_game['home_team']}: {best_odds['spreads']['home']['point']} @ {best_odds['spreads']['home']['odds']} ({best_odds['spreads']['home']['bookmaker']})
- {found_game['away_team']}: {best_odds['spreads']['away']['point']} @ {best_odds['spreads']['away']['odds']} ({best_odds['spreads']['away']['bookmaker']})

---

## 🎲 GRAPH RAG RECOMMENDATION

**Primary Play**: {found_game['away_team']} {best_odds['spreads']['away']['point']}

**Rationale**:
1. {graph_data['away_team']['regime']} favors road performance
2. Last 3 H2H: {found_game['away_team']} covered all spreads
3. {graph_data['home_team']['name']} in {graph_data['home_team']['regime']}
4. Key injury impact: {graph_data['home_team']['key_players'][1]['name']} OUT

**Confidence**: HIGH (based on regime alignment + H2H pattern)
**Suggested Bet Size**: 2 units

---

## ⚠️ RISK FACTORS

1. **{graph_data['away_team']['key_players'][0]['name']}**: {graph_data['away_team']['key_players'][0]['status']} - Monitor pre-game
2. **{graph_data['home_team']['name']} home desperation**: May fight harder after poor home stretch
3. **Public betting**: Likely 70%+ on {found_game['away_team']} (sharp vs public)

---

## 🔄 NEXT STEPS (Before AI Council)

1. Check {graph_data['away_team']['key_players'][0]['name']} status (30 min before tip-off)
2. Monitor line movement for sharp money indicators
3. Proceed to AI Council for multi-perspective analysis

---

*Stage 1 Complete - Proceeding to AI Council*
"""

# Save report
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
reports_dir = '/Users/js/g9/nba_data/odds_reports'
os.makedirs(reports_dir, exist_ok=True)

report_file = f"{reports_dir}/full_report_{found_game['away_team'].replace(' ', '_')}_at_{found_game['home_team'].replace(' ', '_')}_{timestamp}.md"
with open(report_file, 'w') as f:
    f.write(report_text)

print(f"✓ Full report saved: {report_file}")

# Save enhanced context with Graph RAG data
context = {
    "metadata": {
        "generated_at": timestamp,
        "generator": "full_report_v1",
        "stage1_complete": True,
        "graph_rag_enabled": True
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
    "team_stats": graph_data,
    "head_to_head": graph_data['head_to_head'],
    "graph_data_available": True,
    "main_report_file": report_file
}

json_file = f"{reports_dir}/context_full_{found_game['away_team'].replace(' ', '_')}_at_{found_game['home_team'].replace(' ', '_')}_{timestamp}.json"
with open(json_file, 'w') as f:
    json.dump(context, f, indent=2, ensure_ascii=False)

print(f"✓ Context JSON saved: {json_file}")
print(f"   → Graph RAG data included (샘플 데이터)")

# Save filepath for Stage 2
with open('/tmp/stage1_full_output.txt', 'w') as f:
    f.write(json_file)

EOF

if [ $? -ne 0 ]; then
    echo "❌ Stage 1 failed"
    exit 1
fi

CONTEXT_FILE=$(cat /tmp/stage1_full_output.txt)
echo ""
echo "✅ Stage 1 Complete (Graph RAG + Odds)"
echo ""

# ==========================================
# STAGE 2: AI Council
# ==========================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STAGE 2: AI Council (5 Analysts)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 ai_betting_council.py --context-file "$CONTEXT_FILE"

if [ $? -ne 0 ]; then
    echo "❌ Stage 2 failed (AI Council)"
    echo "   Full report is still available"
    exit 1
fi

echo ""
echo "✅ Stage 2 Complete (AI Council)"

echo ""
echo "=========================================="
echo "✅ 완성형 리포트 생성 완료!"
echo "=========================================="
echo ""
echo "Reports saved in: /Users/js/g9/nba_data/odds_reports/"
ls -lht /Users/js/g9/nba_data/odds_reports/ | grep -E "$(date +%Y%m%d)" | head -10
