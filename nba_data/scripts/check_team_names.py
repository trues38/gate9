
import json
import os

def check_names():
    # Load Harvest Names
    harvest_teams = set()
    with open("data/headlines_2019_2025.jsonl", 'r') as f:
        for line in f:
            try:
                row = json.loads(line)
                harvest_teams.add(row.get('home_team'))
                harvest_teams.add(row.get('away_team'))
            except: pass
            
    # Load Quant Names
    quant_teams = set()
    try:
        with open("processed/master_chronicle_index.json", 'r') as f:
            data = json.load(f)
            for row in data:
                quant_teams.add(row.get('team'))
    except FileNotFoundError:
        print("❌ master_chronicle_index.json not found")
        return

    print("🔎 Comparing Team Names...")
    print(f"Harvest Unique: {len(harvest_teams)}")
    print(f"Quant Unique: {len(quant_teams)}")
    
    # Check mismatches
    in_harvest_not_quant = harvest_teams - quant_teams
    in_quant_not_harvest = quant_teams - harvest_teams
    
    print("\n⚠️ In Harvest (ESPN), not in Quant:")
    for t in sorted(in_harvest_not_quant):
        print(f" - {t}")

    print("\n⚠️ In Quant, not in Harvest:")
    for t in sorted(in_quant_not_harvest):
        print(f" - {t}")

if __name__ == "__main__":
    check_names()
