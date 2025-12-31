from soccer_data.graph_analytics.twin_finder import SoccerTwinFinder
import json

NEO4J_URI = "bolt://localhost:7688"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password123"

def test_graph_analysis():
    print("Executing Graph Intelligence Test...")
    finder = SoccerTwinFinder(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    # Test: Find structural twins for Man United vs Fulham (EPL Match 1)
    # Target match xG was roughly 2.0 vs 0.4
    twins = finder.find_structural_twins("Manchester United", "Fulham", 2.0, 0.4)
    
    print(f"\nFound {len(twins)} Structural Twins in historical data:")
    for t in twins:
        print(f" - Date: {t['date']} | Score: {t['h_score']}-{t['a_score']} | xG: {t['h_xg']:.2f}-{t['a_xg']:.2f} | Similarity: {t['similarity']:.4f}")
    
    finder.close()

if __name__ == "__main__":
    test_graph_analysis()
