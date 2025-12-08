import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from supabase import create_client, Client

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load Environment Variables
from pathlib import Path
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
FRED_API_KEY = os.getenv("FRED_API_KEY")
KOSIS_API_KEY = os.getenv("KOSIS_API_KEY")

if not SUPABASE_URL:
    logger.error(f"SUPABASE_URL not found in {env_path}")
else:
    SUPABASE_URL = SUPABASE_URL.strip()
    if not SUPABASE_URL.startswith("https://"):
        logger.error(f"Invalid SUPABASE_URL format: {SUPABASE_URL}")
    else:
        logger.info(f"Loaded SUPABASE_URL from {env_path}")

# Indicator Definitions
INDICATORS = {
    "US": ["CPI", "PCE", "RetailSales", "FOMC"],
    "CN": ["PMI", "Exports", "Retail", "Policy"],
    "JP": ["JPYUSD", "BOJ"],
    "KR": ["Exports", "Retail"]
}

# FRED Series Mapping
FRED_MAP = {
    "CPI": "CPIAUCSL", # Consumer Price Index for All Urban Consumers: All Items
    "PCE": "PCE",      # Personal Consumption Expenditures
    "RetailSales": "RSXFS", # Advance Retail Sales: Retail Trade and Food Services
    "FOMC": "FEDFUNDS" # Effective Federal Funds Rate (Proxy for Policy)
}

# KOSIS Mapping (Tentative)
# Exports: Customs Export/Import (Korea Customs Service) - 101? 301? 
# Retail: Retail Sales Index (Statistics Korea) - 101 / DT_1K31013
KOSIS_MAP = {
    "Exports": {"orgId": "101", "tblId": "DT_1R11005", "objL1": "ALL"}, # Tentative
    "Retail":  {"orgId": "101", "tblId": "DT_1K31013", "objL1": "ALL"}  # Tentative
}

