# Quant Engine V1: Cache-Based Fusion
# This is the Phase 7/8 Core Engine
import json
import os
from datetime import datetime
from regime_weights import REGIME_WEIGHTS  # Fix relative import for direct run

CACHE_DIR = "/Users/js/g9/nba_data/quant_engine_v1/quant_cache"

class CacheFusionEngine:
    def __init__(self):
        print("Initializing Cache-Based Fusion Engine...")
        self.cache = self._load_all_caches()
        
    def _load_all_caches(self):
        cache = {}
        files = {
            "net_rating": "net_rating.json",
            "pace": "pace.json",
            "volatility": "volatility.json",
            "rest": "rest_days.json"
        }
        
        # 1. Load Legacy Caches (Optional fallback, can be empty if not present)
        for key, fname in files.items():
            path = os.path.join(CACHE_DIR, fname)
            if os.path.exists(path):
                with open(path, 'r') as f:
                    cache[key] = json.load(f)
            else:
                cache[key] = {} # Safe empty
        
        # 2. Load Unified Team Stats (The RData SSOT)
        ts_path = os.path.join(CACHE_DIR, 'team_stats_live.json')
        if os.path.exists(ts_path):
            with open(ts_path, 'r') as f:
                self.team_stats = json.load(f)
        else:
            print("⚠️ Warning: Team Stats Live cache missing. Metrics will be default.")
            self.team_stats = {}

        # 3. Load Momentum Cache (Live)
        momentum_path = os.path.join(CACHE_DIR, 'momentum_live.json')
        if os.path.exists(momentum_path):
            with open(momentum_path, 'r') as f:
                self.momentum_map = json.load(f)
        else:
            self.momentum_map = {}
            
        # 4. Load Nemesis Cache (Live)
        nemesis_path = os.path.join(CACHE_DIR, 'nemesis_live.json')
        if os.path.exists(nemesis_path):
            with open(nemesis_path, 'r') as f:
                self.nemesis_map = json.load(f)
        else:
            self.nemesis_map = {}
             
        # 5. Load Regime Stats (G9 Upset Engine)
        regime_path = os.path.join(CACHE_DIR, "..", "regime_stats.json")
        if os.path.exists(regime_path):
             with open(regime_path, 'r') as f:
                 cache['regime_stats'] = json.load(f)
        else:
             cache['regime_stats'] = {}
             
        return cache

    def get_stat(self, team_id, key, default=0.0):
        """Helper to get metric from Unified Team Stats"""
        tid = str(team_id)
        if tid in self.team_stats:
            val = self.team_stats[tid].get(key, default)
            return float(val)
        return float(default)
        
    def get_quant_metrics(self, team_id, target_date_iso):
        tid = str(team_id)
        
        # Calculates Rest Days relative to Target Date
        last_date_str = self.cache['rest'].get(tid, "2000-01-01")
        try:
            last = datetime.strptime(last_date_str, "%Y-%m-%d")
            target = datetime.strptime(target_date_iso, "%Y-%m-%d")
            delta = (target - last).days
            rest_days = max(0, delta - 1) # if last game yesterday (delta=1), rest=0.
        except:
            rest_days = 2 # Default assumption if error
            
        return {
            "net_rating": self.cache['net_rating'].get(tid, 0.0),
            "pace": self.cache['pace'].get(tid, 98.0),
            "volatility": self.cache['volatility'].get(tid, 10.0),
            "rest_days": rest_days
        }

    def _get_team_metrics(self, team_id, target_date_iso):
        # This is a helper method to fetch metrics for a single team
        # It's essentially the old get_quant_metrics, but renamed for clarity
        return self.get_quant_metrics(team_id, target_date_iso)

    
    def get_upset_regime(self, market_line, home_stats, away_stats):
        """
        Determines Historical Upset Regime (Tier 1-4) and Context Tags.
        Returns dict with Tier, Base Rate, Specific Rate, and Tags.
        """
        # 1. Determine Favorite & Odds Proxy
        # We don't have exact odds here, but we have Spread.
        # Approx Mapping: 
        # -4.5 ~ -6.0 -> Tier 1
        # -6.5 ~ -9.0 -> Tier 2
        # -9.5 ~ -12.0 -> Tier 3
        # -13.0+ -> Tier 4
        
        abs_line = abs(market_line)
        is_home_fav = market_line < 0
        
        tier = "0"
        if abs_line >= 13.0: tier = "4"
        elif abs_line >= 9.5: tier = "3"
        elif abs_line >= 6.5: tier = "2"
        elif abs_line >= 4.5: tier = "1"
        
        if tier == "0":
            return None # Not a regime scenario
            
        stats = self.cache.get('regime_stats', {}).get(tier, {})
        if not stats: return None
        
        # 2. Tagging Logic (Must match build_upset_regimes.py)
        tags = []
        
        # Data Mappings
        if is_home_fav:
            fav = home_stats
            und = away_stats
        else:
            fav = away_stats
            und = home_stats
            
        # 2.1 Fatigue Trap: Fav Tired (Rest <=1) vs Und Fresh (Rest >=2) + Fav Bad Form?
        # We don't have rolling Form in standard stats block yet, assume available or proxy.
        # We only have 'rest_days'. Use that.
        if fav.get('rest_days', 2) <= 1 and und.get('rest_days', 2) >= 2:
            tags.append("Fatigue Trap")
            
        # 2.2 Hot Underdog: Und is surging?
        # We can leverage 'net_rating' or recent L10 if available. 
        # Current cache has 'net_rating'. If Und NetRtg > -2.0 (Competent)? or Check Edge Score?
        # Let's use a proxy: If Net Rating Diff is small (< 5) despite Line being large?
        pass # Hard to strict match without rolling logs.
        
        # 2.3 Nemesis
        # Hard to do without H2H history.
        
        # 3. Lookup Probs
        # Default to Base
        base_rate = stats['base_stats']['rate']
        final_rate = base_rate
        active_regime = "Standard"
        
        # Apply Tags Hierarchy (Fatigue > Others)
        if "Fatigue Trap" in tags:
            r_data = stats['regimes'].get('Fatigue Trap', {})
            if r_data:
                final_rate = r_data['rate']
                active_regime = "Fatigue Trap"
                
        return {
            "tier": tier,
            "label": stats['label'],
            "base_rate": base_rate,
            "final_rate": final_rate,
            "active_regime": active_regime,
            "tags": tags
        }
        
    
    def _calc_sched_stress(self, rest_days: int) -> float:
        # Example: More rest days = less stress, 0-1 scale
        if rest_days >= 3:
            return 0.0
        elif rest_days == 2:
            return 0.2
        elif rest_days == 1:
            return 0.5
        else: # 0 rest days (back-to-back)
            return 1.0

    def analyze_matchup(self, home_id, away_id, date_str, odds=None, game_id=None):
        """
        Full Quant Analysis for a single matchup.
        Now includes Decomposed Expected Margin Logic & Regime Weights.
        """
        # 1. Fetch Core Stats (From Unified Cache)
        h = {
            'net_rtg': self.get_stat(home_id, 'net_rating', 0.0),
            'net_rtg_l10': self.get_stat(home_id, 'net_rating_l10', 0.0),
            'pace': self.get_stat(home_id, 'pace', 100.0),
            'volatility': self.get_stat(home_id, 'volatility', 12.0),
            'rest_days': self.momentum_map.get(str(home_id), {}).get('days_since_last', 2)
        }
        a = {
            'net_rtg': self.get_stat(away_id, 'net_rating', 0.0),
            'net_rtg_l10': self.get_stat(away_id, 'net_rating_l10', 0.0),
            'pace': self.get_stat(away_id, 'pace', 100.0),
            'volatility': self.get_stat(away_id, 'volatility', 12.0),
            'rest_days': self.momentum_map.get(str(away_id), {}).get('days_since_last', 2)
        }
        
        # if not h or not a: # This check is no longer needed with default values
        #     return None
        
        # --- Helper for Net Rating Extraction ---
        # This helper is now simplified as stats are directly fetched
        # def get_net_vals(obj):
        #     if isinstance(obj, dict):
        #         return obj.get('season', 0.0), obj.get('l10', 0.0)
        #     val = float(obj or 0.0)
        #     return val, val # Fallback if cache old

        h_sea, h_l10 = h['net_rtg'], h['net_rtg_l10']
        a_sea, a_l10 = a['net_rtg'], a['net_rtg_l10']
        
        # Calculate Hybrid Power for Edge Score AND Decomposition
        # Hybrid: 60% Season, 40% L10
        h_power = (0.6 * h_sea) + (0.4 * h_l10)
        a_power = (0.6 * a_sea) + (0.4 * a_l10)
        
        # Power Gap implies Home Adv. 
        net_diff = h_power - a_power
        
        # --- REGIME IMPACT ANALYSIS ---
        regime_impact_score = 0.0
        
        # 1. Calendar Regimes
        dto = datetime.strptime(date_str, "%Y-%m-%d")
        if dto.month == 6:
            regime_impact_score += REGIME_WEIGHTS["calendar_june"]
        elif dto.month == 5:
            regime_impact_score += REGIME_WEIGHTS["calendar_may"]
            
        # 2. Nemesis Regime (History < -5)
        # Note: Nemesis impact in table is Negative (Upset).
        # We need to know WHO is the Favorite.
        # We assume Edge Score tracks "Home Probability".
        
        # --- LIVE FEATURE LOOKUP (Phase 8: Bridge Data) ---
        # 1. Get Live Momentum & Rest
        h_live = self.momentum_map.get(str(home_id), {})
        a_live = self.momentum_map.get(str(away_id), {})
        
        # Use Live Rest if available, otherwise fallback
        # Note: Live Rest in map is "days since last game" calculated at build time.
        # Ideally we calculate it dynamically: (TargetDate - LastDate).
        # But build_live_cache stores "days_since_last" which is valid for *today's* run.
        # If TargetDate is tomorrow, we might need +1? 
        # For this version, we trust the builder (which ran for "Next Game").
        rest_h_val = float(h_live.get('days_since_last', h.get('rest_days', 1)))
        rest_a_val = float(a_live.get('days_since_last', a.get('rest_days', 1)))
        
        # Momentum (avg_V_4)
        h_mom = float(h_live.get('avg_V_4', 0.5))
        a_mom = float(a_live.get('avg_V_4', 0.5))
        
        # --- REGIME IMPACT ANALYSIS ---
        regime_impact_score = 0.0
        
        # 1. Calendar Regimes
        dto = datetime.strptime(date_str, "%Y-%m-%d")
        if dto.month == 6:
            regime_impact_score += REGIME_WEIGHTS["calendar_june"]
        elif dto.month == 5:
            regime_impact_score += REGIME_WEIGHTS["calendar_may"]
            
        # 2. Nemesis Regime (History < -5)
        # Use LIVE Nemesis Bridge Map
        pair_key = f"{home_id}_{away_id}"
        nemesis_val = self.nemesis_map.get(pair_key, 0.0)
        
        # If Nemesis Value is Negative (< -5.0), Home is struggling.
        # Only apply if Home is Favorite (Implicit or Explicit).
        # User defined: "If market_favorite and nemesis_active".
        # We use `odds` argument if available, or assume Home Fav if unknown.
        is_home_fav = True
        if odds:
            # Check odds if provided (e.g. -4.5)
            # If string "-4.5", parse.
            try:
                if str(odds).startswith("-"): is_home_fav = True
                elif str(odds).startswith("+"): is_home_fav = False
            except: pass
            
        if is_home_fav and nemesis_val < -5.0:
            regime_impact_score += (REGIME_WEIGHTS["nemesis"]) # Negative impact
        
        # 3. Momentum Trap (Real V_4 Data)
        # Fav Cold (Win% < 40%), Dog Hot (Win% > 70%).
        if is_home_fav:
            if h_mom <= 0.40 and a_mom >= 0.70:
                regime_impact_score += REGIME_WEIGHTS["momentum_trap"]
        else:
             # If Away is Fav? (Not defined in simple logic, but symmetric)
             pass
             
        # --- MODIFIED EDGE SCORE LOGIC (User Approved) ---
        HOME_ADV_CONST = 2.8
        
        def get_rest_factor(days):
            if days == 0: return -3.5 # B2B Hell
            if days == 1: return 0.0  # Normal
            if days == 2: return 1.5  # Optimal
            if days >= 3: return 1.0  # Rust Risk
            return 0.0
            
        rest_h = get_rest_factor(rest_h_val) 
        rest_a = get_rest_factor(rest_a_val)
        
        # Net Rating Differential (Hybrid Power)
        net_diff = h_power - a_power
        
        # Regime Impact to Margin
        regime_margin_impact = regime_impact_score * 50.0
        
        predicted_margin = net_diff + HOME_ADV_CONST + (rest_h - rest_a) + regime_margin_impact
        
        # Edge Score conversion
        edge_score = 50 + (predicted_margin * 2.0)
        edge_score = max(0, min(100, edge_score))
        
        # 2. Risk Score (Volatility based)
        h_vol = h['volatility']
        a_vol = a['volatility']
        vol = (h_vol + a_vol) / 2.0
        
        # Risk Formula: Base 20 + Vol * 1.5
        # If High Regime Impact, Risk should Increase?
        risk_adjust = abs(regime_impact_score * 100.0 * 0.5) 
        
        risk_score = 20 + (vol * 1.5) + risk_adjust
        
        # 4. Schedule Stress (0-1.0)
        h_stress = self._calc_sched_stress(h['rest_days'])
        a_stress = self._calc_sched_stress(a['rest_days'])
        
        # 5. Game Classification (The Decision Layer)
        game_type = "C_NEUTRAL"
        
        # Logic Tree
        if risk_score > 35:
            if edge_score > 60: game_type = "B_RISKY_FAVORITE"
            elif edge_score < 40: game_type = "D_UPSET_ZONE" # High risk, Low Edge (Fav is Away or close)
            else: game_type = "D_UPSET_ZONE" # High Risk Neutral -> Chaos
        else:
            # Low Risk
            if edge_score > 60: game_type = "A_SAFE_FAVORITE"
            elif edge_score < 40: game_type = "E_SAFE_UNDERDOG" 
            else: game_type = "C_NEUTRAL"
            
        # 6. MARKET VALIDATION (Regime Zero Core)
        market_analysis = {}

        # --- DECOMPOSITION LOGIC (Always Run) ---
        
        # 1. Base Power (Already calculated as Hybrid)
        base_power = net_diff # This is now the Hybrid Diff
        
        # 2. Pace Adjustment
        avg_pace = (h['pace'] + a['pace']) / 2.0
        pace_factor = avg_pace / 100.0
        pace_adj_power = base_power * pace_factor
        pace_impact = pace_adj_power - base_power
        
        # 3. Home Court
        hca = HOME_ADV_CONST
        
        # 4. Rest Adjustment
        rest_val = rest_h - rest_a
        
        # 5. Regime Impact
        regime_val = regime_margin_impact 
        
        # --- QUALITATIVE INJECTION (ESPN Preview) ---
        try:
            from qualitative_parser import parse_qualitative_data
        except ImportError:
            try:
                from quant_engine_v1.qualitative_parser import parse_qualitative_data
            except ImportError:
                # Last resort
                from nba_data.quant_engine_v1.qualitative_parser import parse_qualitative_data
            
        injury_impact_raw, qual_triggers, qual_headline = parse_qualitative_data(game_id)
        
        # 6. Injury Adjustment (Refactored v2: Dampened Alpha)
        INJURY_DAMPENER = 0.3
        injury_impact = injury_impact_raw * INJURY_DAMPENER
        
        # Volatility Boost (Shock Transfer)
        vol_boost = abs(injury_impact_raw) * 0.5
        vol += vol_boost

        # --- DECOMPOSITION AGGREGATION ---
        # Raw Sum            # 7. Aggregate
        raw_sum = pace_adj_power + hca + rest_val + injury_impact 
        
        # --- HISTORICAL UPSET REGIME (G9) ---
        market_line = 0.0
        if isinstance(odds, dict):
            # Prefer explicit numeric spread from ESPN API
            if 'spread' in odds:
                market_line = float(odds['spread'])
            else:
                market_line = odds.get('home_line', 0.0)
        elif odds is not None:
            try:
                # Handle string like "-11.5" or "CLE -11.5"
                s = str(odds).replace("−", "-")
                # Extract number using regex or simple split?
                # Simple split: take last token if space exists?
                # "CLE -11.5" -> "-11.5"
                if " " in s:
                    tokens = s.split(" ")
                    s = tokens[-1]
                market_line = float(s) 
            except:
                pass
        
        # If market line is 0 (No Odds), Regime is effectively "Standard"/"Neutral" 
        # unless we have a separate "Pure Quant Regime" model (which we don't yet).
        regime_context = self.get_upset_regime(market_line, h, a)
        
        # 8. Volatility Penalties (Regime Adjusted)
        vol_penalty = 0.0
        raw_vol = vol + vol_boost 
        
        # If Regime says "Danger", we ensure Volatility floor
        if regime_context and regime_context['tier'] in ['3', '4']: 
             raw_vol = max(raw_vol, 12.0)
        
        # Dist Calculation
        import math
        # Standard Deviation Model
        # Sigma = 12 + (Vol/10)
        sigma = 10.0 + (raw_vol * 0.4)
        
        # 5. Volatility Penalty (The "Trust" Discount)
        if raw_vol > 13.0:
            vol_penalty = (raw_vol - 13.0) * 0.5
        
        # Apply Penalty
        raw_margin = 0.0
        if raw_sum > 0:
            raw_margin = max(0, raw_sum - vol_penalty)
        else:
            raw_margin = min(0, raw_sum + vol_penalty)
        
        # --- ELASTICITY CLAMP (Safety Guardrail) ---
        market_expect = -1 * market_line
        
        final_margin = raw_margin
        
        # Delta Calculation
        raw_delta = final_margin - market_expect
        
        # Clamp Delta for Signal ONLY
        clamped_delta = raw_delta
        if abs(raw_delta) > 10.0 and odds:
             clamped_delta = raw_delta * 0.8
             
        # 9. Trigger Detection
        triggers = []
        if regime_context and regime_context.get('regime_name', 'Standard') != 'Standard':
             triggers.append(f"Regime: {regime_context.get('regime_name')}")


        # 1. Pace Mismatch
        if abs(h['pace'] - a['pace']) > 4.0:
            triggers.append("⚡ Pace Mismatch (High Variance)")
        
        # 2. Rest Mismatch
        rest_days_diff = rest_h_val - rest_a_val
        if rest_days_diff != 0:
             adv_team = "Home" if rest_days_diff > 0 else "Away"
             triggers.append(f"💤 Rest Advantage: {adv_team} (+{abs(rest_days_diff)}d)")
             
        # 3. Volatility Clash
        if vol > 15.0:
            triggers.append("🎢 High Volatility Environment")
        
        
        # Final Signal Calculation
        signal = "RATIONAL"
        if not odds:
             signal = "NO_MARKET"
        elif abs(clamped_delta) < 3.0: 
            signal = "RATIONAL"
        elif clamped_delta > 3.0:
            signal = "HOME_UNDERVALUED"
        elif clamped_delta < -3.0:
            signal = "HOME_OVERVALUED"
            
        # CDF Helper
        def get_prob(target, mean, std):
            return 0.5 * (1 + math.erf((target - mean) / (std * math.sqrt(2))))
        
        dist_sigma = sigma
        prob_home_win = 1.0 - get_prob(0, final_margin, dist_sigma)
        prob_home_blowout = 1.0 - get_prob(9.5, final_margin, dist_sigma)
        
        probs = {}
        if final_margin > 0: # Home Fav
            probs['blowout'] = round(prob_home_blowout * 100, 1) # Win by 10+
            probs['upset'] = round((1.0 - prob_home_win) * 100, 1) # Lose
            probs['close'] = round((prob_home_win - prob_home_blowout) * 100, 1) # Win by 1-9
        else: # Away Fav
            prob_away_blowout = get_prob(-9.5, final_margin, dist_sigma)
            prob_away_win = get_prob(0, final_margin, dist_sigma)
            
            probs['blowout'] = round(prob_away_blowout * 100, 1)
            probs['upset'] = round((1.0 - prob_away_win) * 100, 1) # Home Wins (Upset)
            probs['close'] = round((prob_away_win - prob_away_blowout) * 100, 1)        
        
        # Verdict Logic
        fav_win_zone_prob = 50.0
        if odds:
             abs_mkt = abs(market_line)
             if abs_mkt >= 13.0: fav_win_zone_prob = 90.0
             elif abs_mkt >= 9.5: fav_win_zone_prob = 80.0
             elif abs_mkt >= 6.5: fav_win_zone_prob = 72.0
             elif abs_mkt >= 4.5: fav_win_zone_prob = 64.0
             else: fav_win_zone_prob = 55.0
        
        engine_upset_risk = probs['upset']
        verdict = "Quant Data Ready."
        
        market_analysis = {
            "market_line": market_line,
            "expected_margin": round(final_margin, 1),
            "delta": round(clamped_delta, 1), 
            "is_clamped": (clamped_delta != raw_delta),
            "raw_delta": round(raw_delta, 1),
            "signal": signal,
            "is_active": True,
            "decomposition": {
                "base_power": round(base_power, 1),
                "pace_impact": round(pace_impact, 1),
                "hca": hca,
                "rest_impact": round(rest_val, 1),
                "injury_impact": round(injury_impact, 1),
                "raw_injury_impact": round(injury_impact_raw, 1),
                "vol_boost": round(vol_boost, 1),
                "vol_penalty": round(vol_penalty, 1),
                "regime_context": regime_context 
            },
            "volatility": round(sigma, 1),
            "prob_dist": probs,
            "reality_check": {
                "market_win_prob": fav_win_zone_prob,
                "engine_upset_risk": engine_upset_risk,
                "verdict": verdict
            },
            "triggers": triggers + qual_triggers,
            "headline": qual_headline
        }
        
        return {
            "edge_score": round(edge_score, 1),
            "risk_score": round(risk_score, 1),
            "game_type": game_type,
            "twin_alert": "Active" if (game_type in ["B_RISKY_FAVORITE", "D_UPSET_ZONE"] and risk_score >= 35) else "None",
            "market_analysis": market_analysis,
            "home_stats": h,
            "away_stats": a
        }

if __name__ == "__main__":
    eng = CacheFusionEngine()
    print(eng.analyze_matchup("1610612766", "1610612741", "2025-12-12"))
