import pandas as pd

def verify_math():
    print("🔍 Loading features_2025.csv...")
    df = pd.read_csv('processed/features_2025.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Pick a team with enough games
    team = 'Boston Celtics' # Or any active team
    df_team = df[df['Team'] == team].sort_values('Date').reset_index(drop=True)
    
    if df_team.empty:
        print(f"❌ Team {team} not found.")
        return

    print(f"📊 Tracing Rolling Logic for {team} (avg_V_4)...")
    
    # Show first 10 games
    cols = ['Date', 'Opponent', 'Points', 'OpponentPoints', 'V', 'avg_V_4']
    print(df_team[cols].head(8))
    
    print("\n🧮 Manual Check:")
    # Check Game 5 (Index 4)
    # avg_V_4 for Game 5 should be Mean(V) of Games 1,2,3,4 (Indices 0,1,2,3)
    
    if len(df_team) > 5:
        slice_v = df_team.loc[0:3, 'V']
        manual_mean = slice_v.mean()
        calc_val = df_team.loc[4, 'avg_V_4']
        
        print(f"   Games 1-4 Wins: {slice_v.tolist()}")
        print(f"   Manual Mean: {manual_mean:.4f}")
        print(f"   Calculated:  {calc_val:.4f}")
        
        if abs(manual_mean - calc_val) < 0.0001:
            print("   ✅ MATCH: Calculation is perfect.")
        else:
            print(f"   ❌ MISMATCH: {manual_mean} vs {calc_val}")
            
        # Check Lag Logic
        # avg_V_4 at Index 0 should be NaN or handled by min_periods?
        # Helper set min_periods=1.
        # So Index 0 -> shift(1) is NaN. So Index 0 avg_V_4 should be NaN (First game has no history).
        # Wait, min_periods=1 on [NaN] is NaN.
        # Index 1 -> shift(1) is Game 0. Mean(Game 0).
        val_idx_1 = df_team.loc[1, 'avg_V_4']
        val_game_0 = df_team.loc[0, 'V']
        print(f"\n   Game 2 Check (Should equal Game 1 result):")
        print(f"   Game 1 Result: {val_game_0}")
        print(f"   Game 2 avg_V_4: {val_idx_1}")
        
    else:
        print("Not enough games to test.")

if __name__ == "__main__":
    verify_math()
