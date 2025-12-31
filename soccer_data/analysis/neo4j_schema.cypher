// Soccer Graph Schema for Neo4J
// Hybrid SQLite + Neo4J Analysis

// ============================================================
// Node Types
// ============================================================

// Team node
// Properties: team_id, name, league
CREATE CONSTRAINT team_id IF NOT EXISTS FOR (t:Team) REQUIRE t.team_id IS UNIQUE;

// Match node
// Properties: match_id, date, home_score, away_score, home_xg, away_xg, league
CREATE CONSTRAINT match_id IF NOT EXISTS FOR (m:Match) REQUIRE m.match_id IS UNIQUE;

// League node
// Properties: league_id, name
CREATE CONSTRAINT league_id IF NOT EXISTS FOR (l:League) REQUIRE l.league_id IS UNIQUE;

// Season node
// Properties: season_id, year
CREATE CONSTRAINT season_id IF NOT EXISTS FOR (s:Season) REQUIRE s.season_id IS UNIQUE;

// ============================================================
// Relationships
// ============================================================

// Team played as home in Match
// (Team)-[:PLAYED_HOME {xg: float, score: int}]->(Match)

// Team played as away in Match
// (Team)-[:PLAYED_AWAY {xg: float, score: int}]->(Match)

// Match belongs to League
// (Match)-[:IN_LEAGUE]->(League)

// Match belongs to Season
// (Match)-[:IN_SEASON]->(Season)

// Match followed by Match (temporal)
// (Match)-[:FOLLOWED_BY {days_gap: int}]->(Match)

// Team's recent form (last 5 matches)
// (Team)-[:RECENT_FORM {matches: int, avg_xg: float, avg_goals: float}]->(Team)

// ============================================================
// Sample Queries for Hybrid Analysis
// ============================================================

// Query 1: Find teams that underperform xG
// MATCH (t:Team)-[p:PLAYED_HOME|PLAYED_AWAY]->(m:Match)
// WITH t,
//      SUM(p.score) as total_goals,
//      SUM(p.xg) as total_xg,
//      COUNT(m) as matches
// WHERE matches >= 5
// WITH t, total_goals, total_xg, matches,
//      total_goals - total_xg as xg_diff
// WHERE xg_diff < -5
// RETURN t.name, total_goals, total_xg, xg_diff
// ORDER BY xg_diff ASC

// Query 2: Find head-to-head patterns
// MATCH (t1:Team)-[:PLAYED_HOME]->(m:Match)<-[:PLAYED_AWAY]-(t2:Team)
// WHERE t1.team_id = 'liverpool' AND t2.team_id = 'man_city'
// RETURN m.date, m.home_score, m.away_score, m.home_xg, m.away_xg
// ORDER BY m.date DESC
// LIMIT 5

// Query 3: Find teams with strong recent form facing weak defense
// MATCH (attacker:Team)-[p1:PLAYED_HOME|PLAYED_AWAY]->(m1:Match)
// WHERE m1.date >= date() - duration({days: 30})
// WITH attacker, AVG(p1.xg) as recent_xg
// WHERE recent_xg > 1.8
// MATCH (defender:Team)-[p2:PLAYED_HOME|PLAYED_AWAY]->(m2:Match)
// WHERE m2.date >= date() - duration({days: 30})
// WITH attacker, recent_xg, defender, AVG(p2.xg) as conceded_xg
// WHERE conceded_xg > 1.8
// RETURN attacker.name, recent_xg, defender.name, conceded_xg
// ORDER BY recent_xg DESC, conceded_xg DESC

// Query 4: Temporal patterns - performance after rest days
// MATCH (t:Team)-[p:PLAYED_HOME|PLAYED_AWAY]->(m1:Match)-[:FOLLOWED_BY]->(m2:Match)<-[p2:PLAYED_HOME|PLAYED_AWAY]-(t)
// WHERE m1.days_gap >= 7
// RETURN t.name, AVG(p2.xg) as xg_after_rest
// ORDER BY xg_after_rest DESC

// Query 5: League-wide patterns
// MATCH (m:Match)-[:IN_LEAGUE]->(l:League)
// WHERE l.league_id = 'EPL'
// RETURN AVG(m.home_xg) as avg_home_xg,
//        AVG(m.away_xg) as avg_away_xg,
//        AVG(m.home_score) as avg_home_goals,
//        AVG(m.away_score) as avg_away_goals
