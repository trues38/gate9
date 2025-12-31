import json
import glob
from neo4j import GraphDatabase
import os

class SoccerMatchIngestor:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def ingest_matches(self, league, season):
        """
        Ingests match results and details into Neo4j.
        """
        results_path = f"soccer_data/raw_data/understat/{league}/{season}/results.json"
        details_path = f"soccer_data/raw_data/understat/{league}/{season}/match_details.json"
        
        if not os.path.exists(results_path):
            return

        with open(results_path, 'r') as f:
            results = json.load(f)
        
        details_map = {}
        if os.path.exists(details_path):
            with open(details_path, 'r') as f:
                details = json.load(f)
                details_map = {d['match_id']: d for d in details}

        with self.driver.session() as session:
            for m in results:
                match_id = m['id']
                d = details_map.get(match_id, {})
                
                # Ingest Match and relationships
                session.run("""
                    MATCH (h:Team {name: $home_team})
                    MATCH (a:Team {name: $away_team})
                    MERGE (m:Match {id: $match_id})
                    SET m.date = $date,
                        m.league = $league,
                        m.home_score = $h_score,
                        m.away_score = $a_score,
                        m.h_xg = $h_xg,
                        m.a_xg = $a_xg,
                        m.referee = $referee
                    MERGE (h)-[:PLAYED_HOME]->(m)
                    MERGE (a)-[:PLAYED_AWAY]->(m)
                """, {
                    "home_team": m['h']['title'],
                    "away_team": m['a']['title'],
                    "match_id": match_id,
                    "date": m['datetime'],
                    "league": league,
                    "h_score": int(m['goals']['h']),
                    "a_score": int(m['goals']['a']),
                    "h_xg": float(m['xG']['h']),
                    "a_xg": float(m['xG']['a']),
                    "referee": d.get('referee', 'Unknown')
                })
                
                # OPTIONAL: Ingest lineups if details exist
                if 'lineups' in d:
                    # In a full impl, we would merge Player nodes here
                    pass

        print(f"Ingested matches for {league} {season}")

if __name__ == "__main__":
    # Placeholder for credentials
    print("Match Ingestor ready. Configuration required.")
