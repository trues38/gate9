
import json
import glob
import os
import sys
from datetime import datetime
import pandas as pd
import numpy as np

# Config
DATA_DIR = "/Users/js/g9/nba_data"
ROSTER_PATH = os.path.join(DATA_DIR, "players/roster_2025.json")
SCHEDULE_PATH = os.path.join(DATA_DIR, "schedule_2025.json")
REPORT_DIR = os.path.join(DATA_DIR, "reports")

class DirectJsonEngine:
    def __init__(self):
        print("Loading Roster...")
        with open(ROSTER_PATH, 'r') as f:
            self.roster = json.load(f)
        
        # Optimize Roster Lookup
        self.team_rosters = {}
        for p in self.roster:
            tid = p.get('TEAM_ID')
            if tid:
                if tid not in self.team_rosters:
                    self.team_rosters[tid] = []
                self.team_rosters[tid].append(p)
                
    def get_team_history(self, team_id, target_date):
        """
        Reconstructs team game history from player logs.
        Returns a DataFrame with [date, wl, pts, poss...] for the team.
        """
        players = self.team_rosters.get(team_id, [])
        game_map = {} # date -> {pts: 0, ...}
        
        for p in players:
            name_part = p['DISPLAY_FIRST_LAST'].replace(' ', '_')
            pattern = os.path.join(DATA_DIR, f"gamelogs_real/{name_part}_*.json")
            matches = glob.glob(pattern)
            if not matches: continue
            
            try:
                with open(matches[0], 'r') as f:
                    data = json.load(f)
                    
                # Extract stats
                events = []
                self._extract_stats(data, events)
                
                meta_events = data.get('events', {})
                
                for e in events:
                    eid = e.get('eventId')
                    if not eid: continue
                    meta = meta_events.get(eid)
                    if not meta: continue
                    
                    date_raw = meta.get('gameDate')
                    if not date_raw: continue
                    d_str = date_raw.split('T')[0]
                    
                    if d_str >= target_date: continue # Ignore future/current
                    
                    if d_str not in game_map:
                        game_map[d_str] = {
                            "wl": meta.get('gameResult', 'N/A'),
                            "pts": 0,
                            "fga": 0,
                            "fta": 0,
                            "tov": 0,
                            "top_scorers": []
                        }
                    
                    stats = e.get('stats', [])
                    if len(stats) >= 14:
                        pts = int(stats[13])
                        game_map[d_str]['pts'] += pts
                        
                        fga = int(stats[1].split('-')[1])
                        game_map[d_str]['fga'] += fga
                        
                        fta = int(stats[5].split('-')[1])
                        game_map[d_str]['fta'] += fta
                        
                        tov = int(stats[12])
                        game_map[d_str]['tov'] += tov
                        
                        # Store individual perfs (for Star Form)
                        pm_val = int(stats[14]) if len(stats) > 14 else 0
                        game_map[d_str]['top_scorers'].append({
                            "pid": p['PERSON_ID'],
                            "pts": pts,
                            "pm": pm_val # Might be missing, assume 0
                        })
                        
            except:
                continue
                
        # Convert to List
        history = []
        for d, vals in game_map.items():
            # Calc Poss
            # 0.96 * (FGA + 0.44*FTA + TOV)
            poss = 0.96 * (vals['fga'] + 0.44 * vals['fta'] + vals['tov'])
            pace = 48 * (poss / 240) if poss > 0 else 98.0 # Approx
            
            history.append({
                "date": d,
                "wl": vals['wl'],
                "pts": vals['pts'],
                "pace": pace,
                "top_scorers": vals['top_scorers']
            })
            
        # Sort desc
        history.sort(key=lambda x: x['date'], reverse=True)
        return history

    def _extract_stats(self, obj, collector):
        if isinstance(obj, dict):
            if 'eventId' in obj and 'stats' in obj:
                collector.append(obj)
            for k,v in obj.items():
                if isinstance(v, (dict, list)):
                    self._extract_stats(v, collector)
        elif isinstance(obj, list):
            for item in obj:
                self._extract_stats(item, collector)

    def calculate_layers(self, team_id, target_date):
        hist = self.get_team_history(team_id, target_date)
        
        # 1. Momentum (Win% L5)
        l5 = hist[:5]
        wins = sum(1 for g in l5 if g['wl'] == 'W')
        momentum = wins / len(l5) if l5 else 0.5
        
        # 2. Pace (Avg Pace L5)
        # Filter outliers
        paces = [g['pace'] for g in l5 if g['pace'] > 80 and g['pace'] < 130]
        pace = sum(paces) / len(paces) if paces else 100.0
        
        # 3. Star Form (Top 3 Scorers of L3 games)
        # We need to identify specific players? Or just sum best perfs?
        # Let's simple sum the top 3 scores of the team on avg L3.
        # Actually correct way is: Find Top 3 season scorers -> Get their recent avg.
        # Simplified: Just take sum of top 3 scorers in L3 games.
        l3 = hist[:3]
        form_val = 0
        if l3:
            total_top3 = 0
            for g in l3:
                # Sort scorers
                scorers = sorted(g['top_scorers'], key=lambda x: x['pts'], reverse=True)
                top3 = scorers[:3]
                total_top3 += sum(p['pts'] for p in top3)
            form_val = total_top3 / len(l3)
        
        return {
            "momentum": round(momentum, 2),
            "pace": round(pace, 2),
            "star_form": round(form_val, 1)
        }

def generate(target_date):
    print(f"Direct JSON Generation for {target_date}...")
    
    with open(SCHEDULE_PATH, 'r') as f:
        schedule = json.load(f)
        
    # Filter games
    games = []
    for s in schedule:
        # Check date format
        # "12/12/2025" or "2025-12-12"
        d_raw = s['date'].split(' ')[0]
        try:
            parts = d_raw.split('/')
            if len(parts) == 3:
                iso = f"{parts[2]}-{parts[0]}-{parts[1]}"
            else:
                iso = d_raw
        except:
            iso = d_raw
            
        if iso == target_date:
            games.append(s)
            
    print(f"Found {len(games)} games.")
    
    engine = DirectJsonEngine()
    
    md_out = f"# REGIME ZERO: DIRECT JSON REPORT ({target_date})\n\n"
    
    for g in games:
        hid = g['home_id']
        aid = g['away_id']
        home_name = g['home_team']
        away_name = g['away_team']
        
        h_stats = engine.calculate_layers(hid, target_date)
        a_stats = engine.calculate_layers(aid, target_date)
        
        md_out += f"## {home_name} vs {away_name}\n"
        md_out += f"**Game ID**: `{g['game_id']}`\n\n"
        md_out += "| Metric | Home | Away |\n| :--- | :---: | :---: |\n"
        md_out += f"| **Momentum** | {h_stats['momentum']} | {a_stats['momentum']} |\n"
        md_out += f"| Pace | {h_stats['pace']} | {a_stats['pace']} |\n"
        md_out += f"| Star Form | {h_stats['star_form']} | {a_stats['star_form']} |\n"
        md_out += "\n---\n\n"
        
    path = os.path.join(REPORT_DIR, f"direct_report_{target_date}.md")
    with open(path, 'w') as f:
        f.write(md_out)
        
    print(f"Report Saved: {path}")
    return path

if __name__ == "__main__":
    if len(sys.argv) > 1:
        date = sys.argv[1]
    else:
        date = "2025-12-12"
        
    generate(date)
