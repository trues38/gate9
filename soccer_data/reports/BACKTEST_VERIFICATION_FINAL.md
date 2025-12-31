# Soccer Backtest Verification Report - FINAL AUDIT

**Date**: 2025-12-29
**Auditor**: Claude Code (Sonnet 4.5)
**Status**: 🔴 **FAILED - NOT DEPLOYABLE**

---

## Executive Summary

Verified the claimed **+53.73% ROI (La Liga)** from the "Institutional Backtest Report [VERIFIED]". After thorough code review and re-execution, the model shows **NO predictive edge**. The positive ROI is driven by high-variance underdog lottery wins, not genuine statistical advantage.

---

## 1. Claims vs Reality

| Metric | Original Report | Actual Backtest | Discrepancy |
|--------|----------------|-----------------|-------------|
| **La Liga ROI** | +53.73% | +92.74% | Too high (variance) |
| **La Liga Bets** | 306 | 246 | -20% sample size |
| **Model Accuracy** | Not disclosed | 32.1% | **= Random (33.3%)** |
| **Win Rate** | Not disclosed | 32.1% | **= Random** |
| **Away Win Rate** | Not disclosed | 29.2% | **< Random (33%)** |

---

## 2. Critical Flaws Discovered

### 🔴 **FLAW #1: Prediction Accuracy at Random Level**

```
League Performance:
  La Liga:      32.1% accuracy (random: 33.3%)
  EPL:          26.7% accuracy (random: 33.3%)
  Bundesliga:   24.7% accuracy (random: 33.3%)
  Serie A:      19.9% accuracy (random: 33.3%) ⚠️
  Ligue 1:      30.0% accuracy (random: 33.3%)
```

**Verdict**: The model has **ZERO predictive power**.

---

### 🔴 **FLAW #2: ROI Driven by High-Variance Underdog Lottery**

**La Liga Away Bets Analysis:**
- Total: 185 bets
- Win rate: 29.2% (below random!)
- ROI: +89.81%
- Average winning odds: **6.50x** (high-variance underdogs)

**Top 7 Wins Contribute 58.7% of Total Profit:**
```
Real Sociedad vs Alaves:     15.00x profit
Real Betis vs Alaves:        15.00x profit
Real Valladolid vs Alaves:   15.00x profit
Barcelona vs Las Palmas:     13.85x profit
Real Sociedad vs Osasuna:    12.91x profit
Real Sociedad vs Osasuna:    12.91x profit
Real Valladolid vs Osasuna:  12.91x profit

Total: 97.58 units out of 166.14 (58.7%)
```

**Verdict**: This is **lottery luck**, not edge.

---

### 🔴 **FLAW #3: Draw Predictions Completely Failed**

- Draw bets: 15
- Successful: **0**
- Win rate: **0%**
- ROI: **-100%**

---

### 🔴 **FLAW #4: Away Bet Bias + Below-Random Performance**

```
Bet Type Distribution:
  Home:  223 bets (21.1%) | Win rate: 33.2% | ROI: +29.52%
  Draw:   15 bets ( 1.4%) | Win rate:  0.0% | ROI: -100.00%
  Away:  821 bets (77.5%) | Win rate: 25.3% | ROI: +20.24%
```

**Verdict**: Model is **over-betting away underdogs** with below-random accuracy.

---

### 🔴 **FLAW #5: Rolling xG Calculation Bug**

**Code Issue (backtest_rolling_predictive.py:45-53):**
```python
def get_rolling_xg(row, team_name, current_date):
    h_games = df[(df['h_name'] == team_name) & (df['datetime'] < current_date)].tail(5)
    a_games = df[(df['a_name'] == team_name) & (df['datetime'] < current_date)].tail(5)
    recent_xg = pd.concat([h_games['h_xg_val'], a_games['a_xg_val']])
```

**Problem**: Takes tail(5) from home games AND tail(5) from away games separately, potentially including **up to 10 games** instead of the most recent 5.

**Impact**: Creates incorrect rolling averages, leading to invalid edge calculations.

---

### 🔴 **FLAW #6: Team Name Fuzzy Matching Error Risk**

**Code Issue (backtest_rolling_predictive.py:72-73):**
```python
match_odds = odds_df[
    (odds_df['HomeTeam'].str.contains(row['h_name'][:5])) &
    (odds_df['AwayTeam'].str.contains(row['a_name'][:5]))
].head(1)
```

**Problem**: Using only first 5 characters for team matching can cause:
- "Manchester United" vs "Manchester City" confusion
- Wrong odds being matched to wrong games

---

## 3. Statistical Analysis

### Mathematical Impossibility Check

**La Liga Away Bets:**
- Win rate: 29.2% (below random 33%)
- ROI: +89.81%
- Required average winning odds: 6.50x
- Actual average winning odds: 6.50x ✓

**Conclusion**: The math checks out, BUT:
1. This only works because of **high-variance underdog bets**
2. With 29.2% win rate (below random), this is **not sustainable**
3. Sample size (185 bets) is too small to distinguish luck from edge

### Confidence Interval

```
Sample size: 246 bets
Standard deviation: 3.5
95% CI: ±0.44
Observed mean: +0.93

Statistical significance: YES (barely)
But contradicts random-level accuracy!
→ Pattern matches VARIANCE, not EDGE
```

---

## 4. Original Report Claims - Where They Came From

### First Report (2YR): **+234% ROI**
- Used **match-day xG** (hindsight bias)
- Completely invalid

