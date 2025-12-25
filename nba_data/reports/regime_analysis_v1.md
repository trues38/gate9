# 📊 Regime Pattern Analysis
**Source**: 7171 games (2019-2025)

## 1. Edge Bucket Performance
| edge_bucket   |   games |   win_rate |   collapse_rate |   hold_rate |   upset_rate |   blowout_win_rate |
|:--------------|--------:|-----------:|----------------:|------------:|-------------:|-------------------:|
| A_45_55       |    1790 |      44.4% |            5.5% |        5.9% |         5.5% |               7.6% |
| B_55_60       |     895 |      53.3% |           21.2% |       22.3% |         2.5% |              13.0% |
| C_60_65       |     941 |      57.5% |           25.3% |       31.6% |         2.8% |              12.8% |
| D_65_70       |     924 |      62.8% |           24.6% |       36.6% |         4.0% |              13.2% |
| E_70_Plus     |    2621 |      72.3% |           21.3% |       37.7% |         2.2% |              22.2% |

## 2. Danger Zones: Collapse Rate by Flow
When does a Favorite Collapse happen based on Momentum?

| edge_bucket   | flow_state   |   games |   collapse_rate |   win_rate |
|:--------------|:-------------|--------:|----------------:|-----------:|
| A_45_55       | UP           |    1074 |            5.9% |      44.4% |
| A_45_55       | STRONG_UP    |     687 |            4.9% |      43.5% |
| B_55_60       | UP           |     502 |           21.9% |      56.4% |
| B_55_60       | STRONG_UP    |     384 |           19.5% |      50.0% |
| C_60_65       | UP           |     525 |           25.9% |      58.3% |
| C_60_65       | STRONG_UP    |     415 |           24.3% |      56.6% |
| D_65_70       | UP           |     460 |           26.1% |      61.5% |
| D_65_70       | STRONG_UP    |     460 |           22.8% |      64.1% |
| E_70_Plus     | STRONG_UP    |    1492 |           21.6% |      71.6% |
| E_70_Plus     | UP           |    1125 |           20.7% |      73.2% |

## 3. The 'Trap' Matrix: Edge vs Confidence
Where does high confidence meet high failure?

| edge_bucket   | fav_confidence   |   games |   collapse_rate |   win_rate |
|:--------------|:-----------------|--------:|----------------:|-----------:|
| A_45_55       | LOW              |    1434 |            4.0% |      43.7% |
| A_45_55       | MID              |     356 |           11.5% |      46.9% |
| B_55_60       | MID              |     895 |           21.2% |      53.3% |
| C_60_65       | MID              |     563 |           24.7% |      54.2% |
| C_60_65       | HIGH             |     378 |           26.2% |      62.4% |
| D_65_70       | HIGH             |     924 |           24.6% |      62.8% |
| E_70_Plus     | HIGH             |     488 |           28.1% |      61.7% |
| E_70_Plus     | EXTREME          |    2133 |           19.7% |      74.7% |