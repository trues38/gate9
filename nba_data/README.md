# NBA Regime Engine

## Overview
This project focuses on building a "Regime Engine" for NBA players, analyzing their career phases (Regimes) by combining statistical data with narrative data (news, stories).

## Specification
See [SPEC.md](./SPEC.md) for the detailed data dictionary, folder structure, and pipeline logic.

## Directory Structure
- `seasons/`: Aggregated season stats
- `gamelogs/`: Detailed game-by-game stats
- `stories_clean/`: Processed narrative data
- `regimes/`: Final output of the engine

## Getting Started
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the pipeline steps in order (see `pipeline/` folder):
   - `python pipeline/01_fetch_players.py`
   - `python pipeline/02_fetch_stats.py`
   - ...
