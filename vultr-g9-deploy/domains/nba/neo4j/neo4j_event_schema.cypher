// ============================================================
// G9 NBA Event Schema - BETTING SIGNALS ONLY
// ============================================================
// Focus: Injury, Lineup, Referee (actionable betting data)
// Excludes: Analysis, commentary, historical data
// ============================================================

// ------------------------------------------------------------
// 1. INDEXES (Performance)
// ------------------------------------------------------------

CREATE INDEX event_id_idx IF NOT EXISTS FOR (e:NBAEvent) ON (e.event_id);
CREATE INDEX event_time_idx IF NOT EXISTS FOR (e:NBAEvent) ON (e.collected_at);
CREATE INDEX event_type_idx IF NOT EXISTS FOR (e:NBAEvent) ON (e.event_type);
CREATE INDEX game_id_idx IF NOT EXISTS FOR (g:Game) ON (g.game_id);
CREATE INDEX player_name_idx IF NOT EXISTS FOR (p:Player) ON (p.name);
CREATE INDEX referee_name_idx IF NOT EXISTS FOR (r:Referee) ON (r.name);
CREATE INDEX team_code_idx IF NOT EXISTS FOR (t:Team) ON (t.code);

// ------------------------------------------------------------
// 2. NODE TYPES
// ------------------------------------------------------------

// === CORE NODES ===

// Game (from existing schema)
// MERGE (g:Game {
//   game_id: "401810221",
//   home_team: "GSW",
//   away_team: "LAL",
//   scheduled_time: datetime(),
//   state: "PRE_GAME_ACTIVE"
// })

// Player (from existing schema)
// MERGE (p:Player {
//   player_id: "2544",
//   name: "LeBron James",
//   team: "LAL"
// })

// Team (from existing schema)
// MERGE (t:Team {
//   code: "LAL",
//   name: "Los Angeles Lakers"
// })

// Referee (NEW)
// MERGE (r:Referee {
//   referee_id: "scott_foster",
//   name: "Scott Foster",
//   total_tendency: "OVER",  // OVER/UNDER/NEUTRAL
//   foul_tendency: "HIGH",   // HIGH/MEDIUM/LOW
//   avg_total_delta: 3.2,    // Historical impact on total
//   avg_foul_count: 46.8     // Average fouls called per game
// })

// === EVENT NODES ===

// NBAEvent (Twitter-sourced signals)
// MERGE (e:NBAEvent {
//   event_id: "evt_1234567890",
//   event_type: "injury",  // injury | lineup | referee | questionable | restriction | ejection
//   source_username: "ShamsCharania",
//   source_credibility: 1.0,
//   raw_text: "LeBron James (ankle) is OUT for tonight's game vs Warriors.",
//   text_hash: "abc123def456",
//   collected_at: datetime(),
//   game_id: "401810221",
//   player: "LeBron James",
//   team: "LAL",
//   status: "OUT",  // OUT | QUESTIONABLE | DOUBTFUL | STARTING | BENCH
//   betting_impact: "HIGH"  // HIGH | MEDIUM | LOW (based on player importance)
// })

// ------------------------------------------------------------
// 3. RELATIONSHIP TYPES
// ------------------------------------------------------------

// === EVENT RELATIONSHIPS ===

// Event -> Game
// (e:NBAEvent)-[:AFFECTS_GAME]->(g:Game)

// Event -> Player
// (e:NBAEvent)-[:ABOUT_PLAYER]->(p:Player)

// Event -> Team
// (e:NBAEvent)-[:AFFECTS_TEAM]->(t:Team)

// === IMPACT RELATIONSHIPS ===

// Player -> Game (injury impact)
// (p:Player)-[:INJURED_FOR {
//   status: "OUT",
//   reported_at: datetime(),
//   source: "ShamsCharania"
// }]->(g:Game)

// Player -> Game (starting lineup)
// (p:Player)-[:STARTS_IN {
//   position: "PG",
//   confirmed_at: datetime(),
//   source: "UnderdogNBA"
// }]->(g:Game)

// Referee -> Game (officiating assignment)
// (r:Referee)-[:OFFICIATES {
//   role: "crew_chief",
//   assigned_at: datetime(),
//   expected_total_impact: 3.2,
//   expected_foul_impact: "HIGH"
// }]->(g:Game)

// ------------------------------------------------------------
// 4. BETTING SIGNAL QUERIES
// ------------------------------------------------------------

// === QUERY 1: Recent injury impacts ===
// Get all recent injuries affecting today's games

MATCH (e:NBAEvent)-[:ABOUT_PLAYER]->(p:Player)
WHERE e.event_type = "injury"
  AND date(e.collected_at) = date()
  AND e.status IN ["OUT", "QUESTIONABLE"]
MATCH (p)-[:PLAYS_FOR]->(t:Team)
RETURN p.name as player,
       t.code as team,
       e.status as status,
       e.raw_text as details,
       e.source_username as source,
       e.collected_at as time
ORDER BY e.collected_at DESC;

// === QUERY 2: Starting lineup confirmations ===
// Get confirmed starters for a specific game

MATCH (e:NBAEvent)-[:AFFECTS_GAME]->(g:Game)
WHERE g.game_id = "401810221"
  AND e.event_type = "lineup"
  AND e.status = "STARTING"
