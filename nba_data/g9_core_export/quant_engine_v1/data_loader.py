
import json
import glob
import os
import pandas as pd
from datetime import datetime

# Config
DATA_DIR = "/Users/js/g9/nba_data"
ROSTER_PATH = os.path.join(DATA_DIR, "players/roster_2025.json")

class DataLoader:
    def __init__(self):
        print("Loading Data...")
        self.roster = self._load_roster()
        self.pid_to_tid = {p['PERSON_ID']: p['TEAM_ID'] for p in self.roster if p.get('TEAM_ID')}
        self.team_game_map = self._build_team_histories()
        
    def _load_roster(self):
        with open(ROSTER_PATH, 'r') as f:
            return json.load(f)

    def _build_team_histories(self):
        print("Building Team Histories via Player Stat Aggregation...")
        
        # 1. Build Abbr -> NBA_ID Map from Roster
        abbr_to_nba = {}
        for p in self.roster:
            tid = p.get('TEAM_ID')
            abbr = p.get('TEAM_ABBREVIATION')
            if tid and abbr:
                abbr_to_nba[abbr] = tid
        
        # Add Manual Overrides for known mismatches if any
        # (Based on standard NBA abbreviations vs ESPN)
        abbr_to_nba['UTA'] = abbr_to_nba.get('UTA', 1610612762)
        abbr_to_nba['GS'] = abbr_to_nba.get('GSW', 1610612744)
        abbr_to_nba['NO'] = abbr_to_nba.get('NOP', 1610612740)
        abbr_to_nba['NY'] = abbr_to_nba.get('NYK', 1610612752)
        abbr_to_nba['SA'] = abbr_to_nba.get('SAS', 1610612759)
        abbr_to_nba['PHX'] = abbr_to_nba.get('PHX', 1610612756)
        abbr_to_nba['PHO'] = abbr_to_nba.get('PHX', 1610612756)
        abbr_to_nba['WSH'] = abbr_to_nba.get('WAS', 1610612764)
        
        print(f"Roster Abbr Map Size: {len(abbr_to_nba)}")
        
        # 2. Scan Files and Aggregate Stats
        # GameDB Structure: 
        # game_id -> { 
        #    "date": "YYYY-MM-DD", 
        #    "teams": { 
        #        nba_tid: { "pts": 0, "fga": 0, "fta": 0, "tov": 0, "reb": 0, "is_home": Bool } 
        #    }
        # }
        
        game_db = {}
        files = glob.glob(os.path.join(DATA_DIR, "gamelogs_real/*.json"))
        
        for fpath in files:
            try:
                with open(fpath, 'r') as f:
                    data = json.load(f)
                
                # PRE-PROCESS: Build Stats Map from seasonTypes
                # eventId -> stats_list
                stats_map = {}
                season_types = data.get('seasonTypes', [])
                for st in season_types:
                    cats = st.get('categories', [])
                    for cat in cats:
                        # We only want "stats" type events usually? 
                        # Or just grab all events inside categories
                        s_events = cat.get('events', [])
                        for se in s_events:
                            eid = se.get('eventId')
                            estats = se.get('stats')
                            if eid and estats:
                                stats_map[eid] = estats

                events = data.get('events', {})
                if not events: continue
                
                scan_list = events.values() if isinstance(events, dict) else events
                
                for evt in scan_list:
                    gid = evt.get('id')
                    if not gid: continue
                    
                    # 1. Identify Game Metadata (Date, etc)
                    # (Rest of logic matches, just lookup stats)
                    
                    if gid not in game_db:
                         # Store Metadata for Single-Team Fallback
                         game_db[gid] = { 
                             "date": evt.get('gameDate', '').split('T')[0], 
                             "teams": {},
                             "meta": {
                                 "home_id_espn": evt.get('homeTeamId'),
                                 "away_id_espn": evt.get('awayTeamId'),
                                 "home_score": int(evt.get('homeTeamScore', 0)),
                                 "away_score": int(evt.get('awayTeamScore', 0))
                             }
                         }
                        
                    # 2. Identify Player's Team (Static Mapping)
                    if 'team' not in evt: continue
                    espn_tid = str(evt['team'].get('id'))
                    
                    # HARDCODED STATIC MAP (ESPN -> NBA)
                    ESPN_TO_NBA = {
                        "26": 1610612762, # UTAH
                        "23": 1610612758, # SAC
                        "3": 1610612740,  # NO
                        "8": 1610612765,  # DET
                        "29": 1610612763, # MEM
                        "5": 1610612739,  # CLE
                        "13": 1610612747, # LAL
                        "7": 1610612743,  # DEN
                        "1": 1610612737,  # ATL
                        "21": 1610612756, # PHX
                        "16": 1610612750, # MIN
                        "2": 1610612738,  # BOS
                        "27": 1610612764, # WSH
                        "6": 1610612742,  # DAL
                        "24": 1610612759, # SA
                        "30": 1610612766, # CHA
                        "20": 1610612755, # PHI
                        "4": 1610612741,  # CHI
                        "25": 1610612760, # OKC
                        "28": 1610612761, # TOR
                        "15": 1610612749, # MIL
                        "17": 1610612751, # BKN
                        "9": 1610612744,  # GS
                        "12": 1610612746, # LAC
                        "11": 1610612754, # IND
                        "18": 1610612752, # NY
                        "19": 1610612753, # ORL
                        "10": 1610612745, # HOU
                        "14": 1610612748, # MIA
                        "22": 1610612757  # POR
                    }
                    
                    nba_tid = ESPN_TO_NBA.get(espn_tid)
                    if not nba_tid: continue
                    
                    # 3. Extract Stats (FROM MAP)
                    stats = stats_map.get(gid, [])
                    if len(stats) < 14: continue
                    
                    try:
                        pts = int(stats[13])
                        tov = int(stats[12])
                        reb = int(stats[7])
                        
                        fg_str = stats[1] # "M-A"
                        fga = int(fg_str.split('-')[1]) if '-' in fg_str else 0
                        
                        ft_str = stats[5] # "M-A"
                        fta = int(ft_str.split('-')[1]) if '-' in ft_str else 0
                        
                    except:
                        continue
                        
                    # 4. Aggregate
                    if nba_tid not in game_db[gid]['teams']:
                         game_db[gid]['teams'][nba_tid] = {
                             "pts": 0, "fga": 0, "fta": 0, "tov": 0, "reb": 0
                         }
                         
                    t_stats = game_db[gid]['teams'][nba_tid]
                    t_stats['pts'] += pts
                    t_stats['fga'] += fga
                    t_stats['fta'] += fta
                    t_stats['tov'] += tov
                    t_stats['reb'] += reb
                    
            except Exception as e:
                # print(f"Error processing {fpath}: {e}")
                continue
                
        # 3. Finalize Histories
        team_histories = {}
        
        print(f"Aggregated Games: {len(game_db)}")
        
        for gid, g in game_db.items():
            teams_data = g['teams']
            meta = g['meta']
            
            for tid, t_stats in teams_data.items():
                if tid not in team_histories: team_histories[tid] = []
                
                # Use Metadata Scores for Truth
                # Determine if 'tid' is Home or Away based on ESPN ID mapping
                # We need to map NBA_ID back to ESPN ID? No.
                # Use the map we just defined? It's inside the loop.
                # Refactor map to class level?
                # Just assume we can find our ID by score match.
                
                h_espn = meta['home_id_espn']
                home_nba_id = ESPN_TO_NBA.get(h_espn)
                
                # Check if current 'tid' is home
                is_home = (tid == home_nba_id)
                
                real_pts = meta['home_score'] if is_home else meta['away_score']
                real_opp_pts = meta['away_score'] if is_home else meta['home_score']
                
                # Scaling logic for partial stat coverage
                scale = 1.0
                if t_stats['pts'] > 0:
                    scale = real_pts / t_stats['pts']
                    if scale > 3.0: scale = 3.0
                    if scale < 1.0: scale = 1.0
                
                adj_fga = int(t_stats['fga'] * scale)
                adj_fta = int(t_stats['fta'] * scale)
                adj_tov = int(t_stats['tov'] * scale)
                adj_reb = int(t_stats['reb'] * scale)
                
                # Opponent Approx (Flat values, but consistent)
                opp_fga_approx = 90
                opp_fta_approx = 22
                opp_tov_approx = 14
                opp_reb_approx = 44
                
                team_histories[tid].append({
                    "game_id": gid, "date": g['date'],
                    "pts": real_pts, "opp_pts": real_opp_pts,
                    "fga": adj_fga, "fta": adj_fta, "tov": adj_tov, "reb": adj_reb,
                    "opp_fga": opp_fga_approx, "opp_fta": opp_fta_approx, 
                    "opp_tov": opp_tov_approx, "opp_reb": opp_reb_approx,
                    "wl": "W" if real_pts > real_opp_pts else "L",
                    "margin": real_pts - real_opp_pts
                })
            
        # Sort
        for tid in team_histories:
            team_histories[tid].sort(key=lambda x: x['date'], reverse=True)
            
        return team_histories
    def _extract_stats_recursive(self, obj, collector):
        if isinstance(obj, dict):
            if 'eventId' in obj and 'stats' in obj:
                collector.append(obj)
            for k,v in obj.items():
                if isinstance(v, (dict, list)):
                    self._extract_stats_recursive(v, collector)
        elif isinstance(obj, list):
            for item in obj:
                self._extract_stats_recursive(item, collector)
                
    def get_history(self, team_id):
        # Return list of games
        return self.team_game_map.get(str(team_id)) or self.team_game_map.get(int(team_id)) or []

