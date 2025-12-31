"""
Time-Based Collection Scheduler

Purpose:
- Minimize API calls by collecting ONLY when valuable
- NBA: Event-based (game times)
- Economy: Session-based (market hours)
- Budget allocation: 500 calls/month

Philosophy:
"API calls are precious - timing is everything"
"""

from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging
import pytz

logger = logging.getLogger(__name__)


@dataclass
class CollectionWindow:
    """Defines when to collect data"""
    name: str
    start_time: datetime
    domain: str  # "nba" or "economy"
    priority: int  # 1-5 (5 = highest)
    accounts: List[str]  # Which accounts to fetch


class TimeBasedScheduler:
    """
    Intelligent scheduler that decides WHEN to collect data

    Key Concepts:
    - NBA: Game-aware (only collect near game times)
    - Economy: Session-aware (market open times)
    - Budget-conscious (track monthly API usage)

    Monthly Budget: 500 calls
    - NBA: 250 calls (50%)
    - Economy: 200 calls (40%)
    - Buffer: 50 calls (10%)
    """

    def __init__(self):
        self.monthly_budget = 500
        self.nba_budget = 250
        self.economy_budget = 200

        # Track usage
        self.nba_used = 0
        self.economy_used = 0

        # Timezone
        self.kst = pytz.timezone("Asia/Seoul")
        self.est = pytz.timezone("America/New_York")

        logger.info("TimeBasedScheduler initialized")
        logger.info(f"Budget: NBA={self.nba_budget}, Economy={self.economy_budget}")

    def should_collect_nba(self, game_times: List[datetime]) -> bool:
        """
        Determine if NBA collection should happen now

        Collection strategy:
        - Start: 1 hour before FIRST game
        - End: When LAST game starts
        - Frequency: Every 30 minutes (via N8N cron)

        This ensures continuous collection during active game period.

        Args:
            game_times: List of scheduled game times (datetime objects)

        Returns:
            True if we're in a collection window
        """
        if self.nba_used >= self.nba_budget:
            logger.warning("NBA budget exceeded")
            return False

        if not game_times:
            logger.debug("No games scheduled - skip NBA collection")
            return False

        now = datetime.now()

        # Find earliest and latest games
        first_game = min(game_times)
        last_game = max(game_times)

        # Collection window: T-1h (first game) to T-0 (last game)
        collection_start = first_game - timedelta(hours=1)
        collection_end = last_game

        if collection_start <= now <= collection_end:
            time_to_first = (first_game - now).total_seconds() / 60
            time_to_last = (last_game - now).total_seconds() / 60
            logger.info(f"NBA collection active (First game in {time_to_first:.0f}m, Last game in {time_to_last:.0f}m)")
            return True

        logger.debug(f"Not in collection window (starts in {(collection_start - now).total_seconds() / 60:.0f}m)")
        return False

    def should_collect_economy(self) -> bool:
        """
        Determine if Economy collection should happen now

        Market session times (KST):
        - 08:00 - Asia open
        - 16:00 - Europe open
        - 22:30 - US open
        - 01:00 - US midday
        - 05:00 - US close

        Budget: ~6-8 calls/day = 200/month
        """
        if self.economy_used >= self.economy_budget:
            logger.warning("Economy budget exceeded")
            return False

        now_kst = datetime.now(self.kst)
        current_hour = now_kst.hour
        current_minute = now_kst.minute

        # Define collection windows (hour, minute_start, minute_end)
        windows = [
            (8, 0, 15, "Asia open"),
            (16, 0, 15, "Europe open"),
            (22, 25, 40, "US open"),
            (1, 0, 15, "US midday"),
            (5, 0, 15, "US close")
        ]

        for hour, min_start, min_end, name in windows:
            if current_hour == hour and min_start <= current_minute <= min_end:
                logger.info(f"Economy collection: {name}")
                return True

        logger.debug("Not in Economy collection window")
        return False

    def get_nba_collection_windows(
        self,
        game_times: List[datetime]
    ) -> List[CollectionWindow]:
        """
        Generate NBA collection windows for scheduled games

        Returns:
            List of CollectionWindow objects
        """
        windows = []

        for game_time in game_times:
            # T-2h: Referee check
            windows.append(CollectionWindow(
                name=f"T-2h (Referee check)",
                start_time=game_time - timedelta(hours=2),
                domain="nba",
                priority=3,
                accounts=["OfficialNBARefs", "NBARefStats"]
            ))

            # T-1h: Injury check
            windows.append(CollectionWindow(
                name=f"T-1h (Injury check)",
                start_time=game_time - timedelta(hours=1),
                domain="nba",
                priority=4,
                accounts=["ShamsCharania", "wojespn", "ChrisBHaynes", "FantasyLabsNBA", "NBAInjuryR3p0rt"]
            ))

            # T-30m: Lineup check
            windows.append(CollectionWindow(
                name=f"T-30m (Lineup check)",
                start_time=game_time - timedelta(minutes=30),
                domain="nba",
                priority=5,
                accounts=["UnderdogNBA", "FantasyLabsDFS", "RotoGrinders", "NBAFantasy"]
            ))

            # T-0: Final check
            windows.append(CollectionWindow(
                name=f"T-0 (Final check)",
                start_time=game_time,
                domain="nba",
                priority=5,
                accounts=["ShamsCharania", "wojespn", "UnderdogNBA"]
            ))

        return windows

    def get_economy_collection_windows(self) -> List[CollectionWindow]:
        """
        Generate Economy collection windows for today

        Returns:
            List of CollectionWindow objects
        """
        now_kst = datetime.now(self.kst)
        today = now_kst.date()

        economy_accounts = [
            "federalreserve", "ECB", "BoJOfficial",
            "markets", "financial_news", "macro_analysts"
        ]

        windows = [
            CollectionWindow(
                name="Asia open",
                start_time=datetime.combine(today, time(8, 0)).replace(tzinfo=self.kst),
                domain="economy",
                priority=3,
                accounts=economy_accounts
            ),
            CollectionWindow(
                name="Europe open",
                start_time=datetime.combine(today, time(16, 0)).replace(tzinfo=self.kst),
                domain="economy",
                priority=4,
                accounts=economy_accounts
            ),
            CollectionWindow(
                name="US open",
                start_time=datetime.combine(today, time(22, 30)).replace(tzinfo=self.kst),
                domain="economy",
                priority=5,
                accounts=economy_accounts
            ),
            CollectionWindow(
                name="US midday",
                start_time=datetime.combine(today, time(1, 0)).replace(tzinfo=self.kst),
                domain="economy",
                priority=4,
                accounts=economy_accounts
            ),
            CollectionWindow(
                name="US close",
                start_time=datetime.combine(today, time(5, 0)).replace(tzinfo=self.kst),
                domain="economy",
                priority=4,
                accounts=economy_accounts
            ),
        ]

        return windows

    def get_next_collection_window(
        self,
        game_times: List[datetime] = None
    ) -> Optional[Tuple[str, datetime, List[str]]]:
        """
        Get the next scheduled collection window

        Args:
            game_times: Optional list of NBA game times

        Returns:
            Tuple of (domain, window_time, accounts) or None
        """
        now = datetime.now()

        # Get all windows
        nba_windows = self.get_nba_collection_windows(game_times or [])
        economy_windows = self.get_economy_collection_windows()

        all_windows = nba_windows + economy_windows

        # Filter future windows
        future_windows = [w for w in all_windows if w.start_time > now]

        if not future_windows:
            logger.info("No upcoming collection windows")
            return None

        # Sort by time
        future_windows.sort(key=lambda w: w.start_time)

        next_window = future_windows[0]
        return (next_window.domain, next_window.start_time, next_window.accounts)

    def increment_usage(self, domain: str, count: int = 1):
        """
        Track API usage

        Args:
            domain: "nba" or "economy"
            count: Number of API calls made
        """
        if domain == "nba":
            self.nba_used += count
        elif domain == "economy":
            self.economy_used += count

        logger.info(f"API usage: NBA={self.nba_used}/{self.nba_budget}, Economy={self.economy_used}/{self.economy_budget}")

    def get_budget_status(self) -> Dict[str, any]:
        """Get current budget status"""
        total_used = self.nba_used + self.economy_used
        total_budget = self.monthly_budget

        return {
            "total_budget": total_budget,
            "total_used": total_used,
            "total_remaining": total_budget - total_used,
            "nba_budget": self.nba_budget,
            "nba_used": self.nba_used,
            "nba_remaining": self.nba_budget - self.nba_used,
            "economy_budget": self.economy_budget,
            "economy_used": self.economy_used,
            "economy_remaining": self.economy_budget - self.economy_used,
            "percentage_used": round((total_used / total_budget) * 100, 1)
        }

    def reset_monthly_usage(self):
        """Reset monthly usage counters (call at start of each month)"""
        self.nba_used = 0
        self.economy_used = 0
        logger.info("Monthly usage reset")
