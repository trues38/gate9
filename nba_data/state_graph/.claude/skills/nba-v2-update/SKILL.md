---
name: nba-v2-update
description: Automates NBA v2.0 daily workflow - updates yesterday's games, recalculates Coach/Player stats, validates lineups, and generates betting context. Use when collecting daily NBA data, updating player statistics, or preparing game analysis.
---

# NBA v2.0 Daily Update Skill

## Purpose
Automates the complete NBA v2.0 analysis pipeline:
1. Collect yesterday's game results + player box scores
2. Recalculate Coach stats (rotation depth, tempo)
3. Update Player attributes (impact, stamina, style tags)
4. Verify lineup data integrity
5. Generate game context for betting analysis

## When to Use

Ask any of these:
- "Run NBA daily update"
- "Update yesterday's games"
- "Refresh NBA stats"
- "NBA v2 update"

## Workflow Steps

### Step 1: Yesterday's Games Collection
- Fetches completed games from ESPN API
- Collects player box scores (25-26 season only)
- Calculates rest days for each team
- Updates Neo4j GameState and PlayerBoxScore nodes

### Step 2: Coach Stats Recalculation
- Analyzes rotation patterns (20min+ players)
- Calculates starter/bench minutes
- Estimates team tempo
- Updates 24 team Coach nodes

### Step 3: Player Attributes Update
- Computes impact metrics (+/-, percentile)
- Calculates stamina (back-to-back performance)
- Auto-classifies style tags
- Tracks injury rates
- Updates 641 player nodes

### Step 4: Lineup Integrity Check
- Verifies all lineup players exist in database
- Checks for recent trades/roster changes
- Flags missing lineup data

### Step 5: Context Summary
- Lists today's games
- Identifies back-to-back situations
- Notes recent player performance changes
- Highlights lineup concerns

## Output

Provides comprehensive summary:
```
✅ 12 games collected (348 player box scores)
✅ 24 Coach nodes updated
✅ 641 Player attributes refreshed
⚠️  HOU lineup needs update (Fred VanVleet traded)
📅 Tonight: 8 games (3 back-to-backs)
```

## Error Handling

- Continues on individual game failures
- Reports missing data
- Suggests manual fixes for lineup issues

## Frequency

Run daily:
- After games complete (typically morning)
- Before analyzing today's matchups
- Keeps v2.0 system current
