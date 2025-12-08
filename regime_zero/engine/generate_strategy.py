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

def generate_strategy(target_date, twin_date):
    print(f"🧠 Generating Strategy for {target_date} (Twin: {twin_date})...")
    
    # 1. Load Regimes
    regimes = {}
    with open(OBJECTS_FILE, "r") as f:
        for line in f:
            try:
                r = json.loads(line)
                regimes[r['date']] = r
            except:
                pass
                
    target_r = regimes.get(target_date)
    twin_r = regimes.get(twin_date)
    
    if not target_r or not twin_r:
        print("❌ Regimes not found.")
        return

    # 2. Calculate Twin Outcomes
    outcomes = {}
    for ticker, name in [("SPY", "S&P 500"), ("GC=F", "Gold"), ("BTC-USD", "Bitcoin")]:
        change = get_price_change(ticker, twin_date, 30)
        if change is not None:
            outcomes[name] = f"{change:+.1%}"
        else:
            outcomes[name] = "N/A"
            
    print(f"📊 Twin Outcome (Next 30 Days): {outcomes}")
    
    # 3. Ask LLM
    system_prompt = "You are a Macro Hedge Fund Strategist. Your job is to devise a trading strategy based on historical analogies."
    
    user_prompt = f"""
We are currently in a market regime called "{target_r['regime_name']}".
Description: {target_r['structural_reasoning']}

This regime is structurally identical to the historical period of {twin_date} ("{twin_r['regime_name']}").

In that historical "Twin" period, the market performance over the next 30 days was:
- S&P 500: {outcomes.get('S&P 500')}
- Gold: {outcomes.get('Gold')}
- Bitcoin: {outcomes.get('Bitcoin')}

Based on this historical precedent and the current regime's characteristics, generate a **Strategic Action Plan**.

[Output Format]
## 🛡 Strategic Stance
(Aggressive / Neutral / Defensive)

## ⚔️ Action Plan
1. **Equities**: (Buy/Sell/Hold & Rationale)
2. **Gold**: (Buy/Sell/Hold & Rationale)
3. **Crypto**: (Buy/Sell/Hold & Rationale)

## ⚠️ Key Risks
(What could break this analogy?)
"""

    response = ask_llm(user_prompt, system_prompt=system_prompt)
    print("\n" + response)

if __name__ == "__main__":
    if len(sys.argv) > 2:
        generate_strategy(sys.argv[1], sys.argv[2])
    else:
        # Default test
        generate_strategy("2025-12-01", "2024-01-04")
