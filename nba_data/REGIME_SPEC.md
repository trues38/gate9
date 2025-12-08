# SPORTS REGIME ENGINE – Direction v1

This document defines the rules for transforming raw NBA story data into structured "Regime Inputs" for the engine.

## 1. Data Cleaning & Normalization

### 1-1. Player Name Normalization
Unified `Player_ID` format for all entities.
- **Rule**: Map aliases to canonical IDs.
- **Examples**:
    - “LeBron”, “James”, “LBJ” → `PLAYER_LeBron_James`
    - “Kyrie”, “Irving” → `PLAYER_Kyrie_Irving`
- **Method**: NER + Alias Dictionary + Fuzzy Matching against Master Roster.

### 1-2. Team Name Normalization
Unified `Team_ID`.
- **Examples**:
    - “Cleveland”, “Cavs”, “CLE” → `TEAM_CLE`
    - “Bulls”, “Chicago”, “CHI” → `TEAM_CHI`

### 1-3. Text Cleaning
Remove non-narrative elements:
- Ticket/Ad text
- Reporter emails
- "UP NEXT" schedules
- HTML tags
- Short (<50 chars) meaningless sentences

### 1-4. Date Alignment
- Format: `YYYY-MM-DD`
- Must strictly match Boxscore/Gamelog dates.

### 1-5. Context Classification
Each sentence classified into:
- `STORY_PLAYER_EVENT`: Specific player action.
- `STORY_TEAM_EVENT`: Team-level action.
- `STORY_GLOBAL_CONTEXT`: General game narrative.

---

## 2. Tagging Rules

### A) Explicit Tags (Rule-based)
Triggered by keywords/regex in text.

| Tag | Trigger Concept |
|---|---|
| `[TripleDouble]` | "triple-double", "10+ pts/reb/ast" |
| `[CareerHigh]` | "career high", "personal best" |
| `[ClutchShot]` | "game winner", "buzzer beater", "final seconds" |
| `[InjuryReport]` | "left game", "sprained", "did not return" |
| `[ReturnFromInjury]` | "made season debut", "returned from" |
| `[HotShooting]` | "on fire", "could not miss" |
| `[LateCollapse]` | "blew a lead", "squandered" |
| `[PhysicalGame]` | "flagrant", "ejected", "shoving" |
| `[MomentumShift]` | "run", "rally", "erased deficit" |

### B) Vector Tags (Embedding-based)
Derived from semantic analysis (LLM).

- `NarrativeIntensity`: Low / Medium / High
- `EmotionalTone`: Calm / Heated / Euphoric / Desperate
- `GameFlow`: Stable / Chaotic / One-Sided
- `DominantStoryArc`: Redemption / Rivalry / Collapse / Surge

---

## 3. Regime Structure (6 Axes)

Output tags are mapped to these 6 dimensions.

1.  **Performance Regime**: `Hot`, `Cold`, `Plateau`, `Surge`, `Decline`
2.  **Momentum Regime**: `EarlyControl`, `LateControl`, `Comeback`, `Collapse`
3.  **Narrative Regime**: `Rivalry`, `Redemption`, `LeadershipArc`
4.  **Health Regime**: `InjuryRisk`, `ReturnBoost`, `Fatigue`
5.  **Tactical Regime**: `HighPace`, `InsideFocus`, `DefensivePressure`
6.  **Variance Regime**: `ThreeVarianceSpike`, `RefImpact`, `MomentumChaos`

---

## 4. Output Schema

```json
{
  "game_id": "0021401148",
  "teams": ["TEAM_CLE", "TEAM_CHI"],
  "players": ["PLAYER_LeBron_James", "PLAYER_Kyrie_Irving"],
  "tags_rule": ["[TripleDouble]", "[Rivalry]"],
  "tags_vector": {
    "NarrativeIntensity": "High",
    "EmotionalTone": "Heated"
  },
  "regime": {
    "Performance": "Surge",
    "Momentum": "LateControl",
    "Narrative": "Rivalry",
    "Health": "Stable",
    "Tactical": "ThreeVarianceSpike",
    "Variance": "HighVariance"
  },
  "summary_points": [
    "LeBron James records first triple-double since return.",
    "Cavs hold off Bulls rally in 4th quarter."
  ]
}
```
