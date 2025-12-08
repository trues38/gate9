import os
import time
import logging
import json
import argparse
import urllib.request
import urllib.error
import re
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.openrouter_client import ask_llm

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("summary_pipeline.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load Env
load_dotenv()

# Credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Configuration
MODEL_NAME = "x-ai/grok-4.1-fast:free"
MAX_WORKERS = 10 # Reduced for stability with 8-way parallel
BATCH_SIZE = 50
CONTEXT_WINDOW = 12000

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Supabase credentials missing.")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.text = []
    def handle_data(self, d):
        self.text.append(d)
    def get_data(self):
        return "".join(self.text)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

def fetch_url_content(url):
    """Fetches and extracts main text from a URL using urllib."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'}
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        # Simple cleaning
        # Remove scripts and styles
        html = re.sub(r'<(script|style).*?</\1>', '', html, flags=re.DOTALL)
        
        text = strip_tags(html)
        
        # Clean text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text[:CONTEXT_WINDOW]
    except Exception as e:
        # logger.debug(f"Crawling failed for {url}: {e}")
        return None

def generate_summary(text):
    """Generates a 3-bullet summary using Grok."""
    prompt = f"""
    Summarize the following news article in 3 concise bullet points in Korean.
    Focus on facts, numbers, and market impact.
    
    [Article Text]:
    {text}
    """
    
    try:
        return ask_llm(prompt, model=MODEL_NAME)
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        return None

def process_article(row):
    """Worker function to process a single article."""
    article_id = row['id']
    url = row.get('url')
    
    if not url:
        return {'id': article_id, 'status': 'FAILED', 'error': 'No URL'}
        
    # 1. Crawl
    raw_text = fetch_url_content(url)
    if not raw_text:
        return {'id': article_id, 'status': 'FAILED', 'error': 'Crawling Failed'}
        
    # [Garbage Filter]
    # 1. Too Short (Increased threshold)
    if len(raw_text) < 500:
        return {'id': article_id, 'status': 'SKIPPED', 'error': 'Text Too Short (<500)', 'raw_text': raw_text}
        
    # 2. Google News Redirect Fail
    if "Google News" in raw_text and len(raw_text) < 800:
        return {'id': article_id, 'status': 'SKIPPED', 'error': 'Google News Redirect Fail', 'raw_text': raw_text}
        
    # 3. Login/Paywall Detection
    garbage_phrases = ["JavaScript is disabled", "Please enable JS", "Subscribe to read", "Log in", "Sign up"]
    if any(phrase in raw_text for phrase in garbage_phrases) and len(raw_text) < 1000:
        return {'id': article_id, 'status': 'SKIPPED', 'error': 'Paywall/Login Detected', 'raw_text': raw_text}
        
    # 2. Summarize
    summary = generate_summary(raw_text)
    if not summary:
        return {'id': article_id, 'status': 'FAILED', 'error': 'Summary Failed', 'raw_text': raw_text}
        
    return {
        'id': article_id,
        'status': 'COMPLETED',
        'raw_text': raw_text,
        'summary': summary
    }

def update_batch(results):
    """Updates Supabase in batches."""
    for res in results:
        try:
            update_data = {
                'summary_status': res['status']
            }
            
            if res['status'] == 'COMPLETED':
                update_data['raw_text'] = res['raw_text']
                update_data['summary'] = res['summary']
            elif 'raw_text' in res: # Saved raw text even if summary failed
                 update_data['raw_text'] = res['raw_text']
            
            supabase.table('global_news_all').update(update_data).eq('id', res['id']).execute()
            
        except Exception as e:
            logger.error(f"Failed to update DB for {res['id']}: {e}")

def run_pipeline(start_date, end_date):
    logger.info(f"Starting News Summary Pipeline ({start_date} ~ {end_date})...")
    logger.info(f"Model: {MODEL_NAME}")

    while True:
        # Fetch pending rows (Reverse Chronological)
        try:
            response = supabase.table('global_news_all')\
                .select('id, url, published_at')\
                .or_('summary_status.eq.PENDING,summary_status.is.null')\
                .gte('published_at', start_date)\
                .lt('published_at', end_date)\
                .order('published_at', desc=True)\
                .limit(BATCH_SIZE)\
                .execute()
                
            rows = response.data
            
            if not rows:
                logger.info(f"No pending articles found for {start_date}~{end_date}. Pipeline finished.")
                break
                
            logger.info(f"Processing batch of {len(rows)} articles...")
            
            results = []
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_row = {executor.submit(process_article, row): row for row in rows}
                
                for future in as_completed(future_to_row):
                    results.append(future.result())
            
            # Update DB
            update_batch(results)
            logger.info(f"Batch complete. Processed {len(results)} articles.")
            
        except Exception as e:
            logger.error(f"Pipeline Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start_date", type=str, default="2000-01-01")
    parser.add_argument("--end_date", type=str, default="2025-12-31")
    args = parser.parse_args()
    
    run_pipeline(args.start_date, args.end_date)
