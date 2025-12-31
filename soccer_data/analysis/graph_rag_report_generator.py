#!/usr/bin/env python3
"""
Graph RAG Enhanced Betting Report Generator

Integrates Neo4j Graph RAG context with SQLite quantitative data
to generate NBA-level contextual betting insights.

Key Features:
- Recent form trends (IMPROVING/DECLINING/STABLE)
- xG regression potential (HIGH/MEDIUM/LOW)
- Head-to-head analysis with xG context
- Referee bias analysis
- Tactical matchup insights

Author: G9 Soccer Analytics
Version: 2.0 (Graph RAG Integrated)
"""

import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from graph_rag.graph_queries import SoccerGraphRAG
    GRAPH_RAG_AVAILABLE = True
except ImportError:
    print("⚠️  Warning: Graph RAG not available. Install neo4j driver: pip install neo4j")
    GRAPH_RAG_AVAILABLE = False

# Paths
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "soccer.db"


def get_upcoming_matches(league: str = 'EPL', days_ahead: int = 7) -> List[Dict[str, Any]]:
    """
    Get upcoming matches for report generation

    For now, returns recent matches with strong xG signals
    In production, this would query an odds API for tomorrow's games
    """
    conn = sqlite3.connect(str(DB_PATH))

    query = """
    SELECT DISTINCT
        m.home_team_id as home_team,
        m.away_team_id as away_team,
        m.league,
        m.date as last_meeting
    FROM matches m
    JOIN match_stats ms_h ON m.match_id = ms_h.match_id AND ms_h.is_home = 1
    JOIN match_stats ms_a ON m.match_id = ms_a.match_id AND ms_a.is_home = 0
    WHERE m.league = ?
    AND ms_h.xg IS NOT NULL
    AND ms_a.xg IS NOT NULL
    ORDER BY m.date DESC
    LIMIT 10
    """

    cursor = conn.execute(query, (league,))
    matches = []

    for row in cursor.fetchall():
        # Capitalize team names to match Neo4j format
        home_team = row[0].replace('_', ' ').title()
        away_team = row[1].replace('_', ' ').title()

        matches.append({
            'home_team': home_team,
            'away_team': away_team,
            'league': row[2],
            'last_meeting': row[3]
        })

    conn.close()
    return matches


