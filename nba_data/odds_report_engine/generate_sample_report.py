"""
Generate sample report without Neo4j (odds-only mode)
"""
import os
import json
from datetime import datetime
from odds_api_adapter import OddsAPIAdapter

def generate_odds_only_report(game_data, best_odds):
    """Generate comprehensive report using only odds data"""

    home_team = game_data['home_team']
    away_team = game_data['away_team']
    game_time = game_data['commence_time']

    # Extract odds
    h2h = best_odds.get('h2h', {})
    spreads = best_odds.get('spreads', {})

    home_ml = h2h.get('home', {}).get('odds', 0)
    away_ml = h2h.get('away', {}).get('odds', 0)
    home_spread = spreads.get('home', {}).get('point', 0)
    away_spread = spreads.get('away', {}).get('point', 0)
    home_spread_odds = spreads.get('home', {}).get('odds', -110)
    away_spread_odds = spreads.get('away', {}).get('odds', -110)

    # Calculate implied probabilities
    if away_ml < 0:
        away_prob = abs(away_ml) / (abs(away_ml) + 100) * 100
    else:
        away_prob = 100 / (away_ml + 100) * 100

    if home_ml < 0:
        home_prob = abs(home_ml) / (abs(home_ml) + 100) * 100
    else:
        home_prob = 100 / (home_ml + 100) * 100

    # Determine favorite
    if away_ml < home_ml:
        favorite = away_team
        underdog = home_team
        fav_ml = away_ml
        dog_ml = home_ml
    else:
        favorite = home_team
        underdog = away_team
        fav_ml = home_ml
        dog_ml = away_ml

    report = f"""# 🏀 NBA Betting Analysis Report

## {away_team} @ {home_team}

**Game Time**: {game_time}
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Report Type**: Odds-Only Analysis (Neo4j graph data not available)

---

## 📊 EXECUTIVE SUMMARY

The betting market has set **{favorite}** as the favorite with a moneyline of **{fav_ml:+d}**.
The spread is set at **{away_spread:+.1f}** points, indicating market expects {abs(away_spread):.1f}-point margin.

**Quick Take**:
- Market Favorite: **{favorite}** (Implied probability: {max(away_prob, home_prob):.1f}%)
- Spread: **{away_team} {away_spread:+.1f}** vs **{home_team} {home_spread:+.1f}**
- Key Factor: This is a road game for {away_team}

---

## 💰 CURRENT BETTING LINES

### Moneyline (h2h)

| Team | Odds | Implied Prob | Bookmaker |
|------|------|--------------|-----------|
| **{away_team}** | {away_ml:+d} | {away_prob:.1f}% | {h2h.get('away', {}).get('bookmaker', 'N/A')} |
| **{home_team}** | {home_ml:+d} | {home_prob:.1f}% | {h2h.get('home', {}).get('bookmaker', 'N/A')} |

### Spreads

| Team | Spread | Odds | Bookmaker |
|------|--------|------|-----------|
| **{away_team}** | {away_spread:+.1f} | {away_spread_odds:+d} | {spreads.get('away', {}).get('bookmaker', 'N/A')} |
| **{home_team}** | {home_spread:+.1f} | {home_spread_odds:+d} | {spreads.get('home', {}).get('bookmaker', 'N/A')} |

---

## 🎯 ODDS ANALYSIS

### Market Positioning

The **{favorite}** is favored by {abs(away_spread):.1f} points according to the spread market.

**Implied Win Probabilities**:
- {away_team}: **{away_prob:.1f}%**
- {home_team}: **{home_prob:.1f}%**

**Vig/Juice**: Total implied probability = {(away_prob + home_prob):.1f}% (Overround: {(away_prob + home_prob - 100):.1f}%)

### Value Assessment

"""

    # Value analysis
    if away_spread < -3:
        report += f"""
**{away_team}** is giving significant points ({away_spread:+.1f}), suggesting:
- Strong road performance expected by oddsmakers
- Public likely backing the favorite
- Consider underdog value if {home_team} has home court advantage

"""
    elif away_spread > 3:
        report += f"""
**{home_team}** is favored by {abs(home_spread):.1f} points at home, indicating:
- Strong home court advantage
- {away_team} struggling on the road (per market consensus)
- Fade-the-public opportunity if line movement suggests sharp money on {away_team}

"""
    else:
        report += f"""
This is a **close spread** ({abs(away_spread):.1f} points), suggesting:
- Market sees this as a competitive matchup
- Small edge to {favorite}
- Moneyline might offer better value than spread
- Look for player props and totals

"""

    # Spread odds analysis
    if away_spread_odds != -110 or home_spread_odds != -110:
        report += f"""
### Spread Juice Analysis

Standard spread odds are -110 on both sides. Deviations indicate:
- {away_team} {away_spread:+.1f}: **{away_spread_odds:+d}** {'(better than standard)' if away_spread_odds > -110 else '(worse than standard)'}
- {home_team} {home_spread:+.1f}: **{home_spread_odds:+d}** {'(better than standard)' if home_spread_odds > -110 else '(worse than standard)'}

"""

    report += """---

## 🎲 BETTING RECOMMENDATIONS

### PRIMARY PLAY
"""

    # Generate recommendation based on odds
    if abs(away_spread) <= 3:
        report += f"""
**Moneyline on {underdog}** @ {dog_ml:+d}

**Rationale**: Close spread suggests competitive game. Underdog moneyline offers value in tight matchups.

**Confidence**: MEDIUM
**Suggested Bet Size**: 0.5-1 unit
"""
    else:
        report += f"""
**{favorite} {-abs(away_spread):+.1f}** @ {away_spread_odds if abs(away_spread_odds) < abs(home_spread_odds) else home_spread_odds:+d}

**Rationale**: Clear market favorite with {abs(away_spread):.1f}-point spread. Follow the sharp money.

**Confidence**: MEDIUM
**Suggested Bet Size**: 1 unit
"""

    report += """
### ALTERNATE PLAYS

**1st Half Spread**: Consider betting the 1H spread at roughly half the full game spread
**Player Props**: Look for over/under on key players (data not available in this report)
**Live Betting**: Monitor first quarter performance for in-game opportunities

---

## ⚠️ RISK FACTORS

### Key Uncertainties

1. **Lineup Changes**: Check injury reports 30 min before tip-off
2. **Back-to-Back Games**: Verify if either team played yesterday (fatigue factor)
3. **Rest Advantage**: Team with more rest often performs better
4. **Home/Away Splits**: Road favorites can be overvalued
5. **Public Betting %**: If >70% on one side, consider contrarian play

### Scenarios That Would Invalidate Analysis

- **Late Scratches**: Star player injury before game
- **Line Movement**: If spread moves 2+ points, re-evaluate
- **Weather/Arena Issues**: Unlikely in NBA but check for emergencies
- **Motivation Factors**: End-of-season scenarios, playoff implications

---

## 📈 ADVANCED METRICS (Graph Data Not Available)

*The following analysis requires Neo4j graph database connection:*

- ❌ Team Regime Patterns (uptrend/downtrend detection)
- ❌ Head-to-Head Historical Performance
- ❌ Player Matchup Analytics
- ❌ Recent Form & Momentum Indicators
- ❌ Coaching Strategy Patterns

**To enable full analysis**: Connect to Neo4j database with historical NBA data

---

## 🔄 NEXT STEPS

1. **Verify Lineups**: Check official team Twitter 30 min before game
2. **Monitor Line Movement**: Use live odds tracker for sharp money indicators
3. **Check News**: Injury reports, coaching changes, team news
4. **Set Alerts**: Significant line moves (2+ points) or injury news
5. **Track Results**: Record bet and outcome for ROI analysis

---

## 📝 DISCLAIMER

This report is for **informational and educational purposes only**.
Betting involves risk. Never wager more than you can afford to lose.

**Data Sources**:
- Odds: The Odds API (Real-time betting lines)
- Graph Analytics: Not available (requires Neo4j connection)

**Report Generated By**: G9 Regime Zero - NBA Odds Report Engine
**Version**: 1.0 (Odds-Only Mode)

---

*For full regime analysis with historical patterns, player stats, and AI-powered insights, configure Neo4j graph database and Anthropic API.*
"""

    return report


if __name__ == '__main__':
    # Load saved game data
    with open('/tmp/warriors_raptors_odds.json', 'r') as f:
        data = json.load(f)

    # Generate report
    report = generate_odds_only_report(data['game'], data['best_odds'])

    # Save to file
    output_dir = '/Users/js/g9/nba_data/odds_reports'
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{output_dir}/sample_report_GSW_TOR_{timestamp}.md"

    with open(filename, 'w') as f:
        f.write(report)

    print("="*60)
    print("✓ Sample Report Generated!")
    print("="*60)
    print(f"\nFile: {filename}\n")
    print("Preview:")
    print("="*60)
    print(report)
