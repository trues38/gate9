import os
import sys
import json
from dotenv import load_dotenv

# Add project root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from g9_macro_factory.config import get_supabase_client
from utils.embedding import get_embedding_sync

# Load env
load_dotenv(override=True)

# Extended Data Structure
FAILED_CASES = [
    {
        "event_name": "Lehman Brothers Bankruptcy",
        "pattern_id": "P-009",
        "regime": "INFLATION_FEAR",
        "historical_context": "2008-09-15: Lehman Brothers filed for Chapter 11 bankruptcy after failing to find a buyer, triggering a global financial panic.",
        "lesson_summary": "Major bank failures often trigger a 'Sell the Rumor, Buy the News' dynamic or eventual Fed intervention, making panic selling at the bottom dangerous.",
        "avoid_rule": "Do not panic sell immediately on major bank failure news if the market has already priced in significant fear.",
        "past_outcome": "The market initially crashed but saw significant volatility and eventual recovery as the Fed stepped in with liquidity (TARP/QE).",
        "recommended_action": "HOLD_CASH and wait for Fed intervention details. Do not short into the hole.",
        "text": "Lehman Brothers Bankruptcy. The investment bank files for Chapter 11 protection, citing massive losses in subprime mortgages."
    },
    {
        "event_name": "GameStop / AMC Mania",
        "pattern_id": "P-048",
        "regime": "LIQUIDITY_CRISIS",
        "historical_context": "2021-01: Retail traders on Reddit coordinated a massive short squeeze on GME and AMC, defying fundamental logic.",
        "lesson_summary": "In a liquidity-fueled mania, fundamentals do not matter. Crowd psychology drives prices to irrational levels.",
        "avoid_rule": "NEVER short a momentum/meme stock during a squeeze, regardless of how poor the fundamentals are.",
        "past_outcome": "Short sellers suffered catastrophic losses as stocks rose 1000%+ in days. Prices eventually collapsed but stayed elevated for long.",
        "recommended_action": "HOLD_CASH or BUY (Speculative). Strictly AVOID SELLING/SHORTING.",
        "text": "GameStop Short Squeeze Peak. Retail investors on Reddit drive GME stock to record highs, forcing hedge funds to cover shorts."
    },
    {
        "event_name": "Russia-Ukraine Invasion",
        "pattern_id": "P-028",
        "regime": "LIQUIDITY_CRISIS",
        "historical_context": "2022-02-24: Russia launched a full-scale invasion of Ukraine. Markets had been falling in anticipation.",
        "lesson_summary": "Geopolitical events often follow 'Sell the Rumor, Buy the Fact'. The actual invasion day marked a local bottom.",
        "avoid_rule": "Do not sell on the day of the actual invasion/war start if the market has been dropping beforehand.",
        "past_outcome": "Markets rallied on the day of the invasion as uncertainty was removed ('Bad news is out').",
        "recommended_action": "BUY_THE_DIP or HOLD. Expect a relief rally.",
        "text": "Russia Invades Ukraine. Russian forces launch a full-scale invasion of Ukraine, triggering global condemnation and sanctions."
    },
    {
        "event_name": "CPI 9.1% Peak Inflation",
        "pattern_id": "P-005",
        "regime": "INFLATION_FEAR",
        "historical_context": "2022-07-13: US CPI hit 9.1%, a 40-year high. Investors feared aggressive Fed hikes.",
        "lesson_summary": "Extreme inflation readings often mark the 'Peak Inflation' point, leading to hopes of a Fed pivot.",
        "avoid_rule": "Do not sell on extreme inflation data (>9%) as it likely signals the peak.",
        "past_outcome": "The market rallied as investors bet that inflation had peaked and the Fed would eventually pause.",
        "recommended_action": "BUY or HOLD. Look for signs of 'Peak Inflation' narrative.",
        "text": "US CPI Hits 9.1%. Inflation reaches a 40-year high, driven by energy and food prices, pressuring the Fed to hike rates."
    },
    {
        "event_name": "SVB Bank Run",
        "pattern_id": "P-012",
        "regime": "NEUTRAL",
        "historical_context": "2023-03-10: Silicon Valley Bank collapsed due to a run on deposits, raising fears of systemic contagion.",
        "lesson_summary": "Systemic banking risks force the Fed to provide liquidity (BTFP), effectively restarting QE.",
        "avoid_rule": "Do not sell on bank run news. Expect immediate liquidity support from Central Banks.",
        "past_outcome": "The Fed introduced the BTFP facility, guaranteeing deposits. Tech stocks (QQQ) rallied significantly.",
        "recommended_action": "BUY (Tech/Growth) or HOLD. Fed liquidity is bullish for risk assets.",
        "text": "SVB Bank Run. Silicon Valley Bank collapses after a run on deposits, raising fears of a broader banking crisis."
    }
]

def seed_meta_rag():
    print("🌱 Seeding Meta-RAG with Expanded Rich Metadata...")
    supabase = get_supabase_client()
    
    # Optional: Clear existing data if possible? 
    # We can't easily delete without ID. We'll just append (or user can clear DB manually).
    # For now, we assume we are appending or overwriting if we could.
    
    for case in FAILED_CASES:
        print(f"   Processing: {case['event_name']}...")
        
        # 1. Generate Embedding
        embedding = get_embedding_sync(case['text'])
        
        # 2. Pack Rich Data into JSON for 'fail_reason' column
        # This allows us to store structured data without altering table schema
        rich_data = {
            "event_name": case['event_name'],
            "historical_context": case['historical_context'],
            "lesson_summary": case['lesson_summary'],
            "past_outcome": case['past_outcome'],
            "recommended_action": case['recommended_action']
        }
        packed_reason = json.dumps(rich_data)
        
        # 3. Insert into DB
        data = {
            "origin_pattern_id": case['pattern_id'],
            "fail_reason": packed_reason, # Storing JSON string here
            "correction_rule": case['avoid_rule'],
            "regime_context": case['regime'],
            "embedding": embedding
        }
        
        try:
            supabase.table("g9_meta_rag").insert(data).execute()
            print(f"   ✅ Inserted: {case['event_name']}")
        except Exception as e:
            print(f"   ❌ Failed to insert {case['event_name']}: {e}")

    print("\n✅ Seeding Complete.")

if __name__ == "__main__":
    seed_meta_rag()
