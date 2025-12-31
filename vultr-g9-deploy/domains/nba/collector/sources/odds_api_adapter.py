"""
The Odds API Adapter - 500 free calls/month

Key Features:
- Tier 1: All games (1 snapshot at T-1h) = 160 calls/month
- Tier 2: Top 5 games (3 snapshots: open/mid/close) = 240 calls/month
- Total: ~400 calls/month (well within 500 limit!)

Strategy:
- Opening line: T-24h (09:00 EST)
- Mid line: T-3h (15:00 EST)
- Closing line: T-1h (30min before game)

Data Structure:
- Moneyline (h2h): Home/Away odds
- Spread: Home/Away spread + odds
- Total: Over/Under line + odds
"""

import os
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class OddsSnapshot:
    """Single odds snapshot at a point in time"""
    # ID
    odds_id: str  # game_id_timestamp
    game_id: str

    # Timestamp
    collected_at: datetime
    time_to_game_minutes: int  # negative = before game
    snapshot_type: str  # "open" / "mid" / "close"

    # Teams
    home_team: str
    away_team: str
    commence_time: datetime

    # Moneyline
    home_ml: Optional[int] = None
    away_ml: Optional[int] = None

    # Spread
    home_spread: Optional[float] = None
    home_spread_odds: Optional[int] = None
    away_spread: Optional[float] = None
    away_spread_odds: Optional[int] = None

    # Total
    total_line: Optional[float] = None
    over_odds: Optional[int] = None
    under_odds: Optional[int] = None

    # Metadata
    bookmaker: str = "fanduel"
    source_api: str = "the-odds-api"
    api_last_update: Optional[datetime] = None


