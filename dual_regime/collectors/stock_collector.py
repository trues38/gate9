#!/usr/bin/env python3
"""
Stock Data Collector
====================
Downloads historical stock price data for US and Korean stocks using yfinance.
Handles different validation rules for KR stocks (.KS suffix).
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
from config.sector_mapping import ALL_US_STOCKS, ALL_KR_STOCKS

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# File lock for thread-safe CSV writes
file_lock = threading.Lock()


class StockCollector:
    """Collects historical stock price data from Yahoo Finance"""

    def __init__(self, output_dir: str = None):
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "data" / "raw"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_stock(self, ticker: str, start: str, end: str = None, is_kr: bool = False) -> dict:
        """
        Download single stock data

        Args:
            ticker: Stock ticker symbol
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD), defaults to today
            is_kr: Whether this is a Korean stock (for validation)

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

            # Data quality validation
            warnings = []

            # Check minimum row count (expect ~4 years = 1000 trading days)
            if len(df) < 1000:
                warnings.append(f"Insufficient data: {len(df)} rows (expected >1000)")

            # Check for large gaps in dates
            df['Date_dt'] = pd.to_datetime(df['Date'])
            df['gap'] = df['Date_dt'].diff().dt.days
            max_gap = df['gap'].max()
            if max_gap > 30:
                warnings.append(f"Large data gap: {max_gap} days")

            # Thread-safe file write
            with file_lock:
                output_path = self.output_dir / f"{ticker}.csv"
                df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].to_csv(output_path, index=False)

            result = {
                "status": "success",
                "ticker": ticker,
                "message": f"Downloaded {len(df)} rows",
                "rows": len(df),
                "warnings": warnings
            }

            if warnings:
                logger.warning(f"⚠️  {ticker}: {', '.join(warnings)}")

            return result

        except Exception as e:
            logger.error(f"Error downloading {ticker}: {e}")
            return {
                "status": "failed",
                "ticker": ticker,
                "message": str(e),
                "rows": 0,
                "warnings": []
            }

    def download_us_stocks(self, start: str = "2015-01-01", end: str = None, max_workers: int = 1) -> dict:
        """Download all US stocks in parallel"""
        results = {"success": [], "failed": []}

        logger.info(f"Starting US stock collection: {len(ALL_US_STOCKS)} tickers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {
                executor.submit(self.download_stock, ticker, start, end, is_kr=False): ticker
                for ticker in ALL_US_STOCKS
            }

            for future in as_completed(future_to_ticker):
                result = future.result()
                if result["status"] == "success":
                    results["success"].append(result)
                    logger.info(f"✅ {result['ticker']}: {result['rows']} rows")
                else:
                    results["failed"].append(result)
                    logger.warning(f"❌ {result['ticker']}: {result['message']}")

        return results

    def download_kr_stocks(self, start: str = "2015-01-01", end: str = None, max_workers: int = 1) -> dict:
        """Download all Korean stocks in parallel with .KS validation"""
        results = {"success": [], "failed": []}

        # Validate .KS suffix
        invalid_tickers = [t for t in ALL_KR_STOCKS if not t.endswith(".KS")]
        if invalid_tickers:
            logger.error(f"Invalid Korean tickers (missing .KS): {invalid_tickers}")
            return {"success": [], "failed": [{"ticker": t, "message": "Invalid .KS suffix"} for t in invalid_tickers]}

        logger.info(f"Starting Korean stock collection: {len(ALL_KR_STOCKS)} tickers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {
                executor.submit(self.download_stock, ticker, start, end, is_kr=True): ticker
                for ticker in ALL_KR_STOCKS
            }

            for future in as_completed(future_to_ticker):
                result = future.result()
                if result["status"] == "success":
                    results["success"].append(result)
                    logger.info(f"✅ {result['ticker']}: {result['rows']} rows")
                else:
                    results["failed"].append(result)
                    logger.warning(f"❌ {result['ticker']}: {result['message']}")

        return results

    def download_all(self, start: str = "2015-01-01", end: str = None, max_workers: int = 1) -> dict:
        """
        Download both US and Korean stocks

        Returns:
            dict with 'us', 'kr', 'summary' keys
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"STOCK COLLECTION STARTED")
        logger.info(f"Date range: {start} to {end or 'today'}")
        logger.info(f"{'='*60}\n")

        # Download US stocks
        logger.info("=" * 40)
        logger.info("US STOCKS")
        logger.info("=" * 40)
        us_results = self.download_us_stocks(start, end, max_workers)

        # Download KR stocks
        logger.info("\n" + "=" * 40)
        logger.info("KOREAN STOCKS")
        logger.info("=" * 40)
        kr_results = self.download_kr_stocks(start, end, max_workers)

        # Combined summary
        total_success = len(us_results["success"]) + len(kr_results["success"])
        total_failed = len(us_results["failed"]) + len(kr_results["failed"])
        total_tickers = len(ALL_US_STOCKS) + len(ALL_KR_STOCKS)

        summary = {
            "us": {
                "success": len(us_results["success"]),
                "failed": len(us_results["failed"]),
                "total": len(ALL_US_STOCKS)
            },
            "kr": {
                "success": len(kr_results["success"]),
                "failed": len(kr_results["failed"]),
                "total": len(ALL_KR_STOCKS)
            },
            "combined": {
                "success": total_success,
                "failed": total_failed,
                "total": total_tickers,
                "success_rate": total_success / total_tickers * 100 if total_tickers else 0
            }
        }

        logger.info(f"\n{'='*60}")
        logger.info(f"STOCK COLLECTION SUMMARY:")
        logger.info(f"  US Stocks: {summary['us']['success']}/{summary['us']['total']}")
        logger.info(f"  KR Stocks: {summary['kr']['success']}/{summary['kr']['total']}")
        logger.info(f"  Total: {summary['combined']['success']}/{summary['combined']['total']} ({summary['combined']['success_rate']:.1f}%)")
        logger.info(f"{'='*60}\n")

        return {
            "us": us_results,
            "kr": kr_results,
            "summary": summary
        }


if __name__ == "__main__":
    collector = StockCollector()
    results = collector.download_all(start="2015-01-01")

    # Print failures if any
    if results["us"]["failed"]:
        print("\nFailed US downloads:")
        for fail in results["us"]["failed"]:
            print(f"  - {fail['ticker']}: {fail['message']}")

    if results["kr"]["failed"]:
        print("\nFailed KR downloads:")
        for fail in results["kr"]["failed"]:
            print(f"  - {fail['ticker']}: {fail['message']}")
