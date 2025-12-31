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

        Collection strategy (UPDATED):
        - Start: 24 hours before FIRST game (to catch early news)
        - End: 2 hours after LAST game starts
        - This accommodates timezone differences (ESPN returns UTC times)
        - Frequency: Every 30 minutes (via N8N cron)

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

        # Collection window: T-24h (first game) to T+2h (last game)
        # Extended to handle timezone differences - ESPN returns UTC times
        # but games may appear as "tomorrow" when it's actually today in US time
        collection_start = first_game - timedelta(hours=24)
        collection_end = last_game + timedelta(hours=2)

        if collection_start <= now <= collection_end:
            time_to_first = (first_game - now).total_seconds() / 3600  # hours
            time_to_last = (last_game - now).total_seconds() / 3600
            logger.info(f"NBA collection active (First game in {time_to_first:.1f}h, Last game in {time_to_last:.1f}h)")
            return True

        logger.debug(f"Not in collection window (starts in {(collection_start - now).total_seconds() / 3600:.1f}h)")
        return False

    def should_collect_economy(self) -> bool:
        """
        Determine if Economy collection should happen now

        Market session times (KST) - EXPANDED:
        - 08:00-09:00 - Asia open
        - 14:00-15:00 - Asia afternoon
        - 16:00-17:00 - Europe open
        - 20:00-21:00 - Europe afternoon
        - 22:00-23:00 - US open
        - 01:00-02:00 - US midday
        - 05:00-06:00 - US close

        Budget: ~10-14 calls/day = 300-420/month (increased budget)
        """
        if self.economy_used >= self.economy_budget:
            logger.warning("Economy budget exceeded")
            return False

        now_kst = datetime.now(self.kst)
        current_hour = now_kst.hour

        # Define collection windows (expanded to 1-hour windows)
        # (hour_start, hour_end, name)
        windows = [
            (8, 9, "Asia open"),
            (14, 15, "Asia afternoon"),
            (16, 17, "Europe open"),
            (20, 21, "Europe afternoon"),
            (22, 23, "US open"),
            (1, 2, "US midday"),
            (5, 6, "US close")
        ]

        for hour_start, hour_end, name in windows:
            if hour_start <= current_hour < hour_end:
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
