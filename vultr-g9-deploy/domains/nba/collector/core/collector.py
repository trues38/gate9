"""
Collection Controller - Game-aware information lifecycle system

CORE PHILOSOPHY:
- ❌ Do NOT collect data continuously
- ❌ Do NOT rely on fixed cron intervals alone
- ✅ Collect ONLY when a game is in a meaningful information state
- ✅ DEAD state = ZERO API calls
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
import logging
import hashlib

from core.game_state import GameState, GameInfo, GameStateManager
from core.whitelist import WhitelistManager, keyword_match, WhitelistAccount
from sources.x_adapter import XAdapter, Tweet, ESPNAdapter

logger = logging.getLogger(__name__)


@dataclass
class CollectedEvent:
    """Parsed and validated event"""
    event_id: str
    game_id: str
    source_username: str
    source_credibility: float
    event_type: str  # injury, lineup, referee, etc.
    raw_text: str
    text_hash: str
    player: Optional[str] = None
    team: Optional[str] = None
    status: Optional[str] = None
    collected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id,
            "game_id": self.game_id,
            "source_username": self.source_username,
            "source_credibility": self.source_credibility,
            "event_type": self.event_type,
            "raw_text": self.raw_text,
            "text_hash": self.text_hash,
            "player": self.player,
            "team": self.team,
            "status": self.status,
            "collected_at": self.collected_at.isoformat()
        }


class DeduplicationCache:
    """In-memory deduplication using text hashes"""

    def __init__(self, ttl_hours: int = 24):
        self.seen_hashes: Dict[str, datetime] = {}
        self.ttl = timedelta(hours=ttl_hours)

    def is_duplicate(self, text_hash: str) -> bool:
        """Check if hash was seen recently"""
        if text_hash in self.seen_hashes:
            if datetime.now() - self.seen_hashes[text_hash] < self.ttl:
                return True
        return False

    def add(self, text_hash: str):
        """Add hash to cache"""
        self.seen_hashes[text_hash] = datetime.now()

    def cleanup(self):
        """Remove expired entries"""
        now = datetime.now()
        expired = [h for h, t in self.seen_hashes.items() if now - t > self.ttl]
        for h in expired:
            del self.seen_hashes[h]
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired hashes")

    def stats(self) -> Dict:
        return {"cached_hashes": len(self.seen_hashes)}


class CollectionController:
    """
    Main controller for game-aware information collection

    This is NOT a "real-time crawler"
    This IS a game-aware information lifecycle system
    """

    def __init__(
        self,
        game_manager: GameStateManager = None,
        whitelist: WhitelistManager = None,
        x_adapter: XAdapter = None,
        neo4j_saver = None  # Will be injected
    ):
        self.game_manager = game_manager or GameStateManager()
        self.whitelist = whitelist or WhitelistManager()
        self.x_adapter = x_adapter or XAdapter()
        self.espn_adapter = ESPNAdapter()
        self.neo4j_saver = neo4j_saver

        self.dedup_cache = DeduplicationCache()
        self.collection_stats = {
            "cycles": 0,
            "events_collected": 0,
            "duplicates_skipped": 0,
            "api_calls": 0
        }

    def load_today_games(self):
        """Load today's games from ESPN and initialize state machine"""
        games = self.espn_adapter.get_today_games()

        if not games:
            logger.info("No games today - collection will be minimal")
            return []

        team_codes = set()

        for game in games:
            try:
                game_id = game.get("id")
                competitions = game.get("competitions", [{}])[0]
                competitors = competitions.get("competitors", [])

                if len(competitors) < 2:
                    continue

                home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
                away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

                home_code = home.get("team", {}).get("abbreviation", "")
                away_code = away.get("team", {}).get("abbreviation", "")

                # Parse scheduled time
                date_str = game.get("date", "")
                try:
                    scheduled = datetime.fromisoformat(date_str.replace("Z", "+00:00")).replace(tzinfo=None)
                except:
                    scheduled = datetime.now() + timedelta(hours=4)

                game_info = GameInfo(
                    game_id=game_id,
                    home_team=home_code,
                    away_team=away_code,
                    scheduled_time=scheduled
                )

                self.game_manager.add_game(game_info)
                team_codes.add(home_code)
                team_codes.add(away_code)

            except Exception as e:
                logger.error(f"Failed to parse game: {e}")
                continue

        # Add team accounts for today's games
        self.whitelist.add_team_accounts(list(team_codes))

        logger.info(f"Loaded {len(self.game_manager.games)} games for today")
        return list(self.game_manager.games.values())

    def run_collection_cycle(self) -> Dict:
        """
        Main collection cycle - call this from n8n/cron

        Returns summary of what was collected
        """
        self.collection_stats["cycles"] += 1
        cycle_start = datetime.now()

        # Update all game states first
        self.game_manager.update_all_states()

        # Get games that need collection
        active_games = self.game_manager.get_active_games()

        if not active_games:
            logger.info("No active games - ZERO API calls")
            return {
                "status": "idle",
                "active_games": 0,
                "events_collected": 0,
                "message": "No games in collectible state"
            }

        logger.info(f"Active games: {len(active_games)}")

        all_events = []
        total_api_calls = 0

        for game in active_games:
            events, api_calls = self._collect_for_game(game)
            all_events.extend(events)
            total_api_calls += api_calls
            game.last_checked = datetime.now()

        # Save to Neo4j if available
        saved_count = 0
        if self.neo4j_saver and all_events:
            saved_count = self._save_events(all_events)

        self.collection_stats["events_collected"] += len(all_events)
        self.collection_stats["api_calls"] += total_api_calls

        duration = (datetime.now() - cycle_start).total_seconds()

        result = {
            "status": "success",
            "active_games": len(active_games),
            "api_calls": total_api_calls,
            "events_found": len(all_events),
            "events_saved": saved_count,
            "duplicates_skipped": self.collection_stats["duplicates_skipped"],
            "duration_seconds": duration,
            "game_states": self.game_manager.get_stats()
        }

        logger.info(f"Cycle complete: {result}")
        return result

    def _collect_for_game(self, game: GameInfo) -> tuple[List[CollectedEvent], int]:
        """Collect events for a single game"""
        events = []
        api_calls = 0

        # Get accounts allowed for this game's state
        accounts = self.whitelist.get_accounts_for_state(game.state)

        for account in accounts:
            # Fetch tweets
            tweets = self.x_adapter.fetch_user_timeline(
                username=account.username,
                since=game.last_checked,
                max_results=10
            )
            api_calls += 1

            for tweet in tweets:
                # Check for keyword match
                event_type = keyword_match(tweet.text, game.state)
                if not event_type:
                    continue

                # Deduplication check
                if self.dedup_cache.is_duplicate(tweet.text_hash):
                    self.collection_stats["duplicates_skipped"] += 1
                    continue

                self.dedup_cache.add(tweet.text_hash)

                # Create event
                event = CollectedEvent(
                    event_id=f"evt_{tweet.tweet_id}",
                    game_id=game.game_id,
                    source_username=account.username,
                    source_credibility=account.credibility,
                    event_type=event_type,
                    raw_text=tweet.text,
                    text_hash=tweet.text_hash,
                    team=self._extract_team(tweet.text, game),
                    status=self._extract_status(tweet.text)
                )

                events.append(event)
                logger.info(f"[{account.username}] {event_type}: {tweet.text[:100]}")

                # Check for state-changing events
                self._check_state_triggers(event, game)

        return events, api_calls

    def _extract_team(self, text: str, game: GameInfo) -> Optional[str]:
        """Extract team from text"""
        text_lower = text.lower()
        if game.home_team.lower() in text_lower:
            return game.home_team
        if game.away_team.lower() in text_lower:
            return game.away_team
        return None

    def _extract_status(self, text: str) -> Optional[str]:
        """Extract status from text"""
        text_lower = text.lower()
        statuses = {
            "OUT": ["out", "ruled out", "will not play"],
            "QUESTIONABLE": ["questionable", "gtd"],
            "DOUBTFUL": ["doubtful"],
            "PROBABLE": ["probable"],
            "STARTING": ["will start", "starting"],
        }
        for status, keywords in statuses.items():
            if any(k in text_lower for k in keywords):
                return status
        return None

    def _check_state_triggers(self, event: CollectedEvent, game: GameInfo):
        """Check if event should trigger state change"""
        if event.event_type == "lineup" and "lineup" in event.raw_text.lower():
            # Check for lineup confirmation patterns
            if "starting" in event.raw_text.lower() and "lineup" in event.raw_text.lower():
                game.confirm_lineup()

        if event.event_type == "referee":
            if "crew chief" in event.raw_text.lower() or "officiating" in event.raw_text.lower():
                game.confirm_referees()

    def _save_events(self, events: List[CollectedEvent]) -> int:
        """Save events to Neo4j"""
        if not self.neo4j_saver:
            return 0

        saved = 0
        for event in events:
            try:
                self.neo4j_saver.save_event(event.to_dict())
                saved += 1
            except Exception as e:
                logger.error(f"Failed to save event: {e}")

        return saved

    def get_status(self) -> Dict:
        """Get current system status"""
        return {
            "games": self.game_manager.get_stats(),
            "whitelist": self.whitelist.get_stats(),
            "collection": self.collection_stats,
            "dedup_cache": self.dedup_cache.stats(),
            "x_adapter": self.x_adapter.get_stats()
        }

    def force_state(self, game_id: str, state: str) -> bool:
        """Manually force a game state (for testing/override)"""
        game = self.game_manager.get_game(game_id)
        if not game:
            return False

        try:
            new_state = GameState(state)
            game.state = new_state
            logger.info(f"Force set game {game_id} to {state}")
            return True
        except ValueError:
            return False
