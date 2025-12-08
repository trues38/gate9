import os
import time
import logging
import json
import argparse
import sys
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from utils.openrouter_client import ask_llm

# Try importing youtube_transcript_api
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    print("❌ 'youtube_transcript_api' is missing. Please install it:")
    print("   pip install youtube-transcript-api")
    sys.exit(1)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("youtube_pipeline.log"),
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

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Supabase credentials missing.")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

import random

# ... (imports)

def fetch_transcript(video_id):
    """Fetches transcript for a video ID with retry and delay."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Random delay before fetch to avoid blocking
            time.sleep(random.uniform(2, 5))
            
            # Use instance-based API for v1.2.3
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)
            
            # Try to find Korean or English transcript
            try:
                transcript = transcript_list.find_transcript(['ko', 'en'])
            except:
                # Fallback to any available
                transcript = transcript_list.find_transcript(['ko', 'en', 'ja', 'zh-Hans', 'zh-Hant'])
                
            transcript_data = transcript.fetch()
            
            # Handle both object (v1.2.3) and dict (older) return types
            full_text = ""
            for t in transcript_data:
                if hasattr(t, 'text'):
                    full_text += t.text + " "
                elif isinstance(t, dict):
                    full_text += t.get('text', '') + " "
                else:
                    full_text += str(t) + " "
            
            return full_text.strip()
        except Exception as e:
            if "Too Many Requests" in str(e):
                wait_time = (attempt + 1) * 60 # Wait 1, 2, 3 minutes
                logger.warning(f"⚠️ YouTube Rate Limit hit for {video_id}. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.warning(f"Failed to fetch transcript for {video_id}: {e}")
                return None
    return None

# ... (rest of code)

    for vid in video_ids:
        process_video(vid)
        # Random delay between videos
        delay = random.uniform(10, 30)
        logger.info(f"Sleeping for {delay:.1f}s...")
        time.sleep(delay)

def generate_summary(text):
    """Generates a summary using Grok."""
    prompt = f"""
    Summarize the following YouTube video transcript in 3 concise bullet points in Korean.
    Focus on macro-economic insights, market predictions, and key data points.
    
    [Transcript]:
    {text[:15000]}  # Truncate to be safe, though Grok has large context
    """
    
    try:
        return ask_llm(prompt, model=MODEL_NAME)
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        return None

def process_video(video_id, channel_id=None, title=None, published_at=None):
    """Processes a single video."""
    logger.info(f"Processing Video: {video_id}")
    
    # Check if already exists
    try:
        res = supabase.table('youtube_transcripts').select('id').eq('video_id', video_id).execute()
        if res.data:
            logger.info(f"Video {video_id} already exists. Skipping.")
            return
    except Exception as e:
        logger.error(f"DB Check Failed: {e}")

    # 1. Fetch Transcript
    transcript = fetch_transcript(video_id)
    if not transcript:
        return

    # 2. Summarize
    summary = generate_summary(transcript)
    if not summary:
        logger.error(f"Summary failed for {video_id}")
        return

    # 3. Save to DB
    try:
        data = {
            'video_id': video_id,
            'channel_id': channel_id,
            'title': title,
            'published_at': published_at, # Needs ISO format
            'transcript_text': transcript,
            'summary': summary,
            'summary_status': 'COMPLETED'
        }
        supabase.table('youtube_transcripts').insert(data).execute()
        logger.info(f"✅ Saved {video_id} to DB.")
    except Exception as e:
        logger.error(f"Failed to save to DB: {e}")

def run_pipeline(video_list_file):
    """Runs pipeline from a list of video IDs."""
    if not os.path.exists(video_list_file):
        logger.error(f"Video list file not found: {video_list_file}")
        return

    with open(video_list_file, 'r') as f:
        video_ids = [line.strip() for line in f if line.strip()]

    logger.info(f"Found {len(video_ids)} videos to process.")
    
    for vid in video_ids:
        process_video(vid)
        # Random delay between videos
        delay = random.uniform(10, 30)
        logger.info(f"Sleeping for {delay:.1f}s...")
        time.sleep(delay)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, help="Path to file containing Video IDs (one per line)")
    parser.add_argument("--video_id", type=str, help="Single Video ID to process")
    args = parser.parse_args()
    
    if args.video_id:
        process_video(args.video_id)
    elif args.file:
        run_pipeline(args.file)
    else:
        print("Usage: python youtube_pipeline.py --file <video_ids.txt> OR --video_id <ID>")
