from typing import List, Dict, Any
import os
import sys
import json

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.engine.regime_detector import RegimeDetector
from g9_macro_factory.engine.pattern_refiner import refine_pattern
from g9_macro_factory.engine.meta_rag import check_meta_fail_log
from g9_macro_factory.engine.explainer.risk_explainer import generate_risk_explanation
from g9_macro_factory.engine.risk.unified_risk_score import calculate_unified_risk
from utils.embedding import get_embedding_sync

from g9_macro_factory.backtest_engine.rag_strategy import retrieve_relevant_patterns, generate_strategy
from g9_macro_factory.utils.macro_processor import get_macro_processor
from g9_macro_factory.config import get_supabase_client

class DecisionEngine:
    """
    G9 Decision Engine v1.5
    Orchestrates the entire decision making process.
    """
    
    def __init__(self):
        self.regime_detector = RegimeDetector()
        self.supabase = get_supabase_client()
        self.macro_processor = get_macro_processor()
        
    def get_dynamic_threshold(self, regime: str) -> float:
        """
        [v1.7] Returns Z-Score threshold based on Regime.
        """
        table = {
            "LIQUIDITY_CRISIS": 1.2,
            "INFLATION_FEAR": 1.8,
            "STAGFLATION": 1.5,
            "NEUTRAL": 2.5,
            "GROWTH_GOLDILOCKS": 2.5,
        }
        return table.get(regime, 2.5)

    def momentum_signal(self, macro: Dict) -> bool:
        """
        [v1.7] Checks if market is in strong momentum (Bull Market).
        Proxy: VIX < 20 and Regime is Neutral/Growth.
        """
        vix = macro.get('VIX', {}).get('value', 20.0)
        regime = macro.get('regime', 'NEUTRAL')
        
        # If we had SPY trend, we would use it.
        # For now, use VIX and Regime as proxy.
        if vix < 20.0 and regime in ["NEUTRAL", "GROWTH_GOLDILOCKS"]:
            return True
        return False

    def check_trend_confirmation(self, macro_state: Dict, z_score_data: Dict) -> bool:
        """
        [v1.8] Checks if market trend supports active trading (BUY/SELL) over HOLD.
        Conditions (2+ required):
        - VIX < 20
        - US10Y Down (Proxy: value < 4.0 or check trend if available)
        - DXY Down (Proxy: value < 102)
        - Z-Score > 0 (Short-term uptrend proxy)
        - Impact Score > 0 (Medium-term uptrend proxy)
        """
        score = 0
        vix = macro_state.get('VIX', {}).get('value', 25.0)
        us10y = macro_state.get('US10Y', {}).get('value', 4.5)
        dxy = macro_state.get('DXY', {}).get('value', 105.0)
        z_score = z_score_data.get('z_score', 0.0)
        impact = z_score_data.get('impact_score', 0.0)
        
        if vix < 20.0: score += 1
        if us10y < 4.0: score += 1 # Simple proxy for "low/falling yields"
        if dxy < 102.0: score += 1 # Simple proxy for "weak dollar"
        if z_score > 0.5: score += 1
        if impact > 2.0: score += 1
        
        return score >= 2

    def get_z_score(self, date_str: str) -> Dict:
        """Fetch Z-Score for a specific date from DB."""
        try:
            res = self.supabase.table("zscore_daily").select("*").eq("date", date_str).execute()
            if res.data:
                row = res.data[0]
                # Map DB columns to expected keys
                return {
                    "z_score": row.get('z_day_local', 0.0), # Use z_day_local as primary Z
                    "impact_score": row.get('impact_score', 0.0)
                }
        except Exception as e:
            print(f"⚠️ Failed to fetch Z-Score for {date_str}: {e}")
        return {"z_score": 0.0, "impact_score": 0.0}

    def decide(self, news_item: Dict, macro_state: Dict = None, z_score_data: Dict = None, mode: str = "general", context_data: Dict = None) -> Dict:
        """
        Main decision logic.
        mode: "general" (Daily Intelligence) or "anomaly" (High-Sensitivity Crisis Detection)
        context_data: Dict from ContextLoader containing 'monthly_summary', 'weekly_context', 'daily_context'
        """
        # [TASK D] Validate Macro Data
        if not macro_state:
            # Try to fetch if not provided (optional, but for now assume provided or use internal)
            # For historical test, it is provided.
            pass
            
        date_str = news_item['published_at'].split("T")[0]
        
        # [TASK D] Validate Macro Data
        if not macro_state:
            raise ValueError(f"Macro data missing for {date_str}")
        
        # 0. Embedding (for RAG)
        full_text = f"{news_item['title']}. {news_item['summary']}"
        embedding = get_embedding_sync(full_text)
        
        # [1] Meta-RAG (Failure Memory)
        # Check if we have failed in a similar situation before
        meta_rag_warning = check_meta_fail_log(embedding, threshold=0.45) # Tuned for better recall (0.7 -> 0.45)
        meta_rag_status = "Clean"
        meta_rag_doc = ""
        
        if meta_rag_warning:
            meta_rag_status = "Warning"
            
            # Parse Rich Metadata
            try:
                rich_data = json.loads(meta_rag_warning.get('fail_reason', '{}'))
            except:
                rich_data = {}
                
            event_name = rich_data.get('event_name', meta_rag_warning.get('origin_pattern_id', 'Unknown Event'))
            hist_ctx = rich_data.get('historical_context', 'N/A')
            past_outcome = rich_data.get('past_outcome', 'N/A')
            lesson = rich_data.get('lesson_summary', meta_rag_warning.get('fail_reason', 'N/A'))
            avoid = meta_rag_warning.get('correction_rule', 'N/A')
            action = rich_data.get('recommended_action', 'N/A')
            similarity = meta_rag_warning.get('similarity', 0.0) * 100
            
            meta_rag_doc = f"⚠ Meta-RAG 경고: 과거 '{event_name}' 패턴과 유사도 {similarity:.1f}% 감지됨.\n\n[역사적 배경]\n{hist_ctx}\n\n[과거 시장 반응]\n{past_outcome}\n\n[핵심 교훈]\n{lesson}\n\n[주의해야 할 행동]\n{avoid}\n\n[이번 뉴스에 대한 최종 조언]\n{action}"
            
            # print(f"DEBUG: Meta-RAG Warning Generated: {event_name}")
            
        # [2] Regime Detector
        regime = self.regime_detector.detect(macro_state)
        regime_desc = self.regime_detector.get_regime_context(regime)
        
        # [3] Pattern RAG (History Miner)
        # Retrieve similar past events
        relevant_patterns = retrieve_relevant_patterns(full_text, top_k=3)
        
        # Refine Pattern (Select best match)
        pattern_id = "None"
        pattern_desc = "No relevant pattern found"
        
        if relevant_patterns:
            top_pattern = relevant_patterns[0]
            raw_id = top_pattern.get('pattern_id', 'Unknown')
            pattern_desc = top_pattern.get('core', top_pattern.get('title', ''))
            
            # Refine based on macro
            pattern_id = refine_pattern(raw_id, macro_state)
        
        # [4] Z-Score Context
        z_score = z_score_data.get('z_score', 0.0)
        impact_score = z_score_data.get('impact_score', 0.0)
        
        # Construct a rich context for LLM
        
        # [5] Logic Branching based on Mode
        final_action = "SKIP"
        reason = ""
        confidence = 0.0
        
        if mode == "anomaly":
            # --- TRACK A: High-Sensitivity Mode ---
            
            # [TASK G] Contrarian Safety Lock
            # Absolute safety lock
            if regime == "STAGFLATION" and pattern_id in ["P-005", "P-007", "P-047"]:
                 return {
                    "action": "HOLD_CASH",
                    "reason": "Stagflation Exception Rule (Safety Lock Triggered)",
                    "confidence": 1.0,
                    "regime": regime,
                    "pattern": pattern_id,
                    "z_score": z_score,
                    "impact_score": impact_score,
                    "meta_rag_status": meta_rag_status,
                    "meta_rag_warning_document": meta_rag_doc,
                    "mode": mode
                }
            
            # [v1.7] Dynamic Threshold based on Regime
            threshold = self.get_dynamic_threshold(regime)
            
            # Z-Score Switch (Noise Filter)
            if z_score < threshold:
                 return {
                    "action": "SKIP",
                    "reason": f"Low Z-Score ({z_score:.2f} < {threshold}). Noise Filtered.",
                    "confidence": 0.0,
                    "regime": regime,
                    "pattern": pattern_id,
                    "z_score": z_score,
                    "impact_score": impact_score,
                    "meta_rag_status": meta_rag_status,
                    "meta_rag_warning_document": meta_rag_doc,
                    "mode": mode
                }
                
            # Call LLM for Strategy
            macro_state_with_regime = macro_state.copy()
            macro_state_with_regime['regime'] = regime
            macro_state_with_regime['regime_desc'] = regime_desc
            
            # Construct pattern dict compatible with rag_strategy
            refined_patterns = [{
                "pattern_id": pattern_id,
                "title": pattern_desc,
                "core": pattern_desc
            }]
            strategies = generate_strategy([news_item], z_score_data, refined_patterns, macro_state_with_regime, context_data=context_data)
            
            if strategies:
                strategy = strategies[0]
                final_action = strategy['action']
                reason = strategy.get('reason', strategy.get('rationale', ''))
                confidence = strategy.get('confidence', 0.0)
            else:
                reason = "No strategy generated by LLM"
                
            # Meta-RAG Override (Weighted System v1.9)
            if meta_rag_warning:
                override_level = meta_rag_warning.get('override_level', 'NONE')
                risk_weight = meta_rag_warning.get('risk_weight', 1.0)
                
                if override_level == 'HARD':
                    # Force HOLD_CASH regardless of action
                    final_action = "HOLD_CASH"
                    reason = f"[Meta-RAG HARD Override] Risk Weight {risk_weight:.1f}. Forced HOLD_CASH."
                    meta_rag_status = "Warning (HARD)"
                    
                elif override_level == 'SOFT':
                    # Downgrade Signal
                    if final_action == "SELL":
                        final_action = "HOLD" # Soften Sell to Hold
                        reason += f" | [Meta-RAG SOFT Override] Risk Weight {risk_weight:.1f}. Downgraded SELL to HOLD."
                        meta_rag_status = "Warning (SOFT)"
                    elif final_action == "BUY":
                        final_action = "HOLD" # Soften Buy to Hold
                        reason += f" | [Meta-RAG SOFT Override] Risk Weight {risk_weight:.1f}. Downgraded BUY to HOLD."
                        meta_rag_status = "Warning (SOFT)"
                    else:
                        reason += f" | [Meta-RAG SOFT Warning] Risk Weight {risk_weight:.1f}. Caution advised."
                        meta_rag_status = "Warning (SOFT)"

            # Z-Score Contrarian (Extreme Reversal)
            if z_score >= 4.0 and final_action == "SELL":
                # Already handled above, but if we want to force BUY_THE_DIP?
                # If Meta-RAG says "Don't Sell", maybe we should BUY?
                # The rule says "Wait for stabilization" or "Don't panic sell".
                # So HOLD_CASH is safe.
                pass
            elif z_score >= 4.0 and final_action == "BUY":
                # Optional: Sell the rip?
                pass
                
        else:
            # --- TRACK B: General Mode (Daily Intelligence) ---
            # No SKIP based on Z-Score.
            # Determine Signal Strength
            signal_strength = "WEAK"
            if z_score >= 2.5: signal_strength = "NORMAL"
            if z_score >= 4.0: signal_strength = "STRONG"
            
            # Call LLM for Strategy (Market View)
            macro_state_with_regime = macro_state.copy()
            macro_state_with_regime['regime'] = regime
            macro_state_with_regime['regime_desc'] = regime_desc
            
            # Construct pattern dict compatible with rag_strategy
            refined_patterns = [{
                "pattern_id": pattern_id,
                "title": pattern_desc,
                "core": pattern_desc
            }]
            strategies = generate_strategy([news_item], z_score_data, refined_patterns, macro_state_with_regime)
            
            if strategies:
                strategy = strategies[0]
                final_action = strategy['action']
                reason_text = strategy.get('reason', strategy.get('rationale', ''))
                reason = f"[{signal_strength} SIGNAL] {reason_text}"
                confidence = strategy.get('confidence', 0.0)
            else:
                reason = "No strategy generated by LLM"
                
            # Meta-RAG Override (Weighted System v1.9)
            if meta_rag_warning:
                override_level = meta_rag_warning.get('override_level', 'NONE')
                risk_weight = meta_rag_warning.get('risk_weight', 1.0)
                
                if override_level == 'HARD':
                    # Force HOLD_CASH regardless of action
                    final_action = "HOLD_CASH"
                    reason = f"[Meta-RAG HARD Override] Risk Weight {risk_weight:.1f}. Forced HOLD_CASH."
                    meta_rag_status = "Warning (HARD)"
                    
                elif override_level == 'SOFT':
                    # Downgrade Signal
                    if final_action == "SELL":
                        final_action = "HOLD" # Soften Sell to Hold
                        reason += f" | [Meta-RAG SOFT Override] Risk Weight {risk_weight:.1f}. Downgraded SELL to HOLD."
                        meta_rag_status = "Warning (SOFT)"
                    elif final_action == "BUY":
                        final_action = "HOLD" # Soften Buy to Hold
                        reason += f" | [Meta-RAG SOFT Override] Risk Weight {risk_weight:.1f}. Downgraded BUY to HOLD."
                        meta_rag_status = "Warning (SOFT)"
                    else:
                        reason += f" | [Meta-RAG SOFT Warning] Risk Weight {risk_weight:.1f}. Caution advised."
                        meta_rag_status = "Warning (SOFT)"
                 
        # [v1.8] False-Hold Reduction Logic
        # Apply rules in specific order: Restriction -> Trend -> Momentum -> Meta-RAG
        
        # Rule 2: HOLD Restriction
        if final_action in ["HOLD", "HOLD_CASH"]:
            if impact_score > 5.0:
                final_action = "BUY"
                reason += " | [Hold Restriction] Impact > 5.0. Forced BUY."
            elif impact_score < -5.0:
                final_action = "SELL"
                reason += " | [Hold Restriction] Impact < -5.0. Forced SELL."
                
        # Rule 1: Trend Confirmation (Convert HOLD to Active)
        if final_action in ["HOLD", "HOLD_CASH"]:
            if self.check_trend_confirmation(macro_state, z_score_data):
                # If trend is good, default to BUY unless Z-Score is very negative
                if z_score > -1.0:
                    final_action = "BUY"
                    reason += " | [Trend Confirmation] Market conditions favorable. Switched HOLD to BUY."
                else:
                    final_action = "SELL"
                    reason += " | [Trend Confirmation] Market conditions active but negative Z. Switched HOLD to SELL."

        # Rule 4: Momentum Priority (Bull/Bear Market)
        # Bull Market -> Force BUY if not already
        if self.momentum_signal(macro_state):
             if final_action != "BUY":
                 final_action = "BUY"
                 reason += " | [Momentum Priority] Bull Market detected. Forced BUY."
        
        # Bear Market (Proxy: VIX > 30 or Regime=Liquidity Crisis)
        vix = macro_state.get('VIX', {}).get('value', 20.0)
        if vix > 30.0 or regime == "LIQUIDITY_CRISIS":
            if final_action == "HOLD":
                final_action = "HOLD_CASH" # Or SELL
                reason += " | [Momentum Priority] Bear Market detected. Switched HOLD to HOLD_CASH."

        # Rule 3: Meta-RAG HOLD Correction
        # If we have a warning and it was a False-Hold before, force action
        if meta_rag_warning:
            risk_weight = meta_rag_warning.get('risk_weight', 1.0)
            # Check if past failure was False-Hold
            try:
                fail_reason = json.loads(meta_rag_warning.get('fail_reason', '{}'))
                past_fail_type = fail_reason.get('fail_type', '')
            except:
                past_fail_type = ''
                
            if risk_weight >= 3.0 and past_fail_type == "false_hold":
                if final_action in ["HOLD", "HOLD_CASH"]:
                    # Force action based on Z-Score direction
                    if z_score >= 0:
                        final_action = "BUY"
                        reason += " | [Meta-RAG Correction] Repeated False-Hold. Forced BUY."
                    else:
                        final_action = "SELL"
                        reason += " | [Meta-RAG Correction] Repeated False-Hold. Forced SELL."
                 
        # [v2.0] Unified Risk Score & Explainer
        unified_risk = calculate_unified_risk(macro_state, pattern_id, meta_rag_warning)
        risk_explanation = generate_risk_explanation(meta_rag_warning, strategy.get('action', 'SKIP') if 'strategy' in locals() else 'SKIP', final_action)
                
        # [6] Composite Output
        return {
            "action": final_action,
            "reason": reason,
            "confidence": confidence,
            "regime": regime,
            "pattern": pattern_id,
            "z_score": z_score,
            "impact_score": impact_score,
            "meta_rag_status": meta_rag_status,
            "meta_rag_warning_document": meta_rag_doc,
            "unified_risk": unified_risk,
            "risk_explanation": risk_explanation,
            "mode": mode
        }

# Singleton instance
engine = DecisionEngine()
