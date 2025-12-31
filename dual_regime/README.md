# Dual Regime System

Economic Macro Regimes × Sector Technical Regimes = Stock Selection Framework

## Overview

The Dual Regime System combines **25 economic macro states** (from `state_machine_engine.py`) with **5-phase sector technical regimes** to create a comprehensive cross-sectional analysis framework for US and Korean stock selection.

## Architecture

```
Economic Regime (25 states)    Sector Regime (5 phases)      Stock Outcomes
------------------------       ----------------------         ---------------
LIQUIDITY_STRESS        ×      BOTTOM                   →    NVDA: +45% (3m)
RISK_APPETITE_EXPANSION ×      RECOVERY                 →    Samsung: +32% (3m)
DELEVERAGING_PRESSURE   ×      PEAK                     →    ...
...                            DECLINE
                               NEUTRAL
```

## Data Scope

- **24 ETFs**: SOXX, XLK, XBI, XLV, XLF, XLE, XLI, XLY, XLP, XLU, XLB, XLRE, LIT, CARZ, TAN, ARKK, SPY, QQQ, DIA, IWM, EEM, EWY, EWJ, VGK
- **60+ US Stocks**: AAPL, NVDA, TSLA, AMD, JPM, etc.
- **20 KR Stocks**: 005930.KS (Samsung), 000660.KS (SK Hynix), etc.
- **13 Macro Indicators**: ^VIX, DX-Y.NYB, ^TNX, GC=F, CL=F, etc.
- **Date Range**: 2015-01-01 to present (10 years)

## Installation

```bash
cd /Users/js/g9/dual_regime
pip install yfinance pandas numpy neo4j python-dotenv
```

## Quick Start

### Full Pipeline (All 5 Steps)

```bash
python run_data_pipeline.py --start 2015-01-01
```

### Run Specific Steps

```bash
# Step 1: Collect data only
python run_data_pipeline.py --step 1

# Step 2: Calculate sector regimes
python run_data_pipeline.py --step 2

# Step 3: Calculate macro regimes
python run_data_pipeline.py --step 3

# Step 4: Match dual regimes
python run_data_pipeline.py --step 4

# Step 5: Calculate outcomes
python run_data_pipeline.py --step 5
```

### Skip Neo4j (CSV only)

```bash
python run_data_pipeline.py --no-neo4j
```

## Pipeline Steps

### Step 1: Data Collection (~10 min)
Downloads historical price data using yfinance with parallel workers (ThreadPoolExecutor).

**Output:** `data/raw/*.csv` (110+ files, ~1.8MB)

### Step 2: Sector Regime Calculation (~5 min)
Calculates 5-phase technical regimes based on momentum, volatility, relative strength vs SPY.

**Phases:**
- `BOTTOM`: Deep drawdown, declining volatility, underperforming
- `RECOVERY`: Momentum turning positive, outperforming SPY
- `PEAK`: Strong momentum, rising volatility
- `DECLINE`: Momentum turning negative
- `NEUTRAL`: Everything else

**Output:** `data/processed/*_regime.csv` (110+ files, ~2.1MB)

### Step 3: Macro Regime Calculation (~2 min)
Wraps `state_machine_engine.py` to extract dominant economic state.

**Output:** `data/processed/macro_regimes.csv` (~100KB, 2,500 rows)

### Step 4: Dual Regime Matching (~10 min)
Combines macro state × sector phase for each date, creates Neo4j nodes.

**Output:** Neo4j graph (~42,500 DualRegime nodes)

### Step 5: Outcome Calculation (~20 min)
Calculates forward returns (1m, 3m, 6m), max drawdown, Sharpe ratio.

**Output:** Neo4j graph (~4.4M Outcome nodes)

## Neo4j Schema

```cypher
(:MacroState {id, name, date, confidence})
(:DualRegime {regime_id, macro_state, sector, sector_phase, date})
(:Stock {ticker, name, sector, market})
(:Outcome {ticker, regime_id, return_1m, return_3m, return_6m, max_dd_3m, sharpe_3m})

(MacroState)-[:FORMS_DUAL_REGIME]->(DualRegime)
(Stock)-[:PERFORMED_IN]->(DualRegime)-[:RESULTED_IN]->(Outcome)
```

## Example Queries

