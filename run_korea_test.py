import json
from factor_engine import run_factor_engine
from auto_sql_engine import run_auto_sql
from utils.openrouter_client import ask_llm
from supabase import create_client
import os

# 1. Hypothesis Prompt
HYPOTHESIS_PROMPT = """
You are a Market Historian.
Analyze the current market context and Korea's specific situation.
Does this remind you of any specific historical market event or pattern?

Context:
{context}

Task:
1. If yes, name the event and explain why (e.g., "This looks like the 2011 US Downgrade shock").
2. If no, state "No specific historical match found."

Output Format:
{
  "match_found": boolean,
  "event_name": "string or null",
  "reasoning": "string",
  "sql_search_terms": ["term1", "term2"] (if match found)
}
"""

def run_test(target_date):
    print(f"🇰🇷 Running Korea Test for {target_date}...")
    
    # 1. Get Factors
    factors = run_factor_engine(target_date)
    
    # 2. Get Headlines (Top 10 for context)
    # We need to fetch headlines from DB for this date
    # Using raw SQL or client
    # We'll use a simple fetch
    from utils.supabase_client import run_sql
    headlines_sql = f"SELECT title FROM ingest_news WHERE published_at >= '{target_date}T00:00:00' AND published_at <= '{target_date}T23:59:59' LIMIT 20"
    headlines_res = run_sql(headlines_sql)
    
    print(f"DEBUG: headlines_res type: {type(headlines_res)}")
    if headlines_res and isinstance(headlines_res, list):
        print(f"DEBUG: First row: {headlines_res[0]}")
        
    headlines = []
    if headlines_res and isinstance(headlines_res, list):
        for r in headlines_res:
            if isinstance(r, dict):
                headlines.append(r.get('title', 'No Title'))
            else:
                print(f"⚠️ Unexpected row format: {r}")
    else:
        print(f"⚠️ No headlines found or error: {headlines_res}")
    
    context = {
        "date": target_date,
        "factors": factors['factors'],
        "headlines_sample": headlines
    }
    
    print("🧠 [Inference] Asking LLM for Historical Match...")
    response = ask_llm(
        prompt=json.dumps(context, indent=2),
        system_prompt=HYPOTHESIS_PROMPT,
        model="x-ai/grok-4.1-fast:free"
    )
    
    try:
        # Parse JSON from LLM (it might wrap in markdown)
        clean_resp = response.replace("```json", "").replace("```", "").strip()
        hypothesis = json.loads(clean_resp)
        print(f"💡 Hypothesis: {hypothesis['event_name']} (Match: {hypothesis['match_found']})")
        
        if hypothesis['match_found']:
            print("🔍 [Verification] Checking DB via AutoSQL...")
            # Construct context for AutoSQL based on hypothesis
            sql_context = {
                "event": hypothesis['event_name'],
                "terms": hypothesis['sql_search_terms']
            }
            sql_result = run_auto_sql(sql_context)
            
            if sql_result['results']:
                print("✅ Verified! Historical match confirmed with data.")
                print(f"   - Evidence: {len(sql_result['results'])} events found.")
            else:
                print("❌ Verification Failed. No actual data found for this hypothesis.")
                print("🔄 Switching to Standard Analysis...")
                run_standard_analysis(context)
        else:
            print("Unknown Pattern. Running Standard Analysis...")
            run_standard_analysis(context)
            
    except Exception as e:
        print(f"⚠️ Error parsing hypothesis: {e}")
        print("Raw Response:", response)

def run_standard_analysis(context):
    print("📊 [Standard Analysis] Analyzing Factors + Headlines...")
    # Simple summary prompt
    prompt = f"""
    Analyze the market situation for Korea on {context['date']}.
    
    Factors:
    {json.dumps(context['factors'], indent=2)}
    
    Headlines:
    {json.dumps(context['headlines_sample'], indent=2)}
    
    Provide a concise market summary and outlook.
    """
    summary = ask_llm(prompt, model="x-ai/grok-4.1-fast:free")
    print("\n📝 Market Report:\n")
    print(summary)

if __name__ == "__main__":
    run_test("2024-11-12")
