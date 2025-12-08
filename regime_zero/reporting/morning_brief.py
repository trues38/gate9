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

def generate_morning_brief(target_date):
    print(f"🌅 Generating Morning Brief for {target_date}...")
    
    # 1. Load Candidates (Assumes find_historical_twin.py was run for target_date)
    if not os.path.exists(CANDIDATES_FILE):
        print("❌ No candidates file found. Run find_historical_twin.py first.")
        return
        
    with open(CANDIDATES_FILE, "r") as f:
        candidates = json.load(f)
        
    # Take Top 5
    top_5 = candidates[:5]
    print(f"📊 Analyzing Top 5 Historical Twins...")

    # 2. Calculate Outcomes
    results = []
    spy_wins = 0
    gold_wins = 0
    btc_wins = 0
    
    for cand in top_5:
        date = cand['date']
        spy_chg = get_price_change("SPY", date, 30)
        gold_chg = get_price_change("GC=F", date, 30)
        btc_chg = get_price_change("BTC-USD", date, 30)
        
        res = {
            "date": date,
            "name": cand['name'],
            "score": cand['score'],
            "reasoning": cand['reasoning'],
            "SPY_30d": f"{spy_chg:+.1%}" if spy_chg is not None else "N/A",
            "Gold_30d": f"{gold_chg:+.1%}" if gold_chg is not None else "N/A",
            "BTC_30d": f"{btc_chg:+.1%}" if btc_chg is not None else "N/A"
        }
        results.append(res)
        
        if spy_chg and spy_chg > 0: spy_wins += 1
        if gold_chg and gold_chg > 0: gold_wins += 1
        if btc_chg and btc_chg > 0: btc_wins += 1

    # 3. Prompt Qwen for Long-Form Report
    system_prompt = """You are the Chief Investment Officer (CIO) of 'Regime Zero', a quantitative macro hedge fund. 
Your job is to write a daily 'Morning Brief' for institutional clients.
Your writing style is:
- **Authoritative & Professional**: Use precise financial terminology.
- **Data-Driven**: Always back claims with the provided probabilities and win rates.
- **Narrative-Rich**: Weave the historical analogies into a compelling story.
- **Actionable**: Give clear Buy/Sell/Hold directives with confidence levels.
- **Lengthy & Detailed**: Do not be brief. Explain the 'Why' in depth.
"""
    
    user_prompt = f"""
**REPORT DATE**: {datetime.now().strftime("%Y-%m-%d")}
**ANALYSIS TARGET**: {target_date} (Yesterday's Close)

**CONTEXT**:
Our proprietary 'Historical Twin Engine' has identified the 5 most similar market regimes in history to yesterday's close.
We use these to project the next 30 days.

**THE DATA (Top 5 Twins)**:
{json.dumps(results, indent=2)}

**PROBABILITY MATRIX (30-Day Forward Win Rates)**:
- **S&P 500**: {spy_wins}/5 ({spy_wins/5:.0%})
- **Gold**: {gold_wins}/5 ({gold_wins/5:.0%})
- **Bitcoin**: {btc_wins}/5 ({btc_wins/5:.0%})

**INSTRUCTIONS**:
Write a comprehensive "Morning Brief" report. Structure it as follows:

1.  **Executive Summary**: A high-level overview of the current regime and the core strategic call.
2.  **The Regime Definition**: Define the current market vibe based on the Top 5 twins (e.g., "We are in a 'Reflationary Euphoria' phase...").
3.  **Historical Forensics (The Twins)**:
    -   Deep dive into the #1 Match ({results[0]['date']}). Why is it the perfect twin? What happened then?
    -   Briefly discuss the other matches to show the consensus pattern.
4.  **The Quantitative Edge**:
    -   Analyze the Win Rates. Is there a statistical edge? (e.g., "With an 80% historical win rate, Equities show a clear bias...")
    -   Discuss any divergences (e.g., Twin #1 says Buy, but Consensus says Sell).
5.  **Strategic Action Plan (The "Alpha")**:
    -   **Equities**: Specific stance (Overweight/Neutral/Underweight).
    -   **Gold**: Specific stance.
    -   **Crypto**: Specific stance.
    -   **Risk Factors**: What could go wrong? (e.g., "If yields spike > 4.5%...")
6.  **Closing Thought**: A philosophical or psychological observation about the current market sentiment.

Make it long, insightful, and worthy of a $10,000/month subscription.
"""

    try:
        # Use DashScope Qwen
        qwen_key = os.getenv("MAIN_LLM_KEY")
        qwen_url = os.getenv("MAIN_LLM_URL")
        qwen_model = os.getenv("MAIN_LLM_MODEL")
        
        if qwen_key and qwen_url:
            full_url = qwen_url.rstrip("/") + "/chat/completions"
            print(f"🚀 Generating Report with {qwen_model}...")
            response = ask_llm(user_prompt, system_prompt=system_prompt, model=qwen_model, api_key=qwen_key, base_url=full_url)
            
            if response:
                # Save to file
                filename = f"Morning_Brief_{target_date}.md"
                with open(filename, "w") as f:
                    f.write(response)
                print(f"\n✅ Report saved to {filename}")
                print(response)
            else:
                print("❌ Failed to get response from LLM.")
        else:
             print("❌ Missing DashScope Credentials.")
             
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = "2025-12-01"
    generate_morning_brief(target)
