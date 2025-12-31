#!/usr/bin/env python3
"""
Sector Regime Calculator
=========================
Calculates 5-phase sector regimes based on:
- Momentum (20d, 60d)
- Volatility (rolling std)
- Relative strength vs SPY benchmark

Phases: BOTTOM, RECOVERY, PEAK, DECLINE, NEUTRAL
"""

import os
import sys
from pathlib import Path
import logging

import pandas as pd
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.sector_mapping import ALL_ETFS, ALL_US_STOCKS, ALL_KR_STOCKS, TICKER_TO_SECTOR

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SectorRegimeCalculator:
    """Calculates sector regimes from price data"""

    # Class-level cache for SPY benchmark (shared across all instances)
    _spy_cache = None

    def __init__(self, data_dir: str = None, output_dir: str = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "raw"
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "data" / "processed"

        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.spy_data = None

    def load_spy_benchmark(self):
        """Load SPY data for relative strength calculation (cached)"""
        if SectorRegimeCalculator._spy_cache is None:
            spy_path = self.data_dir / "SPX.csv"  # Using S&P 500 as benchmark

            if not spy_path.exists():
                logger.warning(f"SPY benchmark not found at {spy_path}, attempting to download...")
                # Try to download SPY if missing
                try:
                    import yfinance as yf
                    from datetime import datetime
                    df = yf.download("^GSPC", start="2015-01-01", end=datetime.now().strftime("%Y-%m-%d"), progress=False)
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    df = df.reset_index()
                    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
                    df.to_csv(spy_path, index=False)
                    logger.info(f"✅ Downloaded SPY benchmark to {spy_path}")
                except Exception as e:
                    logger.error(f"Failed to download SPY benchmark: {e}")
                    raise

            SectorRegimeCalculator._spy_cache = pd.read_csv(spy_path, parse_dates=['Date'])

        self.spy_data = SectorRegimeCalculator._spy_cache.copy()
        self.spy_data.set_index('Date', inplace=True)
        logger.info(f"Loaded SPY benchmark: {len(self.spy_data)} rows")

    def calculate_regime(self, ticker: str) -> pd.DataFrame:
        """
        Calculate sector regime for a single ticker

        Args:
            ticker: Stock/ETF ticker symbol

        Returns:
            DataFrame with columns: Date, Close, sector_regime, momentum_20d, momentum_60d,
                                   volatility, vol_ma60, rel_strength, rel_mom_20d
        """
        # Load ticker data
        ticker_path = self.data_dir / f"{ticker}.csv"
        if not ticker_path.exists():
            logger.error(f"Data file not found for {ticker}: {ticker_path}")
            return None

        df = pd.read_csv(ticker_path, parse_dates=['Date'])
        df.set_index('Date', inplace=True)

        # Calculate returns
        df['returns'] = df['Close'].pct_change()

        # Calculate momentum indicators
        df['momentum_20d'] = df['Close'].pct_change(20)  # 20-day momentum
        df['momentum_60d'] = df['Close'].pct_change(60)  # 60-day momentum

        # Calculate volatility (annualized)
        df['volatility'] = df['returns'].rolling(20).std() * np.sqrt(252)
        df['vol_ma60'] = df['volatility'].rolling(60).mean()

        # Relative strength vs SPY
        if self.spy_data is not None:
            # Merge with SPY data
            merged = df.join(self.spy_data[['Close']], how='left', rsuffix='_spy')

            # Forward-fill SPY for dates when SPY didn't trade (e.g., KR holidays)
            merged['Close_spy'] = merged['Close_spy'].ffill()

            df['spy_close'] = merged['Close_spy']
            df['rel_strength'] = df['Close'] / df['spy_close']
            df['rel_mom_20d'] = df['rel_strength'].pct_change(20)
        else:
            logger.warning(f"SPY benchmark not loaded, skipping relative strength for {ticker}")
            df['rel_strength'] = np.nan
            df['rel_mom_20d'] = np.nan

        # Classify regime
        df['sector_regime'] = self._classify_regime(df)

        # Reset index to make Date a column
        df = df.reset_index()

        return df

    def _classify_regime(self, df: pd.DataFrame) -> pd.Series:
        """
        Classify regime based on technical indicators

        Regime Logic:
        - BOTTOM: Deep drawdown, declining volatility, negative momentum
        - RECOVERY: Momentum turning positive, outperforming SPY
        - PEAK: Strong momentum, rising volatility
        - DECLINE: Momentum turning negative
        - NEUTRAL: Everything else
        """
        regime = pd.Series('NEUTRAL', index=df.index)

        # DECLINE: Momentum turning negative (early warning)
        # mom_20d < 0 AND mom_60d > 0 (short-term down, long-term still up)
        decline_mask = (df['momentum_20d'] < 0) & (df['momentum_60d'] > 0)
        regime[decline_mask] = 'DECLINE'

        # BOTTOM: Deep negative momentum, declining volatility
        # mom_60d < -5%, volatility below 60-day average, underperforming SPY
        bottom_mask = (
            (df['momentum_60d'] < -0.05) &
            (df['volatility'] < df['vol_ma60']) &
            (df['rel_mom_20d'] < -0.02)
        )
        regime[bottom_mask] = 'BOTTOM'

        # RECOVERY: Momentum turning positive, outperforming SPY
        # mom_20d > 0 AND mom_60d < 0 (short-term up, long-term still down = turning point)
        # rel_mom_20d > 0 (outperforming market)
        recovery_mask = (
            (df['momentum_20d'] > 0) &
            (df['momentum_60d'] < 0) &
            (df['rel_mom_20d'] > 0)
        )
        regime[recovery_mask] = 'RECOVERY'

        # PEAK: Strong momentum but rising volatility (late stage)
        # mom_60d > 10%, volatility rising above average
        peak_mask = (
            (df['momentum_60d'] > 0.10) &
            (df['volatility'] > df['vol_ma60'])
        )
        regime[peak_mask] = 'PEAK'

        return regime

    def calculate_all(self) -> dict:
        """
        Calculate regimes for all tickers and save to processed directory

        Returns:
            dict with 'success', 'failed', 'summary' keys
        """
        # Load SPY benchmark first
        self.load_spy_benchmark()

        results = {"success": [], "failed": []}

        all_tickers = ALL_ETFS + ALL_US_STOCKS + ALL_KR_STOCKS
        logger.info(f"Calculating sector regimes for {len(all_tickers)} tickers...")

        for ticker in all_tickers:
            try:
                df = self.calculate_regime(ticker)

                if df is None:
                    results["failed"].append({"ticker": ticker, "message": "Data file not found"})
                    continue

                # Save to processed directory
                output_path = self.output_dir / f"{ticker}_regime.csv"
                df.to_csv(output_path, index=False)

                results["success"].append({
                    "ticker": ticker,
                    "rows": len(df),
                    "sector": TICKER_TO_SECTOR.get(ticker, "UNKNOWN")
                })

                logger.info(f"✅ {ticker}: {len(df)} rows")

            except Exception as e:
                logger.error(f"❌ {ticker}: {e}")
                results["failed"].append({"ticker": ticker, "message": str(e)})

        # Summary
        results["summary"] = {
            "total": len(all_tickers),
            "success_count": len(results["success"]),
            "failed_count": len(results["failed"]),
            "success_rate": len(results["success"]) / len(all_tickers) * 100 if all_tickers else 0
        }

        logger.info(f"\n{'='*60}")
        logger.info(f"SECTOR REGIME CALCULATION SUMMARY:")
        logger.info(f"  Success: {results['summary']['success_count']}/{results['summary']['total']} ({results['summary']['success_rate']:.1f}%)")
        logger.info(f"  Failed: {results['summary']['failed_count']}")
        logger.info(f"{'='*60}\n")

        return results


if __name__ == "__main__":
    calculator = SectorRegimeCalculator()
    results = calculator.calculate_all()

    # Print failures if any
    if results["failed"]:
        print("\nFailed calculations:")
        for fail in results["failed"]:
            print(f"  - {fail['ticker']}: {fail['message']}")
