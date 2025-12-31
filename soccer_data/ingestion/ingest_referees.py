import json
from neo4j import GraphDatabase
import os

class SoccerRefereeIngestor:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def ingest_referees(self, stats_path):
        """
        Ingests calculated referee stats into Neo4j.
        """
        if not os.path.exists(stats_path):
            print(f"Stats not found at {stats_path}")
            return

        with open(stats_path, 'r') as f:
            ref_stats = json.load(f)

        with self.driver.session() as session:
            for ref_name, stats in ref_stats.items():
                session.run("""
                    MERGE (r:Referee {name: $name})
                    SET r.avg_yellow = $avg_y,
                        r.avg_red = $avg_r,
                        r.strictness_index = $strictness,
                        r.total_games = $games
                """, {
                    "name": ref_name,
                    "avg_y": stats.get('avg_yellow', 0),
                    "avg_r": stats.get('avg_red', 0),
                    "strictness": stats.get('strictness_index', 0),
                    "games": stats.get('games', 0)
                })
                
                # Link existing Match nodes to this Referee
                session.run("""
                    MATCH (m:Match {referee: $name})
                    MATCH (r:Referee {name: $name})
                    MERGE (r)-[:OFFICIATED]->(m)
                """, {"name": ref_name})

        print(f"Ingested {len(ref_stats)} referees and linked to matches.")

if __name__ == "__main__":
    print("Referee Ingestor ready.")
