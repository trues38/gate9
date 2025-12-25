# 🔥 Regime Alpha Survivors Summary
**Dataset**: 11950 games
**Criteria**: N >= 30, WinRate >= 55%, ROI > +2%
❌ No strategies met the criteria (N>=30, ROI>2%). Market is efficient.


## 💀 Dead Zones (Avoid)
Conditions where Win Rate < 48% (Systematic Loss).

**Top Spread Fades (Avoid/Fade THIS Side):**
| edge_bucket   | flow_state   | bet_side       |   count |   win_rate |   roi |
|:--------------|:-------------|:---------------|--------:|-----------:|------:|
| Value 60-70   | STRONG_UP    | FAVORITE_COVER |     881 |     0.4767 | -8.99 |

**Top Total Fades (Avoid/Fade THIS Side):**
| flow_state   | edge_bucket   | bet_side   |   count |   win_rate |    roi |
|:-------------|:--------------|:-----------|--------:|-----------:|-------:|
| STABLE       | Weak <50      | UNDER      |     216 |     0.4769 |  -8.97 |
| STRONG_UP    | Value 60-70   | OVER       |     891 |     0.4747 |  -9.37 |
| UP           | Extreme 80+   | UNDER      |     559 |     0.4723 |  -9.84 |
| UP           | Tossup 50-60  | OVER       |    1012 |     0.4704 | -10.21 |
| STRONG_UP    | Extreme 80+   | UNDER      |    1111 |     0.4635 | -11.51 |
| STRONG_UP    | Tossup 50-60  | OVER       |     726 |     0.4518 | -13.75 |