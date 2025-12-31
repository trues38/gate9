// =============================================================================
// Soccer Neo4j Schema v1.0
// 관계/패턴/맥락 데이터 전용 (Graph RAG)
// Common IDs: match_id, team_id, manager_id, referee_id shared with SQLite
// =============================================================================

// =============================================================================
// CONSTRAINTS & INDEXES
// =============================================================================

// Core Entity Constraints (Common IDs)
CREATE CONSTRAINT team_id IF NOT EXISTS FOR (t:Team) REQUIRE t.team_id IS UNIQUE;
CREATE CONSTRAINT manager_id IF NOT EXISTS FOR (m:Manager) REQUIRE m.manager_id IS UNIQUE;
CREATE CONSTRAINT referee_id IF NOT EXISTS FOR (r:Referee) REQUIRE r.referee_id IS UNIQUE;
CREATE CONSTRAINT player_id IF NOT EXISTS FOR (p:Player) REQUIRE p.player_id IS UNIQUE;
CREATE CONSTRAINT match_id IF NOT EXISTS FOR (m:Match) REQUIRE m.match_id IS UNIQUE;

// Pattern & Tactic Constraints
CREATE CONSTRAINT tactic_name IF NOT EXISTS FOR (t:Tactic) REQUIRE t.name IS UNIQUE;
CREATE CONSTRAINT formation_name IF NOT EXISTS FOR (f:Formation) REQUIRE f.name IS UNIQUE;
CREATE CONSTRAINT pattern_id IF NOT EXISTS FOR (p:Pattern) REQUIRE p.pattern_id IS UNIQUE;
CREATE CONSTRAINT context_name IF NOT EXISTS FOR (c:Context) REQUIRE c.name IS UNIQUE;
CREATE CONSTRAINT league_name IF NOT EXISTS FOR (l:League) REQUIRE l.name IS UNIQUE;

// Indexes
CREATE INDEX team_league IF NOT EXISTS FOR (t:Team) ON (t.league);
CREATE INDEX match_date IF NOT EXISTS FOR (m:Match) ON (m.date);
CREATE INDEX match_league IF NOT EXISTS FOR (m:Match) ON (m.league);

// =============================================================================
// CORE NODES
// =============================================================================

// Leagues (5대 리그)
MERGE (l:League {name: 'EPL'}) SET l.country = 'England', l.full_name = 'Premier League';
MERGE (l:League {name: 'LaLiga'}) SET l.country = 'Spain', l.full_name = 'La Liga';
MERGE (l:League {name: 'Bundesliga'}) SET l.country = 'Germany', l.full_name = 'Bundesliga';
MERGE (l:League {name: 'SerieA'}) SET l.country = 'Italy', l.full_name = 'Serie A';
MERGE (l:League {name: 'Ligue1'}) SET l.country = 'France', l.full_name = 'Ligue 1';

// =============================================================================
// CONTEXT NODES (Referee Bias Contexts)
// =============================================================================

// Match Contexts for referee bias analysis
MERGE (c:Context {name: 'home_team'}) SET c.description = 'Referee behavior toward home teams';
MERGE (c:Context {name: 'away_team'}) SET c.description = 'Referee behavior toward away teams';
MERGE (c:Context {name: 'big_team'}) SET c.description = 'Referee behavior toward top 6/big clubs';
MERGE (c:Context {name: 'small_team'}) SET c.description = 'Referee behavior toward smaller clubs';
MERGE (c:Context {name: 'derby'}) SET c.description = 'Referee behavior in derby matches';
MERGE (c:Context {name: 'title_race'}) SET c.description = 'Referee behavior in title-deciding matches';
MERGE (c:Context {name: 'relegation'}) SET c.description = 'Referee behavior in relegation battles';

// =============================================================================
// TACTIC NODES (전술 노드)
// =============================================================================

