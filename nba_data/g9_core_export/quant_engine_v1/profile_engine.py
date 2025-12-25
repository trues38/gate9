# profile_engine.py
# Implements "Report Engine v4" Profile Logic
# Strict Python Mapping from RData -> Profile JSON

class ProfileEngine:
    """
    Engine for generating the 5-Dimension Profile (Flow, Fatigue, Memory, Luck, Tempo)
    """
    def __init__(self):
        pass

    def build_profiles(self, row):
        """
        Alias for build_game_profile (for consistency with other engines)
        """
        return self.build_game_profile(row)

    def build_game_profile(self, row):
        """
        Constructs the 5-Dimension Profile for a single game row.
        Input: RData Row (dict) with injected 'odds'.
        Output: JSON-serializable dict with Profile states.
        """
        
        profiles = {}
        
        # ----------------------------------------------
        # 1. FLOW PROFILE (Current Form vs Season Baseline)
        # ----------------------------------------------
        # flow_gap = avg_diff_P_4 - avg_diff_P_32
        d4 = row.get('avg_diff_P_4', 0)
        d32 = row.get('avg_diff_P_32', 0)
        flow_gap = d4 - d32
        
        flow_state = "NEUTRAL"
        if flow_gap >= 4: flow_state = "STRONG_UP"
        elif flow_gap >= 2: flow_state = "UP"
        elif flow_gap <= -4: flow_state = "COLLAPSE"
        elif flow_gap <= -2: flow_state = "DOWN"
        
        profiles["FLOW"] = {
            "state": flow_state,
            "strength": round(abs(flow_gap), 2),
            "evidence": f"Gap {flow_gap:+.1f} (L4 {d4:+.1f} vs L32 {d32:+.1f})"
        }

        # ----------------------------------------------
        # 2. FATIGUE PROFILE (Rest vs Opponent Rest)
        # ----------------------------------------------
        # rest_diff = days_since_last - days_since_last_o
        rest = row.get('days_since_last', 0)
        rest_o = row.get('days_since_last_o', 0)
        rest_diff = rest - rest_o
        
        fatigue_state = "NEUTRAL"
        if rest_diff >= 2: fatigue_state = "FRESH_ADV"
        elif rest_diff == 1: fatigue_state = "SLIGHT_ADV"
        elif rest_diff == -1: fatigue_state = "SLIGHT_DIS"
        elif rest_diff <= -2: fatigue_state = "DEAD_LEGS"
        
        profiles["FATIGUE"] = {
            "state": fatigue_state,
            "strength": round(abs(rest_diff), 1),
            "evidence": f"Rest Diff {rest_diff:+.0f} (H {rest} vs A {rest_o})"
        }

        # ----------------------------------------------
        # 3. MEMORY PROFILE (Matchup History)
        # ----------------------------------------------
        # memory_score = 0.7 * L10 + 0.3 * L5
        s10 = row.get('score_last_10_between', 0)
        s5 = row.get('score_last_5_between', 0)
        mem_score = (s10 * 0.7) + (s5 * 0.3)
        
        mem_state = "NEUTRAL"
        if mem_score >= 6: mem_state = "DOMINATOR"
        elif mem_score >= 3: mem_state = "EDGE"
        elif mem_score <= -6: mem_state = "PREY"
        elif mem_score <= -3: mem_state = "WEAK"
        
        profiles["MEMORY"] = {
            "state": mem_state,
            "strength": round(abs(mem_score), 1),
            "evidence": f"Matchup Score {mem_score:+.1f} (L10 {s10} / L5 {s5})"
        }

        # ----------------------------------------------
        # 4. MARKET PROFILE (Expectation Mismatch)
        # ----------------------------------------------
        # market_gap = avg_V_32*100 - (avg_diff_P_32 * 2 + 50)
        # Checks if Win% is justified by NetRating
        v32 = row.get('avg_V_32', 0.5)
        diff32 = row.get('avg_diff_P_32', 0)
        odds_val = row.get('odds', 0) # Used for context in evidence?
        
        market_gap = (v32 * 100) - ((diff32 * 2) + 50)
        expected_win = (diff32 * 2) + 50
        
        market_state = "FAIR"
        if market_gap >= 8: market_state = "LUCKY" # Winning more than stats say
        elif market_gap >= 4: market_state = "GOOD_VAR"
        elif market_gap <= -8: market_state = "UNLUCKY" # Losing more than stats say
        elif market_gap <= -4: market_state = "BAD_VAR"
        
        profiles["LUCK"] = {
            "state": market_state,
            "strength": round(abs(market_gap), 1),
            "evidence": f"Gap {market_gap:+.1f} (Rec {v32*100:.0f}% vs Exp {expected_win:.0f}%)"
        }

        # ----------------------------------------------
        # 5. TEMPO PROFILE (Relative Speed Difference) V4.5 RESET
        # ----------------------------------------------
        # pace_diff = pace_home - pace_away
        # No more absolute "TRACK_MEET". Only relative.
        
        p_h = row.get('pace_sea', 100.0)
        p_a = row.get('pace_sea_opp', 100.0)
        
        # If missing, fallback to Pts/0.95 (Rough Est) or just 0 diff
        if p_h == 100.0 and row.get('avg_P_16'):
            p_h = row.get('avg_P_16', 100)
        if p_a == 100.0 and row.get('avg_P_o_16'): 
            pass

        tempo_diff = p_h - p_a
        
        tempo_state = "EVEN_PACE"
        if tempo_diff >= 4.0: tempo_state = "FAST_EDGE"
        elif tempo_diff <= -4.0: tempo_state = "SLOW_TRAP"
        
        profiles["TEMPO"] = {
            "state": tempo_state,
            "strength": round(abs(tempo_diff), 1),
            "evidence": f"Diff {tempo_diff:+.1f} (Home {p_h:.1f} vs Away {p_a:.1f})"
        }
        
        # INJECT SCORES FOR VECTORIZATION
        profiles['FLOW']['score'] = flow_gap
        profiles['FATIGUE']['score'] = rest_diff
        profiles['MEMORY']['score'] = mem_score
        profiles['LUCK']['score'] = market_gap
        profiles['TEMPO']['score'] = tempo_diff

        return profiles