class OddsAPIAdapter:
    """
    The Odds API Adapter for G9 NBA Betting Analysis

    Philosophy:
    - Tier 1: All games (baseline for reports)
    - Tier 2: Top games (time series for analysis)
    - Track budget carefully (500/month)
    """

    # API Configuration
    API_BASE = "https://api.the-odds-api.com/v4"
    SPORT = "basketball_nba"
    MONTHLY_LIMIT = 500

    def __init__(self):
        self.api_key = os.getenv("ODDS_API_KEY")

        # Budget tracking
        self.monthly_calls = 0
        self.tier1_used = 0  # All games baseline
        self.tier2_used = 0  # Top games time series

        # Budget allocation
        self.tier1_budget = 200  # 160 expected + buffer
        self.tier2_budget = 250  # 240 expected + buffer

        # Mock mode check
        self.mock_mode = not self.api_key or self.api_key == ""

        if self.mock_mode:
            logger.warning("ODDS_API_KEY not set - using mock mode")
        else:
            logger.info(f"Using The Odds API: {self.API_BASE}")

        logger.info(f"OddsAPIAdapter initialized (mock={self.mock_mode})")
        logger.info(f"Budget: Tier1={self.tier1_budget}, Tier2={self.tier2_budget}")

    def can_call(self, tier: str = "tier1") -> bool:
        """Check if we can make a call within budget"""
        if self.mock_mode:
            return True

        if tier == "tier1":
            return self.tier1_used < self.tier1_budget
        elif tier == "tier2":
            return self.tier2_used < self.tier2_budget
        else:
            return self.monthly_calls < self.MONTHLY_LIMIT

    def fetch_current_odds(
        self,
        game_ids: List[str] = None,
        tier: str = "tier1",
        snapshot_type: str = "close"
    ) -> List[OddsSnapshot]:
        """
        Fetch current odds for NBA games

        Args:
            game_ids: ESPN game IDs (optional - if None, fetches all games)
            tier: "tier1" (all games) or "tier2" (top games only)
            snapshot_type: "open" / "mid" / "close"

        Returns:
            List of OddsSnapshot objects
        """
        if self.mock_mode:
            logger.warning("Mock mode - returning sample data")
            return self._get_mock_odds()

        if not self.can_call(tier):
            logger.warning(f"Budget exceeded for {tier}")
            return []

        try:
            # API Request
            url = f"{self.API_BASE}/sports/{self.SPORT}/odds/"
            params = {
                "apiKey": self.api_key,
                "regions": "us",  # US bookmakers
                "markets": "h2h,spreads,totals",  # Moneyline, Spread, Total
                "oddsFormat": "american",  # -110, +150 format
                "bookmakers": "fanduel"  # Primary bookmaker
            }

            logger.info(f"Fetching odds from The Odds API ({tier})...")

            response = requests.get(url, params=params, timeout=30)

            # Track API call
            self.monthly_calls += 1
            if tier == "tier1":
                self.tier1_used += 1
            elif tier == "tier2":
                self.tier2_used += 1

            logger.info(f"API Call: {self.monthly_calls}/{self.MONTHLY_LIMIT} (Tier1: {self.tier1_used}, Tier2: {self.tier2_used})")

            if response.status_code == 429:
                logger.error("Rate limit exceeded!")
                return []

            if response.status_code != 200:
                logger.error(f"API error {response.status_code}: {response.text[:200]}")
                return []

            data = response.json()

            # Check remaining quota (returned in headers)
            remaining = response.headers.get('x-requests-remaining')
            if remaining:
                logger.info(f"Remaining API quota: {remaining}")

            snapshots = self._parse_odds_response(data, snapshot_type)

            logger.info(f"✅ Fetched odds for {len(snapshots)} games ({tier})")
            return snapshots

        except Exception as e:
            logger.error(f"Failed to fetch odds: {e}")
            return []

    def _parse_odds_response(
        self,
        data: List[Dict],
        snapshot_type: str
    ) -> List[OddsSnapshot]:
        """
        Parse The Odds API response

        Response structure:
        [
          {
            "id": "unique_event_id",
            "sport_key": "basketball_nba",
            "commence_time": "2025-12-28T19:00:00Z",
            "home_team": "Cleveland Cavaliers",
            "away_team": "Boston Celtics",
            "bookmakers": [
              {
                "key": "fanduel",
                "title": "FanDuel",
                "last_update": "2025-12-28T17:58:12Z",
                "markets": [
                  {
                    "key": "h2h",  // Moneyline
                    "outcomes": [
                      {"name": "Cleveland Cavaliers", "price": -150},
                      {"name": "Boston Celtics", "price": 130}
                    ]
                  },
                  {
                    "key": "spreads",
                    "outcomes": [
                      {"name": "Cleveland Cavaliers", "price": -110, "point": -3.5},
                      {"name": "Boston Celtics", "price": -110, "point": 3.5}
                    ]
                  },
                  {
                    "key": "totals",
                    "outcomes": [
                      {"name": "Over", "price": -110, "point": 225.5},
                      {"name": "Under", "price": -110, "point": 225.5}
                    ]
                  }
                ]
              }
            ]
          }
        ]
        """
        snapshots = []
        now = datetime.now()

        for event in data:
            try:
                # Parse commence time
                commence_str = event.get("commence_time", "")
                commence_time = datetime.fromisoformat(commence_str.replace('Z', '+00:00'))
                commence_time_naive = commence_time.replace(tzinfo=None)

                # Time to game
                time_to_game = (commence_time_naive - now).total_seconds() / 60

                # Teams
                home_team = event.get("home_team", "")
                away_team = event.get("away_team", "")

                # Extract team abbreviations (e.g., "Cleveland Cavaliers" -> "CLE")
                home_abbr = self._get_team_abbr(home_team)
                away_abbr = self._get_team_abbr(away_team)

                # Generate game_id (ESPN format approximation)
                game_id = f"odds_{commence_time_naive.strftime('%Y%m%d')}_{home_abbr}_{away_abbr}"

                # Odds ID
                odds_id = f"{game_id}_{now.strftime('%Y%m%d_%H%M%S')}"

                # Extract bookmaker data
                bookmakers = event.get("bookmakers", [])
                if not bookmakers:
                    continue

                bookmaker = bookmakers[0]  # Use first (FanDuel)
                markets = bookmaker.get("markets", [])

                # Parse markets
                h2h_data = next((m for m in markets if m["key"] == "h2h"), None)
                spreads_data = next((m for m in markets if m["key"] == "spreads"), None)
                totals_data = next((m for m in markets if m["key"] == "totals"), None)

                # Moneyline
                home_ml = None
                away_ml = None
                if h2h_data:
                    for outcome in h2h_data.get("outcomes", []):
                        if outcome["name"] == home_team:
                            home_ml = outcome["price"]
                        elif outcome["name"] == away_team:
                            away_ml = outcome["price"]

                # Spread
                home_spread = None
                home_spread_odds = None
                away_spread = None
                away_spread_odds = None
                if spreads_data:
                    for outcome in spreads_data.get("outcomes", []):
                        if outcome["name"] == home_team:
                            home_spread = outcome.get("point")
                            home_spread_odds = outcome["price"]
                        elif outcome["name"] == away_team:
                            away_spread = outcome.get("point")
                            away_spread_odds = outcome["price"]

                # Total
                total_line = None
                over_odds = None
                under_odds = None
                if totals_data:
                    for outcome in totals_data.get("outcomes", []):
                        if outcome["name"] == "Over":
                            total_line = outcome.get("point")
                            over_odds = outcome["price"]
                        elif outcome["name"] == "Under":
                            under_odds = outcome["price"]

                # API last update
                api_update_str = bookmaker.get("last_update", "")
                api_last_update = datetime.fromisoformat(api_update_str.replace('Z', '+00:00')).replace(tzinfo=None) if api_update_str else None

                # Create snapshot
                snapshot = OddsSnapshot(
                    odds_id=odds_id,
                    game_id=game_id,
                    collected_at=now,
                    time_to_game_minutes=int(time_to_game),
                    snapshot_type=snapshot_type,
                    home_team=home_abbr,
                    away_team=away_abbr,
                    commence_time=commence_time_naive,
                    home_ml=home_ml,
                    away_ml=away_ml,
                    home_spread=home_spread,
                    home_spread_odds=home_spread_odds,
                    away_spread=away_spread,
                    away_spread_odds=away_spread_odds,
                    total_line=total_line,
                    over_odds=over_odds,
                    under_odds=under_odds,
                    bookmaker=bookmaker.get("key", "fanduel"),
                    api_last_update=api_last_update
                )

                snapshots.append(snapshot)

            except Exception as e:
                logger.error(f"Failed to parse odds event: {e}")
                continue

        return snapshots

    def _get_team_abbr(self, team_name: str) -> str:
        """Convert full team name to abbreviation"""
        team_map = {
            "Atlanta Hawks": "ATL",
            "Boston Celtics": "BOS",
            "Brooklyn Nets": "BKN",
            "Charlotte Hornets": "CHA",
            "Chicago Bulls": "CHI",
            "Cleveland Cavaliers": "CLE",
            "Dallas Mavericks": "DAL",
            "Denver Nuggets": "DEN",
            "Detroit Pistons": "DET",
            "Golden State Warriors": "GS",
            "Houston Rockets": "HOU",
            "Indiana Pacers": "IND",
            "Los Angeles Clippers": "LAC",
            "Los Angeles Lakers": "LAL",
            "Memphis Grizzlies": "MEM",
            "Miami Heat": "MIA",
            "Milwaukee Bucks": "MIL",
            "Minnesota Timberwolves": "MIN",
            "New Orleans Pelicans": "NO",
            "New York Knicks": "NY",
            "Oklahoma City Thunder": "OKC",
            "Orlando Magic": "ORL",
            "Philadelphia 76ers": "PHI",
            "Phoenix Suns": "PHX",
            "Portland Trail Blazers": "POR",
            "Sacramento Kings": "SAC",
            "San Antonio Spurs": "SA",
            "Toronto Raptors": "TOR",
            "Utah Jazz": "UTAH",
            "Washington Wizards": "WSH"
        }
        return team_map.get(team_name, team_name[:3].upper())

    def _get_mock_odds(self) -> List[OddsSnapshot]:
        """Mock data for testing"""
        now = datetime.now()
        game_time = now + timedelta(hours=1)

        return [
            OddsSnapshot(
                odds_id="mock_20251228_CLE_BOS",
                game_id="mock_game_1",
                collected_at=now,
                time_to_game_minutes=-60,
                snapshot_type="close",
                home_team="CLE",
                away_team="BOS",
                commence_time=game_time,
                home_ml=-150,
                away_ml=130,
                home_spread=-3.5,
                home_spread_odds=-110,
                away_spread=3.5,
                away_spread_odds=-110,
                total_line=225.5,
                over_odds=-110,
                under_odds=-110,
                bookmaker="fanduel"
            )
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics"""
        return {
            "api_base": self.API_BASE,
            "sport": self.SPORT,
            "mock_mode": self.mock_mode,
            "monthly_limit": self.MONTHLY_LIMIT,
            "monthly_calls": self.monthly_calls,
            "tier1_budget": self.tier1_budget,
            "tier1_used": self.tier1_used,
            "tier1_remaining": self.tier1_budget - self.tier1_used,
            "tier2_budget": self.tier2_budget,
            "tier2_used": self.tier2_used,
            "tier2_remaining": self.tier2_budget - self.tier2_used,
            "percentage_used": round((self.monthly_calls / self.MONTHLY_LIMIT) * 100, 1)
        }


def test_odds_api():
    """Test The Odds API adapter"""
    adapter = OddsAPIAdapter()

    print("=" * 60)
    print("Testing The Odds API - NBA Odds")
    print("=" * 60)

    # Fetch current odds (Tier 1)
    snapshots = adapter.fetch_current_odds(tier="tier1", snapshot_type="close")

    print(f"\nResults: {len(snapshots)} games with odds")

    if snapshots:
        print("\nSample odds:")
        for i, odds in enumerate(snapshots[:3], 1):
            print(f"\n{i}. {odds.away_team} @ {odds.home_team}")
            print(f"   Game time: {odds.commence_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"   Spread: {odds.home_team} {odds.home_spread} ({odds.home_spread_odds:+d})")
            print(f"   Total: {odds.total_line} (O: {odds.over_odds:+d}, U: {odds.under_odds:+d})")
            print(f"   Moneyline: {odds.home_team} {odds.home_ml:+d}, {odds.away_team} {odds.away_ml:+d}")

    print("\n" + "=" * 60)
    print("API Usage:")
    print("=" * 60)
    stats = adapter.get_stats()
    print(f"Total: {stats['monthly_calls']}/{stats['monthly_limit']}")
    print(f"Tier1: {stats['tier1_used']}/{stats['tier1_budget']}")
    print(f"Tier2: {stats['tier2_used']}/{stats['tier2_budget']}")


if __name__ == "__main__":
    test_odds_api()
