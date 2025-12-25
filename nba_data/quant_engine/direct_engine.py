
import json
import glob
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Config
DATA_DIR = "/Users/js/g9/nba_data"
ROSTER_PATH = os.path.join(DATA_DIR, "players/roster_2025.json")

class DirectJsonEngine:
    def __init__(self):
        print("Initializing Direct JSON Engine...")
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
        players = self.team_rosters.get(team_id, [])
        game_map = {} 
        
        for p in players:
            name_part = p['DISPLAY_FIRST_LAST'].replace(' ', '_')
            pattern = os.path.join(DATA_DIR, f"gamelogs_real/{name_part}_*.json")
            matches = glob.glob(pattern)
            if not matches: continue
            
            try:
                with open(matches[0], 'r') as f:
                    data = json.load(f)
                
                events = []
                self._extract_stats(data, events)
                meta_events = data.get('events', {})
                
                for e in events:
                    eid = e.get('eventId')
                    if not eid: continue
                    meta = meta_events.get(eid)
                    if not meta: continue
                    
                    d_str = meta.get('gameDate', '').split('T')[0]
                    if not d_str or d_str >= target_date: continue 
                    
                    if d_str not in game_map:
                        game_map[d_str] = {
                            "wl": meta.get('gameResult', 'N/A'),
                            "pts": 0, "fga": 0, "fta": 0, "tov": 0, "fgm": 0,
                            "top_scorers": []
                        }
                    
                    stats = e.get('stats', [])
                    if len(stats) >= 14:
                        pts = int(stats[13])
                        game_map[d_str]['pts'] += pts
                        
                        fga = int(stats[1].split('-')[1])
                        game_map[d_str]['fga'] += fga
                        
                        fgm = int(stats[1].split('-')[0])
                        game_map[d_str]['fgm'] += fgm
                        
                        fta = int(stats[5].split('-')[1])
                        game_map[d_str]['fta'] += fta
                        
                        tov = int(stats[12])
                        game_map[d_str]['tov'] += tov
                        
                        pm_val = int(stats[14]) if len(stats) > 14 else 0
                        game_map[d_str]['top_scorers'].append({
                            "pid": p['PERSON_ID'],
                            "pts": pts,
                            "pm": pm_val
                        })
            except:
                continue
                
        history = []
        for d, vals in game_map.items():
            # Calc Pace: 0.96 * (FGA + 0.44*FTA + TOV)
            # This is Est Possessions. Pace = 48 * (Poss / Minutes). Assuming 48 min game (240 team mins).
            # Actually, Poss is per team. 
            poss = 0.96 * (vals['fga'] + 0.44 * vals['fta'] + vals['tov'])
            pace = 48 * (poss / 48) # wait, Pace is Poss per 48m. If we sum all players, we get Team Totals.
            # Team Totals = 1 Game. Minutes = 48.
            # So Pace ~= Poss.
            
            history.append({
                "date": d,
                "wl": vals['wl'],
                "pts": vals['pts'],
                "pace": round(poss, 2),
                "top_scorers": vals['top_scorers']
            })
            
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

    def get_daily_scores(self, target_date, matches):
        # matches: list of dict {game_id, home_id, away_id...} from schedule
        results = []
        for m in matches:
            hid, aid = m['home_id'], m['away_id']
            
            h_stats = self.calculate_layers(hid, target_date)
            a_stats = self.calculate_layers(aid, target_date)
            
            # Matchup Calc (Height Diff)
            h_ht = self.get_avg_height(hid)
            a_ht = self.get_avg_height(aid)
            
            # Normalize Matchup (0.5 + diff/10)
            h_adv = 0.5 + ((h_ht - a_ht) * 0.05)
            a_adv = 1.0 - h_adv
            
            # Merge into Match Object
            m.update({
                "home_momentum": h_stats['momentum'],
                "away_momentum": a_stats['momentum'],
                "home_pace": h_stats['pace'],
                "away_pace": a_stats['pace'],
                "home_star_form": h_stats['star_form'],
                "away_star_form": a_stats['star_form'],
                "home_clutch": h_stats['clutch'],
                "away_clutch": a_stats['clutch'],
                "home_defense": h_stats['defense'],
                "away_defense": a_stats['defense'],
                "home_matchup": round(h_adv, 2),
                "away_matchup": round(a_adv, 2),
                "home_injury": h_stats['injury_impact'],
                "away_injury": a_stats['injury_impact'],
                "home_sched": h_stats['sched_stress'],
                "away_sched": a_stats['sched_stress']
            })
            results.append(m)
        return results

    def calculate_layers(self, team_id, target_date):
        hist = self.get_team_history(team_id, target_date)
        
        # 1. Momentum (Win% L5)
        l5 = hist[:5]
        wins = sum(1 for g in l5 if g['wl'] == 'W')
        momentum = wins / len(l5) if l5 else 0.5
        
        # 2. Pace (Avg L5)
        paces = [g['pace'] for g in l5 if g['pace'] > 70]
        pace = sum(paces) / len(paces) if paces else 100.0
        
        # 3. Star Form (Top 3 Scorers of L3)
        l3 = hist[:3]
        form_val = 0
        if l3:
            total_top3 = 0
            for g in l3:
                scorers = sorted(g['top_scorers'], key=lambda x: x['pts'], reverse=True)
                top3 = scorers[:3]
                total_top3 += sum(p['pts'] for p in top3)
            form_val = total_top3 / len(l3)
            
        # 4. Clutch (Win% in Close Games L20 -> Proxy: L10 Win%)
        l10 = hist[:10]
        wins10 = sum(1 for g in l10 if g['wl'] == 'W')
        clutch = wins10 / len(l10) if l10 else 0.5
        
        # 5. Defense (Pts Allowed)
        # Avg Pts Allowed L5.
        # Normalize: 150 is bad (0.0), 90 is good (1.0).
        # Linear scale: 1.0 - ((pts_allowed - 90) / 60)
        allowed = [g['pts'] for g in l5] # Wait, get_team_history returns Team PTS.
        # We need OPPONENT PTS.
        # direct_engine extraction doesn't easily capture Opponent Pts unless we parse "matchup" or look at "scores" in metadata (if avail).
        # Metadata has gameResult but typically not score?
        # Use simple proxy: 1.0 - (Team Pts / Pace) * Factor? No.
        # Let's assume neutral Defense 0.5 if we can't get OppPts.
        # Actually, extracting 'events' might have score? No.
        defense = 0.5 # Placeholder until we can look up game scores from Schedule (if scores are there).
        
        # 6. Schedule Stress (Rest Days)
        # Check date of last game vs target_date
        sched_stress = 0
        if hist:
            last_date_str = hist[0]['date']
            # Diff
            fmt = "%Y-%m-%d"
            try:
                td = datetime.strptime(target_date, fmt) - datetime.strptime(last_date_str, fmt)
                days_off = td.days - 1
                if days_off <= 0: sched_stress = 100 # B2B
                elif days_off == 1: sched_stress = 50 # 1 Day Rest
                else: sched_stress = 0 # Well Rested
            except:
                pass
                
        # 7. Injury Impact (Missing Stars)
        # Check if Top 3 scorers (Season) played in last game.
        # Simplified: Check active roster count variance?
        # Placeholder: Random variance to look realistic? 
        # No, let's look at missing top scorers from L10 in L1.
        injury = 0 # Low impact default
        
        # 8. Matchup (Height/Weight?)
        # Use Roster Avg Height.
        # I have self.roster. simple aggregation.
        matchup_val = 0.5 # Default.
        
        return {
            "momentum": round(momentum, 2),
            "pace": round(pace, 2),
            "star_form": round(form_val, 1),
            "clutch": round(clutch, 2),
            "defense": defense,
            "sched_stress": sched_stress,
            "injury_impact": injury,
            "matchup_strength": matchup_val # Will compare home vs away later
        }

    def get_avg_height(self, team_id):
        players = self.team_rosters.get(team_id, [])
        total_in = 0
        count = 0
        for p in players:
            h_str = p.get('HEIGHT', '') # "6-6"
            try:
                ft, inch = h_str.split('-')
                total_in += int(ft)*12 + int(inch)
                count += 1
            except:
                continue
        return total_in / count if count > 0 else 79 # Approx 6'7

