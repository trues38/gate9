
import pyreadr
import pandas as pd
import json
import os
import numpy as np

# Configuration
INPUT_FILE = "/Users/js/Downloads/NBA_games_info.RData"
OUTPUT_FILE = "/Users/js/g9/nba_data/quant_engine_v1/regime_stats.json"

TIER_MAP = {
    "1": {"range": (1.36, 1.60), "label": "Trap"},
    "2": {"range": (1.25, 1.36), "label": "Caution"},
    "3": {"range": (1.15, 1.25), "label": "Danger"},
    "4": {"range": (1.0, 1.15), "label": "Miracle"}
}

def classify_tier(odds):
    if odds <= 1.15: return "4"
    if odds <= 1.25: return "3"
    if odds <= 1.36: return "2"
    if odds <= 1.60: return "1"
    return "0"

def build_regime_stats():
    print(f"Loading {INPUT_FILE}...")
    try:
        data = pyreadr.read_r(INPUT_FILE)
        df_raw = data['df']
    except Exception as e:
        print(f"Error loading RData: {e}")
        return

    # Filter for Home Games to avoid dupes (assuming local=1)
    if 'local' in df_raw.columns:
        df = df_raw[df_raw['local'] == 1.0].copy()
    else:
        df = df_raw.copy()
        
    print(f"Base Games: {len(df)}")
    
    # ---------------------------------------------------------
    # 1. Preprocessing & Tagging
    # ---------------------------------------------------------
    processed_games = []
    
    for idx, row in df.iterrows():
        try:
            h_odds = float(row['odds']) if not pd.isna(row['odds']) else 99.0
            a_odds = float(row['odds.opponent']) if 'odds.opponent' in row and not pd.isna(row['odds.opponent']) else 99.0
            
            # Identify Favorite
            fav_team = None
            fav_odds = 0.0
            is_home_fav = False
            
            if h_odds <= 1.60:
                fav_team = 'Home'
                fav_odds = h_odds
                is_home_fav = True
            elif a_odds <= 1.60:
                fav_team = 'Away'
                fav_odds = a_odds
                is_home_fav = False
            
            if not fav_team: continue
            
            # Determine Outcome (Upset = Fav Lost)
            h_score = int(row['Points'])
            a_score = int(row['OpponentPoints'])
            
            fav_won = False
            if is_home_fav: fav_won = (h_score > a_score)
            else: fav_won = (a_score > h_score)
            
            is_upset = not fav_won
            
            # Tier
            tier = classify_tier(fav_odds)
            if tier == "0": continue
            
            # Extract Metrics for Tagging
            # Variables depend on Perspective (Fav vs Und)
            # Row has 'days_since_last' (Home), 'days_since_last_o' (Away)
            # 'avg_V_4' (Home), 'avg_V_o_4' (Away)
            
            if is_home_fav:
                fav_rest = row['days_since_last']
                und_rest = row['days_since_last_o']
                fav_form_off = row['avg_P_4']
                fav_avg_off = row['avg_P_32']
                und_form_win = row['avg_V_o_4']
                fav_wins = row['n_victorias']
                und_wins = row['n_victorias_o']
                score_l10 = row['score_last_10_between']
            else:
                fav_rest = row['days_since_last_o']
                und_rest = row['days_since_last']
                fav_form_off = row['avg_P_o_4'] # Away Form
                fav_avg_off = row['avg_P_o_32']
                und_form_win = row['avg_V_4'] # Home Form (Underdog)
                fav_wins = row['n_victorias_o']
                und_wins = row['n_victorias']
                score_l10 = row['score_last_10_between']
            
            # --- REGIME TAGGING ---
            tags = []
            
            # 1. Fatigue Trap (Fav Tired, Und Fresh, Fav Offense Dipping)
            is_fatigue = False
            if (fav_rest <= 1) and (und_rest >= 2) and (fav_form_off < fav_avg_off):
                is_fatigue = True
                tags.append("Fatigue Trap")
                
            # 2. Hot Underdog (Und recently winning)
            is_hot_dog = False
            if und_form_win >= 0.7: # 3+ wins in last 4
                is_hot_dog = True
                tags.append("Hot Underdog")
            
            # 3. Nemesis (Good Team gap, but close H2H)
            is_nemesis = False
            # Diff wins > 10 but avg score diff < 3 ??
            # Simplify: score_last_10_between (avg diff) is small (< 3) but win diff is large?
            # Missing win diff context in row efficiently, let's use score_last_10_between close to 0
            # AND fav_wins >> und_wins
            try:
                if abs(fav_wins - und_wins) > 10 and abs(score_l10) < 5.0 and not pd.isna(score_l10):
                    is_nemesis = True
                    tags.append("Nemesis")
            except:
                pass

            processed_games.append({
                "tier": tier,
                "is_upset": is_upset,
                "tags": tags
            })
            
        except Exception as ex:
            continue
            
    print(f"Processed {len(processed_games)} Favorite Games.")
    
    # ---------------------------------------------------------
    # 2. GroupBy Aggregation (The Analytics)
    # ---------------------------------------------------------
    # We want a lookup tree: Tier -> Tag -> Probability
    
    stats = {}
    
    for t_id, meta in TIER_MAP.items():
        # Filter Tier
        tier_games = [g for g in processed_games if g['tier'] == t_id]
        total = len(tier_games)
        upsets = len([g for g in tier_games if g['is_upset']])
        base_rate = round(upsets / total * 100, 1) if total > 0 else 0
        
        entry = {
            "label": meta['label'],
            "base_stats": {"total": total, "upsets": upsets, "rate": base_rate},
            "regimes": {}
        }
        
        # Calculate for each Tag
        for tag in ["Fatigue Trap", "Hot Underdog", "Nemesis"]:
            tag_games = [g for g in tier_games if tag in g['tags']]
            t_total = len(tag_games)
            t_upsets = len([g for g in tag_games if g['is_upset']])
            t_rate = round(t_upsets / t_total * 100, 1) if t_total > 0 else 0
            
            # Lift (Multiplier)
            lift = round(t_rate / base_rate, 2) if base_rate > 0 else 0
            
            entry["regimes"][tag] = {
                "total": t_total,
                "upsets": t_upsets,
                "rate": t_rate,
                "lift": lift
            }
            
        stats[t_id] = entry
        
    # Save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(stats, f, indent=4)
        
    print(f"Regime Stats Saved to {OUTPUT_FILE}")
    
    # Print Preview
    print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    build_regime_stats()
