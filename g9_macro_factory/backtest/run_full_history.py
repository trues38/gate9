import os
import sys
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.engine.decision_engine import DecisionEngine
from g9_macro_factory.data_pipeline.daily_fuser import DailyNewsFuser
from g9_macro_factory.backtest.backtest_auto_loop import BacktestAutoLoop # Reuse logic

class FullHistoryBacktest(BacktestAutoLoop):
    """
    Runs a continuous daily backtest over full history (e.g., 2000-2025).
    Integrates Daily Multi-RSS Fusing.
    """
    
    def __init__(self):
        super().__init__()
        self.fuser = DailyNewsFuser()
        self.results_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../reports/full_history_results.json")
        
        # Multi-Timeframe Components
        from g9_macro_factory.summarizer.weekly_builder import WeeklyBuilder
        from g9_macro_factory.summarizer.monthly_builder import MonthlyBuilder
        from g9_macro_factory.engine.context_loader import ContextLoader
        
        self.weekly_builder = WeeklyBuilder()
        self.monthly_builder = MonthlyBuilder()
        self.context_loader = ContextLoader()
        
    def run_full_backtest(self, start_year: int, end_year: int, loops: int = 3):
        print(f"🚀 Starting Full History Backtest ({start_year}-{end_year}) | Loops: {loops}")
        
        start_date = datetime(start_year, 1, 1)
        end_date = datetime(end_year, 12, 31)
        delta = timedelta(days=1)
        
        total_days = (end_date - start_date).days + 1
        
        for loop in range(loops):
            print(f"\n🔄 --- LOOP {loop + 1}/{loops} ---")
            current_date = start_date
            
            loop_stats = {"correct": 0, "total": 0, "meta_rag": 0}
            
            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")
                
                # Skip weekends (simple check)
                if current_date.weekday() >= 5:
                    current_date += delta
                    continue
                    
                print(f"[{date_str}] Processing...", end="\r")
                
                # 1. Fetch & Fuse News (3-Stage Pipeline)
                # Stage 1: Raw Summary (Qwen 7B)
                news_items = self.fuser.fetch_daily_news(date_str, "US")
                raw_summary = self.fuser.summarize_raw_headlines(news_items)
                
                # [Multi-Timeframe] Update Buffers & Generate Reports
                # We use Builders to generate and save reports to DB
                
                # Weekly Report (Every Friday)
                if current_date.weekday() == 4: # Friday
                    # We need to pass the start date of the week (Monday)
                    monday = current_date - timedelta(days=4)
                    self.weekly_builder.build_weekly_summary(monday.strftime("%Y-%m-%d"), "US")
                    print(f"   📅 Generated & Saved Weekly Report")
                    
                # Monthly Report (Month End Check)
                next_day = current_date + delta
                if next_day.month != current_date.month:
                    # Build report for the current month
                    month_str = current_date.strftime("%Y-%m-01")
                    self.monthly_builder.build_monthly_summary(month_str, "US")
                    print(f"   🗓️ Generated & Saved Monthly Report")
                
                # Stage 2: Regional Insight (Gemini/DeepSeek/Qwen)
                insight = self.fuser.generate_regional_insight(raw_summary, "US")
                
                # Construct News Item for Engine (Stage 3 happens inside Engine)
                fused_content = f"[Daily Summary]\n{raw_summary}\n\n[Market Insight]\n{insight}"
                
                news_input = {
                    "published_at": f"{date_str}T10:00:00",
                    "ticker": "SPY", # General Market
                    "title": "Daily Market Briefing",
                    "summary": fused_content
                }
                
                # Context Injection (Time Machine Rule: Fetch from DB via ContextLoader)
                context_data = self.context_loader.get_multi_timeframe_context(date_str, "US")
                # Override daily_context with our fresh raw_summary if needed, but ContextLoader builds it too.
                # To save cost/time, we can inject the one we just built.
                context_data['daily_context'] = raw_summary
                
                # 2. Macro State
                macro_state = self.macro_processor.get_state(date_str)
                if not macro_state:
                    # print(f"   ⚠️ Macro Missing: {date_str}")
                    current_date += delta
                    continue
                    
                # 3. Z-Score
                z_score_data = self.engine.get_z_score(date_str)
                
                # 4. Decision
                try:
                    decision = self.engine.decide(news_input, macro_state=macro_state, z_score_data=z_score_data, mode="general", context_data=context_data)
                except Exception as e:
                    print(f"   ❌ Engine Error: {e}")
                    current_date += delta
                    continue
                    
                # 5. Return & Eval
                ret = self.calculate_return("SPY", date_str)
                fail_type = self.classify_error(decision['action'], ret)
                
                loop_stats["total"] += 1
                if fail_type is None:
                    loop_stats["correct"] += 1
                else:
                    # 6. Auto-Learn
                    # Create a mock event for auto-learn context
                    mock_event = {
                        "event_name": f"Market Move {date_str}",
                        "description": fused_content,
                        "date": date_str,
                        "ticker": "SPY"
                    }
                    self.auto_learn(mock_event, decision, ret, fail_type)
                    
                if decision.get('meta_rag_status') == "Warning":
                    loop_stats["meta_rag"] += 1
                    
                current_date += delta
                
            # Loop Summary
            win_rate = (loop_stats["correct"] / loop_stats["total"]) * 100 if loop_stats["total"] > 0 else 0
            print(f"\n✅ Loop {loop + 1} Complete. Win Rate: {win_rate:.1f}% ({loop_stats['correct']}/{loop_stats['total']})")
            
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run G9 Full History Backtest')
    parser.add_argument('--start_year', type=int, default=2000, help='Start year (YYYY)')
    parser.add_argument('--end_year', type=int, default=2025, help='End year (YYYY)')
    parser.add_argument('--loops', type=int, default=3, help='Number of learning loops')
    parser.add_argument('--worker_id', type=int, default=1, help='Worker ID for logging')
    
    args = parser.parse_args()
    
    runner = FullHistoryBacktest()
    print(f"👷 Worker {args.worker_id} initialized for range {args.start_year}-{args.end_year}")
    runner.run_full_backtest(args.start_year, args.end_year, loops=args.loops)
