#!/usr/bin/env python3
"""
Neo4j Dual Regime Loader
=========================
Loads dual regime data into Neo4j graph database.
Creates nodes for MacroState, DualRegime, Stock, and Outcome.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.sector_mapping import TICKER_TO_SECTOR

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logger.error("Neo4j driver not installed: pip install neo4j")


class DualRegimeNeo4jLoader:
    """Loads dual regime data into Neo4j"""

    def __init__(self, uri: str = None, user: str = None, password: str = None, database: str = None):
        if not NEO4J_AVAILABLE:
            raise ImportError("Neo4j driver not available")

        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7688")
        self.user = user or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "regime2025")
        self.database = database or os.getenv("NEO4J_DATABASE", "neo4j")

        self.driver = None

    def connect(self) -> bool:
        """Connect to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )

            # Test connection
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 AS num")
                result.single()

            logger.info(f"✅ Connected to Neo4j: {self.uri}, database: {self.database}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect to Neo4j: {e}")
            logger.error(f"   URI: {self.uri}")
            logger.error(f"   Database: {self.database}")
            logger.error(f"   Make sure Neo4j is running and the database exists")
            return False

    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def create_schema(self):
        """Create Neo4j schema (constraints and indexes)"""
        logger.info("Creating Neo4j schema...")

        with self.driver.session(database=self.database) as session:
            # Constraints (ensure uniqueness)
            constraints = [
                """CREATE CONSTRAINT macro_state_id IF NOT EXISTS
                   FOR (m:MacroState) REQUIRE m.id IS UNIQUE""",
                """CREATE CONSTRAINT dual_regime_id IF NOT EXISTS
                   FOR (d:DualRegime) REQUIRE d.regime_id IS UNIQUE""",
                """CREATE CONSTRAINT stock_ticker IF NOT EXISTS
                   FOR (s:Stock) REQUIRE s.ticker IS UNIQUE""",
                """CREATE CONSTRAINT outcome_id IF NOT EXISTS
                   FOR (o:Outcome) REQUIRE o.id IS UNIQUE"""
            ]

            for constraint_query in constraints:
                try:
                    session.run(constraint_query)
                except Exception as e:
                    logger.warning(f"Constraint may already exist: {e}")

            # Indexes (optimize queries)
            indexes = [
                "CREATE INDEX dual_regime_date IF NOT EXISTS FOR (d:DualRegime) ON (d.date)",
                "CREATE INDEX dual_regime_macro IF NOT EXISTS FOR (d:DualRegime) ON (d.macro_state)",
                "CREATE INDEX dual_regime_sector IF NOT EXISTS FOR (d:DualRegime) ON (d.sector)",
                "CREATE INDEX outcome_return_3m IF NOT EXISTS FOR (o:Outcome) ON (o.return_3m)",
                "CREATE INDEX stock_sector IF NOT EXISTS FOR (s:Stock) ON (s.sector)"
            ]

            for index_query in indexes:
                try:
                    session.run(index_query)
                except Exception as e:
                    logger.warning(f"Index may already exist: {e}")

        logger.info("✅ Schema created successfully")

    def load_stocks(self):
        """Load stock metadata"""
        logger.info("Loading stock metadata...")

        with self.driver.session(database=self.database) as session:
            count = 0
            for ticker, sector in TICKER_TO_SECTOR.items():
                market = "KR" if ticker.endswith(".KS") else "US"

                session.run("""
                    MERGE (s:Stock {ticker: $ticker})
                    SET s.sector = $sector,
                        s.market = $market,
                        s.updated_at = datetime()
                """, {
                    "ticker": ticker,
                    "sector": sector,
                    "market": market
                })
                count += 1

        logger.info(f"✅ Loaded {count} stocks")

    def load_macro_state(self, date: str, state: str, confidence: float):
        """Load a single macro state node"""
        with self.driver.session(database=self.database) as session:
            state_id = f"{state}_{date}"

            session.run("""
                MERGE (m:MacroState {id: $state_id})
                SET m.name = $state,
                    m.date = $date,
                    m.confidence = $confidence,
                    m.updated_at = datetime()
            """, {
                "state_id": state_id,
                "state": state,
                "date": date,
                "confidence": confidence
            })

    def load_dual_regimes(self, date: str, macro_state: str, sector_regimes: Dict[str, str]):
        """
        Load dual regimes for a specific date

        Args:
            date: Date string (YYYY-MM-DD)
            macro_state: Dominant macro state (e.g., 'LIQUIDITY_STRESS')
            sector_regimes: Dict mapping sector -> phase (e.g., {'SEMICONDUCTORS': 'RECOVERY'})
        """
        with self.driver.session(database=self.database) as session:
            # Create DualRegime nodes for each sector
            for sector, phase in sector_regimes.items():
                regime_id = f"{macro_state}_{sector}_{phase}_{date}"

                session.run("""
                    MERGE (d:DualRegime {regime_id: $regime_id})
                    SET d.macro_state = $macro_state,
                        d.sector = $sector,
                        d.sector_phase = $phase,
                        d.date = $date,
                        d.updated_at = datetime()

                    WITH d
                    MATCH (m:MacroState {id: $state_id})
                    MERGE (m)-[:FORMS_DUAL_REGIME]->(d)
                """, {
                    "regime_id": regime_id,
                    "macro_state": macro_state,
                    "sector": sector,
                    "phase": phase,
                    "date": date,
                    "state_id": f"{macro_state}_{date}"
                })

    def load_outcome(self, ticker: str, date: str, regime_id: str, returns: Dict[str, float]):
        """
        Load outcome for a stock in a dual regime

        Args:
            ticker: Stock ticker
            date: Date string
            regime_id: DualRegime regime_id
            returns: Dict with keys: return_1m, return_3m, return_6m, max_dd_1m, max_dd_3m, max_dd_6m, sharpe_3m
        """
        with self.driver.session(database=self.database) as session:
            outcome_id = f"{ticker}_{regime_id}"

            session.run("""
                MATCH (s:Stock {ticker: $ticker})
                MATCH (d:DualRegime {regime_id: $regime_id})

                MERGE (o:Outcome {id: $outcome_id})
                SET o.ticker = $ticker,
                    o.date = $date,
                    o.return_1m = $return_1m,
                    o.return_3m = $return_3m,
                    o.return_6m = $return_6m,
                    o.max_dd_1m = $max_dd_1m,
                    o.max_dd_3m = $max_dd_3m,
                    o.max_dd_6m = $max_dd_6m,
                    o.sharpe_3m = $sharpe_3m,
                    o.updated_at = datetime()

                MERGE (s)-[:PERFORMED_IN]->(d)
                MERGE (d)-[:RESULTED_IN]->(o)
            """, {
                "ticker": ticker,
                "regime_id": regime_id,
                "outcome_id": outcome_id,
                "date": date,
                **returns
            })

    def load_outcomes_batch(self, outcomes: List[Dict]) -> int:
        """
        Load multiple outcomes in batch for performance

        Args:
            outcomes: List of dicts with keys: ticker, date, regime_id, returns

        Returns:
            Number of outcomes loaded
        """
        with self.driver.session(database=self.database) as session:
            for outcome in outcomes:
                try:
                    self.load_outcome(
                        ticker=outcome['ticker'],
                        date=outcome['date'],
                        regime_id=outcome['regime_id'],
                        returns=outcome['returns']
                    )
                except Exception as e:
                    logger.error(f"Failed to load outcome for {outcome.get('ticker')}: {e}")

        return len(outcomes)

    def get_stats(self) -> Dict:
        """Get database statistics"""
        with self.driver.session(database=self.database) as session:
            # Count nodes
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] AS label, count(*) AS count
            """)

            node_counts = {record["label"]: record["count"] for record in result}

            # Count relationships
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) AS rel_type, count(*) AS count
            """)

            rel_counts = {record["rel_type"]: record["count"] for record in result}

            return {
                "nodes": node_counts,
                "relationships": rel_counts
            }

    def print_stats(self):
        """Print database statistics"""
        stats = self.get_stats()

        logger.info(f"\n{'='*60}")
        logger.info("NEO4J DATABASE STATISTICS")
        logger.info(f"{'='*60}")

        logger.info("\nNodes:")
        for label, count in stats["nodes"].items():
            logger.info(f"  {label}: {count:,}")

        logger.info("\nRelationships:")
        for rel_type, count in stats["relationships"].items():
            logger.info(f"  {rel_type}: {count:,}")

        logger.info(f"{'='*60}\n")


if __name__ == "__main__":
    loader = DualRegimeNeo4jLoader()

    if loader.connect():
        loader.create_schema()
        loader.load_stocks()
        loader.print_stats()
        loader.close()
    else:
        logger.error("Cannot proceed without Neo4j connection")
