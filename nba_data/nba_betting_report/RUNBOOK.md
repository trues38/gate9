# Daily Report Generation - RUNBOOK

## 1. Daily Execution Procedure

### 1.1 Execution Command
```bash
cd /path/to/nba_betting_report
python generate_report.py
```

### 1.2 Input Location
```
input/sample_input.json
```

### 1.3 Output Locations
```
output/Daily_Report.md          (primary output)
regime_observations.jsonl       (accumulation log)
```

### 1.4 Pipeline Stages
```
Step 1: Structural Analyst
Step 2: Pattern Matcher
Step 3: Market & Decision
Step 4: Report Editor
(+ Regime Logger - passive)
```

---

## 2. Pre-Execution Checklist

- [ ] input/sample_input.json exists
- [ ] input/sample_input.json contains valid JSON
- [ ] input/sample_input.json has "games" array
- [ ] Each game has: game_id, date, teams, scores, box_stats, market_line
- [ ] **edge_score is NOT in input** (calculated by pipeline)
- [ ] output/ directory exists (auto-created if missing)

---

## 3. Post-Execution Verification

### 3.1 Success Indicators
```
✓ Report generated: output/Daily_Report.md
✓ Logged N observations to regime_observations.jsonl
  Total accumulated: M observations
```

### 3.2 Output File Checks
- [ ] output/Daily_Report.md created/updated
- [ ] Daily_Report.md contains 5 sections:
  - [ ] Executive Summary
  - [ ] Betting Decisions (High Confidence / Monitor / Pass)
  - [ ] Pattern Analysis
  - [ ] Risk Factors
  - [ ] Data Quality
- [ ] regime_observations.jsonl appended (line count increased)

### 3.3 Report Content Verification
- [ ] Date matches input
- [ ] Total Games Analyzed = input game count
- [ ] No win probability mentioned
- [ ] No outcome predictions mentioned
- [ ] No expected value calculations mentioned
- [ ] edge_score shown as "score: X" only
- [ ] Actions are BET/MONITOR/PASS only

### 3.4 Log File Verification
```bash
# Check line count increased
wc -l regime_observations.jsonl

# Verify JSON format
tail -1 regime_observations.jsonl | python -m json.tool
```

---

## 4. Input Data Requirements

### 4.1 Required Fields per Game
```json
{
  "game_id": "string",
  "date": "YYYY-MM-DD",
  "teams": {"home": "ABC", "away": "XYZ"},
  "scores": {"home": int, "away": int},
  "box_stats": {
    "home_fg_pct": float,
    "away_fg_pct": float,
    "home_3p_pct": float,
    "away_3p_pct": float,
    "home_rebounds": int,
    "away_rebounds": int
  },
  "market_line": float
}
```

### 4.2 Prohibited Input Fields
- **edge_score** (calculated by Pattern Matcher)

---

## 5. PROHIBITED ACTIONS

### 5.1 Input Modification
- ❌ Adding edge_score to input JSON
- ❌ Removing market_line from input
- ❌ Changing input schema without pipeline update

### 5.2 Pipeline Modification
- ❌ Skipping any pipeline stage
- ❌ Modifying threshold values without documentation
- ❌ Adding win probability calculations
- ❌ Adding outcome predictions
- ❌ Adding expected value calculations
- ❌ Using regime_observations.jsonl for current decisions

### 5.3 Output Modification
- ❌ Manually editing Daily_Report.md template
- ❌ Adding performance metrics to report
- ❌ Adding betting recommendations to report
- ❌ Deleting or truncating regime_observations.jsonl

### 5.4 Code Modification
- ❌ Modifying edge_score calculation without version tag
- ❌ Changing report structure without updating documentation
- ❌ Introducing market data into Pattern Matcher
- ❌ Using regime log data in Decision Layer

---

## 6. Error Handling

### 6.1 Common Errors

**Error: Missing input file**
```
Solution: Create input/sample_input.json
```

**Error: Invalid JSON**
```
Solution: Validate JSON syntax
Command: python -m json.tool < input/sample_input.json
```

**Error: Missing required fields**
```
Check: game_id, date, teams, scores, box_stats, market_line
```

**Error: Import failed**
```
Check: All files in agents/ directory present
- structural_analyst.py
- pattern_matcher.py
- market_decision.py
- report_editor.py
- regime_logger.py
- __init__.py
```

### 6.2 Logging Failure
```
⚠ Logging failed: [error message]
```
- Pipeline continues (logging is non-blocking)
- Daily_Report.md still generated
- Check regime_observations.jsonl permissions

---

## 7. File Locations

```
nba_betting_report/
├── generate_report.py          # Main execution script
├── input/
│   └── sample_input.json       # Daily input data
├── output/
│   └── Daily_Report.md         # Daily report output
├── regime_observations.jsonl   # Accumulation log (append-only)
├── agents/
│   ├── __init__.py
│   ├── structural_analyst.py
│   ├── pattern_matcher.py
│   ├── market_decision.py
│   ├── report_editor.py
│   └── regime_logger.py
├── SKILL.md                    # System philosophy
├── REGIME_LOG.md               # Log documentation
└── RUNBOOK.md                  # This file
```

---

## 8. Daily Workflow

```
1. Update input/sample_input.json with today's data
2. Run: python generate_report.py
3. Verify: output/Daily_Report.md created
4. Verify: regime_observations.jsonl appended
5. Review: Daily_Report.md content
6. Archive: Move Daily_Report.md to dated backup (optional)
```

---

## 9. Version Information

- Pipeline Version: v0.1
- edge_score Calculation: v0.1 baseline
- Decision Thresholds: BET ≥50, MONITOR 30-49, PASS <30
- Report Template: 5-section fixed structure
- Regime Detection: NOT ACTIVE (logging only)
