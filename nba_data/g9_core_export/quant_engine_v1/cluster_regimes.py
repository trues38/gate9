import pandas as pd
import numpy as np

CSV_FILE = 'processed/rdata_treasury.csv'

def cluster_regimes():
    print(f"🚀 Loading Treasury Data for Clustering...")
    df = pd.read_csv(CSV_FILE)
    
    # Filter for 'Betting on Underdog' Scenario (Odds > 2.0)
    # Target: 'is_win' = 1.0
    items = df[df['odds'] >= 2.0].copy()
    items['is_win'] = items['V'] == 1.0
    
    print(f"📊 Total Underdog Sample: {len(items)} games")
    print(f"📊 Global Underdog Win Rate: {items['is_win'].mean():.1%}")
    print("-" * 40)
    
    # Define Binary Features
    # 1. Tired Favorite
    items['feat_tired'] = (items['days_since_last'] <= 1) & (items['days_since_last_o'] >= 3)
    
    # 2. Momentum Trap
    items['feat_momentum'] = (items['avg_V_4'] <= 0.4) & (items['avg_V_o_4'] >= 0.7)
    
    # 3. Nemesis (Historical)
    # Using -4.0 as threshold to capture more signal
    if 'score_last_10_between' in items.columns:
        items['feat_nemesis'] = items['score_last_10_between'] < -4.0
    else:
        items['feat_nemesis'] = False
        
    # 4. Divisional
    if 'Team_Zone' in items.columns:
        items['feat_divisional'] = items['Team_Zone'] == items['Opponent_Zone']
    else:
        items['feat_divisional'] = False

    # Clustering: Group By Combinations
    features = ['feat_tired', 'feat_momentum', 'feat_nemesis', 'feat_divisional']
    
    # Check if 'feat_tired' is always False? (Since we filtered for odds > 2.0, the ROW is the Underdog.
    # WAIT. The columns 'days_since_last' usually refer to the ROW TEAM.
    # 'days_since_last_o' is the OPPONENT (Favorite).
    # IF the ROW TEAM is Underdog (Odds > 2.0), then:
    # 'feat_tired' definition in my previous script was: "Fav Tired".
    # Here, ROW is Underdog. Opponent is Favorite.
    # So "Fav Tired" means `days_since_last_o <= 1`.
    # Let's double check variables.
    # In 'discover_regime.py', I filtered `favs`.
    # HERE, I filtered `items` (Underdogs).
    # So:
    # 'feat_tired': Fav(Opp) Rest <= 1. -> `days_since_last_o <= 1`.
    # 'feat_momentum': Fav Cold, Dog Hot. -> `avg_V_o_4 <= 0.4` (Fav Cold), `avg_V_4 >= 0.7` (Dog Hot).
    # 'feat_nemesis': Dog dominates Fav using historical score?
    # 'score_last_10_between': Score margin of Row Team vs Opponent.
    # If Row (Dog) dominates, `score > 0`?
    # In 'discover_regime', I used `score < -5` for Fav losing.
    # So for Dog Winning, `score > 5`? 
    # Or is `score_last_10_between` always (Team - Opponent)? Yes.
    # So if I am the Dog, and I am a "Nemesis" to the Fav, it means I usually beat them.
    # So `score_last_10_between > 0`?
    # But usually Nemesis means "Unexpectedly beats".
    # If I usually beat them (`score > 0`), why am I the Underdog?
    # Maybe recent form is bad, but history is good.
    # So 'feat_nemesis' = `score_last_10_between > 2.0` (Dog historically wins).
    
    # Let's adjust definitions for "Dog Perspective":
    items['feat_fatigue_adv'] = (items['days_since_last_o'] <= 1) & (items['days_since_last'] >= 2) # Fav Tired, Dog Rested
    items['feat_momentum_trap'] = (items['avg_V_o_4'] <= 0.4) & (items['avg_V_4'] >= 0.6) # Fav Cold, Dog Hot
    items['feat_nemesis'] = items['score_last_10_between'] > 1.0 # Dog has positive history vs Fav
    items['feat_divisional'] = items['Team_Zone'] == items['Opponent_Zone']

    features = ['feat_fatigue_adv', 'feat_momentum_trap', 'feat_nemesis', 'feat_divisional']
    
    print("\n🔍 Clustering Analysis (Combinations of Advantages)...\n")
    
    grouped = items.groupby(features).agg(
        games=('is_win', 'count'),
        win_rate=('is_win', 'mean')
    ).reset_index()
    
    # Filter for meaningful sample size
    grouped = grouped[grouped['games'] >= 10].sort_values('win_rate', ascending=False)
    
    columns = features + ['games', 'win_rate']
    print(grouped[columns].to_string(index=False))
    
    # Highlight Best Cluster
    best = grouped.iloc[0]
    print(f"\n🏆 God Tier Cluster:")
    print(best.to_string())

if __name__ == "__main__":
    cluster_regimes()
