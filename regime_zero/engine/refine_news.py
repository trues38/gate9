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
# Supabase Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
# Ideally use SERVICE_ROLE_KEY for backend scripts to bypass RLS if needed, but ANON might work if policies allow
# For now, assuming existing env vars. If write fails, we might need SERVICE_ROLE.
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL or SUPABASE_KEY not found in environment variables.")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# LLM Setup
# Main: Google Gemini 2.0 Flash (Free)
# Sub: Amazon Nova 2 Lite (Free)
PRIMARY_MODEL = "google/gemini-2.0-flash-exp:free"
BACKUP_MODEL = "amazon/nova-2-lite-v1:free"

XAI_API_KEY = os.environ.get("XAI_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

def get_llm_client():
    if OPENROUTER_API_KEY:
        return OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
    elif XAI_API_KEY:
        return OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
    elif OPENAI_API_KEY:
        return OpenAI(api_key=OPENAI_API_KEY)
    else:
        raise ValueError("No API Key found for OpenRouter, XAI, or OpenAI")

client = get_llm_client()

def call_llm(model, messages):
    return client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"}
    )

def refine_news_batch(articles):
    """
    Refines a batch of articles using LLM with fallback.
    """
    if not articles:
        return []

    print(f"   🤖 Refining {len(articles)} articles...")

    # Prepare prompt
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
            },
            ...
        ]
    }
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": articles_text}
    ]

    def clean_json(text):
        # Remove markdown code blocks if present
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    try:
        # Try Primary Model
        print(f"      👉 Trying Primary: {PRIMARY_MODEL}...")
        response = call_llm(PRIMARY_MODEL, messages)
        content = response.choices[0].message.content
        try:
            result_json = json.loads(clean_json(content))
            return result_json.get("results", [])
        except json.JSONDecodeError:
            print(f"      ⚠️ Primary JSON Error. Raw content: {content[:100]}...")
            raise # Trigger fallback

    except Exception as e:
        print(f"      ⚠️ Primary failed: {e}")
        
        try:
            # Try Backup Model
            print(f"      👉 Trying Backup: {BACKUP_MODEL}...")
            response = call_llm(BACKUP_MODEL, messages)
            
            if not response or not response.choices:
                print("      ❌ Error: Empty response or choices")
                return []

            content = response.choices[0].message.content
            
            try:
                result_json = json.loads(clean_json(content))
                return result_json.get("results", [])
            except json.JSONDecodeError:
                print(f"      ❌ Backup JSON Error. Raw content: {content[:100]}...")
                return []
            
        except Exception as e2:
            print(f"      ❌ Backup failed: {e2}")
            return []

def run_refinement():
    print(f"🚀 REGIME ZERO REFINEMENT ENGINE [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    
    # 1. Fetch Unrefined News
    # Limit to 20 to avoid timeouts/rate limits per run
    response = supabase.table("ingest_news") \
        .select("id, title, summary") \
        .eq("is_refined", False) \
        .order("published_at", desc=True) \
        .limit(20) \
        .execute()
        
    articles = response.data
    
    if not articles:
        print("   ✅ No unrefined news found.")
        return

    # 2. Process with LLM
    refined_results = refine_news_batch(articles)
    
    # 3. Update DB
    updates_count = 0
    for res in refined_results:
        try:
            # Map back to DB columns
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

    print(f"   ✨ Refined {updates_count}/{len(articles)} articles.")

if __name__ == "__main__":
    run_refinement()
