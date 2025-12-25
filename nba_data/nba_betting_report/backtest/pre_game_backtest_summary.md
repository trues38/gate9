# Pre-Game Engine Backtest Summary

This backtest evaluates structural consistency, not prediction accuracy.
No outcome-based features were used in pre-game scoring.

Total Analyzed Games: 374

## 1. Monotonicity (Decile Analysis)
|   pre_decile |   avg_pre |   avg_struct |   avg_margin |   count |
|-------------:|----------:|-------------:|-------------:|--------:|
|            9 |   63.3711 |      42.7105 |      13.3684 |      38 |
|            8 |   54.3189 |      37.4324 |      12.1351 |      37 |
|            7 |   50.8189 |      34.8378 |      11.1351 |      37 |
|            6 |   48.2765 |      40.5294 |      13.7059 |      34 |
|            5 |   46.1667 |      38.9744 |      13.359  |      39 |
|            4 |   44.0974 |      38.7692 |      14.2821 |      39 |
|            3 |   42.0838 |      39.7838 |      12.3514 |      37 |
|            2 |   40.4412 |      36.5    |      10.6176 |      34 |
|            1 |   38.2293 |      36.7805 |      10.9268 |      41 |
|            0 |   32.85   |      40.7632 |      12.1842 |      38 |

## 2. Separation Power
| Segment | Blowout Rate (>=15) | Close Game Rate (<=5) |
| :--- | :--- | :--- |
| Top 20% (Pre >= 51.8) | 28.0% | 26.7% |
| Bottom 20% (Pre <= 39.5) | 22.8% | 26.6% |


## 3. Structural Failures (High Pre-Edge but Low Structural Support)
Definition: Pre-Edge Top 20% AND Structural Edge Bottom 30% (<= 27.0)
Count: 26

| game_id             |   pre_score |   struct_score |   score_margin |
|:--------------------|------------:|---------------:|---------------:|
| 2025-10-24-ORL-ATL  |        79.9 |             13 |              4 |
| 2025-10-24-BKN-CLE  |        77.4 |             22 |              7 |
| 2025-10-25-PHI-CHA  |        52.4 |             13 |              4 |
| 2025-10-27-PHI-ORL  |        58.2 |             22 |             12 |
| 2025-10-28-WSH-PHI  |        60.7 |             27 |              5 |
| 2025-10-29-PHX-MEM  |        53.2 |             11 |              1 |
| 2025-10-30-CHA-ORL  |        57.9 |             26 |             16 |
| 2025-10-30-SA-MIA   |        55   |             15 |              6 |
| 2025-10-31-CHI-NY   |        53.9 |             22 |             10 |
| 2025-11-01-DET-DAL  |        54.8 |             19 |             12 |
| 2025-11-03-HOU-DAL  |        57.6 |             27 |              8 |
| 2025-11-03-DEN-SAC  |        57.4 |             20 |              6 |
| 2025-11-08-SA-NO    |        52.2 |             23 |              7 |
| 2025-11-10-CHI-SA   |        52.1 |             20 |              4 |
| 2025-11-11-NY-MEM   |        58.8 |             18 |             13 |
| 2025-11-12-SA-GS    |        56.1 |             25 |              5 |
| 2025-11-14-SA-GS    |        55.4 |             18 |              1 |
| 2025-11-18-ORL-GS   |        51.9 |             24 |              8 |
| 2025-11-19-OKC-SAC  |        55.2 |             21 |             14 |
| 2025-11-22-DEN-SAC  |        57.5 |             10 |              5 |
| 2025-11-23-TOR-BKN  |        58.3 |             19 |             10 |
| 2025-11-23-PHX-SA   |        54.3 |             26 |              9 |
| 2025-11-28-DEN-SA   |        56.1 |             27 |              3 |
| 2025-12-08-IND-SAC  |        57   |             25 |             11 |
| 2025-12-12-MEM-UTAH |        52   |             27 |              4 |
| 2025-12-12-DAL-BKN  |        52.3 |             16 |              8 |