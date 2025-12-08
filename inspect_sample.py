import json
import sys

INPUT_FILE = "regime_zero/data/regime_objects.jsonl"

def inspect():
    targets = ["1975-05-01", "1985-09-22", "1997-07-02"]
    found = 0
    
    with open(INPUT_FILE, "r") as f:
        for line in f:
            try:
                r = json.loads(line)
                if r['date'] in targets:
                    print(f"\n📅 DATE: {r['date']}")
                    print(f"🏷 NAME: {r['regime_name']}")
                    print(f"🌊 VIBE: {r['historical_vibe']}")
                    print(f"📝 REASON: {r['structural_reasoning'][:300]}...")
                    print(f"🔑 SIG: {r['signature']}")
                    found += 1
            except:
                pass
            if found >= len(targets):
                break

if __name__ == "__main__":
    inspect()