// 주요 전술 스타일
MERGE (t:Tactic {name: 'high_press'}) SET t.description = 'High intensity pressing from front';
MERGE (t:Tactic {name: 'gegenpressing'}) SET t.description = 'Counter-pressing immediately after losing ball';
MERGE (t:Tactic {name: 'low_block'}) SET t.description = 'Deep defensive line, compact shape';
MERGE (t:Tactic {name: 'mid_block'}) SET t.description = 'Medium defensive line';
MERGE (t:Tactic {name: 'possession_based'}) SET t.description = 'Tiki-taka style possession';
MERGE (t:Tactic {name: 'direct_play'}) SET t.description = 'Long balls, fast transitions';
MERGE (t:Tactic {name: 'counter_attack'}) SET t.description = 'Absorb pressure, quick counters';
MERGE (t:Tactic {name: 'wing_play'}) SET t.description = 'Wide attacks through flanks';
MERGE (t:Tactic {name: 'target_man'}) SET t.description = 'Route one to target striker';
MERGE (t:Tactic {name: 'false_9'}) SET t.description = 'No traditional striker, fluid front';
MERGE (t:Tactic {name: 'inverted_fullbacks'}) SET t.description = 'Fullbacks tuck inside';
MERGE (t:Tactic {name: 'overlapping_cb'}) SET t.description = 'Center-backs join attack';
MERGE (t:Tactic {name: 'park_the_bus'}) SET t.description = 'Ultra defensive, 10 behind ball';
MERGE (t:Tactic {name: 'total_football'}) SET t.description = 'Fluid positional play';

// =============================================================================
// FORMATION NODES
// =============================================================================

MERGE (f:Formation {name: '4-3-3'}) SET f.type = 'attacking';
MERGE (f:Formation {name: '4-2-3-1'}) SET f.type = 'balanced';
MERGE (f:Formation {name: '4-4-2'}) SET f.type = 'classic';
MERGE (f:Formation {name: '3-5-2'}) SET f.type = 'wingback';
MERGE (f:Formation {name: '3-4-3'}) SET f.type = 'attacking';
MERGE (f:Formation {name: '5-3-2'}) SET f.type = 'defensive';
MERGE (f:Formation {name: '5-4-1'}) SET f.type = 'defensive';
MERGE (f:Formation {name: '4-1-4-1'}) SET f.type = 'balanced';
MERGE (f:Formation {name: '4-3-1-2'}) SET f.type = 'narrow';
MERGE (f:Formation {name: '4-4-1-1'}) SET f.type = 'balanced';

// =============================================================================
// PATTERN NODES (승률 패턴)
// =============================================================================

// 베팅 관련 패턴
MERGE (p:Pattern {pattern_id: 'P-S001'}) SET p.name = 'Home Underdog Bounce', p.description = 'Home team as underdog after 2+ losses often covers spread';
MERGE (p:Pattern {pattern_id: 'P-S002'}) SET p.name = 'Manager Bounce', p.description = 'New manager typically gets results in first 3 matches';
MERGE (p:Pattern {pattern_id: 'P-S003'}) SET p.name = 'Derby Volatility', p.description = 'Derby matches tend to have more cards and unpredictable results';
MERGE (p:Pattern {pattern_id: 'P-S004'}) SET p.name = 'Congestion Fade', p.description = 'Teams playing 3rd match in 7 days underperform xG';
MERGE (p:Pattern {pattern_id: 'P-S005'}) SET p.name = 'CL Hangover', p.description = 'Teams after midweek CL away match often struggle domestically';
MERGE (p:Pattern {pattern_id: 'P-S006'}) SET p.name = 'Referee Card Heavy', p.description = 'Specific referees consistently give more cards';
MERGE (p:Pattern {pattern_id: 'P-S007'}) SET p.name = 'Weather Impact', p.description = 'Heavy rain/wind favors defensive teams';
MERGE (p:Pattern {pattern_id: 'P-S008'}) SET p.name = 'Late Season Motivation', p.description = 'Teams with nothing to play for underperform';

