import os
import json
import random
from supabase import create_client
from dotenv import load_dotenv
from utils.openrouter_client import ask_llm

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MODEL_NAME = "x-ai/grok-4.1-fast:free" # Fast and smart enough for QA

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_samples(table, count=5):
    """Fetches random samples with completed summaries."""
    # Supabase doesn't support random() easily in REST, so we fetch a range and sample python-side
    # Or just fetch latest 100 and sample 5
    try:
        # Remove sort to avoid timeout on large table
        res = supabase.table(table)\
            .select('*')\
            .eq('summary_status', 'COMPLETED')\
            .limit(20)\
            .execute()
        
        data = res.data
        if not data:
            return []
        return random.sample(data, min(len(data), count))
    except Exception as e:
        print(f"❌ Fetch Error ({table}): {e}")
        return []

def evaluate_summary(raw_text, summary, source_type="News"):
    """Asks LLM to grade the summary."""
    prompt = f"""
    You are a strict Editor-in-Chief. Grade the following summary based on the raw text.
    
    [Source Type]: {source_type}
    
    [Raw Text]:
    {raw_text[:8000]} (Truncated)
    
    [Summary]:
    {summary}
    
    [Criteria]:
    1. Accuracy (1-10): Does it match the raw text?
    2. Density (1-10): Does it contain specific numbers/facts? (Avoid vague fluff)
    3. Hallucination (Yes/No): Did it make things up?
    4. Verdict (Pass/Fail): Pass if Accuracy >= 8 and Density >= 7.
    
    [Output Format]:
    JSON only: {{ "accuracy": int, "density": int, "hallucination": bool, "verdict": "Pass/Fail", "comment": "short comment" }}
    """
    
    try:
        response = ask_llm(prompt, model=MODEL_NAME)
        # Clean json
        response = response.replace("```json", "").replace("```", "").strip()
        return json.loads(response)
    except Exception as e:
        return {"error": str(e)}

def evaluate_headline(raw_text, headline):
    """Asks LLM to grade the headline."""
    prompt = f"""
    You are a strict Editor-in-Chief. Grade the following headline based on the raw text.
    
    [Raw Text]:
    {raw_text[:5000]} (Truncated)
    
    [Headline]:
    {headline}
    
    [Criteria]:
    1. Accuracy (1-10): Does the headline match the article content?
    2. Clickbait (Yes/No): Is it misleading or exaggerated?
    3. Verdict (Pass/Fail): Pass if Accuracy >= 8 and not Clickbait.
    
    [Output Format]:
    JSON only: {{ "accuracy": int, "clickbait": bool, "verdict": "Pass/Fail", "comment": "short comment" }}
    """
    
    try:
        response = ask_llm(prompt, model=MODEL_NAME)
        response = response.replace("```json", "").replace("```", "").strip()
        return json.loads(response)
    except Exception as e:
        return {"error": str(e)}

def run_qa():
    print("🕵️ Starting QA Agent...")
    
    # 1. News QA (Summary & Headline)
    print("\n📰 Checking News (Summary & Headline)...")
    news_samples = fetch_samples('global_news_all', 3)
    for item in news_samples:
        print(f"   - Checking ID: {item.get('id')}...")
        
        # Summary Check
        print(f"     [Summary Check]")
        grade = evaluate_summary(item.get('raw_text', ''), item.get('summary', ''), "News")
        print(f"     👉 {grade}")
        
        # Headline Check
        print(f"     [Headline Check] '{item.get('title', 'No Title')}'")
        h_grade = evaluate_headline(item.get('raw_text', ''), item.get('title', ''))
        print(f"     👉 {h_grade}")
        
    # 2. YouTube QA
    print("\n📺 Checking YouTube Summaries...")
    # Check if table exists first (it should now)
    yt_samples = fetch_samples('youtube_transcripts', 3)
    for item in yt_samples:
        print(f"   - Checking Video: {item.get('video_id')}...")
        grade = evaluate_summary(item.get('transcript_text', ''), item.get('summary', ''), "YouTube Transcript")
        print(f"     👉 Grade: {grade}")

if __name__ == "__main__":
    run_qa()
