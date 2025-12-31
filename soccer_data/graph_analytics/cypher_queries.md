# Deep Soccer Graph Analysis: Cypher Queries

These queries represent the "Institutional Level" analysis that leverages the power of Neo4j.

## 1. Structural Twin Discovery

Find 3 historical matches that most closely resemble the "Current State" based on xG differential and Team Form.

```cypher
MATCH (h1:Team {name: $home_team})-[r1:PLAYED_HOME]->(m1:Match)
MATCH (a1:Team {name: $away_team})-[r2:PLAYED_AWAY]->(m1:Match)
WITH m1, abs(m1.h_xg - $current_h_xg) + abs(m1.a_xg - $current_a_xg) AS xg_dist
ORDER BY xg_dist ASC
LIMIT 3
RETURN m1.date, m1.home_score, m1.away_score, m1.h_xg, m1.a_xg, xg_dist;
```

## 2. Referee Strictness x Tactical Risk Analysis

Detect if a high-pressing team (high xG, many fouls) has a historical penalty when officiating with a strict referee.

```cypher
MATCH (r:Referee)-[o:OFFICIATED]->(m:Match)<-[ph:PLAYED_HOME]-(t:Team)
WHERE r.strictness_index > 0.18  // Strict Ref
  AND m.h_xg > 1.5              // High Pressure/Attack Team
RETURN t.name, count(m) AS strict_ref_matches, avg(m.home_score) AS avg_goals, r.avg_yellow AS ref_avg_y
ORDER BY strict_ref_matches DESC;
```

## 3. Manager Tactical Regime Signature (Neo4j RAG)

Querying the relationship between a Manager's tactical node and team performance outliers.

```cypher
MATCH (man:Manager)-[:MANAGES]->(t:Team)-[:PLAYED_HOME|PLAYED_AWAY]->(m:Match)
WHERE m.home_score - m.h_xg > 1.0  // "Lucly" over-performance regime
RETURN man.name, count(m) AS lucky_matches, avg(m.h_xg) AS avg_expected_goals;
```
