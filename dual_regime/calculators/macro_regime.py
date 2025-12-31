#!/usr/bin/env python3
"""
Macro Regime Calculator
========================
Wrapper around regime_zero's StateMachineEngine.
Extracts dominant macro state for dual regime matching.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import logging

import pandas as pd

# Add regime_zero to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "regime_zero" / "engine" / "state_graph"))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MacroRegimeCalculator:
    """Calculates macro regimes using StateMachineEngine"""

    def __init__(self, econ_data_path: str = None, output_dir: str = None):
        if econ_data_path is None:
            econ_data_path = Path(__file__).parent.parent.parent / "regime_zero" / "data" / "raw_econ_archive.jsonl"
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "data" / "processed"

        self.econ_data_path = Path(econ_data_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Import StateMachineEngine
        try:
            from state_machine_engine import StateMachineEngine
            self.engine = StateMachineEngine()
            logger.info("✅ StateMachineEngine loaded successfully")
        except Exception as e:
            logger.error(f"Failed to import StateMachineEngine: {e}")
            logger.error("Make sure regime_zero/engine/state_graph/ is accessible")
            raise

        # Load econ data cache
        self.econ_data_cache = self._load_econ_data()

    def _load_econ_data(self) -> dict:
        """Load all econ data into memory for fast lookup"""
        if not self.econ_data_path.exists():
            logger.warning(f"Economic data file not found: {self.econ_data_path}")
            logger.warning("Macro regime calculation will be limited to available dates")
            return {}

        cache = {}
        try:
            with open(self.econ_data_path, 'r') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        date = record.get('date')
                        if date:
                            cache[date] = record.get('econ_data', {})

            logger.info(f"Loaded {len(cache)} dates from economic archive")
            return cache

        except Exception as e:
            logger.error(f"Failed to load economic data: {e}")
            return {}

    def calculate(self, date: str) -> dict:
        """
        Calculate macro regime for a specific date

        Args:
            date: Date string in YYYY-MM-DD format

        Returns:
            dict with keys: date, dominant_state, active_states, confidence, imbalances
            Returns None if no data available for date
        """
        econ_data = self.econ_data_cache.get(date)
        if not econ_data:
            return None

        try:
            result = self.engine.process(econ_data, date)

            # Extract dominant state (highest confidence)
            if result.get('active_states') and len(result['active_states']) > 0:
                dominant = result['active_states'][0]  # Already sorted by confidence
                return {
                    'date': date,
                    'dominant_state': dominant['state'],
                    'active_states': [s['state'] for s in result['active_states']],
                    'confidence': dominant['confidence'],
                    'imbalances': result.get('observation_summary', {}).get('imbalances', {})
                }
            else:
                # No active states = neutral market
                return {
                    'date': date,
                    'dominant_state': 'NEUTRAL',
                    'active_states': [],
                    'confidence': 0.0,
                    'imbalances': {}
                }

        except Exception as e:
            logger.error(f"Error calculating macro regime for {date}: {e}")
            return None

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

        dates = pd.date_range(start_date, end_date, freq='D')
        results = []

        for date in dates:
            date_str = date.strftime("%Y-%m-%d")
            regime = self.calculate(date_str)

            if regime:
                results.append(regime)

        if not results:
            logger.warning("No macro regime data calculated (check raw_econ_archive.jsonl)")
            return pd.DataFrame()

        df = pd.DataFrame(results)
        logger.info(f"Calculated {len(df)} macro regime snapshots")

        return df

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
        df[['date', 'dominant_state', 'confidence', 'active_states_json']].to_csv(
            output_path,
            index=False
        )

        logger.info(f"✅ Saved macro regimes to {output_path}")
        logger.info(f"   Dates: {df['date'].min()} to {df['date'].max()}")
        logger.info(f"   Rows: {len(df)}")

        # Print state distribution
        state_counts = df['dominant_state'].value_counts()
        logger.info(f"\nDominant State Distribution:")
        for state, count in state_counts.head(10).items():
            logger.info(f"  {state}: {count} days ({count/len(df)*100:.1f}%)")

        return str(output_path)


if __name__ == "__main__":
    calculator = MacroRegimeCalculator()
    output_path = calculator.calculate_and_save(start_date="2015-01-01")

    if output_path:
        print(f"\n✅ Macro regimes saved to: {output_path}")
    else:
        print("\n❌ Failed to calculate macro regimes")
