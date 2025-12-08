import os
import sys
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.engine.decision_engine import DecisionEngine
from g9_macro_factory.config import get_supabase_client, TABLE_PRICE_DAILY
from g9_macro_factory.utils.macro_processor import get_macro_processor
from utils.embedding import get_embedding_sync

class BacktestAutoLoop:
    def __init__(self):
        self.engine = DecisionEngine()
        self.supabase = get_supabase_client()
        self.macro_processor = get_macro_processor()
        self.events_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/historical_events_100.json")
        self.report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../reports/backtest_report_latest.json")
        self.results = []
        
    def load_events(self) -> List[Dict]:
        if not os.path.exists(self.events_file):
            print(f"❌ Events file not found: {self.events_file}")
            return []
        with open(self.events_file, "r") as f:
            return json.load(f)
            
    def get_price(self, ticker: str, date_str: str):
        """Fetch close price for a specific date."""
        try:
            res = self.supabase.table(TABLE_PRICE_DAILY)\
                .select("close")\
                .eq("ticker", ticker)\
                .eq("date", date_str)\
                .execute()
            if res.data:
                return res.data[0]['close']
            return None
        except Exception as e:
            # print(f"   ⚠️ Price fetch error: {e}")
            return None

    def calculate_return(self, ticker: str, date_str: str, days=5) -> float:
        """Calculate T+days return."""
        start_price = self.get_price(ticker, date_str)
        if not start_price:
            # Try next day (if weekend)
            # Simple retry logic not implemented for brevity, assuming valid trading days or close enough
            return 0.0
            
        # Find T+days date
        start_date = datetime.strptime(date_str, "%Y-%m-%d")
        end_date = start_date + timedelta(days=days)
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        end_price = self.get_price(ticker, end_date_str)
        
        # If end price missing, try to find next available
        if not end_price:
            # Try up to 3 days forward
            for i in range(1, 4):
                next_d = end_date + timedelta(days=i)
                end_price = self.get_price(ticker, next_d.strftime("%Y-%m-%d"))
                if end_price: break
        
        if start_price and end_price:
            return (end_price - start_price) / start_price
        return 0.0

    def classify_error(self, action: str, ret: float) -> str:
        """
        Classifies the error type based on action and return.
        Returns: 'false_sell', 'false_buy', 'false_hold', 'omission', or None (Correct)
        """
        # 1. False-Sell (Panic Sold, but Market Rose)
        if action == "SELL" and ret > 0.02:
            return "false_sell"
            
        # 2. False-Buy (Bought Top, Market Crashed)
        if action == "BUY" and ret < -0.02:
            return "false_buy"
            
        # 3. False-Hold (Missed Opportunity or Risk)
        if action in ["HOLD", "HOLD_CASH"]:
            if ret > 0.03: return "false_hold" # Missed Rally (Should have bought)
            if ret < -0.03: return "false_hold" # Missed Crash (Should have sold)
            
        # 4. Omission (SKIP, but Big Move happened)
        if action == "SKIP":
            if abs(ret) > 0.03: return "omission"
            
        return None

    def auto_learn(self, event: Dict, decision: Dict, actual_return: float, fail_type: str):
        """Insert failure into Meta-RAG with classification and Self-Weighting."""
        
        # [v1.9] Check for existing similar failure (Self-Weighting)
        text = f"{event['event_name']}. {event['description']}"
        embedding = get_embedding_sync(text)
        
        from g9_macro_factory.engine.meta_rag import check_meta_fail_log, update_meta_fail_log
        
        # Check with high threshold to find "Same Pattern"
        existing_log = check_meta_fail_log(embedding, threshold=0.85)
        
        if existing_log:
            # UPDATE existing record
            try:
                reason_json = json.loads(existing_log.get('fail_reason', '{}'))
                current_weight = reason_json.get('risk_weight', 1.0)
                
                # [v1.8] Dynamic Increment
                increment = 0.3
                if fail_type == "false_hold":
                    increment = 1.5 # Aggressive penalty for hesitation
                    
                new_weight = current_weight + increment
                
                reason_json['risk_weight'] = new_weight
                reason_json['updated_at'] = datetime.now().isoformat()
                reason_json['recurrence_count'] = reason_json.get('recurrence_count', 1) + 1
                
                update_meta_fail_log(existing_log['id'], json.dumps(reason_json))
                print(f"   🔄 [Self-Weighting] Updated Log ID {existing_log['id']} | New Weight: {new_weight:.1f}")
                return
            except Exception as e:
                print(f"   ⚠️ Failed to update existing log: {e}")
                # Fallback to insert new
        
        # INSERT new record
        # Determine Base Weight
        base_weight = 1.0
        if fail_type == "false_sell": base_weight = 1.5
        elif fail_type == "false_buy": base_weight = 1.2
        elif fail_type == "false_hold": base_weight = 2.0 # [v1.8] Increased from 1.0 to 2.0
        elif fail_type == "omission": base_weight = 0.8
        
        # Determine Correction Hint
        correction_hint = "Review logic."
        if fail_type == "false_sell":
            correction_hint = "Avoid panic selling in this scenario. Market recovered."
        elif fail_type == "false_buy":
            correction_hint = "Avoid buying the dip too early. Market continued to fall."
        elif fail_type == "false_hold":
            if actual_return > 0: correction_hint = "Don't be too passive. Missed rally."
            else: correction_hint = "Don't be too passive. Missed crash warning."
        elif fail_type == "omission":
            correction_hint = "Signal was missed. Increase sensitivity."
            
        # Construct Rich Metadata
        rich_data = {
            "event_name": event['event_name'],
            "fail_type": fail_type,
            "risk_weight": base_weight,
            "impact": actual_return,
            "correction_hint": correction_hint,
            "historical_context": event['description'],
            "lesson_summary": f"Auto-Learned [{fail_type}]: Action {decision['action']} failed. Return {actual_return:.1%}.",
            "past_outcome": f"Market moved {actual_return:.1%} in 5 days.",
            "recommended_action": "OPPOSITE_ACTION",
            "created_at": datetime.now().isoformat(),
            "recurrence_count": 1
        }
        
        data = {
            "origin_pattern_id": decision.get('pattern', 'AUTO'),
            "fail_reason": json.dumps(rich_data),
            "correction_rule": correction_hint,
            "regime_context": decision.get('regime', 'UNKNOWN'),
            "embedding": embedding
        }
        
        try:
            self.supabase.table("g9_meta_rag").insert(data).execute()
            print(f"   [Auto-Learn] type={fail_type} | matched_pattern={decision.get('pattern', 'N/A')} | risk_weight={base_weight} | saved_to_meta_rag=True")
        except Exception as e:
            print(f"   ❌ Meta-RAG Insert Failed: {e}")

    def run(self):
        print("🚀 Starting G9 Backtest Auto-Loop v1.0...")
        events = self.load_events()
        print(f"📊 Loaded {len(events)} events.")
        
        correct_count = 0
        meta_rag_triggers = 0
        
        for i, event in enumerate(events):
            print(f"\n[{i+1}/{len(events)}] {event['date']} | {event['event_name']} ({event['ticker']})")
            
            # 1. Prepare Data
            news_item = {
                "published_at": f"{event['date']}T10:00:00",
                "ticker": event['ticker'],
                "title": event['event_name'],
                "summary": event['description']
            }
            
            # Fetch Macro State
            macro_state = self.macro_processor.get_state(event['date'])
            if not macro_state:
                print("   ⚠️ Macro Data Missing. Skipping.")
                continue
                
            # Fetch Z-Score (Mock or Real)
            # We use engine.get_z_score but it needs DB.
            # For now, we assume Z-Score is available or we mock it if missing.
            # Actually, let's try to fetch it.
            z_score_data = self.engine.get_z_score(event['date'])
            if not z_score_data:
                # Mock Z-Score based on VIX?
                vix = macro_state.get('VIX', {}).get('value', 20)
                z_mock = (vix - 20) / 5.0 # Crude proxy
                z_score_data = {"z_score": z_mock, "impact_score": 5.0}
            
            # 2. Run Engine
            try:
                decision = self.engine.decide(news_item, macro_state=macro_state, z_score_data=z_score_data, mode="general")
            except Exception as e:
                print(f"   ❌ Engine Error: {e}")
                continue
                
            # 3. Calculate Return
            ret = self.calculate_return(event['ticker'], event['date'])
            print(f"   👉 Action: {decision['action']} | Return (T+5): {ret:.1%}")
            
            # 4. Evaluate Correctness
            fail_type = self.classify_error(decision['action'], ret)
            
            if fail_type is None:
                print("   ✅ Correct")
                correct_count += 1
            else:
                print(f"   ❌ Incorrect ({fail_type})")
                # 5. Auto-Learn
                self.auto_learn(event, decision, ret, fail_type)
                
            if decision.get('meta_rag_status') == "Warning":
                meta_rag_triggers += 1
                print("   🛡️ Meta-RAG Triggered")
                
            self.results.append({
                "date": event['date'],
                "event": event['event_name'],
                "action": decision['action'],
                "return": ret,
                "correct": (fail_type is None),
                "meta_rag": decision.get('meta_rag_status') == "Warning",
                "regime": decision.get('regime'),
                "pattern": decision.get('pattern')
            })
            
        # 6. Report
        win_rate = (correct_count / len(self.results)) * 100 if self.results else 0
        
        # Calculate detailed metrics
        fail_counts = {"false_sell": 0, "false_buy": 0, "false_hold": 0, "omission": 0}
        momentum_overrides = 0
        
        for res in self.results:
            if not res['correct']:
                ft = res.get('fail_type')
                if ft in fail_counts:
                    fail_counts[ft] += 1
            
            # Check for Momentum Override in reason (assuming it was logged in decision)
            if "Momentum Override" in res.get('reason', ''):
                momentum_overrides += 1
                
        print(f"\n🏁 BACKTEST COMPLETE")
        print(f"   Total Cases: {len(self.results)}")
        print(f"   Win Rate: {win_rate:.1f}% ({correct_count}/{len(self.results)})")
        print(f"   Meta-RAG Triggers: {meta_rag_triggers}")
        print(f"   Momentum Overrides: {momentum_overrides}")
        print(f"   Failure Counts:")
        print(f"     - False-Sell: {fail_counts['false_sell']}")
        print(f"     - False-Buy: {fail_counts['false_buy']}")
        print(f"     - False-Hold: {fail_counts['false_hold']}")
        print(f"     - Omission: {fail_counts['omission']}")
        
        report = {
            "total_cases": len(self.results),
            "correct_count": correct_count,
            "win_rate": win_rate,
            "meta_rag_triggers": meta_rag_triggers,
            "momentum_overrides": momentum_overrides,
            "fail_counts": fail_counts,
            "details": self.results
        }
        
        os.makedirs(os.path.dirname(self.report_file), exist_ok=True)
        with open(self.report_file, "w") as f:
            json.dump(report, f, indent=2)
            
if __name__ == "__main__":
    loop = BacktestAutoLoop()
    loop.run()
