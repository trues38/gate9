import os
import sys
import logging
import argparse
import pandas as pd
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import List, Dict, Any
import requests

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load Env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
FRED_API_KEY = os.getenv("FRED_API_KEY")
KOSIS_API_KEY = os.getenv("KOSIS_API_KEY")

# FRED Series Mapping
FRED_MAP = {
    "CPI": "CPIAUCSL", 
    "PCE": "PCE",      
    "RetailSales": "RSXFS", 
    "FOMC": "FEDFUNDS" 
}

# KOSIS Mapping
KOSIS_MAP = {
    "Exports": {"orgId": "101", "tblId": "DT_1R11005", "objL1": "ALL"}, 
    "Retail":  {"orgId": "101", "tblId": "DT_1K31013", "objL1": "ALL"}  
}

def save_batch(supabase, batch, dry_run=False):
    if not batch:
        return
    
    logger.info(f"Upserting {len(batch)} records...")
    if dry_run:
        logger.info(f"[DRY RUN] Would upsert {len(batch)} records. Sample: {batch[0]}")
        return

    try:
        # Upsert in chunks of 1000 to avoid payload limits
        chunk_size = 1000
        for i in range(0, len(batch), chunk_size):
            chunk = batch[i:i + chunk_size]
            supabase.table("econ_indicators").upsert(
                chunk, on_conflict="country, indicator, date"
            ).execute()
            logger.info(f"  Upserted batch {i} to {i + len(chunk)}")
    except Exception as e:
        logger.error(f"Failed to upsert batch: {e}")

def backfill_kosis(supabase, indicator, config, start_year=2000, dry_run=False):
    if not KOSIS_API_KEY:
        logger.warning("KOSIS_API_KEY not found. Skipping KOSIS backfill.")
        return

    logger.info(f"Backfilling KR:{indicator} from KOSIS ({config['tblId']}) since {start_year}")
    
    current_year = datetime.now().year
    batch = []
    
    for yr in range(start_year, current_year + 1, 5):
        start_ym = f"{yr}01"
        end_ym = f"{min(yr+4, current_year)}12"
        
        url = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
        params = {
            "method": "getList",
            "apiKey": KOSIS_API_KEY,
            "itmId": "T1",
            "objL1": config["objL1"],
            "format": "json",
            "jsonVD": "Y",
            "prdSe": "M",
            "startPrdDe": start_ym,
            "endPrdDe": end_ym,
            "orgId": config["orgId"],
            "tblId": config["tblId"]
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, dict) and 'err' in data:
                logger.warning(f"KOSIS API Error for {start_ym}-{end_ym}: {data.get('errMsg')} (Code: {data.get('err')})")
                continue
            
            if isinstance(data, list):
                for item in data:
                    val_str = item.get("DT")
                    date_str = item.get("PRD_DE") # YYYYMM
                    if val_str and date_str:
                        # Convert YYYYMM to YYYY-MM-01
                        dt = datetime.strptime(date_str, "%Y%m").date()
                        batch.append({
                            "country": "KR",
                            "indicator": indicator,
                            "value": float(val_str),
                            "date": dt.isoformat(),
                            "source": "KOSIS_Backfill",
                            "raw": {"fetched_at": datetime.now().isoformat()}
                        })
                        
        except Exception as e:
            logger.warning(f"KOSIS fetch failed for chunk {start_ym}-{end_ym}: {e}")
            
    save_batch(supabase, batch, dry_run)


def run_backfill(dry_run=False):
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Supabase credentials missing.")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 1. Backfill JPYUSD (Yahoo)
    logger.info("Backfilling JP:JPYUSD from Yahoo (JPY=X) since 2000-01-01")
    try:
        import yfinance as yf
        df = yf.download("JPY=X", start="2000-01-01", progress=True)
        
        batch = []
        for index, row in df.iterrows():
            val = row['Close']
            if hasattr(val, 'item'): val = val.item()
            
            batch.append({
                "country": "JP",
                "indicator": "JPYUSD",
                "value": round(float(val), 2),
                "date": index.date().isoformat(),
                "source": "YahooFinance_Backfill",
                "raw": {"fetched_at": datetime.now().isoformat()}
            })
        
        save_batch(supabase, batch, dry_run)
            
    except Exception as e:
        logger.error(f"Failed to backfill JPYUSD: {e}")

    # 2. Backfill US Data (FRED)
    if FRED_API_KEY:
        import pandas_datareader.data as web
        start_date = "1970-01-01"
        
        for ind, series_id in FRED_MAP.items():
            logger.info(f"Backfilling US:{ind} from FRED ({series_id}) since {start_date}")
            try:
                df = web.DataReader(series_id, 'fred', start_date, api_key=FRED_API_KEY)
                batch = []
                for index, row in df.iterrows():
                    val = row[series_id]
                    batch.append({
                        "country": "US",
                        "indicator": ind,
                        "value": round(float(val), 2),
                        "date": index.date().isoformat(),
                        "source": "FRED_Backfill",
                        "raw": {"fetched_at": datetime.now().isoformat()}
                    })
                save_batch(supabase, batch, dry_run)
            except Exception as e:
                logger.error(f"Failed to backfill US:{ind}: {e}")
    else:
        logger.warning("FRED_API_KEY missing. Skipping US backfill.")

    # 3. Backfill KR Data (KOSIS)
    if KOSIS_API_KEY:
        for ind, config in KOSIS_MAP.items():
            backfill_kosis(supabase, ind, config, start_year=2000, dry_run=dry_run)
    else:
        logger.warning("KOSIS_API_KEY missing. Skipping KR backfill.")

    logger.info("Backfill completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    run_backfill(dry_run=args.dry_run)
