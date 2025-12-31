"""
Graph RAG + Odds Fusion Report Generator
Combines Neo4j graph analysis with real-time betting odds
"""
import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from odds_api_adapter import OddsAPIAdapter

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("[WARNING] neo4j driver not installed. Graph features disabled.")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("[WARNING] anthropic not installed. LLM report generation disabled.")


class GraphOddsReportGenerator:
    """
    Generate comprehensive betting reports combining:
    1. Neo4j graph analysis (historical patterns, regime detection)
    2. Real-time odds from The Odds API
    3. LLM synthesis (Claude)
    """

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "quickpass123",  # Updated password
        odds_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None
    ):
        # Neo4j connection
        if NEO4J_AVAILABLE:
            try:
                self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
                # Test connection
                with self.driver.session() as session:
                    session.run("RETURN 1")
                print("[Neo4j] ✅ 연결 성공")
            except Exception as e:
                print(f"[Neo4j] ⚠️ 연결 실패: {e}")
                self.driver = None
            print(f"[Neo4j] Connected to {neo4j_uri}")
        else:
            self.driver = None

        # Odds API
        if odds_api_key:
            self.odds_adapter = OddsAPIAdapter(api_key=odds_api_key)
        else:
            self.odds_adapter = None
            print("[WARNING] No Odds API key provided. Odds features disabled.")

        # Anthropic API
        if ANTHROPIC_AVAILABLE and anthropic_api_key:
            self.anthropic = anthropic.Anthropic(api_key=anthropic_api_key)
        else:
            self.anthropic = None

        self.reports_dir = "/Users/js/g9/nba_data/odds_reports"
        os.makedirs(self.reports_dir, exist_ok=True)

        # 🚀 OPTIMIZATION: Cache for odds snapshot (avoid multiple API calls)
        self.odds_cache = None
        self.odds_cache_timestamp = None

    def get_team_graph_context(self, team_abbr: str, days_back: int = 10) -> Dict:
        """
        Extract graph-based context for a team from Neo4j

        Returns:
            {
                'recent_form': [...],
                'regime_pattern': {...},
                'key_players': [...],
                'injuries': [...],
                'historical_performance': {...}
            }
        """
        if not self.driver:
            return {'error': 'Neo4j not available'}

        with self.driver.session() as session:
            # Recent form
            recent_games_query = """
            MATCH (t:Team {abbreviation: $team_abbr})-[r:PLAYED_IN]->(g:Game)
            WHERE g.date >= date() - duration({days: $days_back})
            RETURN g.date AS date, g.home_team AS home, g.away_team AS away,
                   g.home_score AS home_score, g.away_score AS away_score,
                   r.is_winner AS won
            ORDER BY g.date DESC
            LIMIT 10
            """

            recent_games = session.run(
                recent_games_query,
                team_abbr=team_abbr,
                days_back=days_back
            ).data()

            # Regime pattern (if exists)
            regime_query = """
            MATCH (t:Team {abbreviation: $team_abbr})-[:IN_REGIME]->(r:Regime)
            WHERE r.active = true OR r.end_date IS NULL
            RETURN r.regime_type AS type, r.start_date AS start,
                   r.confidence AS confidence, r.description AS description
            LIMIT 1
            """

            regime = session.run(regime_query, team_abbr=team_abbr).data()

            # Key players
            players_query = """
            MATCH (t:Team {abbreviation: $team_abbr})<-[:PLAYS_FOR]-(p:Player)
            WHERE p.active = true
            RETURN p.name AS name, p.position AS position,
                   p.ppg AS ppg, p.apg AS apg, p.rpg AS rpg
            ORDER BY p.ppg DESC
            LIMIT 5
            """

            players = session.run(players_query, team_abbr=team_abbr).data()

            return {
                'team': team_abbr,
                'recent_games': recent_games,
                'current_regime': regime[0] if regime else None,
                'key_players': players,
                'graph_available': True
            }

    def get_matchup_context(self, home_team: str, away_team: str) -> Dict:
        """
        Get comprehensive matchup context from graph

        Includes:
        - Head-to-head history
        - Both teams' recent forms
        - Regime analysis
        - Key matchup insights
        """
        if not self.driver:
            return {'error': 'Neo4j not available'}

        home_context = self.get_team_graph_context(home_team)
        away_context = self.get_team_graph_context(away_team)

        # Head-to-head
        with self.driver.session() as session:
            h2h_query = """
            MATCH (g:Game)
            WHERE (g.home_team = $home AND g.away_team = $away)
               OR (g.home_team = $away AND g.away_team = $home)
            AND g.date >= date() - duration({years: 2})
            RETURN g.date AS date, g.home_team AS home, g.away_team AS away,
                   g.home_score AS home_score, g.away_score AS away_score
            ORDER BY g.date DESC
            LIMIT 10
            """

            h2h_games = session.run(h2h_query, home=home_team, away=away_team).data()

        return {
            'home_team': home_context,
            'away_team': away_context,
            'head_to_head': h2h_games
        }

    def get_odds_for_matchup(self, home_team: str, away_team: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Get current betting odds for a specific matchup

        🚀 OPTIMIZED: Uses cached odds data if available (avoid redundant API calls)

        Args:
            home_team: Home team name or abbreviation
            away_team: Away team name or abbreviation
            use_cache: If True, use cached data; If False, force fresh API call
        """
        if not self.odds_adapter:
            return None

        # 🚀 Use cached data if available
        if use_cache and self.odds_cache:
            all_odds = self.odds_cache
            print(f"     → Using cached odds data (saved {datetime.now().timestamp() - self.odds_cache_timestamp:.0f}s ago)")
        else:
            # Fresh API call
            all_odds = self.odds_adapter.get_nba_odds(markets=['h2h', 'spreads'])

            # Cache the result
            if all_odds['success']:
                self.odds_cache = all_odds
                self.odds_cache_timestamp = datetime.now().timestamp()

        if not all_odds['success']:
            return None

        # Find matching game (fuzzy match on team names)
        for game in all_odds['games']:
            game_home = game['home_team'].upper()
            game_away = game['away_team'].upper()

            if home_team.upper() in game_home and away_team.upper() in game_away:
                return {
                    'game': game,
                    'best_odds': self.odds_adapter.extract_best_odds(game),
                    'formatted': self.odds_adapter.format_odds_for_report(game)
                }

        return None

    def generate_llm_report(
        self,
        matchup_context: Dict,
        odds_context: Optional[Dict],
        report_type: str = "detailed"
    ) -> str:
        """
        Generate LLM-powered betting analysis report

        Combines:
        1. Graph context (historical patterns, regimes, player stats)
        2. Odds context (current lines, market sentiment)
        3. Expert synthesis via Claude
        """
        if not self.anthropic:
            return self._generate_fallback_report(matchup_context, odds_context)

        # Build comprehensive prompt
        home = matchup_context['home_team']['team']
        away = matchup_context['away_team']['team']

        prompt = f"""You are an expert NBA betting analyst with access to proprietary graph-based regime analysis.

Generate a comprehensive betting report for:
**{away} @ {home}**

=== GRAPH ANALYSIS CONTEXT ===

HOME TEAM ({home}):
{json.dumps(matchup_context['home_team'], indent=2, default=str)}

AWAY TEAM ({away}):
{json.dumps(matchup_context['away_team'], indent=2, default=str)}

HEAD-TO-HEAD HISTORY:
{json.dumps(matchup_context['head_to_head'], indent=2, default=str)}

"""

        if odds_context:
            prompt += f"""
=== BETTING ODDS ===
{odds_context['formatted']}

Best Available Lines:
{json.dumps(odds_context['best_odds'], indent=2)}

"""

        prompt += """
=== YOUR TASK ===

Generate a structured betting analysis report with the following sections:

1. **EXECUTIVE SUMMARY** (2-3 sentences)
   - Key insight and recommended bet (if any)

2. **REGIME ANALYSIS**
   - Current regime patterns for both teams
   - Historical regime transitions and implications

3. **RECENT FORM**
   - Last 5-10 games analysis
   - Momentum indicators
   - Home/away splits

4. **KEY MATCHUP FACTORS**
   - Player matchups
   - Pace/style contrasts
   - Injuries/lineup changes

5. **ODDS EVALUATION**
   - Market positioning
   - Value opportunities
   - Line movement insights

6. **BETTING RECOMMENDATION**
   - Recommended plays (moneyline/spread/total)
   - Confidence level (HIGH/MEDIUM/LOW)
   - Risk assessment
   - Suggested bet sizing

7. **RISK FACTORS**
   - Key uncertainties
   - Scenarios that would invalidate the analysis

Format as **Markdown** with clear headers and bullet points.
Be direct and actionable. This is for professional bettors.
"""

        try:
            response = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return response.content[0].text

        except Exception as e:
            print(f"[LLM Error] {e}")
            return self._generate_fallback_report(matchup_context, odds_context)

    def _generate_fallback_report(self, matchup_context: Dict, odds_context: Optional[Dict]) -> str:
        """
        Generate basic report without LLM (fallback mode)
        """
        home = matchup_context['home_team']['team']
        away = matchup_context['away_team']['team']

        lines = [
            f"# Betting Report: {away} @ {home}",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            "",
            "## Graph Context",
            "",
            f"### {home} (Home)",
            json.dumps(matchup_context['home_team'], indent=2, default=str),
            "",
            f"### {away} (Away)",
            json.dumps(matchup_context['away_team'], indent=2, default=str),
            "",
        ]

        if odds_context:
            lines.extend([
                "## Betting Odds",
                "",
                odds_context['formatted'],
                ""
            ])

        lines.append("*Note: LLM analysis unavailable. Showing raw data only.*")

        return '\n'.join(lines)

    def generate_report_for_game(
        self,
        home_team: str,
        away_team: str,
        output_format: str = "markdown"
    ) -> Dict:
        """
        Generate complete report for a single game

        Returns:
            {
                'success': bool,
                'report': str (markdown/html),
                'metadata': {...}
            }
        """
        print(f"\n{'='*60}")
        print(f"Generating Report: {away_team} @ {home_team}")
        print(f"{'='*60}\n")

        # Step 1: Get graph context
        print("[1/3] Fetching graph context from Neo4j...")
        matchup_context = self.get_matchup_context(home_team, away_team)

        # Step 2: Get odds context
        print("[2/3] Fetching betting odds from The Odds API...")
        odds_context = self.get_odds_for_matchup(home_team, away_team)

        if odds_context:
            print(f"     ✓ Odds found")
        else:
            print(f"     ✗ No odds available for this matchup")

        # Step 3: Generate LLM report
        print("[3/3] Generating LLM analysis report...")
        report_text = self.generate_llm_report(matchup_context, odds_context)

        # Save Markdown report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.reports_dir}/report_{away_team}_at_{home_team}_{timestamp}.md"

        with open(filename, 'w') as f:
            f.write(report_text)

        print(f"\n✓ Report saved to: {filename}")

        # 🚀 OPTIMIZED: Save RAW DATA context only (no report text to save tokens)
        json_context = {
            "metadata": {
                "generated_at": timestamp,
                "generator": "graph_odds_report_v1",
                "stage1_complete": True
            },
            "game_info": {
                "home_team": home_team,
                "away_team": away_team,
                "game_time": odds_context['game']['commence_time'] if odds_context else None,
                "game_id": odds_context['game'].get('id') if odds_context else None
            },
            "odds": {
                "available": odds_context is not None,
                "moneyline": {
                    "home": odds_context['best_odds'].get('h2h', {}).get('home') if odds_context else None,
                    "away": odds_context['best_odds'].get('h2h', {}).get('away') if odds_context else None
                } if odds_context else None,
                "spreads": {
                    "home": odds_context['best_odds'].get('spreads', {}).get('home') if odds_context else None,
                    "away": odds_context['best_odds'].get('spreads', {}).get('away') if odds_context else None
                } if odds_context else None,
                "formatted_text": odds_context['formatted'] if odds_context else None
            },
            "team_stats": {
                "home": matchup_context.get('home_team') if matchup_context else None,
                "away": matchup_context.get('away_team') if matchup_context else None
            },
            "head_to_head": matchup_context.get('head_to_head', []) if matchup_context else [],
            "graph_data_available": matchup_context is not None,

            # 🔧 Main report는 별도 파일로 (토큰 절약)
            "main_report_file": filename
        }

        # Save JSON context
        json_filename = f"{self.reports_dir}/context_{away_team}_at_{home_team}_{timestamp}.json"
        with open(json_filename, 'w') as f:
            json.dump(json_context, f, indent=2, ensure_ascii=False, default=str)

        print(f"✓ Context JSON saved to: {json_filename}")

        return {
            'success': True,
            'report': report_text,
            'filepath': filename,
            'context_file': json_filename,  # 🚀 NEW: JSON 컨텍스트 파일
            'metadata': {
                'home_team': home_team,
                'away_team': away_team,
                'has_odds': odds_context is not None,
                'has_graph': matchup_context is not None,
                'timestamp': timestamp
            }
        }

    def generate_daily_report(self, date_str: Optional[str] = None) -> List[Dict]:
        """
        Generate reports for all games on a given date

        🚀 OPTIMIZED: Single API call for all games (snapshot approach)

        Args:
            date_str: Date in YYYY-MM-DD format (default: today)

        Returns:
            List of report results
        """
        if not self.odds_adapter:
            print("[ERROR] Odds API not available. Cannot fetch today's games.")
            return []

        print(f"\n{'='*60}")
        print(f"Generating Daily Reports")
        print(f"{'='*60}\n")

        # 🚀 OPTIMIZATION: Single API call to get ALL games (snapshot)
        print("[API] Fetching today's games snapshot (1 API call for all games)...")
        all_odds = self.odds_adapter.get_nba_odds()

        if not all_odds['success']:
            print(f"[ERROR] Failed to fetch odds: {all_odds.get('error')}")
            return []

        # 🚀 Cache the snapshot for subsequent use
        self.odds_cache = all_odds
        self.odds_cache_timestamp = datetime.now().timestamp()

        games = all_odds['games']
        print(f"✓ Found {len(games)} games")
        print(f"✓ Cached odds data (all subsequent calls will use cache)\n")

        results = []

        for i, game in enumerate(games, 1):
            home = game['home_team']
            away = game['away_team']

            print(f"\n[Game {i}/{len(games)}] {away} @ {home}")

            try:
                # 🚀 This will now use cached data (no additional API calls)
                result = self.generate_report_for_game(home, away)
                results.append(result)
            except Exception as e:
                print(f"[ERROR] Failed to generate report: {e}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'game': f"{away} @ {home}"
                })

        # Budget summary
        if self.odds_adapter:
            budget = self.odds_adapter.get_budget_status()
            print(f"\n{'='*60}")
            print(f"Budget Status: {budget['total_used']}/{budget['monthly_limit']} ({budget['usage_percent']}%)")
            print(f"{'='*60}\n")

        return results

    def close(self):
        """Close all connections"""
        if self.driver:
            self.driver.close()


def main():
    parser = argparse.ArgumentParser(description='Generate Graph + Odds Betting Reports')
    parser.add_argument('--home', type=str, help='Home team abbreviation (e.g., LAL)')
    parser.add_argument('--away', type=str, help='Away team abbreviation (e.g., GSW)')
    parser.add_argument('--daily', action='store_true', help='Generate reports for all today\'s games')
    parser.add_argument('--neo4j-uri', default='bolt://localhost:7687', help='Neo4j URI')
    parser.add_argument('--neo4j-user', default='neo4j', help='Neo4j username')
    parser.add_argument('--neo4j-password', required=True, help='Neo4j password')
    parser.add_argument('--odds-api-key', help='The Odds API key')
    parser.add_argument('--anthropic-api-key', help='Anthropic API key')

    args = parser.parse_args()

    # Initialize generator
    generator = GraphOddsReportGenerator(
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password,
        odds_api_key=args.odds_api_key or os.environ.get('ODDS_API_KEY'),
        anthropic_api_key=args.anthropic_api_key or os.environ.get('ANTHROPIC_API_KEY')
    )

    try:
        if args.daily:
            # Generate all daily reports
            results = generator.generate_daily_report()
            print(f"\nGenerated {len(results)} reports")

        elif args.home and args.away:
            # Generate single game report
            result = generator.generate_report_for_game(args.home, args.away)

            if result['success']:
                print("\n" + "="*60)
                print(result['report'])
                print("="*60)

        else:
            parser.print_help()

    finally:
        generator.close()


if __name__ == '__main__':
    main()
