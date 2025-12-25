import duckdb
import pandas as pd
import numpy as np
import os
from datetime import datetime

# Path to the Single Source of Truth
DB_PATH = "nba_sql.duckdb"

class RDataEngine:
    def __init__(self):
        print("🚀 Initializing RData Engine (DuckDB Architecture)...")
        self.conn = duckdb.connect(DB_PATH, read_only=True)
        # Nemesis Map (Pre-load for performance, or query on demand?)
        # Let's preload simple map
        self.nemesis_map = self._build_nemesis_map()
        
    def _build_nemesis_map(self):
        """Build Nemesis Map via SQL Aggregation"""
        try:
            # Get latest match for every pair
            query = """
                SELECT Team, Opponent, score_last_10_between
                FROM rdata_treasury
                QUALIFY ROW_NUMBER() OVER (PARTITION BY Team, Opponent ORDER BY Date DESC) = 1
            """
            df = self.conn.execute(query).df()
            mapping = {}
            for _, row in df.iterrows():
                key = f"{row['Team']}_vs_{row['Opponent']}"
                mapping[key] = row.get('score_last_10_between', 0.0)
            return mapping
        except Exception as e:
            print(f"⚠️ Error building Nemesis Map: {e}")
            return {}
        
    def get_team_name(self, team_identifier):
        # We need a robust way to convert ID to Name available in CSV.
        pass

    def _standardize_name(self, name):
        # Maps Tickers/Aliases -> Full Name (as stored in RData Treasury)
        nba_mapper = {
            # ATL
            'ATL': 'Atlanta Hawks', 'Hawks': 'Atlanta Hawks', 'Atlanta': 'Atlanta Hawks',
            # BOS
            'BOS': 'Boston Celtics', 'Celtics': 'Boston Celtics', 'Boston': 'Boston Celtics',
            # BKN
            'BKN': 'Brooklyn Nets', 'Nets': 'Brooklyn Nets', 'Brooklyn': 'Brooklyn Nets',
            # CHA
            'CHA': 'Charlotte Hornets', 'Hornets': 'Charlotte Hornets', 'Charlotte': 'Charlotte Hornets', 'CHH': 'Charlotte Hornets',
            # CHI
            'CHI': 'Chicago Bulls', 'Bulls': 'Chicago Bulls', 'Chicago': 'Chicago Bulls',
            # CLE
            'CLE': 'Cleveland Cavaliers', 'Cavaliers': 'Cleveland Cavaliers', 'Cleveland': 'Cleveland Cavaliers',
            # DAL
            'DAL': 'Dallas Mavericks', 'Mavericks': 'Dallas Mavericks', 'Dallas': 'Dallas Mavericks',
            # DEN
            'DEN': 'Denver Nuggets', 'Nuggets': 'Denver Nuggets', 'Denver': 'Denver Nuggets',
            # DET
            'DET': 'Detroit Pistons', 'Pistons': 'Detroit Pistons', 'Detroit': 'Detroit Pistons',
            # GSW
            'GSW': 'Golden State Warriors', 'Warriors': 'Golden State Warriors', 'Golden State': 'Golden State Warriors',
            # HOU
            'HOU': 'Houston Rockets', 'Rockets': 'Houston Rockets', 'Houston': 'Houston Rockets',
            # IND
            'IND': 'Indiana Pacers', 'Pacers': 'Indiana Pacers', 'Indiana': 'Indiana Pacers',
            # LAC
            'LAC': 'Los Angeles Clippers', 'Clippers': 'Los Angeles Clippers', 'L.A. Clippers': 'Los Angeles Clippers',
            # LAL
            'LAL': 'Los Angeles Lakers', 'Lakers': 'Los Angeles Lakers', 'L.A. Lakers': 'Los Angeles Lakers',
            # MEM
            'MEM': 'Memphis Grizzlies', 'Grizzlies': 'Memphis Grizzlies', 'Memphis': 'Memphis Grizzlies',
            # MIA
            'MIA': 'Miami Heat', 'Heat': 'Miami Heat', 'Miami': 'Miami Heat',
            # MIL
            'MIL': 'Milwaukee Bucks', 'Bucks': 'Milwaukee Bucks', 'Milwaukee': 'Milwaukee Bucks',
            # MIN
            'MIN': 'Minnesota Timberwolves', 'Timberwolves': 'Minnesota Timberwolves', 'Minnesota': 'Minnesota Timberwolves',
            # NOP
            'NOP': 'New Orleans Pelicans', 'Pelicans': 'New Orleans Pelicans', 'New Orleans': 'New Orleans Pelicans',
            # NYK
            'NYK': 'New York Knicks', 'Knicks': 'New York Knicks', 'New York': 'New York Knicks',
            # OKC
            'OKC': 'Oklahoma City Thunder', 'Thunder': 'Oklahoma City Thunder', 'Oklahoma City': 'Oklahoma City Thunder',
            # ORL
            'ORL': 'Orlando Magic', 'Magic': 'Orlando Magic', 'Orlando': 'Orlando Magic',
            # PHI
            'PHI': 'Philadelphia 76ers', '76ers': 'Philadelphia 76ers', 'Philadelphia': 'Philadelphia 76ers',
            # PHX
            'PHX': 'Phoenix Suns', 'Suns': 'Phoenix Suns', 'Phoenix': 'Phoenix Suns',
            # POR
            'POR': 'Portland Trail Blazers', 'Trail Blazers': 'Portland Trail Blazers', 'Portland': 'Portland Trail Blazers',
            # SAC
            'SAC': 'Sacramento Kings', 'Kings': 'Sacramento Kings', 'Sacramento': 'Sacramento Kings',
            # SAS
            'SAS': 'San Antonio Spurs', 'Spurs': 'San Antonio Spurs', 'San Antonio': 'San Antonio Spurs',
            # TOR
            'TOR': 'Toronto Raptors', 'Raptors': 'Toronto Raptors', 'Toronto': 'Toronto Raptors',
            # UTA
            'UTA': 'Utah Jazz', 'Jazz': 'Utah Jazz', 'Utah': 'Utah Jazz',
            # WAS
            'WAS': 'Washington Wizards', 'Wizards': 'Washington Wizards', 'Washington': 'Washington Wizards'
        }
        return nba_mapper.get(name, name)

    def _resolve_name(self, tid):
        try:
            import json
            with open("quant_engine_v1/team_map.json") as f:
                tmap = json.load(f)
                id_map = {str(v): k for k, v in tmap.items()}
                raw_name = id_map.get(str(tid), str(tid))
                return self._standardize_name(raw_name)
        except:
            return str(tid)

    def _get_latest_metrics(self, team_name, date_str, opp_name=None):
        try:
            # SQL: Calculate Rolling Stats On-The-Fly
            # We want stats *prior* to the game date
            
            # Base Query parameters
            params = [team_name, date_str]
            
            # Nemesis Subquery Setup
            nemesis_select = ""
            if opp_name:
                nemesis_select = """,
                    (SELECT avg(Points - OpponentPoints) FROM (SELECT Points, OpponentPoints FROM rdata_treasury WHERE Team = ? AND Opponent = ? AND Date < ? ORDER BY Date DESC LIMIT 10)) as score_last_10_between,
                    (SELECT avg(Points - OpponentPoints) FROM (SELECT Points, OpponentPoints FROM rdata_treasury WHERE Team = ? AND Opponent = ? AND Date < ? ORDER BY Date DESC LIMIT 5)) as score_last_5_between
                """
                # Add params for Nemesis (Team, Opp, Date, Team, Opp, Date)
                params.extend([team_name, opp_name, date_str, team_name, opp_name, date_str])

            query = f"""
                WITH hist AS (
                    SELECT Points, OpponentPoints, Date, (Points - OpponentPoints) as Margin
                    FROM rdata_treasury 
                    WHERE Team = ? AND Date < ? 
                    ORDER BY Date DESC
                )
                SELECT 
                    (SELECT avg(Margin) FROM (SELECT Margin FROM hist LIMIT 32)) as NetRtg_Sea,
                    (SELECT avg(Margin) FROM (SELECT Margin FROM hist LIMIT 10)) as NetRtg_L10,
                    (SELECT (avg(Points) + avg(OpponentPoints))/2 FROM (SELECT Points, OpponentPoints FROM hist LIMIT 32)) as Pace_Sea,
                    (SELECT stddev(Margin) FROM (SELECT Margin FROM hist LIMIT 32)) as Vol_Sea,
                    (SELECT avg(CASE WHEN Margin > 0 THEN 1.0 ELSE 0.0 END) FROM (SELECT Margin FROM hist LIMIT 32)) as avg_V_32,
                    (SELECT avg(CASE WHEN Margin > 0 THEN 1.0 ELSE 0.0 END) FROM (SELECT Margin FROM hist LIMIT 10)) as avg_V_10,
                    (SELECT Date FROM hist LIMIT 1) as LastGameDate,
                    (SELECT avg(Points) FROM (SELECT Points FROM hist LIMIT 4)) as avg_P_4,
                    (SELECT avg(OpponentPoints) from (SELECT OpponentPoints FROM hist LIMIT 4)) as avg_P_o_4,
                    (SELECT avg(OpponentPoints) from (SELECT OpponentPoints FROM hist LIMIT 4)) as avg_P_opp_4, 
                    (SELECT avg(Margin) from (SELECT Margin FROM hist LIMIT 4)) as avg_diff_P_o_4 
                    {nemesis_select}
            """
            
            df = self.conn.execute(query, params).df()
            
            if df.empty or pd.isna(df.iloc[0]['NetRtg_Sea']): 
                print(f"DEBUG SQL FAIL: No history for '{team_name}' before {date_str}")
                return None
            
            row = df.iloc[0].to_dict()
            
            # Rename keys for compatibility
            row['Team'] = team_name
            row['Date'] = row['LastGameDate']
            
            # --- Legacy Aliases for Profile Engine ---
            row['avg_diff_P_32'] = row['NetRtg_Sea']
            row['avg_diff_P_10'] = row['NetRtg_L10'] 
            row['avg_V_32'] = row['avg_V_32']
            row['avg_diff_P_4'] = row.get('avg_diff_P_o_4', 0.0) 
            
            # CRITICAL ALIASES FOR PROFILE ENGINE (v4.5)
            row['pace_sea'] = row.get('Pace_Sea', 100.0)
            row['pace_sea_opp'] = 100.0 # Will be overwritten by analyze_matchup logic or away team lookup 
            
            # Use 0.0 for Nemesis if None (No history)
            if 'score_last_10_between' in row and pd.isna(row['score_last_10_between']):
                row['score_last_10_between'] = 0.0
            if 'score_last_5_between' in row and pd.isna(row['score_last_5_between']):
                row['score_last_5_between'] = 0.0
            
            # Fill NaNs with defaults
            if pd.isna(row['Vol_Sea']): row['Vol_Sea'] = 12.0
            if pd.isna(row['Pace_Sea']): row['Pace_Sea'] = 100.0
            
            return row
            
        except Exception as e:
            print(f"⚠️ Error calculating metrics for {team_name}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def analyze_matchup(self, home_id, away_id, date_str, odds=None, game_id=None):
        """
        Main Analysis Function.
        """
        # 1. Resolve Names (Standardized)
        h_name = self._resolve_name(home_id)
        a_name = self._resolve_name(away_id)
        
        if not h_name or not a_name:
            print(f"⚠️ Unknown Team IDs: {home_id}, {away_id}")
            return None

        # 2. Fetch Stats (SQL-based On-Fly with Nemesis)
        h_stats = self._get_latest_metrics(h_name, date_str, opp_name=a_name)
        a_stats = self._get_latest_metrics(a_name, date_str, opp_name=h_name)
        
        if not h_stats or not a_stats:
            print(f"⚠️ No RData for {h_name} or {a_name}")
            return None
            
        # 3. Calculate Core Metrics
        # Engine expects Standard Pace (~100).
        p_h = h_stats.get('Pace_Sea', 100)
        p_a = a_stats.get('Pace_Sea', 100)
        pace_avg = (p_h + p_a) / 2.0
        pace_factor = (pace_avg / 100.0)
        
        # Pace Adj to Margin (If game is faster, margin expands?)
        # Base implementation: (Pace - 100) * 0.1 per point of diff?
        # Actually, Logic: Higher Pace = Higher Scoring = Higher Variance?
        # Let's stick to the "Power Multiplier" logic:
        # Expected Margin = Raw Margin * (Pace / LeagueAvgPace)
        # But here we treat Pace Adj as additive term.
        # Simplified: If Pace > 100, add small bonus to Favorite? No.
        # Let's use: Pace makes the "Power Gap" wider.
        
        # --- Base Power ---
        # Hybrid Net Rating
        h_pow = (h_stats['NetRtg_Sea'] * 0.6) + (h_stats['NetRtg_L10'] * 0.4)
        a_pow = (a_stats['NetRtg_Sea'] * 0.6) + (a_stats['NetRtg_L10'] * 0.4)
        
        raw_margin = h_pow - a_pow
        
        # Pace Adjustment (Multiplicative Scaling turned Additive)
        # Adj = Raw * (PaceFactor - 1.0)
        pace_adj = raw_margin * (pace_factor - 1.0)
        
        # --- Home Court ---
        hca = 2.8 # Fixed 2025 standard
        
        # --- Rest ---
        # Rest Advantage (Dynamic Calc for Prediction)
        target_dt = pd.to_datetime(date_str)
        
        # Home
        h_last_date = pd.to_datetime(h_stats['Date'])
        
        h_rest = (target_dt - h_last_date).days
        if h_rest < 0: h_rest = 3 # Sanity check (if data mess up)
        
        # Away
        a_last_date = pd.to_datetime(a_stats['Date'])
        a_rest = (target_dt - a_last_date).days
        if a_rest < 0: a_rest = 3
        
        # Inject Opponent Stats for Profile Engine (Tempo Fix)
        h_stats['days_since_last'] = h_rest
        h_stats['days_since_last_o'] = a_rest
        h_stats['opp_pace_current_L4'] = a_stats.get('avg_P_4', 110.0) # Actual Opponent Pace
        h_stats['opp_pace_current_Sea'] = a_stats.get('Pace_Sea', 100.0)

        a_stats['days_since_last'] = a_rest
        a_stats['days_since_last_o'] = h_rest
        a_stats['opp_pace_current_L4'] = h_stats.get('avg_P_4', 110.0)
        a_stats['opp_pace_current_Sea'] = h_stats.get('Pace_Sea', 100.0)

        # Cap rest at 3 (diminishing returns)
        h_val = min(h_rest, 3)
        a_val = min(a_rest, 3)
        
        rest_diff = h_val - a_val
        rest_adj = rest_diff * 0.5 
        
        # --- Volatility ---
        # Volatility Penalty
        v_h = h_stats.get('Vol_Sea', 12.0)
        v_a = a_stats.get('Vol_Sea', 12.0)
        vol_avg = (v_h + v_a) / 2.0
        
        # Penalty: If Vol > 14, penalize the Favorite (Confidence Discount)
        vol_adj = 0.0
        if vol_avg > 14.0:
            penalty = (vol_avg - 14.0) * 0.3 
            current_margin = raw_margin + hca + rest_adj
            if current_margin > 0: vol_adj = -penalty
            else: vol_adj = penalty
            
        # --- Nemesis Bridge (Corrected) ---
        # Look up H vs A directly from SQL stats
        nemesis_val = h_stats.get('score_last_10_between', 0.0)
        # Handle nan in case SQL returned it
        if pd.isna(nemesis_val): nemesis_val = 0.0
        
        # Weight historical impact
        nemesis_adj = (nemesis_val / 10.0) * 0.1 
        
        # --- Final Expected Margin ---
        total_margin = raw_margin + pace_adj + hca + rest_adj + vol_adj + nemesis_adj
        
        # --- Edge Score Calculation ---
        # Softened Multiplier: 1.5 instead of 2.0
        edge_score = 50 + (total_margin * 1.5)
        edge_score = max(0, min(100, edge_score))
        
        # --- Risk Score ---
        # Based on Volatility and Stability
        risk_score = (vol_avg * 2.5) 
        if abs(total_margin) < 3.0: risk_score += 20 
        risk_score = max(0, min(100, risk_score))
        
        # --- Market Analysis ---
        market_line = odds.get('spread', 0.0) if odds else 0.0
        market_expect = -1 * market_line 
        delta = total_margin - market_expect
        
        # --- Signals ---
        signal = "RATIONAL"
        if delta > 3.0: signal = "HOME_UNDERVALUED"
        elif delta < -3.0: signal = "HOME_OVERVALUED"
        
        # --- Context / Game Type (V4.5 RESET) ---
        # "Summary Only" - No flow interference.
        game_type = "C_FAIR"
        # Logic: 
        # > 10 Delta -> Mispriced (Strong Value)
        # > 5 Delta -> Value
        # Risk > 60 -> Volatile
        
        abs_delta = abs(delta)
        
        if abs_delta >= 10.0:
            game_type = "A_MISPRICED"
        elif abs_delta >= 5.0:
            game_type = "B_VALUE"
        elif risk_score >= 60.0:
            game_type = "D_VOLATILE"
        else:
            game_type = "C_FAIR"
            
        # Twin Status: Removed from here. Twin Engine runs unconditionally upstream.
        # We just pass the risk level if needed, but Engine decides.
        twin_status = "QUIET" # Default to Quiet, let Vector Engine activate
            
        return {
            "edge_score": round(edge_score, 1),
            "risk_score": round(risk_score, 1),
            "game_type": game_type,
            "twin_alert": twin_status,
            "market_analysis": {
                "signal": signal,
                "delta": round(delta, 1),
                "market_line": market_line,
                "expected_margin": round(total_margin, 1),
                "reality_check": "PASS",
                "decomposition": {
                    "base_power": round(raw_margin, 1),
                    "pace_adj": round(pace_adj, 1),
                    "home_court": round(hca, 1),
                    "rest_adj": round(rest_adj, 1),
                    "volatility": round(vol_adj, 1),
                    "nemesis": round(nemesis_adj, 1)
                }
            },
            "metrics": {
                "volatility": round(vol_avg, 1),
                "pace": round(pace_avg, 1),
                "rest_home": round(h_rest, 1),
                "rest_away": round(a_rest, 1)
            },
            "home_stats": h_stats,
            "away_stats": a_stats,
            # --- Narrative Support ---
            # Inject Live Odds AND Dynamic Rest into Home Stats for Profile Engine
            # Profile Engine expects 'days_since_last' (Home) and 'days_since_last_o' (Opponent/Away)
            "raw_row": {
                **h_stats, 
                'odds': market_line,
                'days_since_last': h_rest,       # Dynamic Calc
                'days_since_last_o': a_rest      # Dynamic Calc
            } 
        }


