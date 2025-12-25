from data_loader import DataLoader
import json

dl = DataLoader()
for tid, hist in dl.team_game_map.items():
    if hist:
        print(json.dumps(hist[0], indent=2))
        break
