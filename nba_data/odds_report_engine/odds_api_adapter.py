"""
The Odds API Adapter for NBA Betting Odds
Optimized for 500 credits/month budget
"""
import os
import requests
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

class OddsAPIAdapter:
    """
    The Odds API Client for NBA h2h (moneyline) and spreads

    Budget Strategy (500 credits/month):
    - Tier 1 (Critical): 8 games/day × 2 markets × 10 days = 160 credits
    - Tier 2 (Standard): 12 games/day × 2 markets × 10 days = 240 credits
    - Reserve: 100 credits for re-checks
    """

    API_HOST = "https://api.the-odds-api.com"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('ODDS_API_KEY')
        if not self.api_key:
            raise ValueError("ODDS_API_KEY not provided")

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'G9-Regime-Zero-NBA-Analytics/1.0'
        })

        # Budget tracking
        self.monthly_limit = 500
        self.call_count = 0

    def get_nba_odds(self, markets: List[str] = None, regions: str = 'us') -> Dict:
        """
        Fetch NBA odds for specified markets

        Args:
            markets: List of market types ['h2h', 'spreads', 'totals']
                    Default: ['h2h', 'spreads']
            regions: Bookmaker regions (default: 'us')

        Returns:
            Dict with odds data and metadata
        """
        if markets is None:
            markets = ['h2h', 'spreads']

        url = f"{self.API_HOST}/v4/sports/basketball_nba/odds"

        params = {
            'apiKey': self.api_key,
            'regions': regions,
            'markets': ','.join(markets),
            'oddsFormat': 'american',
            'dateFormat': 'iso'
        }

        print(f"[OddsAPI] Fetching NBA odds for markets: {markets}")

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            # Track API usage from response headers
            remaining = response.headers.get('x-requests-remaining')
            used = response.headers.get('x-requests-used')

            if remaining:
                print(f"[OddsAPI] Credits remaining: {remaining}")
            if used:
                print(f"[OddsAPI] Credits used this month: {used}")
                self.call_count = int(used)

            data = response.json()

            return {
                'success': True,
                'games': data,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'markets': markets,
                'credits_remaining': remaining,
                'credits_used': used
            }

        except requests.exceptions.RequestException as e:
            print(f"[OddsAPI] Error: {e}")
            return {
                'success': False,
                'error': str(e),
                'games': []
            }

    def get_game_odds(self, game_id: str) -> Optional[Dict]:
        """
        Get odds for a specific game by event_id
        Note: This is a filtered client-side operation, not a separate API call
        """
        all_odds = self.get_nba_odds()

        if not all_odds['success']:
            return None

        for game in all_odds['games']:
            if game.get('id') == game_id:
                return game

        return None

    def extract_best_odds(self, game: Dict) -> Dict:
        """
        Extract best available odds from multiple bookmakers

        Returns:
            {
                'h2h': {
                    'home': {'odds': -110, 'bookmaker': 'fanduel'},
                    'away': {'odds': +105, 'bookmaker': 'draftkings'}
                },
                'spreads': {
                    'home': {'point': -5.5, 'odds': -110, 'bookmaker': 'fanduel'},
                    'away': {'point': +5.5, 'odds': -110, 'bookmaker': 'draftkings'}
                }
            }
        """
        result = {}

        for bookmaker in game.get('bookmakers', []):
            bm_name = bookmaker['key']

            for market in bookmaker.get('markets', []):
                market_key = market['key']

                if market_key not in result:
                    result[market_key] = {}

                for outcome in market.get('outcomes', []):
                    team_name = outcome['name']

                    # Determine side (home/away/over/under)
                    if market_key == 'totals':
                        # For totals, use 'over' or 'under' as side
                        side = team_name.lower()  # 'Over' -> 'over', 'Under' -> 'under'
                    elif team_name == game['home_team']:
                        side = 'home'
                    elif team_name == game['away_team']:
                        side = 'away'
                    else:
                        continue

                    # Extract odds data
                    odds_data = {
                        'odds': outcome.get('price'),
                        'bookmaker': bm_name
                    }

                    # Add point for spreads and totals
                    if 'point' in outcome:
                        odds_data['point'] = outcome['point']

                    # Keep best odds (most favorable)
                    if side not in result[market_key]:
                        result[market_key][side] = odds_data
                    else:
                        # For positive odds, higher is better
                        # For negative odds, closer to 0 is better
                        current_odds = result[market_key][side]['odds']
                        new_odds = odds_data['odds']

                        if (new_odds > 0 and current_odds > 0 and new_odds > current_odds) or \
                           (new_odds < 0 and current_odds < 0 and new_odds > current_odds):
                            result[market_key][side] = odds_data

        return result

    def format_odds_for_report(self, game: Dict) -> str:
        """
        Format odds data into human-readable text for LLM report generation

        Returns:
            Formatted string with odds information
        """
        home_team = game.get('home_team', 'Unknown')
        away_team = game.get('away_team', 'Unknown')

        odds_data = self.extract_best_odds(game)

        lines = [
            f"=== BETTING ODDS ===",
            f"{away_team} @ {home_team}",
            f"Game Time: {game.get('commence_time', 'TBD')}",
            ""
        ]

        # Moneyline (h2h)
        if 'h2h' in odds_data:
            h2h = odds_data['h2h']
            lines.append("MONEYLINE (h2h):")

            if 'home' in h2h:
                lines.append(f"  {home_team}: {h2h['home']['odds']:+d} ({h2h['home']['bookmaker']})")
            if 'away' in h2h:
                lines.append(f"  {away_team}: {h2h['away']['odds']:+d} ({h2h['away']['bookmaker']})")
            lines.append("")

        # Spreads
        if 'spreads' in odds_data:
            spreads = odds_data['spreads']
            lines.append("SPREADS:")

            if 'home' in spreads:
                point = spreads['home'].get('point', 0)
                odds = spreads['home']['odds']
                lines.append(f"  {home_team}: {point:+.1f} ({odds:+d}) - {spreads['home']['bookmaker']}")

            if 'away' in spreads:
                point = spreads['away'].get('point', 0)
                odds = spreads['away']['odds']
                lines.append(f"  {away_team}: {point:+.1f} ({odds:+d}) - {spreads['away']['bookmaker']}")
            lines.append("")

        return '\n'.join(lines)

    def get_budget_status(self) -> Dict:
        """Get current API budget usage"""
        return {
            'monthly_limit': self.monthly_limit,
            'total_used': self.call_count,
            'remaining': self.monthly_limit - self.call_count,
            'usage_percent': round((self.call_count / self.monthly_limit) * 100, 1)
        }

    def save_odds_snapshot(self, filepath: str) -> bool:
        """
        Save current odds to JSON file for analysis
        """
        odds_data = self.get_nba_odds()

        if not odds_data['success']:
            return False

        try:
            with open(filepath, 'w') as f:
                json.dump(odds_data, f, indent=2)
            print(f"[OddsAPI] Saved snapshot to {filepath}")
            return True
        except Exception as e:
            print(f"[OddsAPI] Failed to save snapshot: {e}")
            return False


if __name__ == '__main__':
    # Quick test
    import sys

    if len(sys.argv) < 2:
        print("Usage: python odds_api_adapter.py <API_KEY>")
        sys.exit(1)

    adapter = OddsAPIAdapter(api_key=sys.argv[1])

    print("Fetching NBA odds...")
    result = adapter.get_nba_odds(markets=['h2h', 'spreads'])

    if result['success']:
        print(f"\nFound {len(result['games'])} games")

        for game in result['games'][:3]:  # Show first 3
            print("\n" + "="*60)
            print(adapter.format_odds_for_report(game))

        print("\n" + "="*60)
        budget = adapter.get_budget_status()
        print(f"Budget: {budget['total_used']}/{budget['monthly_limit']} ({budget['usage_percent']}%)")
    else:
        print(f"Error: {result.get('error')}")
