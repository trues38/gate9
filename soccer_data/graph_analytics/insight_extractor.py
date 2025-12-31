from neo4j import GraphDatabase
import pandas as pd
import json

NEO4J_URI = "bolt://localhost:7688"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password123"

class SoccerInsightExtractor:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self.driver.close()

    def get_referee_team_deadlock_analysis(self):
        """
        Insight 1: Identify specific Team-Referee combinations that lead to low-scoring 'Deadlocks'.
        """
        query = """
        MATCH (r:Referee)-[:OFFICIATED]->(m:Match)<-[:PLAYED_HOME|PLAYED_AWAY]-(t:Team)
        WHERE r.strictness_index > 0.18
        WITH r, t, count(m) as games, avg(m.home_score + m.away_score) as avg_total_goals
        WHERE games >= 2
        RETURN r.name as referee, t.name as team, games, avg_total_goals
        ORDER BY avg_total_goals ASC
        LIMIT 10
        """
        with self.driver.session() as session:
            return [dict(record) for record in session.run(query)]

    def get_xg_overperformance_anomalies(self):
        """
        Insight 2: Identify teams that consistently over-perform their xG in the presence of specific conditions.
        """
        query = """
        MATCH (t:Team)-[:PLAYED_HOME]->(m:Match)
        WHERE m.home_score > m.h_xg + 1.5
        RETURN t.name as team, m.date as date, m.home_score as actual, m.h_xg as expected, m.referee as referee
        ORDER BY (m.home_score - m.h_xg) DESC
        LIMIT 10
        """
        with self.driver.session() as session:
            return [dict(record) for record in session.run(query)]

    def get_market_inefficiency_by_league(self):
        """
        Insight 3: Connect ML Regime data (from backtest_results.csv) with graph match nodes to find league-specific edges.
        """
        # This part uses the processed CSV linked with graph thinking
        df = pd.read_csv("soccer_data/processed/regime_classified_results.csv")
        summary = df.groupby(['regime_name']).agg({'edge': 'mean', 'match': 'count'}).to_dict()
        return summary

if __name__ == "__main__":
    extractor = SoccerInsightExtractor()
    
    print("--- 1. Referee Deadlock Analysis ---")
    deadlocks = extractor.get_referee_team_deadlock_analysis()
    for d in deadlocks: print(d)
    
    print("\n--- 2. xG Overperformance Anomalies ---")
    anomalies = extractor.get_xg_overperformance_anomalies()
    for a in anomalies: print(a)
    
    extractor.close()
