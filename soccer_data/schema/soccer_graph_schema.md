# Soccer Graph Schema (Neo4j)

## 1. Core Nodes & Relationships

### [Nodes]

- **Team**: `{id, name, country, stadium, current_manager_id}`
- **Player**: `{id, name, position, nationality, birth_date, market_value}`
- **Manager**: `{id, name, preferred_formation, tactical_profile}`
- **Match**: `{id, date, competition, score, home_xg, away_xg}`
- **Injury**: `{id, type, severity, start_date, end_date}`
- **TacticalArchetype**: `{name, description}` (e.g., "Gengenpressing", "Low Block", "Tiki-Taka")

### [Relationships]

- `(Player)-[:PLAYS_FOR {salary, contract_end}]->(Team)`
- `(Manager)-[:MANAGES]->(Team)`
- `(Team)-[:PARTICIPATED_IN {is_home}]->(Match)`
- `(Player)-[:SUFFERED]->(Injury)`
- `(Team)-[:APPLIES {confidence_score}]->(TacticalArchetype)`
- `(Player)-[:HAS_STATS {xg, xa, progressive_passes}]->(Match)`

## 2. Ingestion Cypher Snippets

### Ingesting Player & Team Relations

```cypher
LOAD CSV WITH HEADERS FROM 'file:///players.csv' AS row
MERGE (p:Player {id: row.player_id})
SET p.name = row.name, p.position = row.position;

LOAD CSV WITH HEADERS FROM 'file:///transfers.csv' AS row
MATCH (p:Player {id: row.player_id})
MATCH (t:Team {name: row.to_team})
MERGE (p)-[r:PLAYS_FOR]->(t)
SET r.date = row.transfer_date, r.fee = row.fee;
```

### Ingesting Injury Data (Fragility Detection)

```cypher
LOAD CSV WITH HEADERS FROM 'file:///injuries.csv' AS row
MATCH (p:Player {id: row.player_id})
CREATE (i:Injury {type: row.injury_type, start: row.date})
CREATE (p)-[:SUFFERED]->(i);
```
