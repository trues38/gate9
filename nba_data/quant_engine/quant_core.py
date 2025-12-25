import duckdb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB_PATH = "nba_analytics.duckdb"

class QuantDataManager:
    def __init__(self, db_path=DB_PATH):
        self.con = duckdb.connect(db_path)
        
    def get_season_stats(self, season=2026):
        """Fetch average ORTG, DRTG, Pace for all teams."""
        query = f"""
        SELECT 
            team_id,
            AVG(ortg) as avg_ortg,
            AVG(drtg) as avg_drtg,
            AVG(ortg - drtg) as net_rating,
            AVG(pace) as avg_pace,
            COUNT(*) as games_played
        FROM fact_team_stats
        JOIN fact_game ON fact_team_stats.game_id = fact_game.game_id
        WHERE fact_game.season = {season}
        GROUP BY team_id
        """
        return self.con.sql(query).df().set_index('team_id')
    
    def get_team_momentum(self, team_id, date_str):
        """
        Calculate Momentum (L5 NetRtg) and Volatility (L5 StdDev).
        Uses Window Functions as requested.
        """
        # We need to look at games BEFORE the date_str
        query = f"""
        WITH team_trend AS (
            SELECT 
                s.team_id,
                g.date,
                (s.ortg - s.drtg) as net_rating,
                AVG(s.ortg - s.drtg) OVER (
                    PARTITION BY s.team_id 
                    ORDER BY g.date 
                    ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                ) as momentum,
                STDDEV(s.ortg - s.drtg) OVER (
                    PARTITION BY s.team_id 
                    ORDER BY g.date 
                    ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                ) as volatility
            FROM fact_team_stats s
            JOIN fact_game g ON s.game_id = g.game_id
            WHERE s.team_id = {team_id}
            ORDER BY g.date
        )
        SELECT * FROM team_trend 
        WHERE date < '{date_str}' 
        ORDER BY date DESC 
        LIMIT 1
        """
        df = self.con.sql(query).df()
        if df.empty:
            return {"momentum": 0.0, "volatility": 0.0}
        return df.iloc[0].to_dict()

    def get_schedule_window(self, team_id, date_str, days_lookback=7):
        """Get games in the lookback window for fatigue calc."""
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        start_date = target_date - timedelta(days=days_lookback)
        
        query = f"""
        SELECT date, venue_id FROM fact_game 
        WHERE (home_team_id = {team_id} OR away_team_id = {team_id})
        AND date BETWEEN '{start_date}' AND '{target_date}'
        ORDER BY date
        """
        return self.con.sql(query).df()


    def get_schedule(self, team_id=None, date=None):
        where_clause = []
        if team_id:
            where_clause.append(f"(home_team_id = {team_id} OR away_team_id = {team_id})")
        if date:
            where_clause.append(f"date = '{date}'")
        
        where_str = " AND ".join(where_clause) if where_clause else "1=1"
        
        query = f"""
        SELECT * FROM fact_game 
        WHERE {where_str}
        ORDER BY date
        """
        return self.con.sql(query).df()


    def get_injury_report(self, team_id, date_str):
        """Fetch active injuries for a team on a specific date."""
        # Join with dim_player if available, but for now just raw ID
        query = f"""
        SELECT player_id, status, details
        FROM fact_injury
        WHERE team_id = {team_id} AND report_date = '{date_str}'
        """
        try:
            return self.con.sql(query).df()
        except:
            return pd.DataFrame() # Return empty if table doesn't exist or error

    def get_player_impact_map(self):
        """
        Calculate Player Value (GameScore) for all players.
        GmSc = PTS + 0.4FG - 0.7FGA - 0.4(FTA-FT) + 0.7ORB + 0.3DRB + STL + 0.7AST + 0.7BLK - 0.4PF - TOV
        """
        query = """
        WITH avg_stats AS (
            SELECT 
                player_id,
                AVG(pts) as pts,
                AVG(fgm) as fgm, AVG(fga) as fga,
                AVG(ftm) as ftm, AVG(fta) as fta,
                AVG(oreb) as oreb,
                AVG(dreb) as dreb,
                AVG(ast) as ast,
                AVG(stl) as stl,
                AVG(blk) as blk,
                AVG(pf) as pf,
                AVG(tov) as tov,
                COUNT(*) as games
            FROM fact_boxscore
            GROUP BY player_id
            HAVING games >= 5
        )
        SELECT 
            player_id,
            (pts + 0.4*fgm - 0.7*fga - 0.4*(fta-ftm) + 0.7*oreb + 0.3*dreb + stl + 0.7*ast + 0.7*blk - 0.4*pf - tov) as gmsc
        FROM avg_stats
        """
        df = self.con.sql(query).df()
        return df.set_index('player_id')['gmsc'].to_dict()


class TeamStrengthEngine:
    def __init__(self, data_manager):
        self.dm = data_manager
        self.stats = self.dm.get_season_stats()
        
    def get_team_profile(self, team_id):
        if team_id not in self.stats.index:
            return None
        return self.stats.loc[team_id]

class MomentumEngine:
    def __init__(self, data_manager):
        self.dm = data_manager
        
    def get_momentum_score(self, team_id, date_str):
        """Return Momentum (L5 Net Rating) and Volatility."""
        return self.dm.get_team_momentum(team_id, date_str)

