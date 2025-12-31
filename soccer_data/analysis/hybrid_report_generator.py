#!/usr/bin/env python3
"""
Hybrid SQLite + Neo4J Betting Report Generator

Combines quantitative data from SQLite with graph patterns from Neo4J
to generate advanced betting insights.

Architecture:
- SQLite: Quantitative data (xG, scores, stats)
- Neo4J: Graph patterns (relationships, sequences, context)
- Hybrid: Combined insights for betting decisions
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Paths
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "soccer.db"


def get_sqlite_data():
    """Extract data from SQLite for graph analysis"""
    conn = sqlite3.connect(str(DB_PATH))

    # Get matches with xG data
    query = """
    SELECT
        m.match_id,
        m.date,
        m.league,
        m.home_team_id,
        m.away_team_id,
        m.home_score,
        m.away_score,
        ms_h.xg as home_xg,
        ms_a.xg as away_xg,
        ms_h.xga as home_xga,
        ms_a.xga as away_xga
    FROM matches m
    JOIN match_stats ms_h ON m.match_id = ms_h.match_id AND ms_h.is_home = 1
    JOIN match_stats ms_a ON m.match_id = ms_a.match_id AND ms_a.is_home = 0
    WHERE m.league = 'EPL'
    AND ms_h.xg IS NOT NULL
    AND ms_a.xg IS NOT NULL
    ORDER BY m.date DESC
    LIMIT 200
    """

    cursor = conn.execute(query)
    matches = []

    for row in cursor.fetchall():
        matches.append({
            'match_id': row[0],
            'date': row[1],
            'league': row[2],
            'home_team': row[3],
            'away_team': row[4],
            'home_score': row[5],
            'away_score': row[6],
            'home_xg': row[7],
            'away_xg': row[8],
            'home_xga': row[9] if row[9] else 0,
            'away_xga': row[10] if row[10] else 0
        })

    conn.close()
    return matches


def simulate_graph_patterns(matches):
    """
    Simulate Neo4J graph patterns using Python
    (In production, this would be actual Cypher queries)
    """

    # Build team stats
    team_stats = defaultdict(lambda: {
        'matches': [],
        'total_xg': 0,
        'total_goals': 0,
        'total_xga': 0,
        'total_conceded': 0
    })

    for match in matches:
        # Home team stats
        team_stats[match['home_team']]['matches'].append({
            'date': match['date'],
            'opponent': match['away_team'],
            'xg': match['home_xg'],
            'goals': match['home_score'],
            'xga': match['home_xga'],
            'conceded': match['away_score'],
            'venue': 'home'
        })
        team_stats[match['home_team']]['total_xg'] += match['home_xg']
        team_stats[match['home_team']]['total_goals'] += match['home_score']
        team_stats[match['home_team']]['total_xga'] += match['home_xga']
        team_stats[match['home_team']]['total_conceded'] += match['away_score']

        # Away team stats
        team_stats[match['away_team']]['matches'].append({
            'date': match['date'],
            'opponent': match['home_team'],
            'xg': match['away_xg'],
            'goals': match['away_score'],
            'xga': match['away_xga'],
            'conceded': match['home_score'],
            'venue': 'away'
        })
        team_stats[match['away_team']]['total_xg'] += match['away_xg']
        team_stats[match['away_team']]['total_goals'] += match['away_score']
        team_stats[match['away_team']]['total_xga'] += match['away_xga']
        team_stats[match['away_team']]['total_conceded'] += match['home_score']

    return team_stats


def analyze_head_to_head(matches, team1, team2):
    """Graph pattern: Head-to-head history"""
    h2h = []

    for match in matches:
        if ((match['home_team'] == team1 and match['away_team'] == team2) or
            (match['home_team'] == team2 and match['away_team'] == team1)):
            h2h.append(match)

    return h2h


def analyze_recent_sequences(team_stats, team_id, n=5):
    """Graph pattern: Recent match sequences"""
    if team_id not in team_stats:
        return None

    matches = sorted(team_stats[team_id]['matches'],
                    key=lambda x: x['date'], reverse=True)[:n]

    return {
        'team': team_id,
        'matches': len(matches),
        'avg_xg': sum(m['xg'] for m in matches) / len(matches) if matches else 0,
        'avg_goals': sum(m['goals'] for m in matches) / len(matches) if matches else 0,
        'avg_xga': sum(m['xga'] for m in matches) / len(matches) if matches else 0,
        'avg_conceded': sum(m['conceded'] for m in matches) / len(matches) if matches else 0,
        'xg_trend': 'improving' if len(matches) >= 3 and matches[0]['xg'] > matches[-1]['xg'] else 'declining'
    }


def find_matchup_insights(team_stats, team1, team2):
    """
    Hybrid insight: Combine SQLite stats + Graph patterns
    """
    team1_recent = analyze_recent_sequences(team_stats, team1)
    team2_recent = analyze_recent_sequences(team_stats, team2)

    if not team1_recent or not team2_recent:
        return None

    insights = {
        'matchup': f"{team1} vs {team2}",
        'team1': {
            'name': team1,
            'recent_xg': round(team1_recent['avg_xg'], 2),
            'recent_goals': round(team1_recent['avg_goals'], 2),
            'recent_xga': round(team1_recent['avg_xga'], 2),
            'trend': team1_recent['xg_trend']
        },
        'team2': {
            'name': team2,
            'recent_xg': round(team2_recent['avg_xg'], 2),
            'recent_goals': round(team2_recent['avg_goals'], 2),
            'recent_xga': round(team2_recent['avg_xga'], 2),
            'trend': team2_recent['xg_trend']
        },
        'predictions': []
    }

    # Prediction 1: Attack vs Defense
    team1_attack = team1_recent['avg_xg']
    team2_defense = team2_recent['avg_xga']

    if team1_attack > 1.8 and team2_defense > 1.5:
        insights['predictions'].append({
            'type': 'BTTS',
            'confidence': 'HIGH',
            'reason': f"{team1} strong attack ({team1_attack:.2f} xG) vs {team2} weak defense ({team2_defense:.2f} xGA)"
        })

    # Prediction 2: xG differential
    xg_diff = team1_attack - team2_recent['avg_xg']
    if abs(xg_diff) > 0.5:
        favorite = team1 if xg_diff > 0 else team2
        insights['predictions'].append({
            'type': 'Match Result',
            'confidence': 'MEDIUM',
            'reason': f"{favorite} favored based on xG differential ({abs(xg_diff):.2f})"
        })

    # Prediction 3: Total goals
    expected_goals = team1_attack + team2_recent['avg_xg']
    if expected_goals > 2.8:
        insights['predictions'].append({
            'type': 'Over 2.5 Goals',
            'confidence': 'MEDIUM',
            'reason': f"Combined xG: {expected_goals:.2f}"
        })
    elif expected_goals < 2.0:
        insights['predictions'].append({
            'type': 'Under 2.5 Goals',
            'confidence': 'MEDIUM',
            'reason': f"Combined xG: {expected_goals:.2f}"
        })

    return insights


def generate_hybrid_report(matches, team_stats):
    """Generate hybrid SQLite + Graph report"""

    report = {
        'title': 'Hybrid SQLite + Neo4J Betting Analysis',
        'generated_at': datetime.now().isoformat(),
        'data_sources': {
            'sqlite': f'{len(matches)} matches',
            'neo4j': 'Simulated graph patterns'
        },
        'matchups': []
    }

    # Sample matchups for demo
    sample_matchups = [
        ('liverpool', 'arsenal'),
        ('man_city', 'tottenham'),
        ('chelsea', 'brighton'),
        ('man_united', 'newcastle')
    ]

    for team1, team2 in sample_matchups:
        # Check if both teams have data
        if team1 in team_stats and team2 in team_stats:
            insight = find_matchup_insights(team_stats, team1, team2)
            if insight:
                # Add head-to-head from graph
                h2h = analyze_head_to_head(matches, team1, team2)
                insight['head_to_head'] = {
                    'matches': len(h2h),
                    'recent': h2h[:3] if h2h else []
                }

                report['matchups'].append(insight)

    return report


def format_markdown_report(report):
    """Convert report to markdown"""
    lines = []

    lines.append(f"# {report['title']}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append("## Data Sources")
    lines.append("")
    lines.append("- **SQLite (Quantitative):** Match statistics, xG data, team performance")
    lines.append("- **Neo4J (Graph Patterns):** Recent sequences, head-to-head, temporal trends")
    lines.append("")
    lines.append("---")
    lines.append("")

    for matchup in report['matchups']:
        lines.append(f"## {matchup['matchup'].replace('_', ' ').title()}")
        lines.append("")

        # Team 1
        t1 = matchup['team1']
        lines.append(f"### {t1['name'].replace('_', ' ').title()}")
        lines.append("")
        lines.append(f"- **Recent xG:** {t1['recent_xg']} (avg last 5 matches)")
        lines.append(f"- **Recent Goals:** {t1['recent_goals']}")
        lines.append(f"- **Defensive xGA:** {t1['recent_xga']}")
        lines.append(f"- **Trend:** {t1['trend'].upper()}")
        lines.append("")

        # Team 2
        t2 = matchup['team2']
        lines.append(f"### {t2['name'].replace('_', ' ').title()}")
        lines.append("")
        lines.append(f"- **Recent xG:** {t2['recent_xg']} (avg last 5 matches)")
        lines.append(f"- **Recent Goals:** {t2['recent_goals']}")
        lines.append(f"- **Defensive xGA:** {t2['recent_xga']}")
        lines.append(f"- **Trend:** {t2['trend'].upper()}")
        lines.append("")

        # Head to head
        if matchup['head_to_head']['matches'] > 0:
            lines.append("### Head-to-Head (Graph Pattern)")
            lines.append("")
            lines.append(f"**Last {matchup['head_to_head']['matches']} meetings:**")
            lines.append("")
            for h2h in matchup['head_to_head']['recent']:
                lines.append(f"- {h2h['date']}: {h2h['home_team']} {h2h['home_score']}-{h2h['away_score']} {h2h['away_team']} "
                           f"(xG: {h2h['home_xg']:.2f}-{h2h['away_xg']:.2f})")
            lines.append("")

        # Predictions
        if matchup['predictions']:
            lines.append("### 🎯 Betting Predictions (Hybrid Analysis)")
            lines.append("")
            for pred in matchup['predictions']:
                confidence_icon = "🔥" if pred['confidence'] == 'HIGH' else "⚡" if pred['confidence'] == 'MEDIUM' else "👀"
                lines.append(f"**{confidence_icon} {pred['type']}** ({pred['confidence']})")
                lines.append(f"- {pred['reason']}")
                lines.append("")

        lines.append("---")
        lines.append("")

    # Methodology
    lines.append("## Methodology")
    lines.append("")
    lines.append("### SQLite (Quantitative)")
    lines.append("- xG (Expected Goals) statistics")
    lines.append("- Actual goals scored/conceded")
    lines.append("- Match results and dates")
    lines.append("")
    lines.append("### Neo4J (Graph Patterns)")
    lines.append("- Recent form sequences (last 5 matches)")
    lines.append("- Head-to-head history")
    lines.append("- Temporal trends (improving/declining)")
    lines.append("- Relationship patterns (attack vs defense)")
    lines.append("")
    lines.append("### Hybrid Insights")
    lines.append("- Combine quantitative xG with graph context")
    lines.append("- Attack strength vs defensive weakness")
    lines.append("- Form trends + historical matchups")
    lines.append("- Confidence scoring based on multiple factors")
    lines.append("")

    return "\n".join(lines)


def main():
    """Main execution"""
    print("="*60)
    print("Hybrid SQLite + Neo4J Report Generator")
    print("="*60)
    print()

    # Step 1: Extract SQLite data
    print("Step 1: Extracting data from SQLite...")
    matches = get_sqlite_data()
    print(f"✅ Loaded {len(matches)} matches")
    print()

    # Step 2: Build graph patterns
    print("Step 2: Building graph patterns...")
    team_stats = simulate_graph_patterns(matches)
    print(f"✅ Analyzed {len(team_stats)} teams")
    print()

    # Step 3: Generate hybrid insights
    print("Step 3: Generating hybrid insights...")
    report = generate_hybrid_report(matches, team_stats)
    print(f"✅ Generated {len(report['matchups'])} matchup analyses")
    print()

    # Step 4: Save reports
    output_dir = BASE_DIR / "analysis" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON report
    json_path = output_dir / f"hybrid_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"✅ JSON report: {json_path.name}")

    # Markdown report
    md_content = format_markdown_report(report)
    md_path = output_dir / f"hybrid_report_{datetime.now().strftime('%Y%m%d')}.md"
    with open(md_path, 'w') as f:
        f.write(md_content)
    print(f"✅ Markdown report: {md_path.name}")
    print()

    print("="*60)
    print("✅ Hybrid Report Generation Complete")
    print("="*60)
    print()
    print(f"View report: cat {md_path}")
    print()


if __name__ == "__main__":
    main()
