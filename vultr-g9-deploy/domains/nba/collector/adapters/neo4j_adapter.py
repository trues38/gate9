"""
Neo4j Adapter - Graph database storage for NBA events
"""

from neo4j import GraphDatabase
from typing import Dict, List, Optional
import logging
import os

logger = logging.getLogger(__name__)


class Neo4jAdapter:
    """Neo4j graph database adapter"""

    def __init__(
        self,
        uri: str = None,
        user: str = None,
        password: str = None
    ):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://neo4j-nba:7687")
        self.user = user or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "nba_vultr_2025")

        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            logger.info(f"Connected to Neo4j: {self.uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def save_event(self, event: Dict) -> bool:
        """Save collected event to Neo4j"""
        if not self.driver:
            logger.warning("Neo4j not connected - skipping save")
            return False

        try:
            with self.driver.session() as session:
                query = """
                MERGE (e:NBAEvent {event_id: $event_id})
                ON CREATE SET
                    e.game_id = $game_id,
                    e.source_username = $source_username,
                    e.source_credibility = toFloat($source_credibility),
                    e.event_type = $event_type,
                    e.raw_text = $raw_text,
                    e.text_hash = $text_hash,
                    e.player = $player,
                    e.team = $team,
                    e.status = $status,
                    e.collected_at = datetime($collected_at),
                    e.created_at = datetime()
                ON MATCH SET
                    e.updated_at = datetime()
                RETURN e.event_id as id
                """

                result = session.run(query, event)
                record = result.single()

                if record:
                    logger.debug(f"Saved event: {record['id']}")
                    return True

                return False

        except Exception as e:
            logger.error(f"Failed to save event: {e}")
            return False

    def save_game(self, game: Dict) -> bool:
        """Save game information"""
        if not self.driver:
            return False

        try:
            with self.driver.session() as session:
                query = """
                MERGE (g:Game {game_id: $game_id})
                SET g.home_team = $home_team,
                    g.away_team = $away_team,
                    g.scheduled_time = datetime($scheduled_time),
                    g.state = $state,
                    g.lineup_confirmed = $lineup_confirmed,
                    g.referees_confirmed = $referees_confirmed,
                    g.updated_at = datetime()
                RETURN g.game_id as id
                """

                session.run(query, game)
                return True

        except Exception as e:
            logger.error(f"Failed to save game: {e}")
            return False

    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Get most recent events"""
        if not self.driver:
            return []

        try:
            with self.driver.session() as session:
                query = """
                MATCH (e:NBAEvent)
                RETURN e
                ORDER BY e.created_at DESC
                LIMIT $limit
                """

                result = session.run(query, {"limit": limit})
                return [dict(record["e"]) for record in result]

        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            return []

    def get_events_by_game(self, game_id: str) -> List[Dict]:
        """Get events for a specific game"""
        if not self.driver:
            return []

        try:
            with self.driver.session() as session:
                query = """
                MATCH (e:NBAEvent {game_id: $game_id})
                RETURN e
                ORDER BY e.collected_at DESC
                """

                result = session.run(query, {"game_id": game_id})
                return [dict(record["e"]) for record in result]

        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            return []

    def save_odds(self, odds: Dict) -> bool:
        """
        Save odds snapshot to Neo4j

        Args:
            odds: OddsSnapshot as dict

        Returns:
            True if saved successfully
        """
        if not self.driver:
            logger.warning("Neo4j not connected - skipping odds save")
            return False

        try:
            with self.driver.session() as session:
                query = """
                MERGE (o:Odds {odds_id: $odds_id})
                ON CREATE SET
                    o.game_id = $game_id,
                    o.collected_at = datetime($collected_at),
                    o.time_to_game_minutes = $time_to_game_minutes,
                    o.snapshot_type = $snapshot_type,
                    o.home_team = $home_team,
                    o.away_team = $away_team,
                    o.commence_time = datetime($commence_time),
                    o.home_ml = $home_ml,
                    o.away_ml = $away_ml,
                    o.home_spread = toFloat($home_spread),
                    o.home_spread_odds = $home_spread_odds,
                    o.away_spread = toFloat($away_spread),
                    o.away_spread_odds = $away_spread_odds,
                    o.total_line = toFloat($total_line),
                    o.over_odds = $over_odds,
                    o.under_odds = $under_odds,
                    o.bookmaker = $bookmaker,
                    o.source_api = $source_api,
                    o.created_at = datetime()
                ON MATCH SET
                    o.updated_at = datetime()

                // Link to Game if exists
                WITH o
                OPTIONAL MATCH (g:Game)
                WHERE g.home_team = o.home_team
                  AND g.away_team = o.away_team
                  AND abs(duration.inSeconds(g.scheduled_time, o.commence_time).seconds) < 3600
                FOREACH (_ IN CASE WHEN g IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (g)-[r:HAS_ODDS]->(o)
                    SET r.sequence = CASE o.snapshot_type
                        WHEN 'open' THEN 1
                        WHEN 'mid' THEN 2
                        WHEN 'close' THEN 3
                        ELSE 0 END
                )

                RETURN o.odds_id as id
                """

                result = session.run(query, odds)
                record = result.single()

                if record:
                    logger.debug(f"Saved odds: {record['id']}")
                    return True

                return False

        except Exception as e:
            logger.error(f"Failed to save odds: {e}")
            return False

    def get_latest_odds(self, game_id: str = None, snapshot_type: str = None) -> List[Dict]:
        """
        Get latest odds snapshots

        Args:
            game_id: Filter by game (optional)
            snapshot_type: Filter by type - "open"/"mid"/"close" (optional)

        Returns:
            List of odds snapshots
        """
        if not self.driver:
            return []

        try:
            with self.driver.session() as session:
                # Build dynamic query
                conditions = []
                params = {}

                if game_id:
                    conditions.append("o.game_id = $game_id")
                    params["game_id"] = game_id

                if snapshot_type:
                    conditions.append("o.snapshot_type = $snapshot_type")
                    params["snapshot_type"] = snapshot_type

                where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

                query = f"""
                MATCH (o:Odds)
                {where_clause}
                RETURN o
                ORDER BY o.collected_at DESC
                LIMIT 50
                """

                result = session.run(query, params)
                return [dict(record["o"]) for record in result]

        except Exception as e:
            logger.error(f"Failed to get odds: {e}")
            return []

    def get_stats(self) -> Dict:
        """Get database statistics"""
        if not self.driver:
            return {"connected": False}

        try:
            with self.driver.session() as session:
                query = """
                MATCH (e:NBAEvent)
                WITH count(e) as event_count
                MATCH (g:Game)
                WITH event_count, count(g) as game_count
                MATCH (o:Odds)
                RETURN event_count, game_count, count(o) as odds_count
                """

                result = session.run(query)
                record = result.single()

                return {
                    "connected": True,
                    "events": record["event_count"] if record else 0,
                    "games": record["game_count"] if record else 0,
                    "odds_snapshots": record["odds_count"] if record else 0
                }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"connected": False, "error": str(e)}

    def create_indexes(self):
        """Create database indexes for performance"""
        if not self.driver:
            return

        indexes = [
            "CREATE INDEX event_id_idx IF NOT EXISTS FOR (e:NBAEvent) ON (e.event_id)",
            "CREATE INDEX event_game_idx IF NOT EXISTS FOR (e:NBAEvent) ON (e.game_id)",
            "CREATE INDEX event_hash_idx IF NOT EXISTS FOR (e:NBAEvent) ON (e.text_hash)",
            "CREATE INDEX game_id_idx IF NOT EXISTS FOR (g:Game) ON (g.game_id)",
            "CREATE INDEX odds_id_idx IF NOT EXISTS FOR (o:Odds) ON (o.odds_id)",
            "CREATE INDEX odds_game_idx IF NOT EXISTS FOR (o:Odds) ON (o.game_id)",
            "CREATE INDEX odds_type_idx IF NOT EXISTS FOR (o:Odds) ON (o.snapshot_type)",
        ]

        with self.driver.session() as session:
            for idx in indexes:
                try:
                    session.run(idx)
                except Exception as e:
                    logger.warning(f"Index creation issue: {e}")

        logger.info("Neo4j indexes created/verified")
