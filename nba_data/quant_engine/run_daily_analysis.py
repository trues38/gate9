from nba_data.quant_engine.quant_core import QuantDataManager, TeamStrengthEngine, MomentumEngine, FatigueEngine, MatchupEngine, InjuryEngine
import datetime
import pandas as pd
import argparse

def generate_daily_report(date_str=None):
    if not date_str:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
    print(f"\n🚀 SPO9 QUANT ENGINE REPORT - {date_str}")
    print("==================================================")
    
    dm = QuantDataManager()
    
    # Engines
    tse = TeamStrengthEngine(dm)
    me = MomentumEngine(dm)
    fe = FatigueEngine(dm)
    ie = InjuryEngine(dm)
    matchup = MatchupEngine(tse, me, fe, ie)
    
    # Get Schedule
    games_df = dm.get_schedule(date=date_str)
    
    if games_df.empty:
        print("No games scheduled.")
        return

    # Process each game
    for _, game in games_df.iterrows():
        home_id = game['home_team_id']
        away_id = game['away_team_id']
        
        # Look up names from DM (DimTeam)
        h_dim = dm.con.sql(f"SELECT name, abbreviation FROM dim_team WHERE team_id={home_id}").fetchone()
        a_dim = dm.con.sql(f"SELECT name, abbreviation FROM dim_team WHERE team_id={away_id}").fetchone()
        
        h_name = f"{h_dim[0]} ({h_dim[1]})" if h_dim else str(home_id)
        a_name = f"{a_dim[0]} ({a_dim[1]})" if a_dim else str(away_id)
        h_abbr = h_dim[1] if h_dim else str(home_id)
        a_abbr = a_dim[1] if a_dim else str(away_id)
        
        print(f"\n🏀 MATCHUP: {a_name} @ {h_name}")
        print("--------------------------------------------------")
        
        # Run Matchup Analysis
        anal = matchup.analyze_matchup(home_id, away_id, date_str)
        if not anal:
            print("   Insufficient data for analysis.")
            continue
            
        details = anal['details']
        
        # 1. Strength (Net Rating)
        h_net = anal['home_net']
        a_net = anal['away_net']
        net_edge = details['net_edge']
        print(f"[Strength]  {h_abbr}: {h_net:+.1f} | {a_abbr}: {a_net:+.1f} => Net Edge: {net_edge:+.1f} (Home)")

        # 2. Momentum (Last 5)
        # Fetch momentum scores independently for display
        h_mom_data = me.get_momentum_score(home_id, date_str)
        a_mom_data = me.get_momentum_score(away_id, date_str)
        
        h_mom = h_mom_data.get('momentum', 0.0)
        a_mom = a_mom_data.get('momentum', 0.0)
        mom_edge = details['mom_edge']
        
        hot_tag = ""
        if mom_edge > 5.0: hot_tag = f"🔥 {h_abbr} Hot"
        elif mom_edge < -5.0: hot_tag = f"🔥 {a_abbr} Hot"
        
        print(f"[Momentum]  {h_abbr} L5: {h_mom:+.1f} | {a_abbr} L5: {a_mom:+.1f} => Edge: {mom_edge:+.1f} {hot_tag}")
        
        # 3. Fatigue
        h_fat = details['fatigue_home']
        a_fat = details['fatigue_away']
        
        f_str = ""
        if h_fat > 0: f_str += f"⚠️ {h_abbr} Tired (-{h_fat}) "
        if a_fat > 0: f_str += f"⚠️ {a_abbr} Tired (-{a_fat}) "
        if not f_str: f_str = "None"
        
        print(f"[Fatigue]   {f_str}")

        # 4. Injury Impact
        h_inj = details['injury_home']
        a_inj = details['injury_away']
        
        i_str = ""
        if h_inj > 0: i_str += f"🚑 {h_abbr} Injured (-{h_inj:.1f}) "
        if a_inj > 0: i_str += f"🚑 {a_abbr} Injured (-{a_inj:.1f}) "
        if not i_str: i_str = "None"
        
        print(f"[Injury]    {i_str}")
        
        # 5. Prediction
        spread = anal['projected_spread'] # Negative = Home Fav (Home - Away Score) -> Wait.
        # Logic in Engine: spread = (Net*0.6) + ...
        # If Net is Positive (Home better), Spread is Positive.
        # Standard Spread format: Home -5.5 (Home favored by 5.5).
        # My formula produces a "Margin" (Home Score - Away Score).
        # So Positive Margin = Home Wins.
        
        winner = h_abbr if spread > 0 else a_abbr
        margin = abs(spread)
        
        print(f"[Matchup]   Proj Pace: {anal['projected_pace']:.1f}")
        print(f"[PREDICT]   👉 {winner} to Win by {margin:.1f}")
        print(f"            (Formula: Net {net_edge*0.6:+.1f} + Mom {mom_edge*0.4:+.1f} + Home {2.8} - Fat {h_fat-a_fat} - Inj {h_inj-a_inj:.1f})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, help="YYYY-MM-DD")
    args = parser.parse_args()
    generate_daily_report(args.date)
