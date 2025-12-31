#!/usr/bin/env python3
"""
xG Betting Report Generator

Converts xG analysis JSON to readable markdown betting reports
"""

import json
from pathlib import Path
from datetime import datetime


def format_team_name(team_id):
    """Format team ID to readable name"""
    # Convert underscore to space and title case
    return team_id.replace('_', ' ').title()


def generate_performance_section(performance_data):
    """Generate xG performance section"""
    lines = []

    lines.append("## 📊 xG Performance Analysis")
    lines.append("")
    lines.append("Teams scoring significantly more/less than their xG. **Mean reversion expected.**")
    lines.append("")

    # Overperformers (likely to regress)
    overperformers = [t for t in performance_data if t['status'] == 'overperforming']
    if overperformers:
        lines.append("### 🔴 Overperforming (Regression Risk)")
        lines.append("")
        lines.append("| Team | Matches | Actual | xG | Diff | Performance |")
        lines.append("|------|---------|--------|----|----- |-------------|")

        for team in overperformers[:10]:
            lines.append(
                f"| {format_team_name(team['team'])} | "
                f"{team['matches']} | "
                f"{team['actual_goals']} | "
                f"{team['expected_goals']} | "
                f"**+{team['xg_diff']}** | "
                f"+{team['performance_pct']}% |"
            )
        lines.append("")
        lines.append("**Betting Insight:** These teams are scoring MORE than expected. "
                    "They may score LESS in upcoming matches (regression to mean).")
        lines.append("")

    # Underperformers (value bet opportunities)
    underperformers = [t for t in performance_data if t['status'] == 'underperforming']
    if underperformers:
        lines.append("### 🟢 Underperforming (Value Bet Opportunities)")
        lines.append("")
        lines.append("| Team | Matches | Actual | xG | Diff | Performance |")
        lines.append("|------|---------|--------|----|----- |-------------|")

        # Sort by worst underperformers first
        underperformers_sorted = sorted(underperformers, key=lambda x: x['xg_diff'])

        for team in underperformers_sorted[:10]:
            lines.append(
                f"| {format_team_name(team['team'])} | "
                f"{team['matches']} | "
                f"{team['actual_goals']} | "
                f"{team['expected_goals']} | "
                f"**{team['xg_diff']}** | "
                f"{team['performance_pct']}% |"
            )
        lines.append("")
        lines.append("**Betting Insight:** These teams are scoring LESS than expected. "
                    "They may score MORE in upcoming matches (regression to mean). **VALUE BETS.**")
        lines.append("")

    return "\n".join(lines)


def generate_form_section(form_data):
    """Generate recent form section"""
    lines = []

    lines.append("## 🔥 Recent Form (Last 5 Matches)")
    lines.append("")

    # Top xG creators
    top_xg = sorted(form_data, key=lambda x: x['avg_xg'], reverse=True)[:10]

    lines.append("### ⚡ Strongest Attack (xG Created)")
    lines.append("")
    lines.append("| Team | Avg xG | Avg Goals | Avg xGA | Form |")
    lines.append("|------|--------|-----------|---------|------|")

    for team in top_xg:
        form_indicator = "🔥" if team['avg_xg'] > 1.8 else "✅" if team['avg_xg'] > 1.3 else "⚠️"
        lines.append(
            f"| {format_team_name(team['team'])} | "
            f"**{team['avg_xg']}** | "
            f"{team['avg_goals']} | "
            f"{team['avg_xga']} | "
            f"{form_indicator} |"
        )
    lines.append("")

    # Weakest defense (highest xGA)
    weak_defense = sorted(form_data, key=lambda x: x['avg_xga'], reverse=True)[:10]

    lines.append("### 🚨 Weakest Defense (xG Conceded)")
    lines.append("")
    lines.append("| Team | Avg xGA | Avg Conceded | Avg xG | Defense |")
    lines.append("|------|---------|--------------|--------|---------|")

    for team in weak_defense:
        defense_indicator = "🚨" if team['avg_xga'] > 1.8 else "⚠️" if team['avg_xga'] > 1.3 else "✅"
        lines.append(
            f"| {format_team_name(team['team'])} | "
            f"**{team['avg_xga']}** | "
            f"{team['avg_conceded']} | "
            f"{team['avg_xg']} | "
            f"{defense_indicator} |"
        )
    lines.append("")
    lines.append("**Betting Insight:** Teams with weak defense (high xGA) are likely to concede. "
                "Back opponents to score or over 2.5 goals.")
    lines.append("")

    return "\n".join(lines)


