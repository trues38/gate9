#!/usr/bin/env python3
"""
Dual Regime Data Pipeline
==========================
Orchestrates the complete 5-step pipeline:
1. Collect raw data (ETFs, stocks, macro)
2. Calculate sector regimes
3. Calculate macro regimes
4. Match dual regimes
5. Calculate outcomes and load to Neo4j
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import logging
import json

import pandas as pd
import numpy as np

# Add collectors, calculators, loaders to path
sys.path.insert(0, str(Path(__file__).parent))

from collectors.etf_collector import ETFCollector
from collectors.stock_collector import StockCollector
from collectors.macro_collector import MacroCollector
from calculators.sector_regime import SectorRegimeCalculator
from calculators.macro_regime import MacroRegimeCalculator
from loaders.neo4j_loader import DualRegimeNeo4jLoader
from config.sector_mapping import SECTOR_TAXONOMY, TICKER_TO_SECTOR, ALL_ETFS, ALL_US_STOCKS, ALL_KR_STOCKS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent / "pipeline.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DualRegimePipeline:
    """Main pipeline orchestrator"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path(__file__).parent / "data"

        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"

        # Initialize components
        self.etf_collector = ETFCollector(output_dir=self.raw_dir)
        self.stock_collector = StockCollector(output_dir=self.raw_dir)
        self.macro_collector = MacroCollector(output_dir=self.raw_dir)
        self.sector_calc = SectorRegimeCalculator(data_dir=self.raw_dir, output_dir=self.processed_dir)
        self.macro_calc = MacroRegimeCalculator(output_dir=self.processed_dir)
        self.neo4j_loader = None  # Will initialize if needed

    def step1_collect_data(self, start: str = "2015-01-01", end: str = None):
        """Step 1: Collect all raw data"""
        logger.info("="*60)
        logger.info("STEP 1: DATA COLLECTION")
        logger.info("="*60)

        results = {}

        # ETFs
        logger.info("\n[1/3] Downloading ETFs...")
        etf_results = self.etf_collector.download_all(start, end)
        results['etf'] = etf_results

        # Stocks
        logger.info("\n[2/3] Downloading Stocks...")
        stock_results = self.stock_collector.download_all(start, end)
        results['stocks'] = stock_results

        # Macro
        logger.info("\n[3/3] Downloading Macro Indicators...")
        macro_results = self.macro_collector.download_all(start, end)
        results['macro'] = macro_results

        # Overall summary
        total_success = (
            etf_results['summary']['success_count'] +
            stock_results['summary']['combined']['success'] +
            macro_results['summary']['success_count']
        )

        total_tickers = (
            len(ALL_ETFS) +
            len(ALL_US_STOCKS) +
            len(ALL_KR_STOCKS) +
            len(self.macro_collector.MACRO_INDICATORS if hasattr(self.macro_collector, 'MACRO_INDICATORS') else [])
        )

        logger.info(f"\n{'='*60}")
        logger.info("STEP 1 COMPLETE")
        logger.info(f"Total Success: {total_success}/{total_tickers}")
        logger.info(f"{'='*60}\n")

        return results

    def step2_calculate_sector_regimes(self):
        """Step 2: Calculate sector regimes"""
        logger.info("="*60)
        logger.info("STEP 2: SECTOR REGIME CALCULATION")
        logger.info("="*60)

        results = self.sector_calc.calculate_all()

        logger.info(f"\n{'='*60}")
        logger.info("STEP 2 COMPLETE")
        logger.info(f"{'='*60}\n")

        return results

    def step3_calculate_macro_regimes(self, start: str, end: str = None):
        """Step 3: Calculate macro regimes"""
        logger.info("="*60)
        logger.info("STEP 3: MACRO REGIME CALCULATION")
        logger.info("="*60)

        output_path = self.macro_calc.calculate_and_save(start, end)

        logger.info(f"\n{'='*60}")
        logger.info("STEP 3 COMPLETE")
        logger.info(f"{'='*60}\n")

        return output_path

    def step4_match_dual_regimes(self, use_neo4j: bool = True):
        """Step 4: Match macro + sector regimes by date"""
        logger.info("="*60)
        logger.info("STEP 4: DUAL REGIME MATCHING")
        logger.info("="*60)

        # Load macro regimes
        macro_path = self.processed_dir / "macro_regimes.csv"
        if not macro_path.exists():
            logger.error(f"Macro regimes file not found: {macro_path}")
            return None

        macro_df = pd.read_csv(macro_path)
        logger.info(f"Loaded {len(macro_df)} macro regime snapshots")

        # Initialize Neo4j if requested
        if use_neo4j:
            self.neo4j_loader = DualRegimeNeo4jLoader()
            if not self.neo4j_loader.connect():
                logger.error("Cannot connect to Neo4j, skipping graph loading")
                use_neo4j = False
            else:
                self.neo4j_loader.create_schema()
                self.neo4j_loader.load_stocks()

        matched_count = 0
        skipped_count = 0

        # For each date, load sector regimes and create dual regimes
        for _, row in macro_df.iterrows():
            date = row['date']
            macro_state = row['dominant_state']
            confidence = row['confidence']

            # Load sector regimes for this date
            sector_regimes = {}
            for sector, data in SECTOR_TAXONOMY.items():
                etf = data["etf"]
                if etf is None:
                    continue  # Skip sectors without ETF

                regime_file = self.processed_dir / f"{etf}_regime.csv"
                if not regime_file.exists():
                    continue

                df = pd.read_csv(regime_file, parse_dates=['Date'])
                df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')

                df_date = df[df['Date'] == date]
                if not df_date.empty:
                    sector_regimes[sector] = df_date.iloc[0]['sector_regime']

            if not sector_regimes:
                skipped_count += 1
                continue

            # Load to Neo4j
            if use_neo4j:
                self.neo4j_loader.load_macro_state(date, macro_state, confidence)
                self.neo4j_loader.load_dual_regimes(date, macro_state, sector_regimes)

            matched_count += 1

            if matched_count % 100 == 0:
                logger.info(f"  Matched {matched_count} dates...")

        logger.info(f"\n{'='*60}")
        logger.info(f"STEP 4 COMPLETE")
        logger.info(f"  Matched: {matched_count} dates")
        logger.info(f"  Skipped: {skipped_count} dates (no sector data)")
        logger.info(f"{'='*60}\n")

        return matched_count

    def step5_calculate_outcomes(self, use_neo4j: bool = True):
        """Step 5: Calculate forward returns and load to Neo4j"""
        logger.info("="*60)
        logger.info("STEP 5: OUTCOME CALCULATION")
        logger.info("="*60)

        # Load macro regimes for date lookup
        macro_df = pd.read_csv(self.processed_dir / "macro_regimes.csv")
        macro_dict = dict(zip(macro_df['date'], macro_df['dominant_state']))

        all_tickers = ALL_ETFS + ALL_US_STOCKS + ALL_KR_STOCKS
        total_outcomes = 0
        processed_tickers = 0

        for ticker in all_tickers:
            try:
                # Load regime data
                regime_file = self.processed_dir / f"{ticker}_regime.csv"
                if not regime_file.exists():
                    logger.warning(f"Regime file not found for {ticker}")
                    continue

                df = pd.read_csv(regime_file, parse_dates=['Date'])

                # Calculate forward returns
                df = self._calculate_forward_returns(df)

                # Get sector for this ticker
                sector = TICKER_TO_SECTOR.get(ticker, "UNKNOWN")

                # Load outcomes to Neo4j
                if use_neo4j and self.neo4j_loader:
                    ticker_outcomes = 0

                    for _, row in df.iterrows():
                        # Only load if forward data exists
                        if pd.notna(row.get('return_3m')):
                            date = row['Date'].strftime('%Y-%m-%d')

                            # Get macro state for this date
                            macro_state = macro_dict.get(date)
                            if not macro_state:
                                continue

                            sector_phase = row['sector_regime']
                            regime_id = f"{macro_state}_{sector}_{sector_phase}_{date}"

                            returns = {
                                'return_1m': float(row.get('return_1m', 0)),
                                'return_3m': float(row.get('return_3m', 0)),
                                'return_6m': float(row.get('return_6m', 0)),
                                'max_dd_1m': float(row.get('max_dd_1m', 0)),
                                'max_dd_3m': float(row.get('max_dd_3m', 0)),
                                'max_dd_6m': float(row.get('max_dd_6m', 0)),
                                'sharpe_3m': float(row.get('sharpe_3m', 0)) if pd.notna(row.get('sharpe_3m')) else 0
                            }

                            self.neo4j_loader.load_outcome(ticker, date, regime_id, returns)
                            ticker_outcomes += 1

                    total_outcomes += ticker_outcomes
                    logger.info(f"✅ {ticker}: {ticker_outcomes} outcomes")

                processed_tickers += 1

            except Exception as e:
                logger.error(f"❌ {ticker}: {e}")

        logger.info(f"\n{'='*60}")
        logger.info(f"STEP 5 COMPLETE")
        logger.info(f"  Processed tickers: {processed_tickers}/{len(all_tickers)}")
        logger.info(f"  Total outcomes: {total_outcomes:,}")
        logger.info(f"{'='*60}\n")

        return total_outcomes

    def _calculate_forward_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate forward-looking returns"""
        df = df.copy()

        # Forward returns (shift -N to look ahead)
        df['return_1m'] = df['Close'].pct_change(21).shift(-21)   # 1 month ahead
        df['return_3m'] = df['Close'].pct_change(63).shift(-63)   # 3 months ahead
        df['return_6m'] = df['Close'].pct_change(126).shift(-126) # 6 months ahead

        # Max drawdown during forward period
        def rolling_max_dd(series, window):
            future_series = series.shift(-window)
            roll_max = series.rolling(window).max().shift(-window)
            return np.where(roll_max > 0, (future_series - roll_max) / roll_max, 0)

        df['max_dd_1m'] = rolling_max_dd(df['Close'], 21)
        df['max_dd_3m'] = rolling_max_dd(df['Close'], 63)
        df['max_dd_6m'] = rolling_max_dd(df['Close'], 126)

        # Sharpe ratio (return / volatility) for 3m period
        vol_3m = df['Close'].pct_change().rolling(63).std().shift(-63) * np.sqrt(252)
        df['sharpe_3m'] = np.where(vol_3m > 0, df['return_3m'] / vol_3m, 0)

        return df

    def run_full_pipeline(self, start: str = "2015-01-01", end: str = None, use_neo4j: bool = True):
        """Run complete 5-step pipeline"""
        if end is None:
            end = datetime.now().strftime("%Y-%m-%d")

        logger.info("\n" + "="*60)
        logger.info("DUAL REGIME SYSTEM - FULL PIPELINE")
        logger.info(f"Period: {start} to {end}")
        logger.info(f"Neo4j: {'ENABLED' if use_neo4j else 'DISABLED'}")
        logger.info("="*60 + "\n")

        start_time = datetime.now()

        # Step 1: Collect Data
        self.step1_collect_data(start, end)

        # Step 2: Calculate Sector Regimes
        self.step2_calculate_sector_regimes()

        # Step 3: Calculate Macro Regimes
        self.step3_calculate_macro_regimes(start, end)

        # Step 4: Match Dual Regimes
        self.step4_match_dual_regimes(use_neo4j)

        # Step 5: Calculate Outcomes
        self.step5_calculate_outcomes(use_neo4j)

        # Cleanup
        if self.neo4j_loader:
            self.neo4j_loader.print_stats()
            self.neo4j_loader.close()

        elapsed = datetime.now() - start_time

        logger.info("\n" + "="*60)
        logger.info("PIPELINE COMPLETE")
        logger.info(f"Total time: {elapsed}")
        logger.info("="*60 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run Dual Regime Data Pipeline')
    parser.add_argument('--start', type=str, default='2015-01-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default=None, help='End date (YYYY-MM-DD), defaults to today')
    parser.add_argument('--no-neo4j', action='store_true', help='Skip Neo4j loading')
    parser.add_argument('--step', type=int, choices=[1,2,3,4,5], help='Run specific step only')

    args = parser.parse_args()

    pipeline = DualRegimePipeline()

    if args.step:
        logger.info(f"Running step {args.step} only...")
        if args.step == 1:
            pipeline.step1_collect_data(args.start, args.end)
        elif args.step == 2:
            pipeline.step2_calculate_sector_regimes()
        elif args.step == 3:
            pipeline.step3_calculate_macro_regimes(args.start, args.end)
        elif args.step == 4:
            pipeline.step4_match_dual_regimes(not args.no_neo4j)
        elif args.step == 5:
            pipeline.step5_calculate_outcomes(not args.no_neo4j)
    else:
        pipeline.run_full_pipeline(args.start, args.end, not args.no_neo4j)
