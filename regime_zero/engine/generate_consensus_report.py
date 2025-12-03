import sys
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.openrouter_client import ask_llm

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

CANDIDATES_FILE = "regime_zero/engine/twin_candidates.json"
OBJECTS_FILE = "regime_zero/data/regime_objects.jsonl"

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

def generate_consensus():
    print(f"🧠 Generating Consensus Strategy...")
    
    # 1. Load Candidates
    if not os.path.exists(CANDIDATES_FILE):
        print("❌ No candidates file found.")
        return
        
    with open(CANDIDATES_FILE, "r") as f:
        candidates = json.load(f)
        
    # Filter for > 90% similarity (or take top 5 if fewer)
    high_confidence = [c for c in candidates if c['score'] > 0.90]
    if len(high_confidence) < 3:
        high_confidence = candidates[:5]
        
    print(f"📊 Analyzing {len(high_confidence)} High-Confidence Twins (>90%)...")

    # 2. Calculate Outcomes for Each
    results = []
    spy_wins = 0
    gold_wins = 0
    
    for cand in high_confidence:
        date = cand['date']
        spy_chg = get_price_change("SPY", date, 30)
        gold_chg = get_price_change("GC=F", date, 30)
        
        res = {
            "date": date,
            "name": cand['name'],
            "score": cand['score'],
            "SPY_30d": f"{spy_chg:+.1%}" if spy_chg is not None else "N/A",
            "Gold_30d": f"{gold_chg:+.1%}" if gold_chg is not None else "N/A"
        }
        results.append(res)
        
        if spy_chg and spy_chg > 0: spy_wins += 1
        if gold_chg and gold_chg > 0: gold_wins += 1

    # 3. Ask LLM
    system_prompt = "You are a Macro Hedge Fund Strategist. Synthesize a consensus strategy from multiple historical analogies."
    
    user_prompt = f"""
We are analyzing the current market regime.
We have identified {len(high_confidence)} historical periods with >90% similarity.

Here are their subsequent 30-day performances:
{json.dumps(results, indent=2)}

Win Rates (Positive Return Probability):
- S&P 500: {spy_wins}/{len(high_confidence)} ({spy_wins/len(high_confidence):.0%})
- Gold: {gold_wins}/{len(high_confidence)} ({gold_wins/len(high_confidence):.0%})

Based on this data:
1. **Analyze the #1 Match** ({results[0]['date']}, Score {results[0]['score']:.1%}) in depth.
2. **Analyze the Consensus**: What is the common thread across all these periods?
3. **Formulate a Strategy**:
    - If the #1 match and the Consensus agree -> Strong Conviction.
    - If they disagree -> nuanced approach.

[Output Format]
## 🥇 The Twin Strategy (Based on {results[0]['date']})
(Specific action plan based on the single best match)

## ⚖️ The Consensus View (Based on {len(high_confidence)} Cases)
(Common patterns. e.g., "In 80% of similar cases, Equities rallied...")

## 🚀 Final Verdict & Trade Setup
(Combine both into a final executable strategy)
"""

    try:
        # User requested Qwen 14B via API (DashScope)
        qwen_key = os.getenv("MAIN_LLM_KEY")
        qwen_url = os.getenv("MAIN_LLM_URL")
        qwen_model = os.getenv("MAIN_LLM_MODEL")
        
        if qwen_key and qwen_url:
            print(f"🚀 Using Custom API: {qwen_model}")
            full_url = qwen_url.rstrip("/") + "/chat/completions"
            response = ask_llm(user_prompt, system_prompt=system_prompt, model=qwen_model, api_key=qwen_key, base_url=full_url)
        else:
            # Fallback to OpenRouter
            response = ask_llm(user_prompt, system_prompt=system_prompt, model="qwen/qwen-2.5-14b-instruct")
    except:
        response = None
        
    if response:
        print("\n" + response)
    else:
        print("\n⚠️ API Rate Limit Reached. Generating Fallback Report based on Hard Data...")
        generate_fallback_report(results, spy_wins, gold_wins, len(high_confidence))

def generate_fallback_report(results, spy_wins, gold_wins, total):
    spy_rate = spy_wins / total
    gold_rate = gold_wins / total
    
    top_match = results[0]
    
    print(f"""
## 🥇 The Twin Strategy (Based on {top_match['date']})
**Context**: The #1 match ({top_match['name']}) saw SPY move **{top_match['SPY_30d']}** and Gold move **{top_match['Gold_30d']}**.
**Action**: Follow the trend of the primary twin. If SPY was positive, maintain long exposure. If Gold was negative, reduce hedges.

## ⚖️ The Consensus View (Based on {total} Cases)
**Win Rates**:
- **S&P 500**: {spy_rate:.0%} ({spy_wins}/{total} wins)
- **Gold**: {gold_rate:.0%} ({gold_wins}/{total} wins)

**Analysis**:
The consensus across {total} high-similarity periods (>90%) suggests a **{'Bullish' if spy_rate > 0.5 else 'Bearish'}** bias for Equities and a **{'Bullish' if gold_rate > 0.5 else 'Bearish'}** bias for Gold.
{'The consensus strongly supports the #1 Twin.' if (spy_rate > 0.5 and float(top_match['SPY_30d'].strip('%')) > 0) else 'The consensus diverges from the #1 Twin, suggesting caution.'}

## 🚀 Final Verdict & Trade Setup
1. **Equities**: **{'AGGRESSIVE BUY' if spy_rate >= 0.8 else 'BUY' if spy_rate >= 0.6 else 'NEUTRAL'}**. The historical probability of a rally is {spy_rate:.0%}.
2. **Gold**: **{'BUY' if gold_rate >= 0.6 else 'SELL'}**. 
3. **Risk Management**: Set stops based on the volatility observed in {top_match['date']}.
""")

if __name__ == "__main__":
    generate_consensus()