// =============================================================================
// RELATIONSHIP TEMPLATES (Examples)
// =============================================================================

// Team -> League relationship
// MATCH (t:Team), (l:League) WHERE t.league = l.name MERGE (t)-[:PLAYS_IN]->(l);

// Team -> Tactic relationship (with time/intensity - KEY ADDITION #2)
// MATCH (t:Team {team_id: 'arsenal'}), (tac:Tactic {name: 'high_press'})
// MERGE (t)-[:APPLIES {confidence: 0.85, since: '2022-07', until: null, intensity: 'high'}]->(tac);

// Manager -> Tactic preference
// MATCH (m:Manager {manager_id: 'guardiola'}), (tac:Tactic {name: 'possession_based'})
// MERGE (m)-[:PREFERS {confidence: 0.95}]->(tac);

// Manager -> Formation preference
// MATCH (m:Manager {manager_id: 'guardiola'}), (f:Formation {name: '4-3-3'})
// MERGE (m)-[:USES {frequency: 0.7}]->(f);

// Referee -> Context bias (KEY ADDITION #3)
// MATCH (r:Referee {referee_id: 'michael_oliver'}), (c:Context {name: 'home_team'})
// MERGE (r)-[:FAVORS {bias_score: 0.12, sample_size: 150, confidence: 0.8}]->(c);

// Team -> Team rivalry
// MATCH (t1:Team {team_id: 'arsenal'}), (t2:Team {team_id: 'tottenham'})
// MERGE (t1)-[:RIVALS {type: 'derby', name: 'North London Derby'}]->(t2);

// Match node (thin - KEY ADDITION #1)
// CREATE (m:Match {
//   match_id: 'EPL_2024_arsenal_chelsea_20241215',
//   date: '2024-12-15',
//   league: 'EPL'
// });
// MATCH (m:Match {match_id: 'EPL_2024_arsenal_chelsea_20241215'})
// MATCH (h:Team {team_id: 'arsenal'}), (a:Team {team_id: 'chelsea'})
// MATCH (ref:Referee {referee_id: 'michael_oliver'})
// MERGE (h)-[:PLAYED_IN {role: 'home'}]->(m)
// MERGE (a)-[:PLAYED_IN {role: 'away'}]->(m)
// MERGE (ref)-[:OFFICIATED]->(m);

// =============================================================================
// QUERY EXAMPLES FOR GRAPH RAG
// =============================================================================

// Q1: 아스널 vs 첼시 매치업 맥락
// MATCH (h:Team {team_id: 'arsenal'})-[:PLAYS_IN]->(l:League)
// MATCH (h)-[ht:APPLIES]->(htac:Tactic)
// MATCH (a:Team {team_id: 'chelsea'})-[at:APPLIES]->(atac:Tactic)
// RETURN h.name, htac.name, ht.confidence, a.name, atac.name, at.confidence;

// Q2: 레프리 홈팀 편향 분석
// MATCH (r:Referee)-[f:FAVORS]->(c:Context {name: 'home_team'})
// WHERE f.bias_score > 0.1
// RETURN r.name, f.bias_score, f.sample_size
// ORDER BY f.bias_score DESC;

// Q3: 감독 전술 히스토리
// MATCH (m:Manager {manager_id: 'arteta'})-[p:PREFERS]->(t:Tactic)
// RETURN t.name, p.confidence
// ORDER BY p.confidence DESC;

// Q4: 특정 패턴에 해당하는 팀
// MATCH (t:Team)-[:EXHIBITS]->(p:Pattern {pattern_id: 'P-S004'})
// RETURN t.name, p.description;

// Q5: 더비 매치 찾기
// MATCH (t1:Team)-[r:RIVALS {type: 'derby'}]->(t2:Team)
// RETURN t1.name, t2.name, r.name;