class FatigueEngine:
    def __init__(self, data_manager):
        self.dm = data_manager
        
    def calculate_fatigue_penalty(self, team_id, date_str):
        """
        Calculate Fatigue Penalty:
        - B2B (Back-to-Back): -3.0
        - 3-in-4 (3 Games in 4 Days): -2.5
        - 5-in-7 (5 Games in 7 Days): -2.0
        """
        # Lookback 7 days to cover all cases
        df = self.dm.get_schedule_window(team_id, date_str, days_lookback=7)
        if df.empty:
            return 0.0
            
        # Standardize dates
        df['date'] = pd.to_datetime(df['date'])
        target_date = pd.to_datetime(date_str)
        
        # Filter games strictly before game time
        past_games = df[df['date'] < target_date]['date'].tolist()
        
        penalty = 0.0
        
        # 1. Check B2B
        yesterday = target_date - timedelta(days=1)
        if yesterday in past_games:
            penalty += 3.0
            
        # 2. Check 3-in-4 (Target, T-1, T-2, T-3). 
        # Count for 3in4 (Last 3 days before today)
        g_3days = [d for d in past_games if d >= (target_date - timedelta(days=3))]
        if len(g_3days) >= 2: # Today makes 3
             penalty = max(penalty, 2.5)
             
        # Count for 5in7 (Last 6 days before today)
        g_6days = [d for d in past_games if d >= (target_date - timedelta(days=6))]
        if len(g_6days) >= 4: # Today makes 5
             penalty = max(penalty, 2.0)
             
        return penalty

class InjuryEngine:
    def __init__(self, data_manager):
        self.dm = data_manager
        self.player_values = self.dm.get_player_impact_map()
        self.REPLACEMENT_LEVEL = 10.0
        self.IMPACT_FACTOR = 0.4
        
    def get_injury_impact(self, team_id, date_str):
        """
        Calculate impact of missing players.
        Formula: Sum(max(0, (AvgGmSc - Replacement) * Factor)) for all OUT players.
        Example: SGA (30 GmSc). (30-10)*0.4 = 8.0 Penalty.
        """
        report_df = self.dm.get_injury_report(team_id, date_str)
        if report_df.empty:
            return 0.0
            
        total_penalty = 0.0
        
        for _, row in report_df.iterrows():
            pid = row['player_id']
            status = str(row['status']).lower()
            
            # Filter for confirmed OUT or DOUBTFUL
            if 'out' in status or 'doubtful' in status:
                gmsc = self.player_values.get(pid, self.REPLACEMENT_LEVEL)
                
                # Calculate value over replacement
                value_over_rep = max(0, gmsc - self.REPLACEMENT_LEVEL)
                
                # Apply Factor
                penalty = value_over_rep * self.IMPACT_FACTOR
                total_penalty += penalty
                
        return total_penalty

class MatchupEngine:
    def __init__(self, strength_engine, momentum_engine, fatigue_engine, injury_engine):
        self.se = strength_engine
        self.me = momentum_engine
        self.fe = fatigue_engine
        self.ie = injury_engine
        
    def analyze_matchup(self, home_id, away_id, date_str):
        home_base = self.se.get_team_profile(home_id)
        away_base = self.se.get_team_profile(away_id)
        
        if home_base is None or away_base is None:
            return None
            
        # 1. Net Rating Edge
        home_net = home_base['net_rating']
        away_net = away_base['net_rating']
        net_edge = home_net - away_net
        
        # 2. Momentum Edge
        h_mom = self.me.get_momentum_score(home_id, date_str)
        a_mom = self.me.get_momentum_score(away_id, date_str)
        
        mom_edge = h_mom['momentum'] - a_mom['momentum']
        
        # 3. Fatigue Penalty
        h_fatigue = self.fe.calculate_fatigue_penalty(home_id, date_str)
        a_fatigue = self.fe.calculate_fatigue_penalty(away_id, date_str)
        fatigue_diff = h_fatigue - a_fatigue # If Home tired (-3), Away fresh (0) -> -3 net for Home
        
        # 4. Injury Impact (Placeholder)
        h_inj = self.ie.get_injury_impact(home_id, date_str)
        a_inj = self.ie.get_injury_impact(away_id, date_str)
        inj_diff = h_inj - a_inj
        
        # 5. Projection Formula
        # Spread = (NetEdge * 0.6) + (MomEdge * 0.4) + 2.8 - FatigueDiff
        # Note: FatigueDiff is (HomeFatigue - AwayFatigue). Since penalties are positive numbers in user prompt?
        # User: "Fatigue Penalty: -3.0". So if Home has penalty, we ADD -3.0.
        # If HomeFatigue = 3.0 (penalty value), then formula should likely be:
        # Score = ... - HomeFatigue + AwayFatigue
        # Let's align signs. 
        # My Code returns Positive Penalty (3.0).
        # So: - H_Fatigue + A_Fatigue.
        
        # 4. Injury Impact
        h_injury = self.ie.get_injury_impact(home_id, date_str)
        a_injury = self.ie.get_injury_impact(away_id, date_str)
        injury_diff = h_injury - a_injury

        home_adv = 2.8
        
        # Pace
        avg_pace = (home_base['avg_pace'] + away_base['avg_pace']) / 2.0
        
        # Formula: Net(60%) + Mom(40%) + HCA - FatigueDiff - InjuryDiff
        # Note: h_fatigue is a positive penalty value (e.g. 3.0), so we subtract it from Home's score.
        projected_spread = (net_edge * 0.6) + (mom_edge * 0.4) + home_adv - (h_fatigue - a_fatigue) - (h_injury - a_injury)
        
        return {
            "home_team": home_id,
            "away_team": away_id,
            "projected_spread": projected_spread,
            "projected_pace": avg_pace,
            "home_net": home_net,
            "away_net": away_net,
            "details": {
                "net_edge": net_edge,
                "mom_edge": mom_edge,
                "fatigue_home": h_fatigue,
                "fatigue_away": a_fatigue,
                "injury_home": h_injury,
                "injury_away": a_injury,
                "home_adv": home_adv
            }
        }

