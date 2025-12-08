import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client
from utils.openrouter_client import ask_llm
from g9_macro_factory.prompts import DEEPSEEK_SYSTEM_PROMPT, DAILY_REPORT_PROMPT, GLOBAL_DAILY_PROMPT
from g9_macro_factory.utils.macro_processor import get_macro_processor
from g9_macro_factory.engine.regime_detector import RegimeDetector
from g9_macro_factory.utils.holiday_utils import is_trading_day, get_no_session_json

class DailyReportGenerator:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.model = "x-ai/grok-4.1-fast:free" # Grok 4.1 Fast
        self.macro_processor = get_macro_processor()
        self.regime_detector = RegimeDetector()

    def generate(self, date_str: str, country: str = "US"):
        print(f"   📝 Generating Daily Report for {date_str} ({country})...")
        
        # 1. Fetch Preprocessed Data from macro_daily
        macro_data = self._fetch_macro_daily(date_str, country)
        
        if not macro_data:
            print(f"   ⚠️ No preprocessed data found for {date_str}. Skipping.")
            return None
            
        processed_json = macro_data.get("processed_json", {})
        
        # 2. Check Trading Day / Meta Flags
        meta_flags = processed_json.get("meta_flags", {})
        if not meta_flags.get("is_trading_day", True): # Default to True if missing to be safe, but preprocessor should set it
            print(f"   🏖️ {date_str} is a Holiday/Weekend ({country}). Skipping Report Generation.")
            # We might still want to save a "No Session" report entry in daily_reports if needed, 
        # 2. Extract Data
        # The schema is flattened now, so we access keys directly from the row
        z_score = preprocess_data.get("zscore", 0.0)
        headlines = preprocess_data.get("headline_clean", [])
        
        # 3. Get Yesterday's Context
        yesterday_summary = self._get_yesterday_summary(date_str, country)
        
        # 4. Construct Prompt
        headlines_text = ""
        # headlines is a list of dicts (jsonb)
        if isinstance(headlines, str):
            headlines = json.loads(headlines)
            
        for h in headlines[:50]:
            headlines_text += f"- [{h.get('country', 'UNK')}] {h.get('title', '')}\n"
            
        prompt = GLOBAL_DAILY_PROMPT.format(
            date=date_str,
            regime=self.regime_detector.detect_regime(z_score),
            z_score_list=f"Global/US Proxy: {z_score}", 
            yesterday_summary=yesterday_summary,
            headlines=headlines_text
        )
        
        # 5. Call LLM
        try:
            response_json_str = ask_llm(prompt, model=self.model, system_prompt=DEEPSEEK_SYSTEM_PROMPT)
            
            # Parse JSON
            if "```json" in response_json_str:
                response_json_str = response_json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in response_json_str:
                response_json_str = response_json_str.split("```")[1].split("```")[0].strip()
                
            report_data = json.loads(response_json_str)
            
            # 6. Save to DB (reports_daily)
            self._save_report(date_str, country, report_data)
            return report_data
            
        except Exception as e:
            print(f"   ❌ Daily Generation Failed: {e}")
            return None

    def _fetch_preprocess_daily(self, date_str: str, country: str) -> Dict:
        try:
            res = self.supabase.table("preprocess_daily")\
                .select("*")\
                .eq("date", date_str)\
                .eq("country", country)\
                .execute()
            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            print(f"   ⚠️ Failed to fetch preprocess_daily: {e}")
            return None

    def _get_yesterday_summary(self, date_str: str, country: str) -> str:
        yesterday_date = (datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Fetch previous report from reports_daily
        prev_report = self._fetch_daily_report(yesterday_date, country)
        
        if prev_report and prev_report.get('report_json'):
            content = prev_report['report_json']
            if isinstance(content, str):
        # YouTube
        youtube_summaries = self._fetch_youtube_summaries(date_str)
        youtube_lines = []
        for yt in youtube_summaries:
            youtube_lines.append(f"- [YouTube: {yt.get('channel_name', 'Unknown')}] {yt['title']}: {yt.get('summary', '')}")
            
        combined_text = "--- NEWS ---\n" + "\n".join(news_lines)
        if youtube_lines:
            combined_text += "\n\n--- YOUTUBE INSIGHTS ---\n" + "\n".join(youtube_lines)
            
        headline_text = combined_text
        
        # [GLOBAL FUSION SWITCH]
        if country == "GLOBAL":
            prompt = GLOBAL_DAILY_PROMPT.replace("{date}", date_str)\
                .replace("{regime}", regime)\
                .replace("{z_score_list}", z_score_json) \
                .replace("{delta_z}", f"{delta_z:.2f}")\
                .replace("{yesterday_summary}", yesterday_summary)\
                .replace("{headlines_text}", headline_text)
        else:
            prompt = DAILY_REPORT_PROMPT.replace("{date}", date_str)\
                .replace("{regime}", regime)\
                .replace("{z_score_list}", z_score_list)\
                .replace("{delta_z}", f"{delta_z:.2f}")\
                .replace("{is_weekend}", str(is_weekend))\
                .replace("{yesterday_summary}", yesterday_summary)\
                .replace("{headlines_text}", headline_text)
        
        # 5. Call LLM with Retry & Validation
        report_data = None
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            try:
                response_json_str = ask_llm(prompt, model=self.model, system_prompt=DEEPSEEK_SYSTEM_PROMPT)
                if not response_json_str:
                    raise ValueError("Empty response from LLM")
                    
                # Clean json string
                if "```json" in response_json_str:
                    response_json_str = response_json_str.split("```json")[1].split("```")[0].strip()
                elif "```" in response_json_str:
                    response_json_str = response_json_str.split("```")[1].split("```")[0].strip()
                
                data = json.loads(response_json_str)
                
                # [Certification Point 6] Strict Schema Validation
                # Validate Keys (Updated for G3 Architecture)
                required_keys = [
                    "market_context", 
                    "headline_clusters", 
                    "zscore_focus", 
                    "structural_insight", 
                    "risk_signals", 
                    "action_drivers", 
                    "trader_playbook",
                    "tomorrows_watchlist",
                    "summary_3line"
                ]
                missing_keys = [k for k in required_keys if k not in data]
                if missing_keys:
                    print(f"   ⚠️ Validation Error (Attempt {attempt+1}): Missing JSON keys: {missing_keys}")
                    continue
                
                # Deep Validation for G3.5 Architecture
                if "narrative_arc_stage" not in data.get("market_context", {}):
                    print(f"   ⚠️ Validation Error (Attempt {attempt+1}): Missing 'narrative_arc_stage'")
                    continue
                
                action_drivers = data.get("action_drivers", {})
                if "bias" not in action_drivers and "intraday_bias" not in action_drivers:
                     print(f"   ⚠️ Validation Error (Attempt {attempt+1}): Missing 'bias' or 'intraday_bias'")
                     continue
                
                report_data = data
                break # Success
                
            except json.JSONDecodeError:
                print(f"   ⚠️ JSON Decode Error (Attempt {attempt+1})")
            except ValueError as ve:
                print(f"   ⚠️ Validation Error (Attempt {attempt+1}): {ve}")
            except Exception as e:
                print(f"   ⚠️ Generation Error (Attempt {attempt+1}): {e}")
        
        if not report_data:
            print(f"   ❌ Failed to generate valid report for {date_str} after retries.")
            return None

        # 6. Save to DB
        self._save_report(date_str, country, report_data)
        return report_data

    def _fetch_headlines(self, date_str: str, country: str) -> List[Dict]:
        try:
            query = self.supabase.table("global_news_all")\
                .select("title, summary, country")\
                .gte("published_at", f"{date_str}T00:00:00")\
                .lte("published_at", f"{date_str}T23:59:59")
                
            if country == "GLOBAL":
                # Fetch all major countries
                query = query.in_("country", ["US", "KR", "JP", "CN"])
                # Limit higher for global
                query = query.limit(400)
            else:
                query = query.eq("country", country).limit(250)
                
            res = query.execute()
            return res.data or []
        except Exception as e:
            return []

    def _fetch_z_score(self, date_str: str) -> Dict:
        try:
            res = self.supabase.table("zscore_daily")\
                .select("z_score")\
                .eq("date", date_str)\
                .execute()
            if res.data:
                return res.data[0]
        except:
            pass
        return {"z_score": 0.0}

    def _fetch_youtube_summaries(self, date_str: str) -> List[Dict]:
        try:
            # Fetch YouTube transcripts for the day
            # Assuming published_at is timestamp, we filter by day
            res = self.supabase.table("youtube_transcripts")\
                .select("channel_name, title, summary")\
                .gte("published_at", f"{date_str}T00:00:00")\
                .lte("published_at", f"{date_str}T23:59:59")\
                .execute()
            return res.data or []
        except Exception as e:
            # print(f"   ⚠️ Failed to fetch YouTube summaries: {e}")
            return []

    def _fetch_daily_report(self, date_str: str, country: str) -> Dict:
        try:
            res = self.supabase.table("daily_reports")\
                .select("content")\
                .eq("date", date_str)\
                .eq("country", country)\
                .execute()
            if res.data:
                return res.data[0]
        except:
            pass
        return None

    def _save_report(self, date_str: str, country: str, data: Dict):
        try:
            summary_lines = data.get("summary_3line", [])
            summary_text = "\n".join(summary_lines) if isinstance(summary_lines, list) else str(summary_lines)
            
            payload = {
                "date": date_str,
                "country": country,
                "content": json.dumps(data),
                "summary": summary_text,
                "created_at": "now()"
            }
            # [Certification Point 8] Race Condition Prevention
            # Using upsert with ignoreDuplicates=True equivalent? 
            # Supabase-py 'upsert' usually updates on conflict. 
            # To DO NOTHING, we can rely on the unique index and catch the exception, OR use on_conflict='ignore' if supported.
            # For now, we rely on the Unique Index we just added and catch the error.
            self.supabase.table("daily_reports").insert(payload).execute()
        except Exception as e:
            if "duplicate key" in str(e) or "23505" in str(e): # Postgres unique violation code
                print(f"   ⏭️ Report for {date_str} already exists (DB Constraint).")
            else:
                print(f"   ⚠️ Failed to save daily report: {e}")

if __name__ == "__main__":
    gen = DailyReportGenerator()
    gen.generate("2023-01-03", "US")
