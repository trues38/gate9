import pandas as pd
import numpy as np

CSV_FILE = 'processed/rdata_unified.csv'

def discover_regimes():
    print(f"🚀 Loading Treasury Data...")
    df = pd.read_csv(CSV_FILE)
    
    # 1. Define 'Upset'
    # Odds are likely Decimal. 1.50 = -200 Fav. 2.50 = +150 Dog.
    # Upset = Underdog Winner OR Favorite Loser.
    # Let's focus on "Underdog Wins" (High Payout).
    # Assuming 'odds' corresponds to the 'Team'.
    
    # Filter for valid odds
    df = df[df['odds'].notna() & (df['odds'] > 0)]
    
    # Define Underdog: Odds > 2.0 (Even Money +)
    items = df.copy()
    items['is_underdog'] = items['odds'] >= 2.0
    items['is_favorite'] = items['odds'] < 1.8 # Strong favorite
    
    # Define Win
    # 'V' = 1.0 (Win)
    items['is_win'] = items['V'] == 1.0
    
    # 'Upset' event: Underdog Wins
    items['is_upset_win'] = items['is_underdog'] & items['is_win']
    
    upset_rate_global = items[items['is_underdog']]['is_win'].mean()
    print(f"📊 Global Underdog Win Rate (Odds >= 2.0): {upset_rate_global:.1%}")
    
    print("\n🔍 Investigating User Hypotheses (Regimes)...\n")
    
    # Regime 1: Fatigue Trap (Favorite is Tired, Dog is Rested)
    # Filter: Favorite (Odds < 1.5)
    # Condition: Fav Rest <= 1, Dog Rest >= 3
    
    favs = items[items['is_favorite']].copy()
    
    # Fav Tired
    favs['is_tired'] = favs['days_since_last'] <= 1
    # Dog Rested (Opponent)
    favs['is_opp_rested'] = favs['days_since_last_o'] >= 3
    
    regime_fatigue = favs[favs['is_tired'] & favs['is_opp_rested']]
    
    win_rate_fatigue = regime_fatigue['is_win'].mean()
    base_rate_fav = favs['is_win'].mean()
    
    print(f"🏟️ Regime 1: 'The Tired Favorite' (Rest <= 1 vs Opp Rest >= 3)")
    print(f"   - Baseline Favorite Win Rate: {base_rate_fav:.1%}")
    print(f"   - Tired Favorite Win Rate:    {win_rate_fatigue:.1%}")
    print(f"   - Impact: {win_rate_fatigue - base_rate_fav:.1%} (Negative means Upset likely)")
    print(f"   - Sample Size: {len(regime_fatigue)} games")

    # Regime 2: Momentum Shift
    # Favorite is Cold (Avg_V_4 < 0.3), Dog is Hot (Avg_V_o_4 > 0.7)
    favs['is_cold'] = favs['avg_V_4'] <= 0.4
    favs['opp_hot'] = favs['avg_V_o_4'] >= 0.7
    
    regime_momentum = favs[favs['is_cold'] & favs['opp_hot']]
    win_rate_mom = regime_momentum['is_win'].mean()
    
    print(f"\n🔥 Regime 2: 'Momentum Trap' (Fav Cold < 40%, Dog Hot > 70%)")
    print(f"   - Momentum Trap Win Rate: {win_rate_mom:.1%}")
    print(f"   - Impact: {win_rate_mom - base_rate_fav:.1%}") 
    print(f"   - Sample Size: {len(regime_momentum)} games")
    
    # Regime 3: Nemesis (Matchup)
    # Favorite has lost recent matchups? (score_last_10_between < 0?)
    # Validating col availability
    if 'score_last_10_between' in df.columns:
        # Assuming negative score means 'Team' is losing historically?
        favs['is_nemesis'] = favs['score_last_10_between'] < -5.0
        
        regime_nemesis = favs[favs['is_nemesis']]
        win_rate_nem = regime_nemesis['is_win'].mean()
        
        print(f"\n💀 Regime 3: 'Nemesis' (Historical Score Gap < -5)")
        print(f"   - Nemesis Win Rate: {win_rate_nem:.1%}")
        print(f"   - Impact: {win_rate_nem - base_rate_fav:.1%}")       
        print(f"   - Sample Size: {len(regime_nemesis)} games")

    print("\n⛏️ Mining for Hidden Gems (> 2% Impact)...\n")
    
    # 3. Divisional Dogs (Zone Rivalry)
    # Are Favorites more vulnerable in Divisional games?
    if 'Team_Zone' in df.columns:
        favs['is_divisional'] = favs['Team_Zone'] == favs['Opponent_Zone']
        
        regime_div = favs[favs['is_divisional']]
        win_rate_div = regime_div['is_win'].mean()
        impact = win_rate_div - base_rate_fav
        
        if abs(impact) > 0.02:
            print(f"🗺️ Regime 4: 'Divisional Dogfight' (Same Zone)")
            print(f"   - Win Rate: {win_rate_div:.1%}")
            print(f"   - Impact: {impact:.1%}")
            print(f"   - Interpretation: Rivals play harder? Favs struggle?")

    # 4. Defensive Dogs (Dog allows < 105 pts, Fav scores > 115 pts?)
    # Using 'avg_P_o_4' (Points Allowed Last 4)
    # Check if Dog has Good Defense
    if 'avg_P_o_4' in df.columns:
        # Note: These cols are for the 'Team' (Favorite in 'favs' df).
        # We need OPPONENT defense. 'avg_P_o_4' is "Points allowed by Team".
        # We want "Points allowed by Opponent".
        # The dataset has `avg_P_o_4` (Team's defense) and ... ??
        # Wait, does it have `opponent_avg_P_o_4`?
        # The sample showed `days_since_last_o`. Maybe `avg_P_o_4_o`?
        # Sample output showed `avg_P_o_4` but not opponent's version?
        # Wait, row has 'avg_V_o_4' (Victory Opponent).
        # Let's check keys again. 'avg_P_o_4' is listed. 
        # But 'avg_P_o_4' for opponent might be missing?
        # Use simpler proxy: 'avg_V_o_4' (Opponent Win Rate) -> Dog Form.
        pass

    # 5. Calendar Trends (Weekend vs Weekday)
    if 'weekday' in df.columns:
        # Weekday might be 'ma.' (Martes? Spanish dataset?).
        # Sample showed 'ma.'.
        for day in df['weekday'].unique():
            subset = favs[favs['weekday'] == day]
            wr = subset['is_win'].mean()
            imp = wr - base_rate_fav
            if abs(imp) > 0.02:
                 print(f"📅 Regime 5: 'Calendar Voodoo' ({day})")
                 print(f"   - Win Rate: {wr:.1%}")
                 print(f"   - Impact: {imp:.1%}")
    
    # 6. Season Phase (Month)
    if 'month' in df.columns:
        for m in df['month'].unique():
            subset = favs[favs['month'] == m]
            wr = subset['is_win'].mean()
            imp = wr - base_rate_fav
            if abs(imp) > 0.02:
                 print(f"🍂 Regime 6: 'Season Phase' ({m})")
                 print(f"   - Win Rate: {wr:.1%}")
                 print(f"   - Impact: {imp:.1%}")

if __name__ == "__main__":
    discover_regimes()
