import os
import sys
import json
import time
from dotenv import load_dotenv
from openai import OpenAI

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load env
load_dotenv(override=True)

# Init Client
api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
base_url = "https://openrouter.ai/api/v1" if os.getenv("OPENROUTER_API_KEY") else None
client = OpenAI(api_key=api_key, base_url=base_url)

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "historical_events_100.json")

def generate_batch(start_year, end_year, count=20):
    print(f"   🤖 Generating {count} events for {start_year}-{end_year}...")
    prompt = f"""
    Generate a JSON list of {count} MAJOR global financial market events between {start_year} and {end_year}.
    Focus on events that caused significant market volatility (Crashes, Rallies, Fed Decisions, Geopolitics, Earnings Shocks).
    
    Each item must have:
    - date (YYYY-MM-DD, approximate is fine if exact day unknown, but try to be precise)
    - event_name (Short title)
    - ticker (Relevant ticker, e.g., SPY, QQQ, AAPL, NVDA, TSLA, GLD, USO, VIX, BTC)
    - description (1 sentence summary of what happened and market reaction)
    
    Output ONLY valid JSON array.
    Example:
    [
        {{
            "date": "2008-09-15",
            "event_name": "Lehman Bankruptcy",
            "ticker": "SPY",
            "description": "Lehman Brothers files for bankruptcy, triggering global financial panic and market crash."
        }}
    ]
    """
    
    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial historian."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        # Handle if wrapped in a key
        if "events" in data:
            return data["events"]
        if isinstance(data, list):
            return data
        # Try to find list in values
        for v in data.values():
            if isinstance(v, list):
                return v
        return []
    except Exception as e:
        print(f"   ❌ Error generating batch: {e}")
        return []

def main():
    print("🚀 Generating 100 Historical Events...")
    
    eras = [
        (2000, 2005),
        (2006, 2010),
        (2011, 2015),
        (2016, 2020),
        (2021, 2024)
    ]
    
    all_events = []
    
    for start, end in eras:
        events = generate_batch(start, end, 20)
        if events:
            print(f"   ✅ Got {len(events)} events.")
            all_events.extend(events)
        else:
            print("   ⚠️ No events generated for this batch.")
        time.sleep(1) # Rate limit safety
        
    # Save
    print(f"\n💾 Saving {len(all_events)} events to {OUTPUT_FILE}...")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_events, f, indent=2)
        
    print("✅ Done.")

if __name__ == "__main__":
    main()
