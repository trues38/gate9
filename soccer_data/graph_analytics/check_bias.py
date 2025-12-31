from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7688"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password123"

def check_referee_bias():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    query = """
    MATCH (r:Referee)-[:OFFICIATED]->(m:Match)<-[:PLAYED_HOME]-(t:Team)
    WHERE r.strictness_index > 0.15
    RETURN r.name AS ref, t.name AS team, count(m) AS games, avg(m.home_score) AS avg_score, r.strictness_index AS strictness
    ORDER BY games DESC
    LIMIT 5
    """
    
    with driver.session() as session:
        result = session.run(query)
        print("\nReferee Bias/Insight Analysis (Strictness > 0.15):")
        for record in result:
            print(f" - Ref: {record['ref']} (Strictness: {record['strictness']:.3f}) | Team: {record['team']} | Games: {record['games']} | Avg Score: {record['avg_score']:.2f}")
    
    driver.close()

if __name__ == "__main__":
    check_referee_bias()
