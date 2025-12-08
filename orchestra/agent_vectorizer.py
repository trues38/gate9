import os
import logging
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from sentence_transformers import SentenceTransformer

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_vectorizer.log"),
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
MODEL_NAME = "BAAI/bge-m3" # Multilingual, 1024 dimension
BATCH_SIZE = 50

def get_model():
    logger.info(f"Loading model: {MODEL_NAME}...")
    return SentenceTransformer(MODEL_NAME)

def fetch_pending_rows():
    """Fetch rows where embedding is NULL and summary is not NULL."""
    try:
        response = supabase.table('global_news_all')\
            .select('id, summary, title')\
            .is_('embedding', 'null')\
            .neq('summary', 'null')\
            .limit(BATCH_SIZE)\
            .execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching rows: {e}")
        return []

def update_embeddings(rows, embeddings):
    for i, row in enumerate(rows):
        try:
            # Convert numpy array to list
            embedding_list = embeddings[i].tolist()
            
            supabase.table('global_news_all')\
                .update({'embedding': embedding_list})\
                .eq('id', row['id'])\
                .execute()
        except Exception as e:
            logger.error(f"Error updating row {row['id']}: {e}")

def run_vectorizer():
    model = get_model()
    logger.info("Agent 6 (Vectorizer) Started.")
    
    while True:
        rows = fetch_pending_rows()
        if not rows:
            logger.info("No pending rows. Sleeping...")
            time.sleep(60)
            continue
            
        logger.info(f"Processing batch of {len(rows)} articles...")
        
        # Prepare texts: Title + Summary for better context
        texts = [f"{row['title']}\n{row['summary']}" for row in rows]
        
        try:
            embeddings = model.encode(texts, normalize_embeddings=True)
            update_embeddings(rows, embeddings)
            logger.info(f"Batch complete. Vectorized {len(rows)} articles.")
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_vectorizer()
