import os
import sys
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from openai import OpenAI

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Supabase Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# LLM Setup
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")

MODEL = "google/gemini-2.0-flash-exp:free"

def process_batch(rows):
    """
    Refines a batch of raw news.
    """
    if not rows:
        return []

    print(f"   🤖 Refining {len(rows)} raw articles...")
    
    # Prepare prompt
    articles_text = ""
    for row in rows:
        articles_text += f"ID: {row['id']}\nTitle: {row['title']}\nCountry: {row['country']}\n---\n"

    system_prompt = """
    You are a Global News Filter.
    
    Task:
    1. Filter out NOISE (Celebrity, Sports, Local Crime, Ads, Shopping).
    2. Keep MACRO/FINANCE/TECH/GEOPOLITICS.
    3. Translate Titles to Korean.
    4. Assign Importance Score (0-10).
    
    Output JSON:
    {
        "results": [
            {"id": 123, "keep": true, "title_ko": "...", "score": 8, "category": "ECONOMY"},
            {"id": 124, "keep": false}
        ]
    }
    """

    try:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                completion = client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": articles_text}
                    ],
                    response_format={"type": "json_object"}
                )
                
                content = completion.choices[0].message.content
                try:
                    data = json.loads(content)
                    return data.get("results", [])
                except json.JSONDecodeError as je:
                    print(f"      ❌ JSON Parse Error: {je}")
                    # Optional: Try to repair or just skip this batch
                    return []
                
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    print(f"      ⚠️ Rate Limit (429). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise e
        
    except Exception as e:
        print(f"      ❌ LLM Error: {e}")
        return []

def run_processing():
    print(f"🚀 NEWS REFINEMENT ENGINE (Raw -> Golden) [{datetime.now()}]")
    
    # 1. Fetch Unprocessed Raw News
    response = supabase.table("news_raw") \
        .select("*") \
        .eq("processed", False) \
        .limit(10) \
        .execute()
        
    rows = response.data
    if not rows:
        print("   ✅ No new raw news.")
        return

    # 2. Process
    results = process_batch(rows)
    
    # 3. Update/Insert
    processed_ids = []
    
    for res in results:
        original_id = res['id']
        processed_ids.append(original_id)
        
        if not res.get('keep'):
            continue
            
        # Find original row
        row = next((r for r in rows if r['id'] == original_id), None)
        if not row: continue
        
        # Insert into ingest_news (Golden)
        try:
            golden_data = {
                "title": row['title'],
                "clean_title": res.get('title_ko', row['title']), # Use translated title as clean? Or keep original? Let's use translated for now as requested by user context usually.
                "url": row['url'],
                "published_at": row['published_at'],
                "country": row['country'],
                "source": row['source'],
                "category": res.get('category', 'OTHER'),
                "importance_score": res.get('score', 0),
                "summary": row['raw_data'].get('summary', ''),
                "is_refined": True
            }
            
            supabase.table("ingest_news").upsert(golden_data, on_conflict="url").execute()
            print(f"      ✨ Promoted: {row['title']}")
            
        except Exception as e:
            print(f"      ⚠️ Insert Error: {e}")

    # 4. Mark as Processed
    if processed_ids:
        supabase.table("news_raw").update({"processed": True}).in_("id", processed_ids).execute()
        print(f"   ✅ Marked {len(processed_ids)} rows as processed.")

if __name__ == "__main__":
    run_processing()
