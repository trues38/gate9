#!/usr/bin/env python3
"""
Soccer Neo4j Ingestion Script v1.0

Loads relational/pattern data into Neo4j following the v1.0 architecture:
- Teams with league relationships
- Managers with tactic preferences
- Referees with context biases
- Team rivalries and patterns

Uses Common IDs shared with SQLite:
- team_id, manager_id, referee_id, match_id
"""

import json
import sqlite3
from pathlib import Path
from neo4j import GraphDatabase
import logging
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
SQLITE_PATH = BASE_DIR / "data" / "soccer.db"
SCHEMA_PATH = BASE_DIR / "schema" / "soccer_neo4j_schema.cypher"
PROCESSED_DATA = BASE_DIR / "processed"

# Neo4j connection (VPS)
NEO4J_URI = 'bolt://localhost:7688'
NEO4J_USER = 'neo4j'
NEO4J_PASSWORD = 'g9secret2024'


class SoccerGraphLoader:
    def __init__(self, neo4j_uri=NEO4J_URI, neo4j_user=NEO4J_USER, neo4j_password=NEO4J_PASSWORD):
        self.neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.sqlite_conn = None

    def close(self):
        self.neo4j_driver.close()
        if self.sqlite_conn:
            self.sqlite_conn.close()

    def connect_sqlite(self):
        """Connect to SQLite to read Common IDs"""
        if SQLITE_PATH.exists():
            self.sqlite_conn = sqlite3.connect(str(SQLITE_PATH))
            self.sqlite_conn.row_factory = sqlite3.Row
            logger.info(f"Connected to SQLite: {SQLITE_PATH}")
        else:
            logger.warning("SQLite database not found. Run ingest_to_sqlite.py first.")

    def init_schema(self):
        """Initialize Neo4j schema from Cypher file"""
        with open(SCHEMA_PATH, 'r') as f:
            schema_cypher = f.read()

        # Split by semicolon and execute each statement
        statements = [s.strip() for s in schema_cypher.split(';') if s.strip() and not s.strip().startswith('//')]

        with self.neo4j_driver.session() as session:
            for stmt in statements:
                # Skip comment lines and query examples
                if stmt.startswith('//') or 'RETURN' in stmt.upper():
                    continue
                try:
                    session.run(stmt)
                except Exception as e:
                    # Ignore constraint/index already exists errors
                    if 'already exists' not in str(e).lower():
                        logger.warning(f"Schema statement warning: {e}")

        logger.info("Neo4j schema initialized")

    def load_teams_from_sqlite(self):
        """Load teams from SQLite and create graph nodes"""
        if not self.sqlite_conn:
            self.connect_sqlite()

        if not self.sqlite_conn:
            return 0

        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT DISTINCT team_id, name, league FROM teams")

        count = 0
        with self.neo4j_driver.session() as session:
            for row in cursor:
                session.run('''
                    MERGE (t:Team {team_id: $team_id})
                    SET t.name = $name, t.league = $league
                    WITH t
                    MATCH (l:League {name: $league})
                    MERGE (t)-[:PLAYS_IN]->(l)
                ''', team_id=row['team_id'], name=row['name'], league=row['league'])
                count += 1

        logger.info(f"Loaded {count} teams to Neo4j")
        return count

    def load_managers_from_json(self):
        """Load managers with tactical preferences"""
        manager_file = PROCESSED_DATA / "manager_database.json"
        if not manager_file.exists():
            logger.warning("Manager database not found")
            return 0

        with open(manager_file, 'r') as f:
            managers = json.load(f)

        count = 0
        with self.neo4j_driver.session() as session:
            for team_name, data in managers.items():
                manager_id = self._normalize_id(data['name'])
                team_id = self._normalize_id(team_name)

                # Create manager
                session.run('''
                    MERGE (m:Manager {manager_id: $manager_id})
                    SET m.name = $name,
                        m.nationality = $nationality
                ''', manager_id=manager_id, name=data['name'],
                    nationality=data.get('nationality', ''))

                # Link to team
                session.run('''
                    MATCH (m:Manager {manager_id: $manager_id})
                    MATCH (t:Team {team_id: $team_id})
                    MERGE (m)-[:MANAGES {since: $since}]->(t)
                ''', manager_id=manager_id, team_id=team_id,
                    since=data.get('appointed', ''))

                # Link to preferred formation
                if data.get('preferred_formation'):
                    session.run('''
                        MATCH (m:Manager {manager_id: $manager_id})
                        MERGE (f:Formation {name: $formation})
                        MERGE (m)-[:USES {frequency: 0.7, primary: true}]->(f)
                    ''', manager_id=manager_id, formation=data['preferred_formation'])

                # Link to tactical style
                tactic = self._map_tactical_style(data.get('tactical_style', ''))
                if tactic:
                    session.run('''
                        MATCH (m:Manager {manager_id: $manager_id})
                        MATCH (tac:Tactic {name: $tactic})
                        MERGE (m)-[:PREFERS {confidence: 0.9}]->(tac)
                    ''', manager_id=manager_id, tactic=tactic)

                # Pressing intensity -> high_press tactic link
                if data.get('pressing_intensity') in ['high', 'very_high']:
                    session.run('''
                        MATCH (m:Manager {manager_id: $manager_id})
                        MATCH (tac:Tactic {name: 'high_press'})
                        MERGE (m)-[:PREFERS {confidence: $conf}]->(tac)
                    ''', manager_id=manager_id,
                        conf=0.95 if data.get('pressing_intensity') == 'very_high' else 0.8)

                # Link Team -> Tactic (KEY ADDITION #2)
                if tactic:
                    session.run('''
                        MATCH (t:Team {team_id: $team_id})
                        MATCH (tac:Tactic {name: $tactic})
                        MERGE (t)-[:APPLIES {
                            confidence: 0.85,
                            since: $since,
                            until: null,
                            intensity: $intensity
                        }]->(tac)
                    ''', team_id=team_id, tactic=tactic,
                        since=data.get('appointed', ''),
                        intensity=data.get('pressing_intensity', 'medium'))

                count += 1

        logger.info(f"Loaded {count} managers with tactics to Neo4j")
        return count

    def load_referees_from_sqlite(self):
        """Load referees and create context bias relationships"""
        if not self.sqlite_conn:
            self.connect_sqlite()

        if not self.sqlite_conn:
            return 0

        cursor = self.sqlite_conn.cursor()
        cursor.execute("""
            SELECT referee_id, name,
                   SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) as home_wins,
                   SUM(CASE WHEN away_score > home_score THEN 1 ELSE 0 END) as away_wins,
                   COUNT(*) as total_matches
            FROM referees r
            JOIN matches m ON r.referee_id = m.referee_id
            WHERE m.home_score IS NOT NULL
            GROUP BY r.referee_id
        """)

        count = 0
        with self.neo4j_driver.session() as session:
            for row in cursor:
                if not row['referee_id']:
                    continue

                # Create referee
                session.run('''
                    MERGE (r:Referee {referee_id: $referee_id})
                    SET r.name = $name
                ''', referee_id=row['referee_id'], name=row['name'])

                # Calculate home bias (KEY ADDITION #3)
                if row['total_matches'] and row['total_matches'] > 5:
                    home_win_rate = row['home_wins'] / row['total_matches']
                    # Average EPL home win rate is ~46%, so bias = rate - 0.46
                    home_bias = round(home_win_rate - 0.46, 3)

                    session.run('''
                        MATCH (r:Referee {referee_id: $referee_id})
                        MATCH (c:Context {name: 'home_team'})
                        MERGE (r)-[:FAVORS {
                            bias_score: $bias,
                            sample_size: $sample,
                            confidence: $conf
                        }]->(c)
                    ''', referee_id=row['referee_id'],
                        bias=home_bias,
                        sample=row['total_matches'],
                        conf=min(0.95, row['total_matches'] / 50))

                count += 1

        logger.info(f"Loaded {count} referees with bias to Neo4j")
        return count

    def load_rivalries(self):
        """Create team rivalry relationships"""
        rivalries = [
            # EPL
            ('arsenal', 'tottenham', 'North London Derby', 'derby'),
            ('liverpool', 'everton', 'Merseyside Derby', 'derby'),
            ('man_united', 'man_city', 'Manchester Derby', 'derby'),
            ('man_united', 'liverpool', 'North-West Derby', 'derby'),
            ('chelsea', 'arsenal', 'London Derby', 'derby'),
            ('chelsea', 'tottenham', 'London Derby', 'derby'),
            ('west_ham', 'tottenham', 'London Derby', 'derby'),
            # LaLiga
            ('barcelona', 'real_madrid', 'El Clasico', 'derby'),
            ('atletico_madrid', 'real_madrid', 'Madrid Derby', 'derby'),
            ('real_betis', 'sevilla', 'Seville Derby', 'derby'),
            # Bundesliga
            ('borussia_dortmund', 'bayern_munich', 'Der Klassiker', 'derby'),
            # SerieA
            ('inter_milan', 'ac_milan', 'Derby della Madonnina', 'derby'),
            ('juventus', 'inter_milan', 'Derby dItalia', 'derby'),
            ('roma', 'lazio', 'Derby della Capitale', 'derby'),
            # Ligue1
            ('paris_sg', 'marseille', 'Le Classique', 'derby'),
            ('lyon', 'saint_etienne', 'Derby Rhone-Alpes', 'derby'),
        ]

        with self.neo4j_driver.session() as session:
            for home, away, name, rivalry_type in rivalries:
                session.run('''
                    MATCH (t1:Team) WHERE t1.team_id CONTAINS $home
                    MATCH (t2:Team) WHERE t2.team_id CONTAINS $away
                    MERGE (t1)-[:RIVALS {type: $type, name: $name}]-(t2)
                ''', home=home, away=away, type=rivalry_type, name=name)

        logger.info(f"Created {len(rivalries)} rivalry relationships")

    def load_patterns(self):
        """Link teams to betting patterns"""
        # This would be enhanced with actual pattern detection
        # For now, create base pattern nodes (already done in schema)
        logger.info("Pattern nodes created via schema initialization")

    def _normalize_id(self, name: str) -> str:
        """Normalize names to IDs"""
        name = name.lower()
        name = re.sub(r"['\s\-\.]+", '_', name)
        name = re.sub(r'_+', '_', name)
        return name.strip('_')

    def _map_tactical_style(self, style: str) -> str:
        """Map tactical style descriptions to Tactic node names"""
        style_map = {
            'possession-based': 'possession_based',
            'possession': 'possession_based',
            'attacking-transition': 'counter_attack',
            'transition': 'counter_attack',
            'counter-attacking': 'counter_attack',
            'direct': 'direct_play',
            'defensive': 'low_block',
            'gegenpressing': 'gegenpressing',
            'high-pressing': 'high_press',
            'attacking': 'high_press',
        }
        return style_map.get(style.lower().replace(' ', '-'), '')

    def get_stats(self):
        """Get Neo4j graph statistics"""
        with self.neo4j_driver.session() as session:
            result = session.run('''
                MATCH (n)
                RETURN labels(n)[0] as label, count(*) as count
                ORDER BY count DESC
            ''')
            node_stats = {r['label']: r['count'] for r in result}

            result = session.run('''
                MATCH ()-[r]->()
                RETURN type(r) as type, count(*) as count
                ORDER BY count DESC
            ''')
            rel_stats = {r['type']: r['count'] for r in result}

            return {'nodes': node_stats, 'relationships': rel_stats}


def main():
    loader = SoccerGraphLoader()

    try:
        # Initialize schema
        logger.info("Initializing Neo4j schema...")
        loader.init_schema()

        # Connect to SQLite for Common IDs
        loader.connect_sqlite()

        # Load data
        logger.info("\n=== Loading Teams ===")
        loader.load_teams_from_sqlite()

        logger.info("\n=== Loading Managers with Tactics ===")
        loader.load_managers_from_json()

        logger.info("\n=== Loading Referees with Bias ===")
        loader.load_referees_from_sqlite()

        logger.info("\n=== Creating Rivalries ===")
        loader.load_rivalries()

        logger.info("\n=== Loading Patterns ===")
        loader.load_patterns()

        # Print stats
        stats = loader.get_stats()
        logger.info("\n=== Neo4j Graph Statistics ===")
        logger.info("Nodes:")
        for label, count in stats['nodes'].items():
            logger.info(f"  {label}: {count}")
        logger.info("Relationships:")
        for rel_type, count in stats['relationships'].items():
            logger.info(f"  {rel_type}: {count}")

    finally:
        loader.close()


if __name__ == "__main__":
    main()