def generate_home_away_section(home_away_data):
    """Generate home/away split section"""
    lines = []

    lines.append("## 🏠 Home vs Away Performance")
    lines.append("")

    # Home advantage teams
    home_teams = [t for t in home_away_data if t.get('home_advantage', False)][:10]

    if home_teams:
        lines.append("### 🏠 Strong Home Teams")
        lines.append("")
        lines.append("| Team | Home xG | Away xG | Difference |")
        lines.append("|------|---------|---------|------------|")

        for team in home_teams:
            lines.append(
                f"| {format_team_name(team['team'])} | "
                f"**{team['home_xg']}** | "
                f"{team['away_xg']} | "
                f"+{team['home_away_diff']} |"
            )
        lines.append("")
        lines.append("**Betting Insight:** Back these teams when playing at HOME.")
        lines.append("")

    # Away advantage teams
    away_teams = [t for t in home_away_data if t.get('away_advantage', False)][:10]

    if away_teams:
        lines.append("### ✈️ Strong Away Teams")
        lines.append("")
        lines.append("| Team | Away xG | Home xG | Difference |")
        lines.append("|------|---------|---------|------------|")

        for team in away_teams:
            lines.append(
                f"| {format_team_name(team['team'])} | "
                f"**{team['away_xg']}** | "
                f"{team['home_xg']} | "
                f"{abs(team['home_away_diff'])} |"
            )
        lines.append("")
        lines.append("**Betting Insight:** Back these teams even when playing AWAY.")
        lines.append("")

    return "\n".join(lines)


def generate_value_bets_section(value_bets):
    """Generate value bets section"""
    lines = []

    lines.append("## 💰 Value Bet Opportunities")
    lines.append("")

    if not value_bets:
        lines.append("No strong value bets identified at this time.")
        lines.append("")
        return "\n".join(lines)

    lines.append("Teams creating chances but not converting. **Expected to score more soon.**")
    lines.append("")

    lines.append("| Team | xG Diff | Recent xG | Recent Goals | Recommendation |")
    lines.append("|------|---------|-----------|--------------|----------------|")

    for bet in value_bets[:10]:
        rec_icon = "🔥" if bet['recommendation'] == 'BACK TO SCORE' else "👀"
        lines.append(
            f"| {format_team_name(bet['team'])} | "
            f"**{bet['xg_diff']}** | "
            f"{bet['recent_avg_xg']} | "
            f"{bet['recent_avg_goals']} | "
            f"{rec_icon} {bet['recommendation']} |"
        )

    lines.append("")
    lines.append("**Betting Strategy:**")
    lines.append("- 🔥 **BACK TO SCORE**: Strong value bets (xG diff < -3)")
    lines.append("- 👀 **MONITOR**: Watch these teams closely")
    lines.append("")

    return "\n".join(lines)


def generate_league_report(league, analysis_data):
    """Generate report for a single league"""
    lines = []

    # Header
    lines.append(f"# {league} xG Betting Analysis")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Performance section
    lines.append(generate_performance_section(analysis_data['performance']))
    lines.append("")

    # Form section
    lines.append(generate_form_section(analysis_data['recent_form']))
    lines.append("")

    # Home/Away section
    lines.append(generate_home_away_section(analysis_data['home_away']))
    lines.append("")

    # Value bets section
    lines.append(generate_value_bets_section(analysis_data['value_bets']))
    lines.append("")

    return "\n".join(lines)


