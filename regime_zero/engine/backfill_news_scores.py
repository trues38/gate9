import os
import sys
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.openrouter_client import ask_llm
from regime_zero.config.model_config import MODEL_REFINER_FAST, MODEL_REFINER_DEEP

# Load environment variables
load_dotenv()

# Supabase Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def process_stage_1(rows):
    """
    Stage 1: Fast Filter & Initial Scoring
    """
    if not rows: return []
    
    print(f"   🏎️  Stage 1 (Fast): Re-scoring {len(rows)} articles...")
    
    articles_text = ""
    for row in rows:
        articles_text += f"ID: {row['id']}\nTitle: {row['title']}\n---\n"

    system_prompt = """
    You are a Fast News Filter.
    
    Task:
    1. Identify if the news is NOISE (Celebrity, Sports, Local Crime, Ads) or SIGNAL (Economy, Finance, Tech, Politics, Energy).
    2. Assign Initial Score (0-5).
       - 0-1: Noise/Irrelevant.
       - 2-3: Minor Signal.
       - 4-5: Potential High Impact.
    
    Output JSON:
    {
        "results": [
            {"id": 123, "keep": true, "score": 4},
            {"id": 124, "keep": false, "score": 0}
        ]
    }
    """
    
    try:
        response = ask_llm(
            prompt=articles_text,
            system_prompt=system_prompt,
            model=MODEL_REFINER_FAST,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        if not response: return []
        
        try:
            data = json.loads(response)
            return data.get("results", [])
        except:
            if "```json" in response:
                try:
                    return json.loads(response.split("```json")[1].split("```")[0]).get("results", [])
                except: pass
            return []
    except Exception as e:
        print(f"      ❌ Stage 1 Error: {e}")
        return []

def process_stage_2(item, original_row):
    """
    Stage 2: Deep Analysis & Translation
    """
    print(f"   🧠 Stage 2 (Deep): Analyzing '{original_row['title']}'...")
    
    system_prompt = """
    You are a Senior Macro Analyst.
    
    Task:
    1. Analyze the news importance (0-10).
       - 6-7: Significant Macro Data.
       - 8-9: Market Movers.
       - 10: Historic.
    2. Translate Title to Korean (Professional).
    3. Categorize (ECONOMY, POLITICS, SOCIETY, TECH). STRICTLY choose one of these 4.
       - ENERGY/FINANCE -> ECONOMY
       - GEOPOLITICS -> POLITICS
    
    Output JSON:
    {
        "score": 8,
        "title_ko": "...",
        "category": "ECONOMY"
    }
    """
    
    prompt = f"Title: {original_row['title']}\nSource: {original_row['source']}\nSummary: {original_row.get('summary', '')}"
    
    try:
        response = ask_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            model=MODEL_REFINER_DEEP,
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        if not response: return None
        
        try:
            return json.loads(response)
        except:
            if "```json" in response:
                try:
                    return json.loads(response.split("```json")[1].split("```")[0])
                except: pass
            return None
    except Exception as e:
        print(f"      ❌ Stage 2 Error: {e}")
        return None

def run_backfill():
    print(f"🚀 NEWS SCORE BACKFILL (2-Stage) [{datetime.now()}]")
    
    batch_size = 20
    
    while True:
        print("   🔍 Fetching batch of low-quality scores (5 or 0)...")
        response = supabase.table("ingest_news") \
            .select("*") \
            .or_("importance_score.eq.5,importance_score.eq.0") \
            .limit(batch_size) \
            .execute()
            
        rows = response.data
        if not rows:
            print("   ✅ No more items to backfill.")
            break
            
        print(f"   Found {len(rows)} items to re-score.")
        
        # Stage 1
        stage1_results = process_stage_1(rows)
        
        for s1_res in stage1_results:
            original_id = s1_res.get('id')
            if not original_id: continue
            
            row = next((r for r in rows if r['id'] == original_id), None)
            if not row: continue
            
            final_score = s1_res.get('score', 0)
            final_title_ko = ""
            final_category = "OTHER"
            
            # If Stage 1 says keep and score is high, go to Stage 2
            if s1_res.get('keep') and final_score >= 4:
                s2_res = process_stage_2(s1_res, row)
                if s2_res:
                    final_score = s2_res.get('score', final_score)
                    final_title_ko = s2_res.get('title_ko', "")
                    final_category = s2_res.get('category', "OTHER")
            
            # Update
            try:
                update_data = {
                    "importance_score": final_score,
                    "title_ko": final_title_ko if final_title_ko else row.get('title_ko'),
                    "category": final_category
                }
                
                supabase.table("ingest_news").update(update_data).eq("id", original_id).execute()
                print(f"      ✨ Updated ID {original_id}: Score {final_score} | {final_title_ko}")
                
            except Exception as e:
                print(f"      ⚠️ Update Error for ID {original_id}: {e}")
        
        time.sleep(2)

if __name__ == "__main__":
    run_backfill()
