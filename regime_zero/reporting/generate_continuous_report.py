import sys
import os
import json
import glob
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.openrouter_client import ask_llm
from regime_zero.engine.find_historical_twin import find_twin

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

REPORTS_DIR = "regime_zero/reports"
CANDIDATES_FILE = "regime_zero/engine/twin_candidates.json"

def get_price_change(ticker, start_date, days=30):
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = start_dt + timedelta(days=days)
        end_date = end_dt.strftime("%Y-%m-%d")
        
        res = supabase.table("ingest_prices").select("date, close").eq("ticker", ticker).gte("date", start_date).lte("date", end_date).order("date").execute()
        data = res.data
        
        if not data or len(data) < 2:
            return None
            
        start_price = data[0]['close']
        end_price = data[-1]['close']
        
        return (end_price - start_price) / start_price
    except Exception as e:
        return None

def get_past_context(target_date, report_type="daily"):
    """
    Retrieves the most recent past report to provide context.
    """
    target_dt = datetime.strptime(target_date, "%Y-%m-%d")
    
    if report_type == "daily":
        # Look for yesterday's report
        prev_date = (target_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        path = os.path.join(REPORTS_DIR, "daily", f"{prev_date}.md")
        if os.path.exists(path):
            with open(path, "r") as f:
                return f"**YESTERDAY'S REPORT ({prev_date})**:\n" + f.read()[:2000] + "..." # Truncate
    
    return "No previous report context available."

def generate_report(target_date, report_type="daily"):
    print(f"📝 Generating {report_type.upper()} Report for {target_date}...")
    
    # 0. Ensure Candidates Exist (Run Twin Search)
    # We run this silently to populate the json
    try:
        # Redirect stdout to suppress output
        # sys.stdout = open(os.devnull, 'w') 
        find_twin(target_date)
        # sys.stdout = sys.__stdout__
    except Exception as e:
        print(f"⚠️ Twin Search Warning: {e}")

    # 1. Load Candidates
    if not os.path.exists(CANDIDATES_FILE):
        print("❌ No candidates file found.")
        return
        
    with open(CANDIDATES_FILE, "r") as f:
        candidates = json.load(f)
        
    top_5 = candidates[:5]

    # 2. Calculate Outcomes
    results = []
    spy_wins = 0
    gold_wins = 0
    
    for cand in top_5:
        date = cand['date']
        spy_chg = get_price_change("SPY", date, 30)
        gold_chg = get_price_change("GC=F", date, 30)
        
        res = {
            "date": date,
            "name": cand['name'],
            "score": cand['score'],
            "reasoning": cand['reasoning'],
            "SPY_30d": f"{spy_chg:+.1%}" if spy_chg is not None else "N/A",
            "Gold_30d": f"{gold_chg:+.1%}" if gold_chg is not None else "N/A"
        }
        results.append(res)
        
        if spy_chg and spy_chg > 0: spy_wins += 1
        if gold_chg and gold_chg > 0: gold_wins += 1

    # 3. Get Context
    context = get_past_context(target_date, report_type)

    # 4. Prompt
    system_prompt = """You are the Chief Investment Officer (CIO) of 'Regime Zero'.
Your goal is to write a **Continuity-Based Investment Report**.

**CRITICAL RULES**:
1. **NO VOLATILE NUMBERS**: Do NOT quote specific values for volatile indices like VIX, RSI, or P/E ratios. These change too fast and confuse the reader.
   - ❌ BAD: "The VIX is at 12.5."
   - ✅ GOOD: "Volatility is compressing to historically low levels."
   - ✅ GOOD: "Valuations remain elevated relative to historical norms."
   - (Fixed fundamental data like 'GDP Growth' or 'Interest Rates' are okay to mention if necessary, but prefer trends).

2. **MAINTAIN CONTINUITY**: You will be provided with the *Previous Report*. You MUST reference it to show a coherent narrative evolution.
   - "As noted in yesterday's brief..."
   - "Continuing the trend identified last week..."

3. **PROBABILITY-DRIVEN**: Base your strategy on the Win Rates of the Historical Twins.
"""
    
    user_prompt = f"""
**REPORT DATE**: {target_date}
**TYPE**: {report_type.upper()}

**PREVIOUS CONTEXT**:
{context}

**CURRENT REGIME ANALYSIS (Top 5 Historical Twins)**:
{json.dumps(results, indent=2)}

**WIN RATES (30-Day Forward)**:
- S&P 500: {spy_wins}/5 ({spy_wins/5:.0%})
- Gold: {gold_wins}/5 ({gold_wins/5:.0%})

**INSTRUCTIONS**:
Write the {report_type} report.
1. **Regime Update**: How has the regime evolved since the last report?
2. **The Twin Signal**: Deep dive into the #1 match ({results[0]['date']}).
3. **Strategic Verdict**: Clear Buy/Sell/Hold based on the {spy_wins/5:.0%} / {gold_wins/5:.0%} probabilities.
4. **Closing**: A forward-looking statement.

Remember: NO VOLATILE NUMBERS. Focus on Direction & Flow.
"""

    try:
        # Use DashScope Qwen
        qwen_key = os.getenv("MAIN_LLM_KEY")
        qwen_url = os.getenv("MAIN_LLM_URL")
        qwen_model = os.getenv("MAIN_LLM_MODEL")
        
        if qwen_key and qwen_url:
            full_url = qwen_url.rstrip("/") + "/chat/completions"
            response = ask_llm(user_prompt, system_prompt=system_prompt, model=qwen_model, api_key=qwen_key, base_url=full_url)
            
            if response:
                # Save
                save_path = os.path.join(REPORTS_DIR, report_type, f"{target_date}.md")
                with open(save_path, "w") as f:
                    f.write(response)
                print(f"✅ Saved to {save_path}")
            else:
                print("❌ LLM No Response")
        else:
             print("❌ Missing Credentials")
             
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = datetime.now().strftime("%Y-%m-%d")
        
    generate_report(target)
