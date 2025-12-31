import json
from neo4j import GraphDatabase
import os

class SoccerTwinFinder:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def find_structural_twins(self, home_team, away_team, current_h_xg, current_a_xg):
        """
        Queries Neo4j for matches with the same matchup and similar xG signatures.
        """
        query = """
        MATCH (h:Team {name: $home})-[:PLAYED_HOME]->(m:Match)<-[:PLAYED_AWAY]-(a:Team {name: $away})
        WITH m, abs(m.h_xg - $h_xg) + abs(m.a_xg - $a_xg) AS similarity
        ORDER BY similarity ASC
        LIMIT 5
        RETURN m.date AS date, m.home_score AS h_score, m.away_score AS a_score, 
               m.h_xg AS h_xg, m.a_xg AS a_xg, similarity, m.referee AS ref
        """
        
        with self.driver.session() as session:
            result = session.run(query, {
                "home": home_team,
                "away": away_team,
                "h_xg": current_h_xg,
                "a_xg": current_a_xg
            })
            twins = [dict(record) for record in result]
            
        return twins

if __name__ == "__main__":
    # Example logic
    print("Graph Twin Finder initialized. Requires Neo4j dataset to be ingested.")
    # finder = SoccerTwinFinder("bolt://localhost:7687", "neo4j", "password")
    # twins = finder.find_structural_twins("Man United", "Liverpool", 1.5, 1.2)
    # print(twins)