### Query 1: Best stocks in LIQUIDITY_STRESS × SEMICONDUCTORS × RECOVERY

```cypher
MATCH (d:DualRegime {
  macro_state: 'LIQUIDITY_STRESS',
  sector: 'SEMICONDUCTORS',
  sector_phase: 'RECOVERY'
})
MATCH (d)-[:RESULTED_IN]->(o:Outcome)

WITH o.ticker AS ticker,
     AVG(o.return_3m) AS avg_return,
     STDEV(o.return_3m) AS std_return,
     COUNT(o) AS occurrences

RETURN ticker,
       avg_return,
       avg_return / std_return AS sharpe,
       occurrences
ORDER BY sharpe DESC
LIMIT 10
```

### Query 2: Surviving stocks in DELEVERAGING × FINANCE × DECLINE

```cypher
MATCH (d:DualRegime {
  macro_state: 'DELEVERAGING_PRESSURE',
  sector: 'FINANCE',
  sector_phase: 'DECLINE'
})
MATCH (d)-[:RESULTED_IN]->(o:Outcome)
WHERE o.return_3m > -0.10

RETURN o.ticker,
       AVG(o.return_3m) AS avg_return,
       COUNT(o) AS survival_count
ORDER BY survival_count DESC
```

### Query 3: Find historical twins for current regime

```cypher
MATCH (current:DualRegime {date: '2025-12-31'})
WITH collect(current.regime_id) AS current_regimes

MATCH (past:DualRegime)
WHERE past.date < '2025-12-31'
  AND past.regime_id IN current_regimes

WITH past.date AS historical_date, COUNT(*) AS matching_regimes
ORDER BY matching_regimes DESC
LIMIT 5

RETURN historical_date, matching_regimes
```

## Configuration

### Neo4j Connection

```bash
export NEO4J_URI="bolt://localhost:7688"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="regime2025"
```

### Sector Taxonomy

Edit `config/sector_mapping.py` to customize:
- Sector definitions
- ETF mappings
- Stock assignments

## Directory Structure

```
dual_regime/
├── config/
│   └── sector_mapping.py       # 17 sector taxonomy
├── collectors/
│   ├── etf_collector.py        # 24 ETFs
│   ├── stock_collector.py      # US + KR stocks
│   └── macro_collector.py      # 13 macro indicators
├── calculators/
│   ├── sector_regime.py        # 5-phase classifier
│   └── macro_regime.py         # StateMachineEngine wrapper
├── loaders/
│   └── neo4j_loader.py         # Neo4j operations
├── data/
│   ├── raw/                    # CSV price data
│   └── processed/              # Regime calculations
├── run_data_pipeline.py        # Main orchestrator
├── pipeline.log                # Execution log
└── README.md
```

## Performance

- **Initial Backfill**: ~47 minutes (one-time)
- **Daily Update**: ~2 minutes (incremental)
- **Simple Query**: <10ms
- **Aggregation Query**: ~100ms
- **Total Storage**: ~504MB (CSV + Neo4j)

## Deployment

### Local Development (Current)
```bash
cd /Users/js/g9/dual_regime
python run_data_pipeline.py
```

### VPS Production
```bash
scp -r dual_regime/ root@141.164.35.214:/opt/g9/
ssh root@141.164.35.214
cd /opt/g9/dual_regime
python run_data_pipeline.py
```

## Troubleshooting

### Neo4j Connection Failed
```bash
# Check if Neo4j is running
docker ps | grep neo4j

# Create dual_regime database
# (Neo4j Browser: CREATE DATABASE dual_regime)
```

### Missing SPY Benchmark
Will auto-download if missing, or manually download:
```bash
python -c "from collectors.macro_collector import MacroCollector; c = MacroCollector(); c.download_indicator('SPX', '^GSPC', '2015-01-01')"
```

### Korean Stock Data Issues
Korean stocks may have gaps due to different trading calendar. System auto-handles with forward-fill.

## Next Steps

1. **Daily Updates**: Add cron job for incremental data refresh
2. **Parquet Export**: Convert CSV to Parquet for data science workflows
3. **Dashboard**: Build Streamlit app for regime visualization
4. **Backtest Engine**: Calculate portfolio returns using regime signals
5. **Alert System**: Notify on high-return regime pattern matches

## License

Internal G9 Project - Not for public distribution