def generate_summary_report(all_analysis):
    """Generate summary report across all leagues"""
    lines = []

    # Header
    lines.append("# xG Betting Analysis - All Leagues Summary")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Top value bets across all leagues
    lines.append("## 🔥 Top Value Bets (All Leagues)")
    lines.append("")

    all_value_bets = []
    for league, analysis in all_analysis.items():
        for bet in analysis['value_bets']:
            bet_copy = bet.copy()
            bet_copy['league'] = league
            all_value_bets.append(bet_copy)

    # Sort by xG diff (most underperforming)
    all_value_bets.sort(key=lambda x: x['xg_diff'])

    if all_value_bets:
        lines.append("| League | Team | xG Diff | Recent xG | Recommendation |")
        lines.append("|--------|------|---------|-----------|----------------|")

        for bet in all_value_bets[:15]:
            rec_icon = "🔥" if bet['recommendation'] == 'BACK TO SCORE' else "👀"
            lines.append(
                f"| **{bet['league']}** | "
                f"{format_team_name(bet['team'])} | "
                f"**{bet['xg_diff']}** | "
                f"{bet['recent_avg_xg']} | "
                f"{rec_icon} {bet['recommendation']} |"
            )
    else:
        lines.append("No value bets found.")

    lines.append("")
    lines.append("---")
    lines.append("")

    # League-by-league summaries
    for league in ['EPL', 'LaLiga', 'Bundesliga', 'SerieA', 'Ligue1']:
        if league not in all_analysis:
            continue

        analysis = all_analysis[league]

        lines.append(f"## {league}")
        lines.append("")

        # Top overperformer
        overperformers = [t for t in analysis['performance'] if t['status'] == 'overperforming']
        if overperformers:
            top = overperformers[0]
            lines.append(f"🔴 **Top Overperformer:** {format_team_name(top['team'])} "
                        f"({top['xg_diff']:+.1f} goals vs xG)")

        # Top underperformer
        underperformers = [t for t in analysis['performance'] if t['status'] == 'underperforming']
        if underperformers:
            under = sorted(underperformers, key=lambda x: x['xg_diff'])[0]
            lines.append(f"🟢 **Top Underperformer:** {format_team_name(under['team'])} "
                        f"({under['xg_diff']:+.1f} goals vs xG)")

        # Best attack
        if analysis['recent_form']:
            best_attack = max(analysis['recent_form'], key=lambda x: x['avg_xg'])
            lines.append(f"⚡ **Strongest Attack:** {format_team_name(best_attack['team'])} "
                        f"({best_attack['avg_xg']} xG per game)")

        lines.append("")

    return "\n".join(lines)


def main():
    """Main report generation"""
    # Find latest analysis JSON
    base_dir = Path(__file__).parent.parent
    reports_dir = base_dir / "analysis" / "reports"

    json_files = list(reports_dir.glob("xg_analysis_*.json"))
    if not json_files:
        print("❌ No analysis JSON found. Run xg_betting_analyzer.py first.")
        return

    # Use latest
    latest_json = max(json_files, key=lambda p: p.stat().st_mtime)
    print(f"Loading analysis from: {latest_json.name}")

    # Load analysis
    with open(latest_json) as f:
        all_analysis = json.load(f)

    # Generate summary report
    print("\nGenerating summary report...")
    summary = generate_summary_report(all_analysis)
    summary_path = reports_dir / f"xg_summary_{datetime.now().strftime('%Y%m%d')}.md"
    with open(summary_path, 'w') as f:
        f.write(summary)
    print(f"✅ Summary report: {summary_path.name}")

    # Generate league-specific reports
    for league, analysis in all_analysis.items():
        print(f"Generating {league} report...")
        report = generate_league_report(league, analysis)
        report_path = reports_dir / f"xg_{league.lower()}_{datetime.now().strftime('%Y%m%d')}.md"
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"✅ {league} report: {report_path.name}")

    print("\n" + "="*60)
    print("✅ All reports generated")
    print("="*60)


if __name__ == "__main__":
    main()
