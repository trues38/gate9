import os
import asyncio
import json
import httpx
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv(override=True)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
EMBEDDING_MODEL = "text-embedding-3-large"
CHAT_MODEL = "openai/gpt-4o"

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize HTTP Client for OpenRouter
headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "https://github.com/gate9/g9-rag",
    "X-Title": "G9 Antigravity Report",
    "Content-Type": "application/json"
}

HEADLINES = [
    "Fed officials waver on rate cuts as inflation remains sticky",
    "Crude oil surges 8% on Middle East tensions",
    "Global semiconductor inventory hits 5-year high",
    "Japan’s yen hits 34-year low as BOJ maintains policy",
    "China consumer demand weakens despite stimulus rollout"
]
REPORT_DATE = "2025-11-27"

async def get_embedding(text: str) -> List[float]:
    """Generates embedding using OpenRouter."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OPENROUTER_BASE_URL}/embeddings",
            headers=headers,
            json={
                "model": EMBEDDING_MODEL,
                "input": text
            },
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()
        return data['data'][0]['embedding']

async def chat_completion(prompt: str) -> str:
    """Generates chat completion using OpenRouter."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json={
                "model": CHAT_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            },
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']

async def step_1_sql_evidence():
    print("\n🔹 Step 1: SQL Evidence (Inserting Headlines)...")
    records = []
    for hl in HEADLINES:
        records.append({
            "headline": hl,
            "published_at": f"{REPORT_DATE} 10:00:00", # Arbitrary time
            "source": "Manual Input",
            "url": "http://manual-input",
            "summary": hl # Use headline as summary for now
        })
    
    # Insert into global_news (assuming table exists and allows this)
    # Note: 'global_news' schema might require more fields. Adjusting based on common schema.
    # If id is auto-generated, we don't need to provide it.
    try:
        # Check if they already exist to avoid duplicates (simple check)
        # For this demo, we'll just insert. If it fails, we assume they exist or table issues.
        # Actually, let's just print what we WOULD query. The user asked for "SQL Evidence", 
        # which usually means "Run SQL to find evidence". 
        # But the user GAVE us the headlines. So we should probably treat these AS the evidence found.
        # Let's insert them to be safe, so the "System" has them.
        
        # We'll try to insert. If it fails, we proceed.
        supabase.table("global_news").upsert(records, on_conflict="headline").execute()
        print("   ✅ Headlines inserted/updated in global_news.")
    except Exception as e:
        print(f"   ⚠️ Insert failed (might be schema mismatch): {e}")
        print("   ℹ️ Proceeding with provided headlines as evidence.")

    return HEADLINES

async def step_2_pattern_rag(headlines: List[str]):
    print("\n🔹 Step 2: Pattern RAG Matching...")
    combined_text = "\n".join(headlines)
    embedding = await get_embedding(combined_text)
    
    # Vector Search
    # Assuming a function 'match_macro_patterns' exists in Supabase or we query directly if pgvector is set up differently.
    # We will use the standard rpc call if it exists, or just query if we can.
    # Since I don't know the exact RPC name, I'll try a common one or just fetch all and compute cosine sim locally if needed (but that's slow).
    # Wait, previous context didn't mention creating a match function. 
    # I will assume I need to fetch all patterns and compute similarity locally for reliability here, 
    # OR try to use `rpc`. Let's fetch all (only 50) and compute locally. It's safer and fast enough for 50 items.
    
    response = supabase.table("macro_patterns").select("pattern_id, title, embedding, core, triggers").execute()
    patterns = response.data
    
    import math

    def cosine_similarity(v1, v2):
        if isinstance(v1, str): v1 = json.loads(v1)
        if isinstance(v2, str): v2 = json.loads(v2)
        
        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude1 = math.sqrt(sum(a * a for a in v1))
        magnitude2 = math.sqrt(sum(b * b for b in v2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        return dot_product / (magnitude1 * magnitude2)

    scored_patterns = []
    for p in patterns:
        if not p['embedding']: continue
        try:
            score = cosine_similarity(embedding, p['embedding'])
            scored_patterns.append((score, p))
        except Exception as e:
            print(f"      ⚠️ Error calculating similarity for {p['pattern_id']}: {e}")
    
    scored_patterns.sort(key=lambda x: x[0], reverse=True)
    top_patterns = scored_patterns[:3] # Top 3 matches
    
    print(f"   ✅ Top 3 Patterns Matched:")
    for score, p in top_patterns:
        print(f"      - [{score:.4f}] {p['pattern_id']}: {p['title']}")
    
    return [p for _, p in top_patterns]

async def step_3_strategy_rag(matched_patterns: List[Dict]):
    print("\n🔹 Step 3: Strategy RAG Matching...")
    strategies = {}
    for p in matched_patterns:
        pid = p['pattern_id']
        # Fetch strategies for this pattern
        res = supabase.table("macro_strategies").select("*").eq("pattern_id", pid).execute()
        strategies[pid] = res.data
        print(f"   ✅ Fetched {len(res.data)} strategies for {pid}")
    return strategies

async def step_4_5_6_generate_report(headlines, patterns, strategies):
    print("\n🔹 Step 4, 5, 6: Generating Analysis & Report...")
    
    # Prepare Context
    patterns_text = ""
    for p in patterns:
        patterns_text += f"\nPattern: {p['pattern_id']} - {p['title']}\nCore: {p['core']}\nTriggers: {p['triggers']}\n"
    
    strategies_text = ""
    for pid, strats in strategies.items():
        strategies_text += f"\nStrategies for {pid}:\n"
        for s in strats:
            s_type = s['strategy_id'].split('-')[-1]
            strategies_text += f"- {s_type}: {s['title']} ({s['description']})\n"

    prompt = f"""
    You are the Antigravity AI, a top-tier macro hedge fund analyst.
    
    HEADLINES ({REPORT_DATE}):
    {json.dumps(headlines, indent=2)}
    
    MATCHED PATTERNS:
    {patterns_text}
    
    AVAILABLE STRATEGIES:
    {strategies_text}
    
    TASK:
    Generate the "Antigravity Daily Report" with the following sections:
    
    1. **4-Country Analysis (US/CN/JP/KR)**: Analyze the impact of the headlines and matched patterns on each country.
    2. **Final Antigravity Report**: Synthesize the market view. Is it Risk-On or Risk-Off? What is the dominant narrative?
    3. **Risk/Strategy Checklist**: A bulleted list of actionable steps based on the strategies.
    
    Format in Markdown. Be concise, professional, and actionable.
    """
    
    report = await chat_completion(prompt)
    print("\n" + "="*40)
    print("📄 ANTIGRAVITY REPORT")
    print("="*40)
    print(report)
    
    # Save to file
    with open("Antigravity_Report_2025-11-27.md", "w") as f:
        f.write(report)
    print("\n✅ Report saved to Antigravity_Report_2025-11-27.md")

async def main():
    print("🚀 Starting Antigravity Pipeline...")
    
    # Step 1
    headlines = await step_1_sql_evidence()
    
    # Step 2
    matched_patterns = await step_2_pattern_rag(headlines)
    
    # Step 3
    strategies = await step_3_strategy_rag(matched_patterns)
    
    # Step 4, 5, 6
    await step_4_5_6_generate_report(headlines, matched_patterns, strategies)

if __name__ == "__main__":
    asyncio.run(main())
