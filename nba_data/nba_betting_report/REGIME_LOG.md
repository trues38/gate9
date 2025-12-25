# Regime Observation Log

## Purpose

The `regime_observations.jsonl` file accumulates raw observations for **future regime discovery**.

This is NOT used in v0.1 pipeline decisions.

---

## What is Logged

Each observation contains:

| Field | Source | Description |
|-------|--------|-------------|
| `date` | Structural Analyst | Game date |
| `game_id` | Structural Analyst | Unique game identifier |
| `timestamp` | Regime Logger | When observation was logged |
| `edge_score` | Pattern Matcher | Market-independent structural signal (0-100) |
| `market_line` | Raw input | Market spread or total |
| `action` | Decision Layer | BET / MONITOR / PASS |
| `confidence` | Decision Layer | high / medium / low |
| `pace` | Pattern Matcher | Structural profile (stub in v0.1) |
| `trend` | Pattern Matcher | Historical pattern (stub in v0.1) |
| `pipeline_version` | Regime Logger | Pipeline version tag |

---

## How it Works

**Passive Accumulation:**
- Every time the pipeline runs, observations are **appended** to the log
- Each line is a valid JSON object (JSON Lines format)
- No analysis or interpretation is performed during logging

**File Format:**
```jsonl
{"date": "2025-12-18", "game_id": "0022400415", "edge_score": 17.0, "market_line": -4.5, "action": "pass", ...}
{"date": "2025-12-18", "game_id": "0022400416", "edge_score": 39.0, "market_line": 221.5, "action": "monitor", ...}
...
```

---

## NOT Used For

**This log does NOT:**
- Influence current pipeline decisions
- Detect regimes automatically
- Make predictions
- Calculate probabilities
- Optimize edge_score calculation

**This is pure data collection.**

---

## Future Use (Post-hoc Analysis)

After accumulating **100+ observations**, you can:

1. **Identify Repeated Patterns**
   - Find combinations of (edge_score, market_line, action) that repeat
   - Example: "edge_score 70-80 + market_line -3 to -5 + action BET" appears 15 times

2. **Name Emergent Regimes**
   - Label patterns based on observable characteristics
   - Example: `regime_high_edge_tight_line`

3. **Validate Consistency**
   - Check if regime definitions produce consistent outcomes over time
   - Measure regime stability across different market conditions

4. **Refine Thresholds**
   - Use historical data to calibrate edge_score thresholds
   - Adjust BET/MONITOR/PASS boundaries based on empirical patterns

---

## Analysis Tools (Future)

**Suggested workflow:**

```python
# Load observations
import json
observations = []
with open("regime_observations.jsonl", "r") as f:
    for line in f:
        observations.append(json.loads(line))

# Group by edge_score range and action
# Find repeated combinations
# Identify regimes post-hoc
# Validate consistency
```

**NOT included in v0.1:**
- Regime detection scripts
- Pattern clustering algorithms
- Threshold optimization tools

These will be added in future versions after sufficient data is collected.

---

## Important Notes

**Minimum Observations:**
- Regime naming should require at least 5-10 occurrences
- Single-instance patterns are NOT regimes

**No Real-time Detection:**
- Regime discovery is POST-HOC only
- Current pipeline does not use regime labels

**Transparency:**
- All logged data is reproducible from pipeline inputs
- No hidden calculations or black-box operations

---

## Version History

- **v0.1**: Initial passive logging implementation
  - No regime detection
  - No threshold optimization
  - Pure data accumulation only
