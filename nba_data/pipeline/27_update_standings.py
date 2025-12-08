
import requests
import json
import os

URL = "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"

def update_standings():
    print("🚀 Fetching Live NBA Standings from ESPN...")
    try:
        resp = requests.get(URL, timeout=10)
        data = resp.json()
    except Exception as e:
        print(f"❌ API Failed: {e}")
        return

    # Map ESPN Team ID -> Record/Streak
    team_stats = {}
    
    # Structure: children -> groups -> standings -> entries -> team
    if 'children' in data:
        for conf in data['children']:
            for div in conf.get('children', []): # Sometimes structure varies, usually children[0] is conf
                # Wait, NBA structure is often strictly tiered.
                # Let's verify commonly known ESPN structure or just recursive search.
                # Actually, iterate 'standings' entries if accessible directly?
                # The V2 API usually has `children` as Conferences.
                pass
    
    # Flatten loop
    entries = []
    
    # Recursive fetcher
    def extract_entries(node):
        if 'standings' in node and 'entries' in node['standings']:
            entries.extend(node['standings']['entries'])
        if 'children' in node:
            for child in node['children']:
                extract_entries(child)
                
    extract_entries(data)
    
    print(f"📋 Found {len(entries)} team entries.")
    
    for entry in entries:
        team_id = int(entry['team']['id'])
        stats = entry.get('stats', [])
        
        # Parse Stats
        wins = 0
        losses = 0
        streak = 0
        l10 = 0 # Wins in last 10
        
        for s in stats:
            if s['name'] == 'wins': wins = s['value']
            elif s['name'] == 'losses': losses = s['value']
            elif s['name'] == 'streak': streak = s['value'] # e.g. 1
            # L10 might be in different breakdown, ESPN V2 sometimes hides it.
            # We'll use streak and W% for momentum.
            
        team_stats[team_id] = {
            "wins": wins,
            "losses": losses,
            "streak": streak,
            "pct": wins / max(1, wins+losses)
        }
        
    # Update team_regimes.json
    regime_path = "nba_data/regimes/team_regimes.json"
    with open(regime_path, "r") as f:
        regimes = json.load(f)
        
    updates = 0
    for r in regimes:
        tid = r['team_id']
        if tid in team_stats:
            s = team_stats[tid]
            
            # Simple Logic for Regime Label
            pct = s['pct']
            strk = s['streak']
            
            label = "Balanced"
            if pct > 0.65: label = "Juggernaut"
            elif pct < 0.35: label = "Slumping"
            elif strk >= 3: label = "Surging"
            elif strk <= -3: label = "Freefall"
            
            # Key Narratives
            narratives = []
            if strk > 4: narratives.append("Unstoppable")
            if strk < -4: narratives.append("Frustrated")
            if pct > 0.7: narratives.append("Euphoric")
            if pct < 0.2: narratives.append("Crisis")
            
            r['momentum'] = round(pct * 2.0 + (strk * 0.1), 2) # Algorithmic momentum
            r['volatility'] = round(abs(0.5 - pct), 2) # Deviation from average
            r['regime_label'] = label
            r['key_narratives'] = narratives
            
            updates += 1
            print(f"✅ Updated {r['team_name']}: {s['wins']}-{s['losses']} ({label})")
            
    with open(regime_path, "w") as f:
        json.dump(regimes, f, indent=2)
    print(f"💾 Saved {updates} team regimes.")

if __name__ == "__main__":
    update_standings()
