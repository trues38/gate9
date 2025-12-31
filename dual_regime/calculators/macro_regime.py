#!/usr/bin/env python3
"""
Macro Regime Calculator (CSV-based)
====================================
Calculates macro economic regimes using Yahoo Finance CSV data.
No dependency on raw_econ_archive.jsonl or StateMachineEngine.

Regime Classification Logic:
- Uses VIX, DXY, TNX, HYG, LQD, TLT, SPX to determine market state
- Inspired by G9 25-state engine but simplified for CSV data availability
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import logging

import pandas as pd
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MacroRegimeCalculator:
    """Calculates macro regimes from Yahoo Finance CSV data"""

    def __init__(self, raw_data_dir: str = None, output_dir: str = None):
        if raw_data_dir is None:
            raw_data_dir = Path(__file__).parent.parent / "data" / "raw"
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "data" / "processed"

        self.raw_data_dir = Path(raw_data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load all macro indicators into memory
        self.macro_data = self._load_macro_data()

    def _load_macro_data(self) -> pd.DataFrame:
        """
        Load all macro indicator CSVs and merge into single DataFrame

        Returns:
            DataFrame with columns: Date, VIX, DXY, TNX, HYG, LQD, TLT, SPX
        """
        logger.info("Loading macro indicator CSVs...")

        indicators = {
            'VIX': 'VIX.csv',
            'DXY': 'DXY.csv',
            'TNX': 'TNX.csv',      # 10-year Treasury Yield
            'HYG': 'HYG.csv',      # High Yield Corporate Bond ETF
            'LQD': 'LQD.csv',      # Investment Grade Corporate Bond ETF
            'TLT': 'TLT.csv',      # 20+ Year Treasury Bond ETF
            'SPX': 'SPX.csv',      # S&P 500 Index
            'GOLD': 'GOLD.csv',    # Gold Futures
            'OIL': 'OIL.csv'       # Crude Oil Futures
        }

        # Load first indicator as base
        base_df = None

        for name, filename in indicators.items():
            filepath = self.raw_data_dir / filename

            if not filepath.exists():
                logger.warning(f"Missing {filename}, skipping {name}")
                continue

            try:
                df = pd.read_csv(filepath)
                df['Date'] = pd.to_datetime(df['Date'])

                # Keep only Date and Close, rename Close to indicator name
                df = df[['Date', 'Close']].copy()
                df.rename(columns={'Close': name}, inplace=True)

                if base_df is None:
                    base_df = df
                else:
                    base_df = base_df.merge(df, on='Date', how='outer')

                logger.info(f"  ✅ {name}: {len(df)} rows")

            except Exception as e:
                logger.error(f"  ❌ Failed to load {name}: {e}")

        if base_df is None:
            raise ValueError("No macro indicators loaded!")

        # Sort by date and forward-fill missing values
        base_df = base_df.sort_values('Date').reset_index(drop=True)
        base_df = base_df.ffill()

        # Calculate derived indicators
        if 'HYG' in base_df.columns and 'LQD' in base_df.columns:
            # Credit spread proxy: HY/IG ratio (higher = more stress)
            base_df['CREDIT_SPREAD'] = base_df['HYG'] / base_df['LQD']

        if 'TLT' in base_df.columns and 'SPX' in base_df.columns:
            # Flight to safety: TLT/SPX ratio (higher = risk-off)
            base_df['FLIGHT_TO_SAFETY'] = base_df['TLT'] / base_df['SPX']

        logger.info(f"✅ Loaded {len(base_df)} trading days across {len(base_df.columns)-1} indicators")
        logger.info(f"   Date range: {base_df['Date'].min().date()} to {base_df['Date'].max().date()}")

        return base_df

    def _classify_regime(self, row: pd.Series) -> dict:
        """
        Classify macro regime for a single date based on indicator thresholds

        Args:
            row: DataFrame row with VIX, DXY, TNX, HYG, LQD, etc.

        Returns:
            dict with 'dominant_state', 'active_states', 'confidence'

        Regime Logic (inspired by G9 25-state engine):
        - RISK_OFF: VIX > 25, CREDIT_SPREAD widening, FLIGHT_TO_SAFETY rising
        - RISK_ON: VIX < 15, SPX rising, Credit stable
        - LIQUIDITY_STRESS: HYG falling sharply, credit spreads widening
        - DOLLAR_STRENGTH: DXY > 105
        - RATE_SHOCK: TNX rising sharply (>20bp in 20 days)
        - STAGFLATION: High rates + falling stocks
        - GOLDILOCKS: Low VIX + rising stocks + stable rates
        - NEUTRAL: None of the above
        """
        states = []

        # Extract values with NaN handling
        vix = row.get('VIX', np.nan)
        dxy = row.get('DXY', np.nan)
        tnx = row.get('TNX', np.nan)
        hyg = row.get('HYG', np.nan)
        spx = row.get('SPX', np.nan)
        credit_spread = row.get('CREDIT_SPREAD', np.nan)
        flight_to_safety = row.get('FLIGHT_TO_SAFETY', np.nan)

        # Momentum calculations (from previous rows, handled externally)
        hyg_mom = row.get('HYG_mom_20d', 0)
        spx_mom = row.get('SPX_mom_20d', 0)
        tnx_change = row.get('TNX_change_20d', 0)
        credit_spread_change = row.get('CREDIT_SPREAD_change_20d', 0)

        # === PRIMARY REGIMES ===

        # 1. RISK_OFF (highest priority in crisis)
        if vix > 25 or (credit_spread_change > 0.05 and hyg_mom < -0.05):
            confidence = min(100, vix * 2) if vix > 25 else 70
            states.append({
                'state': 'RISK_OFF',
                'confidence': confidence,
                'reason': f'VIX={vix:.1f}' if vix > 25 else f'Credit stress (HYG {hyg_mom*100:.1f}%)'
            })

        # 2. LIQUIDITY_STRESS (credit markets freezing)
        if hyg_mom < -0.10 or credit_spread_change > 0.08:
            states.append({
                'state': 'LIQUIDITY_STRESS',
                'confidence': 80,
                'reason': f'HYG -{abs(hyg_mom)*100:.1f}%, Credit spread +{credit_spread_change*100:.1f}%'
            })

        # 3. RISK_ON (low volatility, rising stocks)
        if vix < 15 and spx_mom > 0.05 and credit_spread_change < 0.02:
            states.append({
                'state': 'RISK_ON',
                'confidence': 75,
                'reason': f'VIX={vix:.1f}, SPX +{spx_mom*100:.1f}%'
            })

        # 4. GOLDILOCKS (perfect conditions)
        if vix < 13 and spx_mom > 0.08 and abs(tnx_change) < 0.3:
            states.append({
                'state': 'GOLDILOCKS',
                'confidence': 85,
                'reason': f'Low vol (VIX={vix:.1f}), rising stocks, stable rates'
            })

        # === SECONDARY REGIMES ===

        # 5. DOLLAR_STRENGTH
        if dxy > 105:
            states.append({
                'state': 'DOLLAR_STRENGTH',
                'confidence': 70,
                'reason': f'DXY={dxy:.1f}'
            })

        # 6. RATE_SHOCK (rapid rate increase)
        if tnx_change > 0.5:  # >50bp increase in 20 days
            states.append({
                'state': 'RATE_SHOCK',
                'confidence': 75,
                'reason': f'TNX +{tnx_change:.2f}% in 20 days'
            })

        # 7. STAGFLATION (high rates + weak stocks)
        if tnx > 4.5 and spx_mom < -0.05:
            states.append({
                'state': 'STAGFLATION',
                'confidence': 70,
                'reason': f'TNX={tnx:.2f}%, SPX {spx_mom*100:.1f}%'
            })

        # 8. DELEVERAGING (bond selloff + stock selloff)
        if hyg_mom < -0.08 and spx_mom < -0.08 and vix > 20:
            states.append({
                'state': 'DELEVERAGING_PRESSURE',
                'confidence': 80,
                'reason': f'Multi-asset selloff (HYG {hyg_mom*100:.1f}%, SPX {spx_mom*100:.1f}%)'
            })

        # 9. FLIGHT_TO_QUALITY (bonds up, stocks down)
        if flight_to_safety > row.get('FLIGHT_TO_SAFETY_avg_60d', flight_to_safety) * 1.1:
            states.append({
                'state': 'FLIGHT_TO_QUALITY',
                'confidence': 65,
                'reason': 'TLT/SPX ratio elevated'
            })

        # 10. MODERATE_GROWTH (mild positive, not euphoric)
        if 15 <= vix <= 20 and 0.03 <= spx_mom <= 0.10 and credit_spread_change < 0.03:
            states.append({
                'state': 'MODERATE_GROWTH',
                'confidence': 70,
                'reason': f'Healthy growth (VIX={vix:.1f}, SPX +{spx_mom*100:.1f}%)'
            })

        # === FALLBACK ===
        if not states:
            states.append({
                'state': 'NEUTRAL',
                'confidence': 50,
                'reason': 'No strong regime signals'
            })

        # Sort by confidence (highest first)
        states.sort(key=lambda x: x['confidence'], reverse=True)

        return {
            'dominant_state': states[0]['state'],
            'active_states': [s['state'] for s in states],
            'confidence': states[0]['confidence'],
            'reason': states[0]['reason'],
            'all_states': states  # For debugging
        }

    def calculate_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Calculate macro regimes for a date range

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with columns: date, dominant_state, active_states, confidence
        """
        logger.info(f"Calculating macro regimes from {start_date} to {end_date}")

        # Filter date range
        df = self.macro_data.copy()
        df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]

        if df.empty:
            logger.error(f"No data in range {start_date} to {end_date}")
            return pd.DataFrame()

        # Calculate momentum indicators (needed for regime classification)
        logger.info("Calculating momentum indicators...")

        if 'HYG' in df.columns:
            df['HYG_mom_20d'] = df['HYG'].pct_change(20)
        if 'SPX' in df.columns:
            df['SPX_mom_20d'] = df['SPX'].pct_change(20)
            df['SPX_mom_60d'] = df['SPX'].pct_change(60)
        if 'TNX' in df.columns:
            df['TNX_change_20d'] = df['TNX'].diff(20)
        if 'CREDIT_SPREAD' in df.columns:
            df['CREDIT_SPREAD_change_20d'] = df['CREDIT_SPREAD'].pct_change(20)
        if 'FLIGHT_TO_SAFETY' in df.columns:
            df['FLIGHT_TO_SAFETY_avg_60d'] = df['FLIGHT_TO_SAFETY'].rolling(60).mean()

        # Apply regime classification to each row
        logger.info("Classifying regimes...")
        results = []

        for idx, row in df.iterrows():
            regime = self._classify_regime(row)
            results.append({
                'date': row['Date'].strftime('%Y-%m-%d'),
                'dominant_state': regime['dominant_state'],
                'active_states': regime['active_states'],
                'confidence': regime['confidence'],
                'reason': regime['reason']
            })

        result_df = pd.DataFrame(results)
        logger.info(f"✅ Calculated {len(result_df)} macro regime snapshots")

        return result_df

    def calculate_and_save(self, start_date: str = "2015-01-01", end_date: str = None) -> str:
        """
        Calculate macro regimes and save to CSV

        Args:
            start_date: Start date
            end_date: End date (defaults to today)

        Returns:
            Path to saved CSV file
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        df = self.calculate_range(start_date, end_date)

        if df.empty:
            logger.error("No macro regime data to save")
            return None

        # Convert active_states list to JSON string for CSV storage
        df['active_states_json'] = df['active_states'].apply(json.dumps)

        # Save to CSV
        output_path = self.output_dir / "macro_regimes.csv"
        df[['date', 'dominant_state', 'confidence', 'active_states_json', 'reason']].to_csv(
            output_path,
            index=False
        )

        logger.info(f"✅ Saved macro regimes to {output_path}")
        logger.info(f"   Dates: {df['date'].min()} to {df['date'].max()}")
        logger.info(f"   Rows: {len(df)}")

        # Print state distribution
        state_counts = df['dominant_state'].value_counts()
        logger.info(f"\nDominant State Distribution:")
        for state, count in state_counts.items():
            logger.info(f"  {state}: {count} days ({count/len(df)*100:.1f}%)")

        return str(output_path)


if __name__ == "__main__":
    calculator = MacroRegimeCalculator()
    output_path = calculator.calculate_and_save(start_date="2015-01-01")

    if output_path:
        print(f"\n✅ Macro regimes saved to: {output_path}")
    else:
        print("\n❌ Failed to calculate macro regimes")