def generate_match_report(rag: SoccerGraphRAG, home_team: str, away_team: str,
                         referee: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate comprehensive match report using Graph RAG
    """

    # Extract full context from Graph RAG
    context = rag.extract_full_context(home_team, away_team, referee)

    # Build structured report
    report = {
        'matchup': f"{home_team} vs {away_team}",
        'home_team': home_team,
        'away_team': away_team,
        'referee': referee,
        'generated_at': datetime.now().isoformat(),

        # Form analysis
        'home_form': context.get('home_form', {}),
        'away_form': context.get('away_form', {}),

        # Regression potential
        'home_regression': context.get('home_regression', {}),
        'away_regression': context.get('away_regression', {}),

        # Head to head
        'head_to_head': context.get('head_to_head', []),

        # Tactical
        'tactical': context.get('tactical', {}),

        # Referee analysis
        'referee_analysis': {
            'overall_bias': context.get('referee_bias', {}),
            'home_record': context.get('home_referee_record', {}),
            'away_record': context.get('away_referee_record', {})
        } if referee else None,

        # Generate predictions
        'predictions': []
    }

    # Generate predictions based on Graph RAG context
    report['predictions'] = generate_predictions(report)

    return report


def generate_predictions(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate betting predictions using Graph RAG context

    This is much smarter than the old version - uses regression potential,
    form trends, and referee bias
    """
    predictions = []

    home_form = report['home_form']
    away_form = report['away_form']
    home_reg = report['home_regression']
    away_reg = report['away_regression']

    # Prediction 1: xG Regression Value Bet
    if home_reg.get('regression_potential') == 'HIGH':
        predictions.append({
            'type': f"{report['home_team']} to Score (O0.5 TT)",
            'confidence': 'HIGH',
            'reason': f"Strong xG regression signal ({home_reg.get('xG_diff', 0):.2f} goal deficit). "
                     f"Creating {home_form.get('recent_avg_xG', 0):.2f} xG/match but underperforming. "
                     f"Form: {home_form.get('trend', 'UNKNOWN')}",
            'market': 'Team Total Over 0.5',
            'value_score': 8.5
        })

    if away_reg.get('regression_potential') == 'HIGH':
        predictions.append({
            'type': f"{report['away_team']} to Score (O0.5 TT)",
            'confidence': 'HIGH',
            'reason': f"Strong xG regression signal ({away_reg.get('xG_diff', 0):.2f} goal deficit). "
                     f"Creating {away_form.get('recent_avg_xG', 0):.2f} xG/match but underperforming. "
                     f"Form: {away_form.get('trend', 'UNKNOWN')}",
            'market': 'Team Total Over 0.5',
            'value_score': 8.5
        })

    # Prediction 2: BTTS based on combined xG
    home_xg = home_form.get('recent_avg_xG', 0)
    away_xg = away_form.get('recent_avg_xG', 0)

    if home_xg > 1.2 and away_xg > 1.2:
        predictions.append({
            'type': 'Both Teams to Score',
            'confidence': 'MEDIUM' if (home_xg > 1.5 and away_xg > 1.5) else 'LOW',
            'reason': f"Both teams creating chances: {report['home_team']} {home_xg:.2f} xG, "
                     f"{report['away_team']} {away_xg:.2f} xG. "
                     f"Trends: {home_form.get('trend')} vs {away_form.get('trend')}",
            'market': 'BTTS',
            'value_score': 7.0 if (home_xg > 1.5 and away_xg > 1.5) else 5.5
        })

    # Prediction 3: Total goals (Over/Under)
    expected_goals = home_xg + away_xg

    if expected_goals > 2.8:
        predictions.append({
            'type': 'Over 2.5 Goals',
            'confidence': 'MEDIUM' if expected_goals > 3.2 else 'LOW',
            'reason': f"High combined xG: {expected_goals:.2f}. "
                     f"Both teams averaging good chances creation.",
            'market': 'Total Goals Over 2.5',
            'value_score': 7.5 if expected_goals > 3.2 else 6.0
        })
    elif expected_goals < 2.0:
        predictions.append({
            'type': 'Under 2.5 Goals',
            'confidence': 'LOW',
            'reason': f"Low combined xG: {expected_goals:.2f}. Defensive matchup expected.",
            'market': 'Total Goals Under 2.5',
            'value_score': 5.5
        })

    # Prediction 4: Form-based result prediction
    home_win_rate = home_form.get('win_rate', 0)
    away_win_rate = away_form.get('win_rate', 0)

    if home_form.get('trend') == 'IMPROVING' and away_form.get('trend') == 'DECLINING':
        predictions.append({
            'type': f"{report['home_team']} to Win",
            'confidence': 'MEDIUM',
            'reason': f"Form divergence: {report['home_team']} IMPROVING ({home_win_rate:.0f}% win rate) "
                     f"vs {report['away_team']} DECLINING ({away_win_rate:.0f}% win rate)",
            'market': 'Match Result (Home)',
            'value_score': 6.5
        })
    elif away_form.get('trend') == 'IMPROVING' and home_form.get('trend') == 'DECLINING':
        predictions.append({
            'type': f"{report['away_team']} to Win",
            'confidence': 'MEDIUM',
            'reason': f"Form divergence: {report['away_team']} IMPROVING ({away_win_rate:.0f}% win rate) "
                     f"vs {report['home_team']} DECLINING ({home_win_rate:.0f}% win rate)",
            'market': 'Match Result (Away)',
            'value_score': 6.5
        })

    # Sort by value score
    predictions.sort(key=lambda x: x.get('value_score', 0), reverse=True)

    return predictions


def format_markdown_report(reports: List[Dict[str, Any]], league: str) -> str:
    """
    Format reports as markdown with Graph RAG insights
    """
    lines = []

    # Header
    lines.append(f"# Graph RAG Enhanced Betting Report - {league}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Matches Analyzed:** {len(reports)}")
    lines.append(f"**Data Sources:** SQLite (Quantitative) + Neo4j (Graph RAG)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Executive Summary
    lines.append("## 📊 Executive Summary")
    lines.append("")

    high_value_bets = []
    for report in reports:
        for pred in report['predictions']:
            if pred.get('value_score', 0) >= 8.0:
                high_value_bets.append({
                    'matchup': report['matchup'],
                    'prediction': pred
                })

    if high_value_bets:
        lines.append("### 🔥 High Value Bets (Score ≥ 8.0)")
        lines.append("")
        for bet in high_value_bets:
            pred = bet['prediction']
            lines.append(f"**{bet['matchup']}**")
            lines.append(f"- **{pred['type']}** ({pred['confidence']}) - Value Score: {pred['value_score']:.1f}")
            lines.append(f"  - {pred['reason']}")
            lines.append("")
    else:
        lines.append("*No high-value bets identified in this analysis.*")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Individual match reports
    for report in reports:
        lines.extend(format_match_section(report))

    # Methodology
    lines.append("## 📖 Methodology")
    lines.append("")
    lines.append("### Graph RAG Context Extraction")
    lines.append("")
    lines.append("This report uses **Graph RAG** (Retrieval-Augmented Generation) to extract context from Neo4j:")
    lines.append("")
    lines.append("1. **Recent Form Analysis** (5-match window)")
    lines.append("   - xG creation trends (IMPROVING/DECLINING/STABLE)")
    lines.append("   - Win rate and result patterns")
    lines.append("   - Form trajectory comparison")
    lines.append("")
    lines.append("2. **xG Regression Potential** (15-match window)")
    lines.append("   - xG vs actual goals differential")
    lines.append("   - Regression likelihood (HIGH/MEDIUM/LOW)")
    lines.append("   - Overperformance/underperformance detection")
    lines.append("")
    lines.append("3. **Head-to-Head History**")
    lines.append("   - Recent matchup results with xG")
    lines.append("   - Historical patterns and trends")
    lines.append("")
    lines.append("4. **Referee Bias Analysis** (when available)")
    lines.append("   - Overall home/away tendencies")
    lines.append("   - Team-specific referee records")
    lines.append("")
    lines.append("### Value Scoring")
    lines.append("")
    lines.append("Each prediction is assigned a **Value Score (0-10)**:")
    lines.append("")
    lines.append("- **8.0-10.0**: 🔥 High-value bet (strong Graph RAG signals)")
    lines.append("- **6.0-7.9**: ⚡ Medium-value bet (good signals, moderate confidence)")
    lines.append("- **0-5.9**: 👀 Low-value bet (weak signals, informational only)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Report generated by G9 Soccer Analytics - Graph RAG v2.0*")
    lines.append("")

    return "\n".join(lines)


def format_match_section(report: Dict[str, Any]) -> List[str]:
    """Format individual match section"""
    lines = []

    lines.append(f"## {report['matchup']}")
    lines.append("")

    # Form Analysis
    lines.append("### 📈 Form Analysis (Graph RAG)")
    lines.append("")

    # Home team
    home_form = report['home_form']
    if home_form:
        trend_icon = "🔺" if home_form.get('trend') == 'IMPROVING' else "🔻" if home_form.get('trend') == 'DECLINING' else "➡️"
        lines.append(f"**{report['home_team']}** {trend_icon} {home_form.get('trend', 'UNKNOWN')}")
        lines.append(f"- Recent xG: {(home_form.get('recent_avg_xG') or 0):.2f}/match (last 5)")
        lines.append(f"- Recent goals: {(home_form.get('recent_goals') or 0):.2f}/match")
        lines.append(f"- Win rate: {(home_form.get('win_rate') or 0):.1f}%")
        lines.append(f"- Defensive xGA: {(home_form.get('recent_avg_xGA') or 0):.2f}/match")
        lines.append("")

    # Away team
    away_form = report['away_form']
    if away_form:
        trend_icon = "🔺" if away_form.get('trend') == 'IMPROVING' else "🔻" if away_form.get('trend') == 'DECLINING' else "➡️"
        lines.append(f"**{report['away_team']}** {trend_icon} {away_form.get('trend', 'UNKNOWN')}")
        lines.append(f"- Recent xG: {(away_form.get('recent_avg_xG') or 0):.2f}/match (last 5)")
        lines.append(f"- Recent goals: {(away_form.get('recent_goals') or 0):.2f}/match")
        lines.append(f"- Win rate: {(away_form.get('win_rate') or 0):.1f}%")
        lines.append(f"- Defensive xGA: {(away_form.get('recent_avg_xGA') or 0):.2f}/match")
        lines.append("")

    # Regression Potential
    lines.append("### 🎲 xG Regression Potential")
    lines.append("")

    home_reg = report['home_regression']
    away_reg = report['away_regression']

    if home_reg:
        potential = home_reg.get('regression_potential', 'UNKNOWN')
        potential_icon = "🔥" if potential == 'HIGH' else "⚡" if potential == 'MEDIUM' else "👀"
        lines.append(f"**{report['home_team']}**: {potential_icon} {potential}")
        xg_diff = home_reg.get('xG_diff') or 0
        lines.append(f"- xG differential: {xg_diff:.2f} goals (last 15 matches)")
        if xg_diff < 0:
            lines.append(f"  - *Unlucky: {abs(xg_diff):.2f} goals below expected*")
        lines.append("")

    if away_reg:
        potential = away_reg.get('regression_potential', 'UNKNOWN')
        potential_icon = "🔥" if potential == 'HIGH' else "⚡" if potential == 'MEDIUM' else "👀"
        lines.append(f"**{report['away_team']}**: {potential_icon} {potential}")
        xg_diff = away_reg.get('xG_diff') or 0
        lines.append(f"- xG differential: {xg_diff:.2f} goals (last 15 matches)")
        if xg_diff < 0:
            lines.append(f"  - *Unlucky: {abs(xg_diff):.2f} goals below expected*")
        lines.append("")

    # Head to Head
    h2h = report['head_to_head']
    if h2h:
        lines.append("### 🔄 Head-to-Head History")
        lines.append("")
        lines.append(f"**Last {len(h2h)} meetings:**")
        lines.append("")
        for match in h2h[:3]:  # Show last 3
            home_xg = match.get('home_xG') or 0
            away_xg = match.get('away_xG') or 0
            lines.append(f"- {match.get('date', 'N/A')}: "
                        f"{match.get('home_score', 0)}-{match.get('away_score', 0)} "
                        f"(xG: {home_xg:.2f}-{away_xg:.2f})")
        lines.append("")

    # Predictions
    if report['predictions']:
        lines.append("### 🎯 Betting Predictions")
        lines.append("")
        for pred in report['predictions'][:5]:  # Top 5 predictions
            confidence_icon = "🔥" if pred['confidence'] == 'HIGH' else "⚡" if pred['confidence'] == 'MEDIUM' else "👀"
            lines.append(f"**{confidence_icon} {pred['type']}** ({pred['confidence']}) - Value Score: {pred.get('value_score', 0):.1f}/10")
            lines.append(f"- Market: {pred.get('market', 'N/A')}")
            lines.append(f"- Reason: {pred['reason']}")
            lines.append("")

    lines.append("---")
    lines.append("")

    return lines


def main():
    """Main execution"""
    print("="*70)
    print("Graph RAG Enhanced Betting Report Generator")
    print("="*70)
    print()

    if not GRAPH_RAG_AVAILABLE:
        print("❌ Graph RAG not available. Please install: pip install neo4j")
        return

    # Initialize Graph RAG
    print("Step 1: Connecting to Neo4j Graph RAG...")
    try:
        rag = SoccerGraphRAG()
        print("✅ Connected to Neo4j")
        print()
    except Exception as e:
        print(f"❌ Failed to connect to Neo4j: {e}")
        print("   Make sure Neo4j is running on bolt://localhost:7689")
        return

    try:
        # Get matches to analyze
        print("Step 2: Loading matches...")
        league = 'EPL'  # Can be parameterized
        matches = get_upcoming_matches(league)
        print(f"✅ Found {len(matches)} matchups to analyze")
        print()

        # Generate reports
        print("Step 3: Extracting Graph RAG context...")
        reports = []

        for i, match in enumerate(matches[:5], 1):  # Limit to 5 for demo
            print(f"  [{i}/{min(5, len(matches))}] {match['home_team']} vs {match['away_team']}")
            try:
                report = generate_match_report(
                    rag,
                    match['home_team'],
                    match['away_team'],
                    referee=None  # Add referee if available
                )
                reports.append(report)
            except Exception as e:
                print(f"      ⚠️  Warning: {e}")
                continue

        print(f"✅ Generated {len(reports)} match reports")
        print()

        # Save reports
        print("Step 4: Saving reports...")
        output_dir = BASE_DIR / "analysis" / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)

        # JSON report
        json_path = output_dir / f"graphrag_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_path, 'w') as f:
            json.dump(reports, f, indent=2, default=str)
        print(f"✅ JSON: {json_path.name}")

        # Markdown report
        md_content = format_markdown_report(reports, league)
        md_path = output_dir / f"graphrag_{league.lower()}_{datetime.now().strftime('%Y%m%d')}.md"
        with open(md_path, 'w') as f:
            f.write(md_content)
        print(f"✅ Markdown: {md_path.name}")
        print()

        # Summary
        total_predictions = sum(len(r['predictions']) for r in reports)
        high_value = sum(1 for r in reports for p in r['predictions'] if p.get('value_score', 0) >= 8.0)

        print("="*70)
        print("✅ Graph RAG Report Generation Complete")
        print("="*70)
        print()
        print(f"📊 Summary:")
        print(f"   - Matches analyzed: {len(reports)}")
        print(f"   - Total predictions: {total_predictions}")
        print(f"   - High-value bets (≥8.0): {high_value}")
        print()
        print(f"📄 View report: cat {md_path}")
        print()

    finally:
        rag.close()


if __name__ == "__main__":
    main()