class IndicatorCollector:
    def __init__(self, supabase_url: str, supabase_key: str):
        if not supabase_url or not supabase_key:
            logger.warning("Supabase credentials not found. DB operations will be skipped (Dry Run).")
            self.supabase: Optional[Client] = None
        else:
            try:
                self.supabase = create_client(supabase_url, supabase_key)
                logger.info("Supabase client initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.supabase = None

    def fetch_yahoo(self, ticker: str, target_date: date) -> Optional[float]:
        try:
            import yfinance as yf
            # Fetch a bit more history to ensure we get the date (timezones etc)
            # Convert date to datetime for yfinance if needed, but it accepts strings or dates.
            # We add timedelta to end_date because yfinance end is exclusive.
            start_date = target_date
            end_date = target_date + timedelta(days=1)
            
            # yfinance download
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if not df.empty:
                # Get Close price
                val = df['Close'].iloc[0]
                # Handle Series or scalar
                if hasattr(val, 'item'):
                    return round(float(val.item()), 4)
                return round(float(val), 4)
            return None
        except Exception as e:
            logger.warning(f"Yahoo fetch failed for {ticker}: {e}")
            return None

    def fetch_fred(self, series_id: str, target_date: date) -> Optional[float]:
        if not FRED_API_KEY:
            logger.warning("FRED_API_KEY not found. Skipping FRED fetch.")
            return None
        try:
            import pandas_datareader.data as web
            # FRED often has lag, so exact date might be NaN. 
            # For monthly data (CPI), it's usually released mid-month for prev month.
            # We try to fetch a range around the date.
            start = target_date - timedelta(days=30)
            end = target_date
            
            df = web.DataReader(series_id, 'fred', start, end, api_key=FRED_API_KEY)
            if not df.empty:
                # Return the latest available value in the range
                val = df.iloc[-1, 0]
                return round(float(val), 2)
            return None
        except Exception as e:
            logger.warning(f"FRED fetch failed for {series_id}: {e}")
            return None

    def fetch_kosis(self, org_id: str, tbl_id: str, target_date: date) -> Optional[float]:
        if not KOSIS_API_KEY:
            logger.warning("KOSIS_API_KEY not found. Skipping KOSIS fetch.")
            return None
        
        # KOSIS API expects YYYYMM for monthly data
        # If target_date is 2023-11-25, we want 202311
        prd_de = target_date.strftime("%Y%m")
        
        url = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
        params = {
            "method": "getList",
            "apiKey": KOSIS_API_KEY,
            "itmId": "T1", # Total usually
            "objL1": "ALL",
            "format": "json",
            "jsonVD": "Y",
            "prdSe": "M",
            "startPrdDe": prd_de,
            "endPrdDe": prd_de,
            "orgId": org_id,
            "tblId": tbl_id
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, dict) and 'err' in data:
                logger.warning(f"KOSIS API Error: {data.get('errMsg')} (Code: {data.get('err')})")
                return None
                
            if isinstance(data, list) and len(data) > 0:
                # Assuming the first item is the total/main value
                # Value is usually in "DT" field
                val_str = data[0].get("DT")
                if val_str:
                    return float(val_str)
            return None
        except Exception as e:
            logger.warning(f"KOSIS fetch failed for {tbl_id}: {e}")
            return None

    def fetch_indicator(self, country: str, indicator: str, target_date: date) -> Optional[Dict[str, Any]]:
        """
        Fetches data for a specific indicator.
        """
        logger.info(f"Fetching {country} - {indicator} for {target_date}")
        
        value = None
        source = "Mock"
        
        # Real Data Logic
        if country == "JP" and indicator == "JPYUSD":
            # Yahoo Finance: JPY=X
            val = self.fetch_yahoo("JPY=X", target_date)
            if val:
                value = val
                source = "YahooFinance"
        
        elif country == "US" and indicator in FRED_MAP:
            # FRED
            val = self.fetch_fred(FRED_MAP[indicator], target_date)
            if val:
                value = val
                source = "FRED"

        elif country == "KR" and indicator in KOSIS_MAP:
            # KOSIS
            cfg = KOSIS_MAP[indicator]
            val = self.fetch_kosis(cfg["orgId"], cfg["tblId"], target_date)
            if val:
                value = val
                source = "KOSIS"

        # Fallback to Mock if Real Data failed or not implemented
        if value is None:
            import random
            mock_value = round(random.uniform(100, 200), 2)
            return {
                "country": country,
                "indicator": indicator,
                "value": mock_value,
                "date": target_date.isoformat(),
                "source": "Mock_Fallback",
                "raw": {}
            }
            logger.error(f"Error fetching {country}:{indicator}: {e}")
            return None

    def save_to_db(self, data: Dict[str, Any], dry_run: bool = False):
        """
        Saves the fetched data to Supabase.
        """
        if dry_run:
            logger.info(f"[DRY RUN] Would save: {json.dumps(data, indent=2)}")
            return

        if not self.supabase:
            logger.warning(f"Skipping save for {data['country']}:{data['indicator']} due to missing DB connection.")
            return

        try:
            # Use upsert with explicit conflict resolution
            response = self.supabase.table("econ_indicators").upsert(
                data, 
                on_conflict="country, indicator, date"
            ).execute()
            logger.info(f"Successfully saved {data['country']}:{data['indicator']}")
        except Exception as e:
            logger.error(f"DB Save Error for {data['country']}:{data['indicator']} - {e}")

    def process_indicator(self, country: str, indicator: str, target_date: date, dry_run: bool):
        """
        Helper method to fetch and save a single indicator.
        """
        result = self.fetch_indicator(country, indicator, target_date)
        if result:
            self.save_to_db(result, dry_run=dry_run)
        else:
            logger.warning(f"Skipping save for {country}:{indicator} due to fetch failure.")

    def run(self, target_date: date, dry_run: bool = False):
        logger.info(f"Starting collection for date: {target_date} (Dry Run: {dry_run})")
        
        tasks = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            for country, indicators in INDICATORS.items():
                for indicator in indicators:
                    tasks.append(
                        executor.submit(self.process_indicator, country, indicator, target_date, dry_run)
                    )
            
            # Wait for all tasks to complete
            for future in as_completed(tasks):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Task failed: {e}")

        logger.info(f"Collection completed.")

def main():
    parser = argparse.ArgumentParser(description="Collect Economic Indicators")
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD)", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--dry-run", action="store_true", help="Run without saving to DB")
    
    args = parser.parse_args()
    
    try:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    except ValueError:
        logger.error("Invalid date format. Use YYYY-MM-DD")
        exit(1)

    collector = IndicatorCollector(SUPABASE_URL, SUPABASE_KEY)
    collector.run(target_date, dry_run=args.dry_run)

if __name__ == "__main__":
    main()

# ------------------------------------------------------------------------------
# Cron Example:
# To run this script daily at 6:00 AM:
# 0 6 * * * /usr/bin/python3 /path/to/collect_indicators.py >> /var/log/econ_cron.log 2>&1
# ------------------------------------------------------------------------------
