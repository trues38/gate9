import os
import sys
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    Uses lightweight models (Nvidia Nano, etc.)
    """
    if not rows: return []
    
    print(f"   🏎️  Stage 1 (Fast): Filtering {len(rows)} articles...")
    
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
    Uses reasoning models (Olmo 3 Think, etc.) for high-value items.
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
    
    prompt = f"Title: {original_row['title']}\nSource: {original_row['source']}\nSummary: {original_row['raw_data'].get('summary', '')}"
    
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

def run_processing():
    print(f"🚀 NEWS PIPELINE (2-Stage) [{datetime.now()}]")
    
    # 1. Fetch Raw
    response = supabase.table("news_raw") \
        .select("*") \
        .eq("processed", False) \
        .order("published_at", desc=True) \
        .limit(20) \
        .execute()
        
    rows = response.data
    if not rows:
        print("   ✅ No new raw news.")
        return

    # 2. Stage 1: Fast Filter
    stage1_results = process_stage_1(rows)
    
    processed_ids = []
    
    # Prepare tasks for Stage 2
    stage2_tasks = []
    ready_to_insert = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_item = {}
        
        for s1_res in stage1_results:
            original_id = s1_res.get('id')
            if not original_id: continue
            
            processed_ids.append(original_id)
            row = next((r for r in rows if r['id'] == original_id), None)
            if not row: continue

            if not s1_res.get('keep'):
                continue
                
            final_score = s1_res.get('score', 0)
            
            if final_score >= 4:
                # Submit to Stage 2
                future = executor.submit(process_stage_2, s1_res, row)
                future_to_item[future] = (s1_res, row)
            else:
                # No Stage 2 needed
                ready_to_insert.append({
                    "row": row,
                    "score": final_score,
                    "title_ko": "",
                    "category": "OTHER"
                })
        
        # Collect Stage 2 results
        for future in as_completed(future_to_item):
            s1_res, row = future_to_item[future]
            try:
                s2_res = future.result()
                if s2_res:
                    ready_to_insert.append({
                        "row": row,
                        "score": s2_res.get('score', s1_res.get('score', 0)),
                        "title_ko": s2_res.get('title_ko', ""),
                        "category": s2_res.get('category', "OTHER")
                    })
                else:
                    # Stage 2 failed, fallback to Stage 1
                    ready_to_insert.append({
                        "row": row,
                        "score": s1_res.get('score', 0),
                        "title_ko": "",
                        "category": "OTHER"
                    })
            except Exception as e:
                print(f"      ❌ Stage 2 Future Error: {e}")
                # Fallback
                ready_to_insert.append({
                    "row": row,
                    "score": s1_res.get('score', 0),
                    "title_ko": "",
                    "category": "OTHER"
                })

    # Insert all ready items
    for item in ready_to_insert:
        row = item['row']
        final_score = item['score']
        final_title_ko = item['title_ko']
        final_category = item['category']
        
        try:
            golden_data = {
                "title": row['title'],
                "clean_title": row['title'],
                "url": row['url'],
                "published_at": row['published_at'],
                "country": row['country'],
                "source": row['source'],
                "category": final_category,
                "importance_score": final_score,
                "summary": row['raw_data'].get('summary', ''),
                "is_refined": True,
                "title_ko": final_title_ko
            }
            
            supabase.table("ingest_news").upsert(golden_data, on_conflict="url").execute()
            print(f"      ✨ Promoted: {row['title']} (Score: {final_score})")
            
        except Exception as e:
            print(f"      ⚠️ Insert Error: {e}")

    # 4. Mark Processed
    if processed_ids:
        supabase.table("news_raw").update({"processed": True}).in_("id", processed_ids).execute()
        print(f"   ✅ Processed {len(processed_ids)} items.")

if __name__ == "__main__":
    run_processing()
