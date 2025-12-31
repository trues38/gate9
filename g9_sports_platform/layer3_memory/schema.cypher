// ============================================
// G9 Sports Intelligence Platform
// Neo4j Graph Schema - Universal + NBA
// ============================================

// ========================================
// CONSTRAINTS (Unique Identifiers)
// ========================================

// Sport
CREATE CONSTRAINT sport_code IF NOT EXISTS
FOR (s:Sport) REQUIRE s.code IS UNIQUE;

// Team
CREATE CONSTRAINT team_id IF NOT EXISTS
FOR (t:Team) REQUIRE t.team_id IS UNIQUE;

// Player
CREATE CONSTRAINT player_id IF NOT EXISTS
FOR (p:Player) REQUIRE p.player_id IS UNIQUE;

// Coach
CREATE CONSTRAINT coach_id IF NOT EXISTS
FOR (c:Coach) REQUIRE c.coach_id IS UNIQUE;

// Game
CREATE CONSTRAINT game_id IF NOT EXISTS
FOR (g:Game) REQUIRE g.game_id IS UNIQUE;

// Referee
CREATE CONSTRAINT referee_id IF NOT EXISTS
FOR (r:Referee) REQUIRE r.referee_id IS UNIQUE;

// ExpertDataset
CREATE CONSTRAINT expert_dataset_id IF NOT EXISTS
FOR (ed:ExpertDataset) REQUIRE ed.dataset_id IS UNIQUE;

// RealTimeAlert
CREATE CONSTRAINT alert_tweet_id IF NOT EXISTS
FOR (ra:RealTimeAlert) REQUIRE ra.tweet_id IS UNIQUE;

// RedditThread
CREATE CONSTRAINT thread_id IF NOT EXISTS
FOR (rt:RedditThread) REQUIRE rt.thread_id IS UNIQUE;

// PlayerEvaluation
CREATE CONSTRAINT player_eval_id IF NOT EXISTS
FOR (pe:PlayerEvaluation) REQUIRE pe.eval_id IS UNIQUE;

// CoachAnalysis
CREATE CONSTRAINT coach_analysis_id IF NOT EXISTS
FOR (ca:CoachAnalysis) REQUIRE ca.analysis_id IS UNIQUE;

// ========================================
// INDEXES (Query Performance)
// ========================================

// Time-based queries
CREATE INDEX game_date IF NOT EXISTS FOR (g:Game) ON (g.game_date);
CREATE INDEX alert_timestamp IF NOT EXISTS FOR (ra:RealTimeAlert) ON (ra.timestamp);
CREATE INDEX eval_timestamp IF NOT EXISTS FOR (pe:PlayerEvaluation) ON (pe.timestamp);
CREATE INDEX thread_collected IF NOT EXISTS FOR (rt:RedditThread) ON (rt.collected_at);

// Search indexes
CREATE INDEX player_name IF NOT EXISTS FOR (p:Player) ON (p.name);
CREATE INDEX team_name IF NOT EXISTS FOR (t:Team) ON (t.name);
CREATE INDEX team_abbr IF NOT EXISTS FOR (t:Team) ON (t.abbreviation);

// Sentiment indexes
CREATE INDEX eval_sentiment IF NOT EXISTS FOR (pe:PlayerEvaluation) ON (pe.sentiment);
CREATE INDEX analysis_sentiment IF NOT EXISTS FOR (ca:CoachAnalysis) ON (ca.rotations_sentiment);

// ========================================
// SAMPLE DATA: Sports
// ========================================

MERGE (nba:Sport {code: 'NBA'})
SET nba.name = 'National Basketball Association',
    nba.country = 'USA',
    nba.enabled = true;

MERGE (nfl:Sport {code: 'NFL'})
SET nfl.name = 'National Football League',
    nfl.country = 'USA',
    nfl.enabled = false;

MERGE (mlb:Sport {code: 'MLB'})
SET mlb.name = 'Major League Baseball',
    mlb.country = 'USA',
    mlb.enabled = false;

// ========================================
// SAMPLE DATA: NBA Teams (선택된 팀들)
// ========================================

// Lakers
MERGE (lal:Team {team_id: 'NBA_LAL'})
SET lal.name = 'Los Angeles Lakers',
    lal.abbreviation = 'LAL',
    lal.city = 'Los Angeles',
    lal.conference = 'Western',
    lal.division = 'Pacific',
    lal.sport = 'NBA';

// Warriors
MERGE (gsw:Team {team_id: 'NBA_GSW'})
SET gsw.name = 'Golden State Warriors',
    gsw.abbreviation = 'GSW',
    gsw.city = 'San Francisco',
    gsw.conference = 'Western',
    gsw.division = 'Pacific',
    gsw.sport = 'NBA';

// Celtics
MERGE (bos:Team {team_id: 'NBA_BOS'})
SET bos.name = 'Boston Celtics',
    bos.abbreviation = 'BOS',
    bos.city = 'Boston',
    bos.conference = 'Eastern',
    bos.division = 'Atlantic',
    bos.sport = 'NBA';

// Heat
MERGE (mia:Team {team_id: 'NBA_MIA'})
SET mia.name = 'Miami Heat',
    mia.abbreviation = 'MIA',
    mia.city = 'Miami',
    mia.conference = 'Eastern',
    mia.division = 'Southeast',
    mia.sport = 'NBA';

// Sport -> Team relationships
MATCH (s:Sport {code: 'NBA'})
MATCH (t:Team)
WHERE t.sport = 'NBA'
MERGE (s)-[:HAS_TEAM]->(t);

// ========================================
// RELATIONSHIP TYPES (Documentation)
// ========================================

// Core Relationships:
// (:Sport)-[:HAS_TEAM]->(:Team)
// (:Team)-[:HAS_PLAYER]->(:Player)
// (:Team)-[:COACHED_BY]->(:Coach)
// (:Game)-[:HOME_TEAM]->(:Team)
// (:Game)-[:AWAY_TEAM]->(:Team)
// (:Game)-[:REFEREED_BY]->(:Referee)

// Layer 0 (Expert Data):
// (:ExpertDataset)-[:CONTAINS_STATS]->(:Player)
// (:ExpertDataset)-[:VALIDATES]->(:PlayerEvaluation)

// Layer 1 (Real-time):
// (:Player)-[:HAS_ALERT]->(:RealTimeAlert)
// (:Team)-[:HAS_ALERT]->(:RealTimeAlert)
// (:RealTimeAlert)-[:ABOUT_GAME]->(:Game)

// Layer 2 (Reddit):
// (:Game)-[:HAS_REDDIT_THREAD]->(:RedditThread)
// (:Player)-[:HAS_EVALUATION]->(:PlayerEvaluation)
// (:Coach)-[:HAS_ANALYSIS]->(:CoachAnalysis)
// (:PlayerEvaluation)-[:FROM_THREAD]->(:RedditThread)
// (:CoachAnalysis)-[:FROM_THREAD]->(:RedditThread)

// Cross-validation:
// (:RealTimeAlert)-[:CONFIRMED_BY]->(:RedditThread)
// (:ExpertDataset)-[:CORRELATES_WITH]->(:PlayerEvaluation)

// ========================================
// HELPER PROCEDURES
// ========================================

// Create Player with Team relationship
// CALL g9.createPlayer('LeBron James', 'LAL', 'SF', {ppg: 25.4, rpg: 7.3})

// Store Real-time Alert
// CALL g9.storeAlert({...RealTimeEvent})

// Store Reddit Analysis
// CALL g9.storeRedditAnalysis({...RedditAnalysis})
