
import json
import glob
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Config
DATA_DIR = "/Users/js/g9/nba_data"
ROSTER_PATH = os.path.join(DATA_DIR, "players/roster_2025.json")

class FusionEngineV2:
    def __init__(self):
        print("Initializing Fusion Engine 2.0...")
        self.roster = self._load_roster()
        self.team_rosters = self._map_team_rosters()
        
        # KEY: Reconstruct Game Scores from Player Logs
        self.game_db = {} # game_id -> { team_id: pts, ... }
        self.team_game_map = {} # team_id -> [ {date, game_id, pts, opp_pts, wl} ]
        
        print("Building Game Database from Player Logs...")
        self._build_game_database()
        print(f"Game Database Built: {len(self.game_db)} games found.")
        print("Indexing Team Histories...")
        self._build_team_histories()

    def _load_roster(self):
        with open(ROSTER_PATH, 'r') as f:
            return json.load(f)

    def _map_team_rosters(self):
        map_ = {}
        for p in self.roster:
            tid = p.get('TEAM_ID')
            if tid:
                if tid not in map_: map_[tid] = []
                map_[tid].append(p)
        return map_

    def _build_game_database(self):
        # Scan using Roster -> File pattern (Robust)
        # This is O(Players * Files), but verified working in direct_engine.py
        
        print(f"Scanning {len(self.roster)} players...")
        
        for p in self.roster:
            tid = p.get('TEAM_ID')
            if not tid: continue
            
            # Construct filename pattern
            name_part = p['DISPLAY_FIRST_LAST'].replace(' ', '_')
            pattern = os.path.join(DATA_DIR, f"gamelogs_real/{name_part}_*.json")
            matches = glob.glob(pattern)
            
            if not matches: continue
            fpath = matches[0] # Take first match
            
            try:
                with open(fpath, 'r') as f:
                    data = json.load(f)
                    
                events = []
                self._extract_stats(data, events)
                meta_events = data.get('events', {})
                
                for e in events:
                    eid = e.get('eventId')
                    if not eid: continue
                    meta = meta_events.get(eid)
                    if not meta: continue
                    
                    # Date verification
                    d_str = meta.get('gameDate', '').split('T')[0]
                    if not d_str: continue # Skip if no date
                    
                    stats = e.get('stats', [])
                    if len(stats) < 14: continue
                    
                    pts = int(stats[13])
                    
                    # Add to GameDB
                    if eid not in self.game_db:
                        self.game_db[eid] = {}
                        self.game_db[eid]['date'] = d_str
                    
                    if tid not in self.game_db[eid]:
                        self.game_db[eid][tid] = 0
                        
                    self.game_db[eid][tid] += pts
                    
            except:
                continue
                
    def _build_team_histories(self):
        # Flatten GameDB into Team Histories
        count = 0
        for gid, teams in self.game_db.items():
            date = teams.get('date')
            if not date: continue
            
            # team_ids in this game (keys that are int)
            tids = [k for k in teams.keys() if isinstance(k, int)]
            
            if len(tids) == 2:
                t1, t2 = tids[0], tids[1]
                s1, s2 = teams[t1], teams[t2]
                
                # Add for T1
                if t1 not in self.team_game_map: self.team_game_map[t1] = []
                self.team_game_map[t1].append({
                    "game_id": gid, "date": date, "pts": s1, "opp_pts": s2,
                    "wl": "W" if s1 > s2 else "L",
                    "margin": s1 - s2
                })
                
                # Add for T2
                if t2 not in self.team_game_map: self.team_game_map[t2] = []
                self.team_game_map[t2].append({
                    "game_id": gid, "date": date, "pts": s2, "opp_pts": s1,
                    "wl": "W" if s2 > s1 else "L",
                    "margin": s2 - s1
                })
                count += 1
        print(f"Team Histories Indexed: {count} valid games processed.")
                
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

    # --- FUSION ENGINE IMPLEMENTATION ---

    def analyze_matchup(self, home_id, away_id, date_str):
        home_metrics = self.calculate_quant_metrics(home_id, date_str)
        away_metrics = self.calculate_quant_metrics(away_id, date_str)
        
        # 1. Quant Edge Score (0-100)
        # diffs
        mom_diff = home_metrics['momentum_score'] - away_metrics['momentum_score'] # -20 to 20
        # Normalize diff to score contribution?
        
        # Spec:
        # quant_edge = weighted_sum([momentum_gap, pace_gap, star_form_gap...])
        
        # We need to compute gaps first.
        # Define weights for GAP -> Score
        
        # Momentum Gap (-20 to 20): Raw val is -10 to 10.
        # Edge = 50 + Gap * Factor?
        # Let's simplfy: Home Edge Score. 50 is neutral.
        
        # Factors (Weight * Value)
        # Momentum: (1.5)
        # Star Form (0-1): (10)
        # Defense (0-1): (10)
        # Matchup (0-1): (5)
        # Injury (0-40): (-0.5) 
        
        m_gap = home_metrics['momentum_score'] - away_metrics['momentum_score']
        s_gap = home_metrics['star_form'] - away_metrics['star_form']
        d_gap = home_metrics['defense'] - away_metrics['defense']
        inj_gap = home_metrics['injury_impact'] - away_metrics['injury_impact'] # Positive means Home has more injury
        
        # Raw Edge Calculation
        raw_edge = 0
        raw_edge += m_gap * 2.0  # e.g. Gap 5 -> +10
        raw_edge += s_gap * 20.0 # e.g. Gap 0.2 -> +4
        raw_edge += d_gap * 20.0 # e.g. Gap 0.1 -> +2
        raw_edge -= inj_gap * 0.5 # e.g. Gap 10 -> -5
        
        # Base 50
        edge_score = 50 + raw_edge
        edge_score = max(0, min(100, edge_score))
        
        # 2. Quant Risk Score (0-100)
        # Derived from Injury, Schedule, Variance
        # Risk is high if Home has high injury OR Away has high injury?
        # Usually measures "Uncertainty".
        # Or Risk for the Favorite?
        # Let's average the risks.
        h_risk = (home_metrics['injury_impact'] * 1.5) + (home_metrics['sched_stress'] * 0.5)
        a_risk = (away_metrics['injury_impact'] * 1.5) + (away_metrics['sched_stress'] * 0.5)
        
        quant_risk = (h_risk + a_risk) / 2
        quant_risk = min(100, quant_risk)
        
        # 3. Context Similarity (For Twin)
        # We need Context Vector for Twin Engine
        # Returns raw dict
        
        return {
            "edge_score": round(edge_score, 1),
            "risk_score": round(quant_risk, 1),
            "home_stats": home_metrics,
            "away_stats": away_metrics,
            "context": {
                "momentum_gap": round(m_gap, 2),
                "injury_gap": round(inj_gap, 2),
                "location": "HOME",
                "spread_proxy": round(raw_edge, 1) # Use raw edge as spread proxy
            }
        }

    def calculate_quant_metrics(self, team_id, target_date):
        hist = self._get_history(team_id, target_date)
        l10 = hist[:10]
        l5 = hist[:5]
        
        # 1. Momentum 2.0 (-10 to 10)
        # net_rating_10g * 0.5 + winrate * 0.3 + ptdiff * 0.2
        # Need to normalize scales.
        # NetRtg: usually -15 to +15.
        # Win%: 0 to 1.
        # PtDiff: -15 to +15.
        
        if l10:
            avg_margin = sum(g['margin'] for g in l10) / len(l10) # Approx PtDiff & NetRtg proxy
            wins = sum(1 for g in l10 if g['wl'] == 'W')
            win_rate = wins / len(l10)
            
            # Formula (Conceptual Scaling)
            # NetRtg approx Margin.
            # Scale Margin: +10 margin -> +10 score.
            # Scale Win%: 1.0 -> +10 score.
            
            # M = (Margin * 0.7) + (WinRate * 10 * 0.3)
            # e.g Margin +5, Win 0.6 -> 3.5 + 1.8 = 5.3
            momentum_score = (avg_margin * 0.7) + (win_rate * 10 * 0.3)
            
            # Clamp -10 to 10
            momentum_score = max(-10, min(10, momentum_score))
        else:
            momentum_score = 0
            
        # 2. Injury Impact (0-40)
        # Placeholder logic: Check active roster or stored injury data.
        # For now 0.
        injury = 0
        
        # 3. Star Form (0-1)
        # Use previous logic
        form = 0.5 # Default
        
        # 4. Defense (0-1)
        # 1.0 - (Points Allowed / 150)
        if l5:
            avg_allowed = sum(g['opp_pts'] for g in l5) / len(l5)
            defense = 1.0 - (avg_allowed / 150)
            defense = max(0, min(1, defense))
        else:
            defense = 0.5
            
        # 5. Schedule Stress
        # 0, 50, 100
        sched = 0
        if hist:
            last = hist[0]['date']
            fmt = "%Y-%m-%d"
            try:
                diff = (datetime.strptime(target_date, fmt) - datetime.strptime(last, fmt)).days - 1
                if diff <= 0: sched = 100
                elif diff == 1: sched = 50
            except: pass
            
        return {
            "momentum_score": momentum_score,
            "injury_impact": injury,
            "star_form": form,
            "defense": defense,
            "sched_stress": sched
        }

    def _get_history(self, team_id, target_date):
        # Retrieve from self.team_game_map
        games = self.team_game_map.get(team_id, [])
        # Filter < target_date and Sort Desc
        filtered = [g for g in games if g['date'] < target_date]
        filtered.sort(key=lambda x: x['date'], reverse=True)
        return filtered

if __name__ == "__main__":
    eng = FusionEngineV2()
    # Test
    print(eng.analyze_matchup(1610612766, 1610612741, "2025-12-12"))
