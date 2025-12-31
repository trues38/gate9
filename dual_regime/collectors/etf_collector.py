#!/usr/bin/env python3
"""
ETF Data Collector
==================
Downloads historical price data for sector and market ETFs using yfinance.
Uses parallel downloads with ThreadPoolExecutor for efficiency.
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

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.sector_mapping import ALL_ETFS

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# File lock for thread-safe CSV writes
file_lock = threading.Lock()


class ETFCollector:
    """Collects historical ETF price data from Yahoo Finance"""

    def __init__(self, output_dir: str = None):
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "data" / "raw"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_etf(self, ticker: str, start: str, end: str = None) -> dict:
        """
        Download single ETF data

        Args:
            ticker: ETF ticker symbol
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD), defaults to today

        Returns:
            dict with 'status', 'ticker', 'message', 'rows'
        """
        if end is None:
            end = datetime.now().strftime("%Y-%m-%d")

        try:
            logger.info(f"Downloading {ticker}...")
            df = yf.download(ticker, start=start, end=end, progress=False)

            if df.empty:
                return {"status": "failed", "ticker": ticker, "message": "No data returned", "rows": 0}

            # Flatten MultiIndex columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Reset index to make Date a column
            df = df.reset_index()

            # Standardize Date format
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')

            # Ensure Close is numeric
            df['Close'] = pd.to_numeric(df['Close'], errors='coerce')

            # Thread-safe file write
            with file_lock:
                output_path = self.output_dir / f"{ticker}.csv"
                df.to_csv(output_path, index=False)

            return {
                "status": "success",
                "ticker": ticker,
                "message": f"Downloaded {len(df)} rows",
                "rows": len(df)
            }

        except Exception as e:
            logger.error(f"Error downloading {ticker}: {e}")
            return {
                "status": "failed",
                "ticker": ticker,
                "message": str(e),
                "rows": 0
            }

    def download_all(self, start: str = "2015-01-01", end: str = None, max_workers: int = 1) -> dict:
        """
        Download all ETFs in parallel

        Args:
            start: Start date
            end: End date
            max_workers: Number of parallel download threads

        Returns:
            dict with 'success', 'failed', 'summary' keys
        """
        results = {"success": [], "failed": []}

        logger.info(f"Starting ETF collection: {len(ALL_ETFS)} tickers")
        logger.info(f"Date range: {start} to {end or 'today'}")
        logger.info(f"Parallel workers: {max_workers}")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_ticker = {
                executor.submit(self.download_etf, etf, start, end): etf
                for etf in ALL_ETFS
            }

            # Collect results as they complete
            for future in as_completed(future_to_ticker):
                result = future.result()
                if result["status"] == "success":
                    results["success"].append(result)
                    logger.info(f"✅ {result['ticker']}: {result['rows']} rows")
                else:
                    results["failed"].append(result)
                    logger.warning(f"❌ {result['ticker']}: {result['message']}")

        # Summary
        results["summary"] = {
            "total": len(ALL_ETFS),
            "success_count": len(results["success"]),
            "failed_count": len(results["failed"]),
            "success_rate": len(results["success"]) / len(ALL_ETFS) * 100 if ALL_ETFS else 0,
            "total_rows": sum(r["rows"] for r in results["success"])
        }

        logger.info(f"\n{'='*60}")
        logger.info(f"ETF Collection Summary:")
        logger.info(f"  Success: {results['summary']['success_count']}/{results['summary']['total']} ({results['summary']['success_rate']:.1f}%)")
        logger.info(f"  Failed: {results['summary']['failed_count']}")
        logger.info(f"  Total rows downloaded: {results['summary']['total_rows']:,}")
        logger.info(f"{'='*60}\n")

        return results


if __name__ == "__main__":
    collector = ETFCollector()
    results = collector.download_all(start="2015-01-01")

    # Print failures if any
    if results["failed"]:
        print("\nFailed downloads:")
        for fail in results["failed"]:
            print(f"  - {fail['ticker']}: {fail['message']}")
