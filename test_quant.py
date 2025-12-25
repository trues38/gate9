from nba_data.quant_engine.quant_core import QuantDataManager, TeamStrengthEngine, MomentumEngine, FatigueEngine

def test_engines():
    print("🔬 Testing Quant Engines...")
    dm = QuantDataManager()
    
    # 1. Team Strength
    tse = TeamStrengthEngine(dm)
    print("\n[Team Strength] Top 5 Net Rating:")
    print(tse.stats.sort_values('net_rating', ascending=False).head(5)[['net_rating', 'avg_ortg', 'avg_drtg']])
    
    # Check LAL (13)
    lal = tse.get_team_profile(13) # LAL ID might differ in ESPN. 
    # Use 13 (Lakers) as example.
    # Actually, dim_team has IDs. 
    # Let's find IDs first.
    teams_df = dm.con.sql("SELECT * FROM dim_team WHERE abbreviation = 'LAL'").df()
    if not teams_df.empty:
        lal_id = teams_df.iloc[0]['team_id']
        print(f"\n[LAL Profile] ID: {lal_id}")
        print(tse.get_team_profile(lal_id))
        
        # 2. Momentum
        me = MomentumEngine(dm)
        mom = me.get_momentum_score(lal_id)
        print(f"\n[LAL Momentum] Last 5 NetRtg: {mom:.2f}")
        
        # 3. Fatigue
        fe = FatigueEngine(dm)
        # Check today
        fatigue = fe.assess_fatigue(lal_id, "2025-12-11")
        print(f"\n[LAL Fatigue Dec 11] {fatigue}")

if __name__ == "__main__":
    test_engines()
