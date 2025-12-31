import json
import glob
from neo4j import GraphDatabase
import os

class SoccerIngestor:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def ingest_teams(self, results_path):
        """
        Extracts and ingests teams from Understat results.json.
        """
        with open(results_path, 'r') as f:
            results = json.load(f)
        
        teams = set()
        for match in results:
            teams.add(match['h']['title'])
            teams.add(match['a']['title'])
        
        with self.driver.session() as session:
            for team_name in teams:
                session.run("""
                    MERGE (t:Team {name: $name})
                    ON CREATE SET t.created_at = timestamp()
                """, name=team_name)
        
        print(f"Ingested {len(teams)} teams from {results_path}")

if __name__ == "__main__":
    # Placeholder for credentials - in local dev, these would be in .env
    # NEO4J_URI = "bolt://localhost:7687"
    # NEO4J_USER = "neo4j"
    # NEO4J_PASSWORD = "password"
    
    # ingestor = SoccerIngestor(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    # paths = glob.glob("soccer_data/raw_data/understat/*/2024/results.json")
    # for p in paths:
    #     ingestor.ingest_teams(p)
    # ingestor.close()
    print("Ingestion script ready. Requires Neo4j connection.")