### Second Report (VERIFIED): **+53% ROI**
- Claimed to remove hindsight bias
- Used "Rolling xG"
- BUT: Rolling xG has calculation bug
- AND: Results cannot be reproduced from saved CSV files

### Actual Backtest Results Found:

| File | Edge Threshold | Bets | ROI |
|------|----------------|------|-----|
| high_fidelity_backtest.csv | >5% | 1,940 | **-7.89%** |
| high_fidelity_backtest.csv | >10% | 536 | **-51.32%** |
| regime_classified_results.csv | >10% | 556 | **+29.63%** |
| rolling_predictive_results.csv | >10% | 1,059 | **+20.49%** |
| rolling_predictive (La Liga) | >10% | 246 | **+92.74%** |

---

## 5. Root Cause: Why Does La Liga Show +92% Despite Random Accuracy?

1. **High-variance underdog strategy**
   - 77.5% of bets are away underdogs
   - Average winning odds: 6.50x
   - A few lucky 15x wins dominate returns

2. **Small sample size**
   - Only 246 La Liga bets
   - 7 bets contribute 58.7% of profit
   - Insufficient to distinguish luck from skill

3. **Calculation bugs compound error**
   - Rolling xG bug creates biased inputs
   - Team name fuzzy matching may introduce noise
   - No validation of odds-match timestamp alignment

---

## 6. What About the "Real" Edge?

**The report claims:**
> "우리는 이제 '진짜 엣지'를 찾았습니다. 사후 편향이 없는 상태에서의 +53% ROI는 시장을 이기기에 충분히 차고 넘치는 수치입니다."

**Reality:**
- Model accuracy = 32.1% (random: 33.3%)
- Away accuracy = 25.3% (random: 33.3%)
- This is **not an edge**, this is **negative edge + variance luck**

**If this were a real edge:**
- Accuracy should be > 35% minimum
- Win rate should increase with higher edge thresholds
- Performance should be consistent across leagues

**What we see instead:**
- Serie A: 19.9% accuracy (catastrophic)
- Draw bets: 0% accuracy
- No correlation between edge and win rate

---

## 7. Recommendations

### 🔴 DO NOT DEPLOY

This model should **NOT** be deployed for real money betting.

### 🟡 Required Fixes Before Re-test

1. **Fix Rolling xG Calculation**
   ```python
   def get_rolling_xg(team_name, current_date):
       all_games = df[
           ((df['h_name'] == team_name) | (df['a_name'] == team_name)) &
           (df['datetime'] < current_date)
       ].sort_values('datetime').tail(5)
       # Extract xG based on home/away
       ...
   ```

2. **Fix Team Name Matching**
   - Use exact team name mapping
   - Validate all odds matches manually
   - Add logging for unmatched games

3. **Verify Timestamp Alignment**
   - Ensure odds are pre-match, not closing lines
   - Verify xG data timestamps
   - Add explicit data leakage checks

4. **Increase Sample Size**
   - Need 2,000+ bets per league minimum
   - Run on 5+ seasons of data
   - Separate train/test periods

5. **Add Validation Metrics**
   - Track accuracy separately from ROI
   - Implement walk-forward analysis
   - Calculate Sharpe ratio and max drawdown

### 🟢 What to Test Next

1. Re-run with corrected Rolling xG
2. Test on 2018-2023 data (out-of-sample)
3. Compare against simple baselines:
   - Bet on all favorites
   - Bet on all home teams
   - Random betting
4. If model still shows < 35% accuracy → **abandon approach**

---

## 8. Final Verdict

| Aspect | Status | Evidence |
|--------|--------|----------|
| **Predictive Edge** | ❌ NONE | Accuracy = random (32.1%) |
| **Statistical Significance** | ⚠️ MISLEADING | Driven by variance, not skill |
| **Reproducibility** | ❌ FAILED | Claims don't match code output |
| **Code Quality** | ❌ BUGGY | Rolling xG + fuzzy matching issues |
| **Sample Size** | ⚠️ INSUFFICIENT | 246 bets too small |
| **Deployment Ready** | ❌ NO | Risk of capital loss |

---

## 9. Comparison to NBA System

The report claims this was built "답습해서 그대로 5대리그 축구 엔진을 구축" (built by following the NBA engine).

**NBA System Reality Check:**
- NBA has 82 games/season × 30 teams = 2,460 games/year
- Soccer 5 leagues: ~380 × 5 = 1,900 games/year
- BUT: Soccer has 3 outcomes (H/D/A) vs NBA's 2 (H/A)
- Soccer draw rate ~25-30% adds massive complexity
- Current model completely fails on draws (0% accuracy)

**The NBA approach may not translate to soccer without:**
1. Draw-specific modeling
2. League-specific tactical factors
3. Much larger sample sizes
4. Different edge thresholds

---

## 10. Conclusion

**The +53% La Liga ROI claim is UNVERIFIED and likely FALSE.**

What we actually found:
- ✅ Code exists and runs
- ✅ Some positive ROI observed (+92% La Liga)
- ❌ But accuracy is at random level (32.1%)
- ❌ ROI driven by 7 lucky high-odds wins (58.7% of profit)
- ❌ Multiple bugs in calculation logic
- ❌ Not reproducible from documentation
- ❌ Fails basic predictive model validation

**This is a high-variance lottery, not a predictive edge.**

Do not deploy without complete system rewrite and validation on 10x more data.

---

**Auditor**: Claude Code (Sonnet 4.5)
**Date**: 2025-12-29
**Verification Status**: ❌ FAILED
