import os
import json
import time
import asyncio
import httpx
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
MODEL_NAME = "openai/gpt-4o"  # Or "anthropic/claude-3.5-sonnet"
EMBEDDING_MODEL = "text-embedding-3-large"

# Initialize Supabase
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize HTTP Client for OpenRouter
headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "https://github.com/gate9/g9-rag",
    "X-Title": "G9 Strategy Engine",
    "Content-Type": "application/json"
}

async def get_embedding(text: str, retries=3) -> List[float]:
    """Generates embedding using OpenRouter (or OpenAI compatible endpoint)."""
    for attempt in range(retries):
        try:
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
        except Exception as e:
            if attempt == retries - 1:
                print(f"❌ Embedding failed after {retries} attempts: {e}")
                raise
            time.sleep(2 ** attempt)
    return []

async def generate_strategies_for_pattern(pattern: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generates 6 strategies for a given pattern using LLM."""
    
    prompt = f"""
    You are the MacroMind Strategy Engine.
    Generate 6 distinct investment strategies based on the following market pattern.
    
    # Pattern Context
    ID: {pattern['pattern_id']}
    Category: {pattern['category']}
    Title: {pattern['title']}
    Core Logic: {pattern['core']}
    Full Text Summary: {pattern['full_text'][:1000]}... (truncated)

    # Required Strategies (6 Types)
    1. Conservative Strategy (Preservation focus)
    2. Moderate Strategy (Balanced growth)
    3. Aggressive Strategy (High alpha focus)
    4. Hedge Strategy (Protection against downside)
    5. Risk Signals (Early warning signs)
    6. Playbook (Step-by-step execution roadmap)

    # Output Format
    Return a JSON object with a key "strategies" containing a list of 6 objects.
    Each object must have:
    - "type": One of ["CONSERVATIVE", "MODERATE", "AGGRESSIVE", "HEDGE", "RISKS", "PLAYBOOK"]
    - "title": A descriptive title for the strategy
    - "description": Detailed description (2-3 sentences)
    - "rationale": Why this strategy works for this pattern
    - "risk": Specific risks associated with this strategy
    - "checklist": A list of 3-5 actionable items
    
    Ensure the content is high-quality, actionable, and specific to the pattern.
    """

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a sophisticated macro investment strategist."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60.0
        )
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        try:
            parsed = json.loads(content)
            return parsed['strategies']
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ JSON Parsing failed for {pattern['pattern_id']}: {e}")
            return []

async def process_pattern(pattern: Dict[str, Any]):
    """Process a single pattern: Generate, Embed, Upsert."""
    print(f"🔄 Processing {pattern['pattern_id']}...")
    
    try:
        strategies = await generate_strategies_for_pattern(pattern)
        if not strategies:
            print(f"⚠️ No strategies generated for {pattern['pattern_id']}")
            return

        for strat in strategies:
            strategy_type = strat['type'].upper()
            strategy_id = f"{pattern['pattern_id']}-{strategy_type}"
            
            # Construct text for embedding
            embed_text = f"{strat['title']} {strat['description']} {strat['rationale']} {strat['risk']} {' '.join(strat['checklist'])}"
            
            # Generate embedding
            embedding = await get_embedding(embed_text)
            
            # Prepare record
            record = {
                "strategy_id": strategy_id,
                "pattern_id": pattern['pattern_id'],
                "category": pattern['category'],
                "title": strat['title'],
                "description": strat['description'],
                "rationale": strat['rationale'],
                "risk": strat['risk'],
                "checklist": strat['checklist'],
                "embedding": embedding
            }
            
            # Upsert to Supabase
            supabase.table("macro_strategies").upsert(record).execute()
            print(f"   ✅ Upserted {strategy_id}")
            
    except Exception as e:
        print(f"❌ Error processing {pattern['pattern_id']}: {e}")

async def main():
    print("🚀 Starting Strategy RAG Pipeline...")
    
    # 1. Fetch Patterns
    response = supabase.table("macro_patterns").select("*").execute()
    patterns = response.data
    print(f"📂 Loaded {len(patterns)} patterns from Supabase.")
    
    # 2. Process each pattern
    # We process sequentially to avoid rate limits, or maybe chunks of 5
    for pattern in patterns:
        await process_pattern(pattern)
        # time.sleep(1) # Optional delay

    print("✨ Strategy Generation Complete.")

if __name__ == "__main__":
    asyncio.run(main())
