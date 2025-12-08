import os
import logging
import time
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_signal_scorer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load Env
BASE_DIR = Path(__file__).parent.parent
ENV_PATH = BASE_DIR / 'econ_pipeline' / '.env'
load_dotenv(dotenv_path=ENV_PATH)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Supabase credentials missing.")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuration
MODEL_NAME = "BAAI/bge-m3"
BATCH_SIZE = 50

# Reference Concepts for Similarity (Crisis/Risk focus)
# We use English as BGE-m3 aligns multilingual space well.
REFERENCE_TEXT = "Economic Crisis Recession Inflation War Market Crash Financial Instability"
REFERENCE_VECTOR = None

def load_model_and_reference():
    global REFERENCE_VECTOR
    logger.info(f"Loading model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    logger.info("Encoding reference concept...")
    REFERENCE_VECTOR = model.encode(REFERENCE_TEXT, normalize_embeddings=True)
    return model

def calculate_impact_score(row):
    """
    Heuristic Impact Score (0-100).
    Based on keyword presence and summary length.
    """
    text = (row.get('title') or "") + " " + (row.get('summary') or "")
    
    # Keywords (KR/EN mixed)
    high_impact_keywords = [
        '위기', '폭락', '급락', '붕괴', '전쟁', '공포', '쇼크', '긴급',
        'Crisis', 'Crash', 'Plunge', 'Collapse', 'War', 'Panic', 'Shock', 'Emergency'
    ]
    medium_impact_keywords = [
        '상승', '하락', '금리', '인플레이션', '고용', '실적',
        'Rise', 'Fall', 'Rate', 'Inflation', 'Jobs', 'Earnings'
    ]
    
    score = 50 # Base score
    
    for kw in high_impact_keywords:
        if kw in text:
            score += 10
            
    for kw in medium_impact_keywords:
        if kw in text:
            score += 5
            
    return min(100, score)

def fetch_pending_rows():
    """Fetch rows where signal_score is NULL but embedding is present."""
    try:
        response = supabase.table('global_news_all')\
            .select('id, title, summary, embedding')\
            .is_('signal_score', 'null')\
            .filter('embedding', 'not.is', 'null')\
            .limit(BATCH_SIZE)\
            .execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching rows: {e}")
        return []

def update_scores(rows, scores):
    for i, row in enumerate(rows):
        try:
            supabase.table('global_news_all')\
                .update({'signal_score': scores[i]})\
                .eq('id', row['id'])\
                .execute()
        except Exception as e:
            logger.error(f"Error updating row {row['id']}: {e}")

def run_signal_scorer():
    load_model_and_reference()
    logger.info("Agent 7 (Signal Scorer) Started.")
    
    while True:
        rows = fetch_pending_rows()
        if not rows:
            logger.info("No pending rows. Sleeping...")
            time.sleep(60)
            continue
            
        logger.info(f"Processing batch of {len(rows)} articles...")
        
        scores = []
        for row in rows:
            # 1. Impact Score (0-100) -> Normalized to 0-1
            impact = calculate_impact_score(row) / 100.0
            
            # 2. Similarity Score (Cosine Similarity)
            # embedding is list, convert to array
            emb = np.array(row['embedding'])
            # Reshape for sklearn
            sim = cosine_similarity([emb], [REFERENCE_VECTOR])[0][0]
            # Normalize sim (-1 to 1) to 0-1 roughly, though usually positive for relevant texts
            sim = max(0, sim) 
            
            # 3. Indicator Score (Placeholder 0.5 for neutral)
            indicator = 0.5
            
            # Formula: Signal = (Impact*0.4) + (Similarity*0.3) + (Indicator*0.3)
            final_signal = (impact * 0.4) + (sim * 0.3) + (indicator * 0.3)
            
            # Scale back to 0-100
            scores.append(round(final_signal * 100, 2))
            
        update_scores(rows, scores)
        logger.info(f"Batch complete. Scored {len(rows)} articles.")

if __name__ == "__main__":
    run_signal_scorer()
