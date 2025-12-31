from soccer_data.ingestion.ingest_teams import SoccerIngestor
from soccer_data.ingestion.ingest_matches import SoccerMatchIngestor
from soccer_data.ingestion.ingest_referees import SoccerRefereeIngestor
import glob
import time

NEO4J_URI = "bolt://localhost:7688"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password123"

def run_full_ingestion():
    print("Starting Institutional Soccer Ingestion...")
    
    # 1. Ingest Teams
    print("--- Phase 1: Ingesting Teams ---")
    team_ingestor = SoccerIngestor(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    paths = glob.glob("soccer_data/raw_data/understat/*/2024/results.json")
    for p in paths:
        team_ingestor.ingest_teams(p)
    team_ingestor.close()
    
    # 2. Ingest Matches
    print("--- Phase 2: Ingesting Matches & Lineups ---")
    match_ingestor = SoccerMatchIngestor(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    leagues = ["EPL", "La_liga", "Bundesliga", "Serie_A", "Ligue_1"]
    for league in leagues:
        match_ingestor.ingest_matches(league, "2024")
    match_ingestor.close()
    
    # 3. Ingest Referees
    print("--- Phase 3: Ingesting Referees & Linking ---")
    ref_ingestor = SoccerRefereeIngestor(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    ref_ingestor.ingest_referees("soccer_data/processed/referee_stats.json")
    ref_ingestor.close()
    
    print("--- Ingestion Complete ---")

if __name__ == "__main__":
    # Wait a bit longer for Neo4j to be fully ready
    print("Waiting for Neo4j Port 7688 to warm up...")
    time.sleep(10)
    run_full_ingestion()
