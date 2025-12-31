import pandas as pd
import glob
from neo4j import GraphDatabase
import os

NEO4J_URI = "bolt://localhost:7688"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password123"

def enrich_referees_from_csv():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    odds_files = glob.glob("soccer_data/raw_data/historical_odds/*.csv")
    
    with driver.session() as session:
        for f in odds_files:
            print(f"Enriching from {f}...")
            df = pd.read_csv(f, encoding='unicode_escape')
            if 'Referee' not in df.columns: continue
            
            for _, row in df.iterrows():
                h_team = row['HomeTeam']
                a_team = row['AwayTeam']
                referee = row['Referee']
                
                # Simple name matching to find the Match node
                # Note: Match nodes have full titles, CSV has abbreviations sometimes
                # Using fuzzy match or substring
                session.run("""
                    MATCH (h:Team) WHERE h.name CONTAINS $h_team
                    MATCH (a:Team) WHERE a.name CONTAINS $a_team
                    MATCH (h)-[:PLAYED_HOME]->(m:Match)<-[:PLAYED_AWAY]-(a)
                    SET m.referee = $ref
                """, {"h_team": h_team[:10], "a_team": a_team[:10], "ref": referee})
    
    # After enrichment, re-run the link to Referee nodes
    print("Re-linking Referee nodes...")
    with driver.session() as session:
        session.run("""
            MATCH (m:Match)
            MATCH (r:Referee {name: m.referee})
            MERGE (r)-[:OFFICIATED]->(m)
        """)
        
    driver.close()
    print("Enrichment complete.")

if __name__ == "__main__":
    enrich_referees_from_csv()
