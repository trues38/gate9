import os
import sys
import logging
import argparse
from typing import List, Dict, Any
from pathlib import Path

# Add project root to sys.path to allow running as script
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from dotenv import load_dotenv
from supabase import create_client
from econ_pipeline.kosis_full_backfill import KosisBackfillEngine

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load Env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Target Indicators (Keywords & Heuristics)
TARGETS = [
    {"name": "GDP (Real)", "keywords": ["국내총생산", "실질", "분기"], "org_pref": ["301"]},
    {"name": "CPI (Consumer Price Index)", "keywords": ["소비자물가지수", "총지수"], "org_pref": ["101"]},
    {"name": "Unemployment Rate", "keywords": ["실업률", "성/연령별"], "org_pref": ["101"]},
    {"name": "Industrial Production", "keywords": ["광공업생산지수", "시도/산업별"], "org_pref": ["101"]},
    {"name": "Retail Sales", "keywords": ["소매판매액지수", "재별"], "org_pref": ["101"]},
    {"name": "Exports/Imports (Total)", "keywords": ["수출입총괄"], "org_pref": ["101", "301"]},
    {"name": "Leading Economic Index", "keywords": ["경기선행지수"], "org_pref": ["101"]},
    {"name": "Sentiment (BSI)", "keywords": ["기업경기실사지수"], "org_pref": ["301"]},
]

class SmartBackfill:
    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Supabase credentials missing.")
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.engine = KosisBackfillEngine() # Reuse the engine

    def find_best_table(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """Find the best matching table for a target indicator."""
        query = self.supabase.table("econ_kosis_master").select("org_id, tbl_id, tbl_nm")
        
        # 1. Filter by first keyword (most important)
        first_kw = target["keywords"][0]
        query = query.ilike("tbl_nm", f"%{first_kw}%")
        
        results = query.execute().data
        if not results:
            logger.warning(f"No tables found for '{target['name']}' (Keyword: {first_kw})")
            return None
            
        # 2. Score candidates
        best_score = -1
        best_table = None
        
        for row in results:
            score = 0
            tbl_nm = row["tbl_nm"]
            org_id = row["org_id"]
            
            # Keyword matches
            for kw in target["keywords"]:
                if kw in tbl_nm:
                    score += 10
            
            # Org preference
            if org_id in target.get("org_pref", []):
                score += 5
                
            # Penalize long names (often too specific)
            if len(tbl_nm) > 30:
                score -= 2
                
            if score > best_score:
                best_score = score
                best_table = row
                
        if best_table:
            logger.info(f"Selected for {target['name']}: {best_table['tbl_nm']} ({best_table['tbl_id']})")
            
        return best_table

    def run(self):
        logger.info("Starting Smart Backfill...")
        
        selected_tables = []
        for target in TARGETS:
            table = self.find_best_table(target)
            if table:
                selected_tables.append(table)
                
        if not selected_tables:
            logger.warning("No targets found.")
            return

        logger.info(f"\nBackfilling {len(selected_tables)} selected tables:")
        for t in selected_tables:
            logger.info(f" - {t['tbl_nm']} ({t['tbl_id']})")
            
        # Execute Backfill
        for t in selected_tables:
            logger.info(f"\nProcessing {t['tbl_nm']}...")
            try:
                self.engine.fetch_and_backfill(t["org_id"], t["tbl_id"])
            except Exception as e:
                logger.error(f"Failed to backfill {t['tbl_id']}: {e}")

if __name__ == "__main__":
    SmartBackfill().run()
