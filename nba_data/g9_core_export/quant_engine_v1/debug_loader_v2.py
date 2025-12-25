
import json
import os
import glob
from data_loader import DataLoader

DATA_DIR = "/Users/js/g9/nba_data"
ROSTER_PATH = os.path.join(DATA_DIR, "players/roster_2025.json")

print("--- DEBUG LOADER V2 ---")

# 1. Check Roster
with open(ROSTER_PATH, 'r') as f:
    roster = json.load(f)
print(f"Roster Size: {len(roster)}")
print(f"Sample Roster Item: {roster[0]}")

# 2. Check PID Map
pid_to_tid = {p['PERSON_ID']: p['TEAM_ID'] for p in roster if p.get('TEAM_ID')}
print(f"PID Map Size: {len(pid_to_tid)}")
sample_pid = list(pid_to_tid.keys())[0]
print(f"Sample MAP: {sample_pid} -> {pid_to_tid[sample_pid]}")

# 3. Check Files
files = glob.glob(os.path.join(DATA_DIR, "gamelogs_real/*.json"))
print(f"Files Found: {len(files)}")
if len(files) > 0:
    fpath = files[0]
    print(f"Sample File: {fpath}")
    base = os.path.basename(fpath)
    print(f"Base: {base}")
    try:
        pid_str = base.split('_')[-1].split('.')[0]
        print(f"Parsed PID Str: '{pid_str}'")
        pid = int(pid_str)
        print(f"Parsed PID Int: {pid}")
        tid = pid_to_tid.get(pid)
        print(f"Lookup TID: {tid}")
    except Exception as e:
        print(f"Parse Error: {e}")

# 4. Check DataLoader Class
dl = DataLoader()
print(f"DataLoader Team Keys: {len(dl.team_game_map.keys())}")
