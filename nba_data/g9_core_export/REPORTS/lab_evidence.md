# 🧪 Track 2: Regime x Market Research Lab
**Dataset**: 11950 games

## Available Regimes
| regime_type         |   count |
|:--------------------|--------:|
| Favorite_Hold       |    2695 |
| Star_Takeover       |    2308 |
| Blowout_Loss        |    1624 |
| Favorite_Collapse   |    1426 |
| Blowout_Win         |    1342 |
| Underdog_Upset      |    1061 |
| Underdog_Resilience |    1061 |
| Grind_Win           |     242 |
| Grind_Loss          |     190 |
| Favorite_Resilience |       1 |

## 🧪 Experiment A: Spread (Regime Impact)
Does Regime Type predict Spread Cover better than Edge Score?

**Spread Cover Rates by Regime (Line 4.5 - 12.5)**:
| regime_type         |   count |   fav_cover_rate |   dog_cover_rate |
|:--------------------|--------:|-----------------:|-----------------:|
| Blowout_Win         |     764 |        0.0248691 |        0.975131  |
| Blowout_Loss        |     965 |        0.0766839 |        0.923316  |
| Favorite_Hold       |    1738 |        0.39183   |        0.587457  |
| Star_Takeover       |    1094 |        0.50457   |        0.472578  |
| Grind_Win           |      87 |        0.666667  |        0.264368  |
| Grind_Loss          |      61 |        0.754098  |        0.213115  |
| Underdog_Resilience |     559 |        0.779964  |        0.207513  |
| Underdog_Upset      |     792 |        0.941919  |        0.0555556 |
| Favorite_Collapse   |     747 |        0.974565  |        0.0227577 |

## 🧪 Experiment B: Total (Regime Impact)
Does Regime Type predict Over/Under?

**Over/Under Rates by Regime (Total 210-240)**:
| regime_type         |   count |   over_rate |   under_rate |
|:--------------------|--------:|------------:|-------------:|
| Grind_Win           |     218 |    0.288991 |     0.711009 |
| Grind_Loss          |     161 |    0.322981 |     0.677019 |
| Favorite_Hold       |    2396 |    0.45576  |     0.54424  |
| Underdog_Resilience |     956 |    0.463389 |     0.536611 |
| Favorite_Collapse   |    1288 |    0.46972  |     0.53028  |
| Underdog_Upset      |     950 |    0.490526 |     0.509474 |
| Blowout_Loss        |    1466 |    0.508868 |     0.491132 |
| Blowout_Win         |    1217 |    0.51931  |     0.48069  |
| Star_Takeover       |    2049 |    0.593948 |     0.406052 |

## 🧪 Experiment C: Dead Zone Flip
Can specific Regimes save us from the 'Dead Zones'?
**Baseline Dead Zone (Fav Cover Rate)**: 47.1% (N=891)

**Dead Zone Breakdown by Regime**:
| regime_type       |   count |   fav_cover_rate |
|:------------------|--------:|-----------------:|
| Blowout_Loss      |      56 |         1        |
| Underdog_Upset    |      33 |         1        |
| Favorite_Collapse |     212 |         0.995283 |
| Star_Takeover     |     151 |         0.456954 |
| Grind_Win         |      19 |         0.263158 |
| Favorite_Hold     |     296 |         0.148649 |
| Blowout_Win       |     122 |         0        |

## 💡 Insights for Track 1 Tuning
- **Dog Triggers (>60%)**: ['Blowout_Win', 'Blowout_Loss']
- **Under Triggers (>60%)**: ['Grind_Win', 'Grind_Loss']
