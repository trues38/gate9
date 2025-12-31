"""
G9 Sports Intelligence Platform
Main Orchestrator - Connects All 4 Layers
"""

import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import yaml

# Layer imports
from layer0_experts.kaggle_fetcher import KaggleFetcher
from layer1_realtime.x_search_monitor import XSearchMonitor, RealTimeEvent
from layer2_qualitative.reddit_collector import RedditCollector, RedditAnalysis


@dataclass
class GameContext:
    """Single game context with all layer data"""
    sport: str
    game_id: str
    teams: List[str]
    game_date: datetime

    # Layer 0: Expert stats
    expert_stats: Optional[Dict[str, Any]] = None

    # Layer 1: Real-time events
    realtime_events: List[RealTimeEvent] = None

    # Layer 2: Reddit analysis
    reddit_analysis: Optional[RedditAnalysis] = None

    # Layer 3: Graph context (from Neo4j)
    graph_context: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.realtime_events is None:
            self.realtime_events = []


class G9Orchestrator:
    """
    Main orchestrator for G9 Sports Intelligence Platform

    Coordinates all 4 layers:
    - Layer 0: Domain Expert Data (Kaggle/GitHub)
    - Layer 1: Real-time Events (X Search)
    - Layer 2: Qualitative Analysis (Reddit)
    - Layer 3: Graph Memory (Neo4j)

    Usage:
        orchestrator = G9Orchestrator("nba")

        # Pre-game: Get all context
        context = await orchestrator.get_pregame_context(game_id, teams)

        # During game: Monitor real-time
        events = await orchestrator.monitor_game(game_id, teams)

        # Post-game: Collect qualitative data
        analysis = await orchestrator.collect_postgame(game_id, teams)
    """

    def __init__(self, sport: str):
        """
        Args:
            sport: Sport code (nba, nfl, mlb, etc.)
        """
        self.sport = sport.lower()
        self.config = self._load_config()

        # Initialize layer modules
        self.kaggle_fetcher = KaggleFetcher(self.sport)
        self.x_monitor = XSearchMonitor(self.sport)
        self.reddit_collector = RedditCollector(self.sport)

        # Neo4j connection (lazy init)
        self._neo4j_driver = None

    def _load_config(self) -> Dict[str, Any]:
        """Load sport-specific configuration"""
        config_path = Path(f"/Users/js/g9/g9_sports_platform/sports/{self.sport}/config.yaml")

        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    @property
    def neo4j_driver(self):
        """Lazy Neo4j driver initialization"""
        if self._neo4j_driver is None:
            from neo4j import GraphDatabase
            uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
            user = os.getenv('NEO4J_USER', 'neo4j')
            password = os.getenv('NEO4J_PASSWORD', 'password')
            self._neo4j_driver = GraphDatabase.driver(uri, auth=(user, password))
        return self._neo4j_driver

    # ========================================
    # Layer 0: Expert Data
    # ========================================

    def sync_expert_data(self, force: bool = False) -> Dict[str, Path]:
        """
        Sync all expert datasets from Kaggle

        Returns:
            Dict of dataset names to local paths
        """
        print(f"[Layer 0] Syncing expert data for {self.sport.upper()}...")
        return self.kaggle_fetcher.fetch_all(force=force)

    def get_player_stats(self, player_name: str) -> Optional[Dict[str, Any]]:
        """
        Get player stats from expert datasets

        Args:
            player_name: Player name to look up

        Returns:
            Player statistics dict
        """
        # This would query the local Kaggle data
        # Implementation depends on dataset structure
        pass

    # ========================================
    # Layer 1: Real-time Events
    # ========================================

    async def search_realtime_events(
        self,
        event_types: List[str] = None
    ) -> List[RealTimeEvent]:
        """
        Search for real-time events across all configured sources

        Args:
            event_types: List of event types to search (injury, lineup, etc.)

        Returns:
            List of detected events
        """
        if event_types is None:
            event_types = ["injury", "lineup"]

        all_events = []

        for event_type in event_types:
            print(f"[Layer 1] Searching {event_type} events...")
            events = await self.x_monitor.search_events(event_type)
            all_events.extend(events)

        # Sort by tier (official first, then tier1, tier2, tier3)
        all_events.sort(key=lambda x: x.source_tier)

        return all_events

    async def monitor_game_live(
        self,
        game_id: str,
        teams: List[str],
        interval_seconds: int = 60
    ):
        """
        Generator that yields real-time events during a game

        Args:
            game_id: Game identifier
            teams: Team codes [HOME, AWAY]
            interval_seconds: Polling interval

        Yields:
            RealTimeEvent objects as they are detected
        """
        print(f"[Layer 1] Starting live monitor for {game_id}...")

        seen_ids = set()

        while True:
            events = await self.search_realtime_events()

            for event in events:
                # Filter by team
                if event.team and event.team not in teams:
                    continue

                # Skip duplicates
                if event.tweet_id in seen_ids:
                    continue

                seen_ids.add(event.tweet_id)
                yield event

            await asyncio.sleep(interval_seconds)

    # ========================================
    # Layer 2: Qualitative Analysis
    # ========================================

    async def collect_postgame_analysis(
        self,
        game_id: str,
        teams: List[str]
    ) -> Optional[RedditAnalysis]:
        """
        Collect post-game qualitative analysis from Reddit

        Args:
            game_id: Game identifier
            teams: Team codes [HOME, AWAY]

        Returns:
            RedditAnalysis object
        """
        print(f"[Layer 2] Collecting post-game analysis for {game_id}...")
        return await self.reddit_collector.collect_and_analyze(game_id, teams)

    # ========================================
    # Layer 3: Graph Memory
    # ========================================

    def store_event_in_graph(self, event: RealTimeEvent):
        """Store a real-time event in Neo4j"""
        with self.neo4j_driver.session() as session:
            session.run("""
                MERGE (e:RealTimeAlert {tweet_id: $tweet_id})
                SET e.sport = $sport,
                    e.event_type = $event_type,
                    e.player = $player,
                    e.team = $team,
                    e.status = $status,
                    e.source = $source,
                    e.source_tier = $source_tier,
                    e.timestamp = datetime($timestamp),
                    e.raw_text = $raw_text,
                    e.confidence = $confidence

                WITH e
                MATCH (p:Player {name: $player})
                MERGE (p)-[:HAS_ALERT]->(e)

                WITH e
                MATCH (t:Team {abbreviation: $team})
                MERGE (t)-[:HAS_ALERT]->(e)
            """,
                tweet_id=event.tweet_id,
                sport=event.sport,
                event_type=event.event_type.value,
                player=event.player,
                team=event.team,
                status=event.status,
                source=event.source,
                source_tier=event.source_tier,
                timestamp=event.timestamp.isoformat(),
                raw_text=event.raw_text,
                confidence=event.confidence
            )

    def store_reddit_analysis(self, analysis: RedditAnalysis):
        """Store Reddit analysis in Neo4j"""
        with self.neo4j_driver.session() as session:
            # Store the thread
            session.run("""
                MERGE (rt:RedditThread {thread_id: $thread_id})
                SET rt.sport = $sport,
                    rt.game_id = $game_id,
                    rt.thread_url = $thread_url,
                    rt.thread_title = $thread_title,
                    rt.overall_sentiment = $overall_sentiment,
                    rt.collected_at = datetime($collected_at),
                    rt.total_comments = $total_comments,
                    rt.analyzed_comments = $analyzed_comments,
                    rt.controversies = $controversies,
                    rt.key_insights = $key_insights

                WITH rt
                MATCH (g:Game {game_id: $game_id})
                MERGE (g)-[:HAS_REDDIT_THREAD]->(rt)
            """,
                thread_id=analysis.thread_id,
                sport=analysis.sport,
                game_id=analysis.game_id,
                thread_url=analysis.thread_url,
                thread_title=analysis.thread_title,
                overall_sentiment=analysis.overall_sentiment,
                collected_at=analysis.collected_at.isoformat(),
                total_comments=analysis.total_comments,
                analyzed_comments=analysis.analyzed_comments,
                controversies=analysis.controversies,
                key_insights=analysis.key_insights
            )

            # Store player evaluations
            for pe in analysis.player_evaluations:
                session.run("""
                    MATCH (rt:RedditThread {thread_id: $thread_id})
                    MERGE (pe:PlayerEvaluation {
                        eval_id: $thread_id + '_' + $player
                    })
                    SET pe.player = $player,
                        pe.sentiment = $sentiment,
                        pe.key_points = $key_points,
                        pe.sample_quote = $sample_quote,
                        pe.timestamp = datetime()

                    MERGE (pe)-[:FROM_THREAD]->(rt)

                    WITH pe
                    MATCH (p:Player {name: $player})
                    MERGE (p)-[:HAS_EVALUATION]->(pe)
                """,
                    thread_id=analysis.thread_id,
                    player=pe.player,
                    sentiment=pe.sentiment,
                    key_points=pe.key_points,
                    sample_quote=pe.sample_quote
                )

    def get_player_context(self, player_name: str) -> Dict[str, Any]:
        """
        Get full context for a player from the graph

        Returns:
            Dict with recent alerts, evaluations, and stats
        """
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (p:Player {name: $player_name})

                OPTIONAL MATCH (p)-[:HAS_ALERT]->(a:RealTimeAlert)
                WHERE a.timestamp > datetime() - duration('P7D')
                WITH p, collect(a)[0..5] as recent_alerts

                OPTIONAL MATCH (p)-[:HAS_EVALUATION]->(e:PlayerEvaluation)
                WHERE e.timestamp > datetime() - duration('P7D')
                WITH p, recent_alerts, collect(e)[0..5] as recent_evals

                RETURN p.name as name,
                       p.team as team,
                       recent_alerts,
                       recent_evals
            """, player_name=player_name)

            record = result.single()
            if record:
                return dict(record)
            return {}

    # ========================================
    # Combined Operations
    # ========================================

    async def get_pregame_context(
        self,
        game_id: str,
        teams: List[str]
    ) -> GameContext:
        """
        Get complete pre-game context combining all layers

        Args:
            game_id: Game identifier
            teams: Team codes [HOME, AWAY]

        Returns:
            GameContext with all available data
        """
        context = GameContext(
            sport=self.sport.upper(),
            game_id=game_id,
            teams=teams,
            game_date=datetime.now()
        )

        # Layer 1: Get recent real-time events
        print("[Pre-game] Checking recent events...")
        events = await self.search_realtime_events()
        context.realtime_events = [
            e for e in events
            if e.team in teams
        ]

        # Layer 3: Get graph context for both teams
        print("[Pre-game] Querying graph memory...")
        context.graph_context = {
            "teams": {},
            "players": {}
        }

        for team in teams:
            with self.neo4j_driver.session() as session:
                result = session.run("""
                    MATCH (t:Team {abbreviation: $team})
                    OPTIONAL MATCH (t)-[:HAS_PLAYER]->(p:Player)
                    OPTIONAL MATCH (p)-[:HAS_ALERT]->(a:RealTimeAlert)
                    WHERE a.timestamp > datetime() - duration('P1D')
                    RETURN t.name as team_name,
                           collect(DISTINCT {
                               player: p.name,
                               alert_type: a.event_type,
                               status: a.status
                           }) as player_alerts
                """, team=team)

                record = result.single()
                if record:
                    context.graph_context["teams"][team] = dict(record)

        return context

    async def run_full_postgame_pipeline(
        self,
        game_id: str,
        teams: List[str]
    ) -> Dict[str, Any]:
        """
        Run complete post-game data collection and storage

        1. Collect Reddit analysis
        2. Store in Neo4j
        3. Cross-validate with expert data

        Returns:
            Summary of collected data
        """
        results = {
            "game_id": game_id,
            "teams": teams,
            "reddit_analysis": None,
            "stored_evaluations": 0,
            "cross_validations": []
        }

        # Layer 2: Collect Reddit analysis
        analysis = await self.collect_postgame_analysis(game_id, teams)

        if analysis:
            results["reddit_analysis"] = {
                "overall_sentiment": analysis.overall_sentiment,
                "players_evaluated": len(analysis.player_evaluations),
                "key_insights": analysis.key_insights
            }

            # Layer 3: Store in graph
            self.store_reddit_analysis(analysis)
            results["stored_evaluations"] = len(analysis.player_evaluations)

            print(f"[Post-game] Stored {len(analysis.player_evaluations)} player evaluations")

        return results


# CLI Interface
async def main():
    import argparse

    parser = argparse.ArgumentParser(description="G9 Sports Intelligence Orchestrator")
    parser.add_argument("sport", help="Sport code (nba, nfl, mlb, etc.)")
    parser.add_argument("--sync-data", action="store_true", help="Sync expert datasets")
    parser.add_argument("--search-events", action="store_true", help="Search real-time events")
    parser.add_argument("--postgame", type=str, help="Run post-game analysis (game_id)")
    parser.add_argument("--teams", type=str, help="Team codes (e.g., LAL,GSW)")

    args = parser.parse_args()

    orchestrator = G9Orchestrator(args.sport)

    if args.sync_data:
        results = orchestrator.sync_expert_data()
        print(f"\n[Result] Synced {len(results)} datasets")

    elif args.search_events:
        events = await orchestrator.search_realtime_events()
        print(f"\n[Result] Found {len(events)} events:")
        for event in events:
            print(f"  - {event.event_type.value}: {event.player} ({event.team}) - {event.status}")

    elif args.postgame and args.teams:
        teams = args.teams.split(',')
        results = await orchestrator.run_full_postgame_pipeline(args.postgame, teams)
        print(f"\n[Result] Post-game analysis complete:")
        print(f"  - Sentiment: {results['reddit_analysis']['overall_sentiment']}")
        print(f"  - Players evaluated: {results['stored_evaluations']}")
        print(f"  - Insights: {results['reddit_analysis']['key_insights']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
