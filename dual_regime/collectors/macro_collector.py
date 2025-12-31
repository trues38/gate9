#!/usr/bin/env python3
"""
Macro Indicator Collector
==========================
Downloads historical data for macro economic indicators using yfinance.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import logging

import yfinance as yf
import pandas as pd

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# File lock for thread-safe CSV writes
file_lock = threading.Lock()

# Macro indicators mapping
MACRO_INDICATORS = {
    "VIX": "^VIX",              # Volatility Index
    "DXY": "DX-Y.NYB",          # Dollar Index
    "TNX": "^TNX",              # 10-Year Treasury Yield
    "TYX": "^TYX",              # 30-Year Treasury Yield
    "FVX": "^FVX",              # 5-Year Treasury Yield
    "IRX": "^IRX",              # 3-Month Treasury Bill
    "HYG": "HYG",               # High Yield Corporate Bond ETF
    "LQD": "LQD",               # Investment Grade Corporate Bond ETF
    "TLT": "TLT",               # 20+ Year Treasury Bond ETF
    "GOLD": "GC=F",             # Gold Futures
    "SILVER": "SI=F",           # Silver Futures
    "OIL": "CL=F",              # Crude Oil Futures
    "SPX": "^GSPC"              # S&P 500 Index
}


class MacroCollector:
    """Collects historical macro indicator data from Yahoo Finance"""

    def __init__(self, output_dir: str = None):
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "data" / "raw"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_indicator(self, name: str, ticker: str, start: str, end: str = None) -> dict:
        """
        Download single macro indicator

        Args:
            name: Indicator name (for file naming)
            ticker: Yahoo Finance ticker symbol
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD), defaults to today

        Returns:
            dict with 'status', 'name', 'ticker', 'message', 'rows'
        """
        if end is None:
            end = datetime.now().strftime("%Y-%m-%d")

        try:
            logger.info(f"Downloading {name} ({ticker})...")
            df = yf.download(ticker, start=start, end=end, progress=False)

            if df.empty:
                return {"status": "failed", "name": name, "ticker": ticker, "message": "No data returned", "rows": 0}

            # Flatten MultiIndex columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Reset index to make Date a column
            df = df.reset_index()

            # Standardize Date format
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')

            # Ensure Close is numeric
            df['Close'] = pd.to_numeric(df['Close'], errors='coerce')

            # Thread-safe file write (save using name, not ticker for clarity)
            with file_lock:
                output_path = self.output_dir / f"{name}.csv"
                df.to_csv(output_path, index=False)

            return {
                "status": "success",
                "name": name,
                "ticker": ticker,
                "message": f"Downloaded {len(df)} rows",
                "rows": len(df)
            }

        except Exception as e:
            logger.error(f"Error downloading {name} ({ticker}): {e}")
            return {
                "status": "failed",
                "name": name,
                "ticker": ticker,
                "message": str(e),
                "rows": 0
            }

    def download_all(self, start: str = "2015-01-01", end: str = None, max_workers: int = 10) -> dict:
        """
        Download all macro indicators in parallel

        Args:
            start: Start date
            end: End date
            max_workers: Number of parallel download threads

        Returns:
            dict with 'success', 'failed', 'summary' keys
        """
        results = {"success": [], "failed": []}

        logger.info(f"Starting macro indicator collection: {len(MACRO_INDICATORS)} indicators")
        logger.info(f"Date range: {start} to {end or 'today'}")
        logger.info(f"Parallel workers: {max_workers}")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_indicator = {
                executor.submit(self.download_indicator, name, ticker, start, end): name
                for name, ticker in MACRO_INDICATORS.items()
            }

            # Collect results as they complete
            for future in as_completed(future_to_indicator):
                result = future.result()
                if result["status"] == "success":
                    results["success"].append(result)
                    logger.info(f"✅ {result['name']}: {result['rows']} rows")
                else:
                    results["failed"].append(result)
                    logger.warning(f"❌ {result['name']}: {result['message']}")

        # Summary
        results["summary"] = {
            "total": len(MACRO_INDICATORS),
            "success_count": len(results["success"]),
            "failed_count": len(results["failed"]),
            "success_rate": len(results["success"]) / len(MACRO_INDICATORS) * 100 if MACRO_INDICATORS else 0,
            "total_rows": sum(r["rows"] for r in results["success"])
        }

        logger.info(f"\n{'='*60}")
        logger.info(f"MACRO INDICATOR COLLECTION SUMMARY:")
        logger.info(f"  Success: {results['summary']['success_count']}/{results['summary']['total']} ({results['summary']['success_rate']:.1f}%)")
        logger.info(f"  Failed: {results['summary']['failed_count']}")
        logger.info(f"  Total rows downloaded: {results['summary']['total_rows']:,}")
        logger.info(f"{'='*60}\n")

        return results


if __name__ == "__main__":
    collector = MacroCollector()
    results = collector.download_all(start="2015-01-01")

    # Print failures if any
    if results["failed"]:
        print("\nFailed downloads:")
        for fail in results["failed"]:
            print(f"  - {fail['name']} ({fail['ticker']}): {fail['message']}")
