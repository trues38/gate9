# 🦅 Regime Delta: Alpha Mining Report
**Dataset**: 11950 games (Unified Regime + Spread)

## 1. Spread Cover Rate by Edge Bucket
Global Cover Rate (id_spread=1): 52.0%
| edge_bucket   |   id_spread |
|:--------------|------------:|
| Trash <40     |    0.515086 |
| Weak 40-50    |    0.530931 |
| Tossup 50-60  |    0.520159 |
| Value 60-70   |    0.529126 |
| Strong 70-80  |    0.523286 |
| Extreme 80+   |    0.505692 |
## 2. High Edge (70+) Deep Dive

**By Flow State**:
| flow_state   |   id_spread |
|:-------------|------------:|
| STABLE       |    0.75     |
| STRONG_UP    |    0.514052 |
| UP           |    0.512921 |
## 3. Total (Over/Under) Analysis
Global Over Rate (id_total=1): 51.9%

**Over Rate by Flow State**:
| flow_state   |   id_total |
|:-------------|-----------:|
| STABLE       |   0.544355 |
| STRONG_UP    |   0.518813 |
| UP           |   0.517491 |
## 4. ALPHA CANDIDATES (ROI Zones)
- ❌ No simple segments > 54% found.
