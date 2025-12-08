# NBA Regime Engine — Dataset Construction Specification

## 1. Data Scope Definition
**Season Range**: 2009-2010 Season to 2024-2025 Season (Total 16 Seasons)
*   *Rationale*: Based on current 2025 rosters, pre-2009 data has minimal relevance for active player analysis.

**Player Scope**:
*   Target: ~259 players (from 2025 roster of 535) who have actual game logs.
*   Filters: Exclude players with < 5 games, no stats, or temporary 10-day contracts.
*   Primary Analysis Set: Approx. 150 Core Rotation Players.

## 2. Data Collection Targets (5 Types)
All data must be saved locally in JSON/CSV formats.

### A. Season Stats (Season Level)
*   **Source**: NBA Stats API / Basketball Reference
*   **Fields**: `player_id`, `season`, `team`, `gp`, `min`, `pts`, `reb`, `ast`, `stl`, `blk`, `tov`, `fg%`, `3p%`, `ft%`, `usg%`, `per`, `ws`, `bpm`, `vorp`

### B. Game Logs (Game Level)
*   **Source**: NBA Stats API
*   **Fields**: `game_id`, `date`, `team`, `opponent`, `home_away`, `player_id`, `starter`, `min`, `pts`, `reb`, `ast`, `blk`, `stl`, `tov`, `plus_minus`, `ts%`, `usg%`, `ortg`, `drtg`

### C. Play-by-Play (Event Level - Optional Phase 2)
*   **Fields**: `game_id`, `timestamp`, `event_type`, `player`, `team`, `action`, `score`

### D. Game Stories (Narrative Data)
*   **Source**: ESPN, Yahoo Sports, Bleacher Report, etc.
*   **Process**: Crawl -> Clean -> Split -> Summarize (LLM) -> Embed
*   **Output (JSONL)**: `game_id`, `date`, `player_mentions` (list), `team_mentions`, `headline`, `summary`, `sentiment`, `keywords`, `embedding`

### E. Player Story Archive (Long-term Narrative)
*   **Output (JSON)**: `player_id`, `stories` list (`date`, `source`, `summary`, `sentiment`, `embedding`)

## 3. Directory Structure
```
nba_data/
├── seasons/            # Season-level aggregated stats (2009-2025)
├── gamelogs/           # Detailed game logs organized by season
├── stories_raw/        # Raw crawled HTML/Text
├── stories_clean/      # Processed JSONL with summaries/embeddings
├── embeddings/         # Vector stores
│   ├── players/
│   ├── games/
│   └── stories/
├── players/            # Meta data
│   ├── master_list.json
│   └── roster_2025.json
├── regimes/            # Final output of the engine
│   ├── players/
│   ├── teams/
│   └── league/
└── pipeline/           # Scripts and Logs
    └── logs/
```

## 4. File Schemas

**`gamelog_sample.jsonl`**
```json
{
  "game_id": "20141102_LAL_HOU",
  "player_id": "2544", 
  "player_name": "LeBron James",
  "date": "2014-11-02",
  "pts": 28, "reb": 10, "ast": 8, "min": 36,
  "usg": 0.321, "ts_pct": 0.61
}
```

**`story_clean_sample.jsonl`**
```json
{
  "game_id": "20141102_LAL_HOU",
  "player_mentions": ["2544", "201566"],
  "headline": "LeBron struggles after minor injury",
  "summary": "LeBron showed signs of fatigue...",
  "sentiment": -0.18,
  "embedding": [0.023, 0.115, ...]
}
```

**`regime_player_sample.json`**
```json
{
  "player_id": "2544",
  "regimes": [
    {
      "period": "2018-2020",
      "type": "Late Prime → Decline Onset",
      "evidence_games": ["..."],
      "description": "Maintained high efficiency but defense usage dropped..."
    }
  ]
}
```

## 5. Pipeline Execution Order
1.  **Player Master**: Build `master_list.json` from 2025 active roster.
2.  **Season Stats**: Fetch aggregated stats for 2009-2025.
3.  **Game Logs**: Fetch 30k+ game logs for target players.
4.  **Story Crawling**: Fetch game recaps/news for game dates.
5.  **Story Processing**: LLM Summary + Embedding.
6.  **Timeline Construction**: Merge Stats + Stories per player.
7.  **Regime Generation**: Run Clustering/LLM Analysis to define regimes.

## 6. Regime Engine Architecture (3-Layer Logic)

The core of the engine follows a 3-Layer Architecture to capture the "Relativity" and "Time-Series" nature of sports.

### Layer 1: Tagging (Explicit Signals)
*   **Goal**: Extract structural signals from text via Rule-based/LLM extraction.
*   **Tags**: `[Injury: BodyPart]`, `[Feud: Target]`, `[Trade Rumor]`, `[Fatigue]`, `[Role Change]`, `[Slump]`.
*   **Role**: Explicit filtering and immediate penalty/bonus logic (e.g., "Ankle Injury" = -10% mobility).

### Layer 2: Vectorization (Contextual Signals)
*   **Goal**: Capture implicit meaning and similarity via Embeddings.
*   **Mechanism**: Embed full story text + summary.
*   **Role**: Find historical "Structural Twins". 
    *   *Query*: "Current Luka (Feud + Soreness)"
    *   *Result*: "Similar to 2018 Jimmy Butler (0.92 cosine similarity)"

### Layer 3: Regime Modeling (Time-Series Phases)
*   **Goal**: Define "Phase Changes" over time by combining Stats + Layer 1 + Layer 2.
*   **Definition**: "A pattern of state maintained over a specific period."
*   **Examples**:
    *   `Injury Onset` → `Degradation` → `Recovery`
    *   `Trade Rumor Turbulence`
    *   `Usage Spike Overload`
    *   `Team Chemistry Collapse`
*   **Output JSON**:
    ```json
    {
      "player": "Luka Doncic",
      "regime": "Overload Fatigue → Injury Risk",
      "period": "2024-12-01 ~ 2025-01-14",
      "evidence": {
        "stats": ["TS% -8%", "Usage +6%"],
        "tags": ["ankle soreness", "feud rumor"],
        "vectors": ["Sim: 2018 Butler"]
      }
    }
    ```

