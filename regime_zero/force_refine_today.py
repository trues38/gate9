import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from openai import OpenAI

# Load environment variables
load_dotenv()

# Supabase Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# LLM Setup
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    print("❌ Error: OPENROUTER_API_KEY not found.")
    sys.exit(1)

client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")

# Models to try in order
MODELS = [
    "google/gemini-2.0-flash-exp:free",
    "amazon/nova-2-lite-v1:free",
    "meta-llama/llama-3.2-11b-vision-instruct:free",
    "microsoft/phi-3-medium-128k-instruct:free"
]

def refine_news_batch(articles):
    if not articles:
        return []

    print(f"   🤖 Refining batch of {len(articles)} articles...")

    articles_text = ""
    for i, art in enumerate(articles):
        articles_text += f"ID: {art['id']}\nTitle: {art['title']}\n---\n"

    system_prompt = """
    You are a Financial News Editor. Your job is to classify, score, and filter news for a professional trading dashboard.
    
    For each article, provide:
    1. Category: One of [ECONOMY, FINANCE, CRYPTO, COMMODITIES, POLITICS, TECH, WORLD, OTHER]
    2. Importance Score (0-10): 
       - 10: Market moving event (Rate hike, War, Major Crash)
       - 8-9: Significant corporate/economic news
       - 6-7: Relevant sector news
       - 0-5: Noise, Opinion, Minor updates, Ads, Gossip
    3. Korean Translation:
       - title_ko: Translate the title to natural business Korean.
    
    CRITICAL: 
    - Mark any "Shopping", "Deal", "Sale", "Celebrity", "Gossip", "Sponsored" content as Score 0.
    - Mark "Opinion" or "Clickbait" as Score 2-3.
    
    Output JSON format:
    {
        "results": [
            {
                "id": 123, 
                "category": "ECONOMY", 
                "score": 8, 
                "title_ko": "연준, 금리 인상 중단"
            }
        ]
    }
    """

    for model in MODELS:
        try:
            # print(f"      Trying model: {model}")
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": articles_text}
                ],
                response_format={"type": "json_object"}
            )
            
            content = completion.choices[0].message.content
            data = json.loads(content)
            results = data.get("results", [])
            if results:
                return results
            
        except Exception as e:
            print(f"      ❌ Error with {model}: {e}")
            continue
            
    return []

import json

def run_force_refinement():
    print(f"🚀 STARTING FORCE REFINEMENT LOOP [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    
    total_processed = 0
    
    while True:
        # Fetch batch of 20 unrefined items
        response = supabase.table("ingest_news") \
            .select("id, title, summary") \
            .eq("is_refined", False) \
            .order("published_at", desc=True) \
            .limit(20) \
            .execute()
            
        articles = response.data
        
        if not articles:
            print("✅ All news refined! No more unrefined items found.")
            break
            
        print(f"\n📦 Processing batch of {len(articles)} items (Total processed: {total_processed})")
        
        refined_results = refine_news_batch(articles)
        
        if not refined_results:
            print("   ⚠️ No results from LLM, skipping batch (might be error)")
            time.sleep(2)
            continue
            
        updates_count = 0
        for res in refined_results:
            try:
                update_data = {
                    "category": res.get("category", "OTHER"),
                    "importance_score": res.get("score", 0),
                    "title_ko": res.get("title_ko", ""),
                    "is_refined": True
                }
                
                supabase.table("ingest_news") \
                    .update(update_data) \
                    .eq("id", res["id"]) \
                    .execute()
                    
                updates_count += 1
            except Exception as e:
                print(f"   ⚠️ Update failed for ID {res.get('id')}: {e}")
        
        total_processed += updates_count
        print(f"   ✨ Saved {updates_count} updates.")
        
        # Sleep slightly to avoid rate limits
        time.sleep(1)

if __name__ == "__main__":
    run_force_refinement()
