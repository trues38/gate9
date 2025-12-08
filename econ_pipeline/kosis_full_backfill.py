import os
import sys
import time
import json
import logging
import random
import requests
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# Setup Logging
logging.basicConfig(
    level=logging.DEBUG, # Changed to DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("kosis_backfill.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load Env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
KOSIS_API_KEY = os.getenv("KOSIS_API_KEY")

class KosisBackfillEngine:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.supabase = self._init_supabase()
        self.api_key = KOSIS_API_KEY
        self.batch_size = 1000
        
        if not self.api_key:
            logger.error("KOSIS_API_KEY is missing!")
            sys.exit(1)

    def _init_supabase(self) -> Optional[Client]:
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.warning("Supabase credentials missing. DB operations will be skipped.")
            return None
        try:
            return create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            logger.error(f"Supabase init failed: {e}")
            return None

    def _sleep(self):
        """Throttling: 0.2 - 0.5 seconds"""
        if not self.dry_run:
            time.sleep(random.uniform(0.2, 0.5))

    @staticmethod
    def parse_kosis_date(prd_de: str, prd_se: str = "M") -> Optional[str]:
        """
        Robust date parsing for KOSIS PRD_DE.
        Returns YYYY-MM-DD string or None if invalid.
        """
        if not prd_de:
            return None
            
        prd_de = str(prd_de).strip()
        
        try:
            # 1. Monthly (YYYYMM) -> YYYY-MM-01
            if len(prd_de) == 6 and prd_de.isdigit():
                return f"{prd_de[:4]}-{prd_de[4:]}-01"
            
            # 2. Annual (YYYY) -> YYYY-01-01
            if len(prd_de) == 4 and prd_de.isdigit():
                return f"{prd_de}-01-01"
                
            # 3. Quarterly (YYYYQx) -> YYYY-MM-01 (Start of Quarter)
            # Q1: 01, Q2: 04, Q3: 07, Q4: 10
            if len(prd_de) >= 5 and "Q" in prd_de.upper():
                # Example: 2023Q1
                parts = prd_de.upper().split("Q")
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    year = parts[0]
                    q = int(parts[1])
                    month = (q - 1) * 3 + 1
                    return f"{year}-{month:02d}-01"

            # 4. Daily/Weekly (YYYYMMDD or similar) - Less common for these stats
            if len(prd_de) == 8 and prd_de.isdigit():
                return f"{prd_de[:4]}-{prd_de[4:6]}-{prd_de[6:]}"

            logger.warning(f"Unrecognized date format: {prd_de}")
            return None
            
        except Exception as e:
            logger.error(f"Date parsing error for '{prd_de}': {e}")
            return None

    def upsert_batch(self, batch: List[Dict[str, Any]]):
        if not batch or not self.supabase:
            return
            
        try:
            # Upsert to econ_kosis_data
            # Unique constraint: org_id, tbl_id, date, itm_id, obj_l1, obj_l2
            self.supabase.table("econ_kosis_data").upsert(
                batch, 
                on_conflict="org_id, tbl_id, date, itm_id, obj_l1, obj_l2"
            ).execute()
            logger.info(f"  Upserted {len(batch)} rows.")
        except Exception as e:
            logger.error(f"Batch upsert failed: {e}")
            # Retry logic could be added here

    def fetch_and_backfill(self, org_id: str, tbl_id: str, start_year: int = 2000):
        logger.info(f"Starting backfill for {tbl_id} (Org: {org_id}) from {start_year}...")
        
        current_year = datetime.now().year
        total_rows = 0
        
        for year in range(start_year, current_year + 1):
            start_prd = f"{year}01"
            end_prd = f"{year}12"
            
            # Expanded Strategies
            strategies = [
                {"itmId": "ALL", "objL1": "ALL"},
                {"itmId": "T1", "objL1": "ALL"}, # Common default
                {"itmId": "T1"}, # Just Total
                {"itmId": "ALL"}, # All items, no classification
                {"itmId": "ALL", "objL1": "ALL", "objL2": "ALL"},
            ]
            
            success = False
            for strategy in strategies:
                if success: break
                
                params = {
                    "method": "getList",
                    "apiKey": self.api_key,
                    "format": "json",
                    "jsonVD": "Y",
                    "prdSe": "M",
                    "startPrdDe": start_prd,
                    "endPrdDe": end_prd,
                    "orgId": org_id,
                    "tblId": tbl_id
                }
                params.update(strategy)
                
                self._sleep()
                
                try:
                    url = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
                    response = requests.get(url, params=params)
                    
                    if response.status_code != 200:
                        logger.warning(f"HTTP {response.status_code} for {year} (Strat: {strategy})")
                        continue
                        
                    data = response.json()
                    
                    if isinstance(data, dict) and 'err' in data:
                        # Log error for debugging
                        logger.debug(f"API Error {data.get('err')}: {data.get('errMsg')} (Year: {year}, Strat: {strategy})")
                        continue
                    
                    if not isinstance(data, list):
                        logger.debug(f"Unexpected data format: {type(data)}")
                        continue

                    if not data:
                        logger.debug(f"Empty data list (Year: {year}, Strat: {strategy})")
                        continue

                    # Success! Process Data
                    success = True
                    batch = []
                    for item in data:
                        val_str = item.get("DT")
                        prd_de = item.get("PRD_DE")
                        itm_id = item.get("ITM_ID", "")
                        obj_l1 = item.get("C1", "")
                        obj_l2 = item.get("C2", "")
                        unit = item.get("UNIT_NM", "")
                        
                        if not val_str or not prd_de: continue
                        
                        date_str = self.parse_kosis_date(prd_de)
                        if not date_str: continue
                        
                        try:
                            # val_float = float(val_str) # Keep as text as per schema
                            pass
                        except ValueError:
                            continue

                        record = {
                            "org_id": org_id,
                            "tbl_id": tbl_id,
                            "date": date_str,
                            "itm_id": itm_id,
                            "obj_l1": obj_l1,
                            "obj_l2": obj_l2,
                            "value": val_str,
                            "unit": unit
                        }
                        batch.append(record)
                        
                        if len(batch) >= self.batch_size:
                            if not self.dry_run:
                                self.upsert_batch(batch)
                            batch = []
                    
                    if batch and not self.dry_run:
                        self.upsert_batch(batch)
                        
                    total_rows += len(data)
                    logger.info(f"Processed {len(data)} rows for {year} (Strategy: {strategy})")
                    
                except Exception as e:
                    logger.error(f"Exception fetching {year}: {e}")
            
            if not success:
                logger.debug(f"Failed all strategies for {year}")

        logger.info(f"Finished {tbl_id}. Total rows: {total_rows}")

    def _upsert_master(self, records: List[Dict[str, Any]]):
        if not records or not self.supabase: return
        try:
            self.supabase.table("econ_kosis_master").upsert(records).execute()
            logger.info(f"Saved {len(records)} tables to Master.")
        except Exception as e:
            logger.error(f"Failed to save master records: {e}")

    def _crawl_category(self, parent_list_id: str, depth: int = 0):
        """Recursively crawl KOSIS category tree."""
        if depth > 5: return # Safety break
        
        # CORRECT ENDPOINT for Lists/Categories
        url = "https://kosis.kr/openapi/statisticsList.do"
        params = {
            "method": "getList",
            "apiKey": self.api_key,
            "vwCd": "MT_ZTITLE",
            "parentListId": parent_list_id,
            "format": "json",
            "jsonVD": "Y"
        }
        
        try:
            self._sleep()
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                logger.warning(f"Crawl HTTP {response.status_code} for {parent_list_id}")
                return

            data = response.json()
            
            if isinstance(data, dict) and 'err' in data:
                logger.debug(f"Crawl API Error {data.get('err')} for {parent_list_id}: {data.get('errMsg')}")
                return

            tables = []
            sub_categories = []
            for item in data:
                list_id = item.get("LIST_ID")
                list_nm = item.get("LIST_NM")
                tbl_id = item.get("TBL_ID")
                tbl_nm = item.get("TBL_NM") # Correct key for tables
                org_id = item.get("ORG_ID")
                
                if tbl_id:
                    tables.append({
                        "org_id": org_id,
                        "tbl_id": tbl_id,
                        "tbl_nm": tbl_nm or list_nm, # Prefer TBL_NM
                        "meta_raw": item,
                        "last_crawled_at": datetime.now().isoformat()
                    })
                    logger.info(f"Found Table: {tbl_nm or list_nm} ({tbl_id})")
                
                if not tbl_id and list_id:
                    sub_categories.append(list_id)

            if tables and not self.dry_run:
                self._upsert_master(tables)

            for sub_id in sub_categories:
                self._crawl_category(sub_id, depth + 1)

        except Exception as e:
            logger.error(f"Failed to crawl {parent_list_id}: {e}")

    def crawl_tables(self):
        """Crawl all tables from KOSIS starting from top-level categories."""
        logger.info("Starting Table Crawl... (Press Ctrl+C to skip crawling and proceed to backfill)")
        # Top-level roots (Standard KOSIS Categories)
        roots = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R"]
        
        try:
            for r in roots:
                self._crawl_category(r)
        except KeyboardInterrupt:
            logger.warning("\nCrawl skipped by user. Proceeding to backfill...")
        except Exception as e:
            logger.error(f"Crawl failed: {e}")

    def backfill_from_master(self):
        """Fetch tables from Master and backfill."""
        if not self.supabase: return
        
        try:
            # Fetch all tables from master
            # For large datasets, pagination is needed. For now, fetch first 1000.
            res = self.supabase.table("econ_kosis_master").select("*").execute()
            tables = res.data
            
            logger.info(f"Found {len(tables)} tables in Master to backfill.")
            
            for t in tables:
                self.fetch_and_backfill(t["org_id"], t["tbl_id"])
                
        except Exception as e:
            logger.error(f"Failed to fetch from master: {e}")

    def run(self):
        logger.info("Starting KOSIS Robust Backfill...")
        
        # 1. Crawl (Optional: can be skipped if Master is populated)
        # We run it to ensure we have data.
        self.crawl_tables()
        
        # 2. Backfill from Master
        self.backfill_from_master()
        
        # 3. Fallback: Run specific known working table if Master is empty
        # DT_2KAA2301 (Retail Sales) is known to exist.
        try:
            if not self.supabase:
                logger.warning("Supabase not configured. Skipping DB checks.")
                return

            # Check if master has data
            res = self.supabase.table("econ_kosis_master").select("tbl_id", count="exact").execute()
            if res.count == 0:
                 logger.info("Master empty. Running fallback target.")
                 self.fetch_and_backfill("101", "DT_2KAA2301")
                 
        except Exception as e:
            # Check for missing table error
            err_str = str(e)
            if "PGRST205" in err_str or "Could not find the table" in err_str:
                logger.critical("\n" + "="*60)
                logger.critical("CRITICAL ERROR: Missing Database Table")
                logger.critical("="*60)
                logger.critical("The table 'econ_kosis_master' does not exist in Supabase.")
                logger.critical("Please run the following SQL in your Supabase SQL Editor:")
                logger.critical("-" * 40)
                logger.critical("""
CREATE TABLE IF NOT EXISTS econ_kosis_master (
    org_id TEXT NOT NULL,
    tbl_id TEXT NOT NULL,
    tbl_nm TEXT,
    meta_raw JSONB,
    last_crawled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (org_id, tbl_id)
);

CREATE TABLE IF NOT EXISTS econ_kosis_data (
    org_id TEXT NOT NULL,
    tbl_id TEXT NOT NULL,
    date DATE NOT NULL,
    itm_id TEXT NOT NULL,
    obj_l1 TEXT DEFAULT '',
    obj_l2 TEXT DEFAULT '',
    value NUMERIC,
    unit TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (org_id, tbl_id, date, itm_id, obj_l1, obj_l2)
);
                """)
                logger.critical("-" * 40)
                logger.critical("After running this SQL, try running the script again.")
                sys.exit(1)
            else:
                logger.error(f"Unexpected DB Error: {e}")

        logger.info("All tasks completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    engine = KosisBackfillEngine(dry_run=args.dry_run)
    engine.run()