MATCH (e)-[:ABOUT_PLAYER]->(p:Player)
RETURN p.name as player,
       p.team as team,
       e.source_username as source,
       e.collected_at as confirmed_at
ORDER BY e.collected_at DESC;

// === QUERY 3: Referee impact analysis ===
// Get referee assignment and historical tendencies

MATCH (r:Referee)-[rel:OFFICIATES]->(g:Game)
WHERE g.game_id = "401810221"
  AND rel.role = "crew_chief"
RETURN r.name as referee,
       r.total_tendency as total_lean,
       r.avg_total_delta as avg_impact,
       r.foul_tendency as foul_style,
       rel.expected_total_impact as expected_impact;

// === QUERY 4: Game-level betting signal summary ===
// Aggregate all signals for a game (for odds adjustment)

MATCH (g:Game {game_id: "401810221"})
OPTIONAL MATCH (g)<-[:AFFECTS_GAME]-(e:NBAEvent)
WHERE e.event_type IN ["injury", "lineup", "referee"]
WITH g,
     COUNT(CASE WHEN e.event_type = "injury" THEN 1 END) as injuries,
     COUNT(CASE WHEN e.event_type = "lineup" THEN 1 END) as lineup_changes,
     COUNT(CASE WHEN e.event_type = "referee" THEN 1 END) as ref_assignments
OPTIONAL MATCH (g)<-[:INJURED_FOR {status: "OUT"}]-(p:Player)
WITH g, injuries, lineup_changes, ref_assignments,
     COLLECT(p.name) as out_players
OPTIONAL MATCH (g)<-[:OFFICIATES {role: "crew_chief"}]-(r:Referee)
RETURN g.game_id as game,
       g.home_team + " vs " + g.away_team as matchup,
       out_players,
       injuries,
       lineup_changes,
       ref_assignments,
       r.name as crew_chief,
       r.total_tendency as total_lean;

// === QUERY 5: Source credibility tracking ===
// Track which sources are most reliable

MATCH (e:NBAEvent)
WHERE date(e.collected_at) = date()
WITH e.source_username as source,
     AVG(e.source_credibility) as avg_credibility,
     COUNT(e) as total_events,
     COUNT(CASE WHEN e.event_type = "injury" THEN 1 END) as injuries,
     COUNT(CASE WHEN e.event_type = "lineup" THEN 1 END) as lineups
RETURN source,
       avg_credibility,
       total_events,
       injuries,
       lineups
ORDER BY avg_credibility DESC, total_events DESC;

// ------------------------------------------------------------
// 5. DEDUPLICATION LOGIC
// ------------------------------------------------------------

// Merge events by text_hash to prevent duplicates
// This runs in the collector before saving

MERGE (e:NBAEvent {text_hash: $text_hash})
ON CREATE SET
  e.event_id = $event_id,
  e.event_type = $event_type,
  e.source_username = $source_username,
  e.source_credibility = $source_credibility,
  e.raw_text = $raw_text,
  e.collected_at = datetime($collected_at),
  e.game_id = $game_id,
  e.player = $player,
  e.team = $team,
  e.status = $status
ON MATCH SET
  e.updated_at = datetime();

// ------------------------------------------------------------
// 6. CLEANUP QUERIES
// ------------------------------------------------------------

// Delete old events (keep last 7 days only)
MATCH (e:NBAEvent)
WHERE e.collected_at < datetime() - duration('P7D')
DETACH DELETE e;

// Delete events from DEAD games
MATCH (g:Game {state: "DEAD"})<-[:AFFECTS_GAME]-(e:NBAEvent)
WHERE datetime(g.scheduled_time) < datetime() - duration('P7D')
DETACH DELETE e;

// ------------------------------------------------------------
// 7. EXAMPLE: Full event ingestion pipeline
// ------------------------------------------------------------

// Step 1: Create/update the event
MERGE (e:NBAEvent {text_hash: "abc123def456"})
ON CREATE SET
  e.event_id = "evt_1234567890",
  e.event_type = "injury",
  e.source_username = "ShamsCharania",
  e.source_credibility = 1.0,
  e.raw_text = "LeBron James (ankle) is OUT for tonight's game vs Warriors.",
  e.collected_at = datetime(),
  e.game_id = "401810221",
  e.player = "LeBron James",
  e.team = "LAL",
  e.status = "OUT",
  e.betting_impact = "HIGH";

// Step 2: Link to Game
MATCH (e:NBAEvent {event_id: "evt_1234567890"})
MATCH (g:Game {game_id: "401810221"})
MERGE (e)-[:AFFECTS_GAME]->(g);

// Step 3: Link to Player
MATCH (e:NBAEvent {event_id: "evt_1234567890"})
MERGE (p:Player {name: "LeBron James"})
ON CREATE SET p.team = "LAL"
MERGE (e)-[:ABOUT_PLAYER]->(p);

// Step 4: Create injury impact relationship
MATCH (p:Player {name: "LeBron James"})
MATCH (g:Game {game_id: "401810221"})
MERGE (p)-[:INJURED_FOR {
  status: "OUT",
  reported_at: datetime(),
  source: "ShamsCharania"
}]->(g);

// ------------------------------------------------------------
// END OF SCHEMA
// ------------------------------------------------------------
