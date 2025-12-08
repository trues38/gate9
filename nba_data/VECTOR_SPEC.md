# SPORTS REGIME ENGINE — Vector Tagging Module Spec (v1.0)

## 1. Purpose
Process text chunks to generate semantic/emotional tags using Embeddings + LLM.
Complements Rule-based tags to capture the "vibe" and "structure" of the game.

## 2. Input/Output
- **Input**: `stories_chunks/*.jsonl`
    - `text`, `role` (lead, body, closing), `order`
- **Output**: `stories_vector_tags/*.jsonl`
    - `vector_tags` (JSON), `embedding` (Vector)

## 3. Tag Definitions (6 Axes)

### A. Narrative Tags
| Tag | Description |
|---|---|
| `Rivalry` | Intense competition/history |
| `RedemptionArc` | Comeback from failure/injury |
| `CollapseArc` | Falling apart under pressure |
| `LeadershipArc` | Player carrying the team |
| `BreakoutArc` | Unexpected star performance |

### B. Emotional Tone
`Calm`, `Neutral`, `Intense`, `Heated`, `Hostile`

### C. Game Flow
`Stable`, `Chaotic`, `MomentumSwing`, `EarlyControl`, `LateSurge`

### D. Psychological
`ConfidenceRise`, `ConfidenceDrop`, `StressHigh`, `Composure`, `PsychologicalShift`

### E. Tactical
`SpacingFocus`, `PaintDominance`, `TransitionGame`, `DefensiveIntensity`, `MismatchExploitation`

### F. Spotlight
`PlayerFocus` (List of IDs), `CoachImpact`, `CrowdImpact`

## 4. LLM Prompt Template
```json
{
  "NarrativeIntensity": "High/Medium/Low",
  "DominantArc": "Rivalry/...",
  "EmotionalTone": "Heated/...",
  "GameFlow": "Chaotic/...",
  "PsychologicalShift": true/false,
  "PlayerFocus": ["PLAYER_ID..."]
}
```
