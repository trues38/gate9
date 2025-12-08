import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client
from g9_macro_factory.utils.holiday_utils import is_trading_day, get_no_session_json

class DailyPreprocessor:
    def __init__(self):
        self.supabase = get_supabase_client()

    def process(self, date_str: str, country: str = "GLOBAL") -> bool:
        """
        Aggregates data for the given date and saves to preprocess_daily.
        Returns True if successful.
        """
        # 1. Holiday Check & Meta Flags
        is_trading = is_trading_day(date_str, country)
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        is_weekend_bool = dt.weekday() >= 5
        
        meta_flags = {
            "is_trading_day": is_trading,
            "is_weekend": is_weekend_bool,
            "holiday_name": None
        }
        
        if not is_trading:
            # Save No-Session Data (Flattened)
            return self._save_to_preprocess_daily_flattened(
                date_str=date_str,
                country=country,
                is_market_open=False,
                is_holiday=not is_trading and not is_weekend_bool,
                is_weekend=is_weekend_bool,
                headline_count=0,
                valid_headline_count=0,
                noise_rate=0.0,
                zscore=None,
                delta_z=None,
                headline_raw=[],
                headline_clean=[],
                meta_flags=meta_flags
            )

        # 2. Fetch Headlines (Raw & Clean)
        raw_headlines = self._fetch_headlines(date_str, country)
        clean_headlines = self._filter_garbage(raw_headlines)
        
        noise_count = len(raw_headlines) - len(clean_headlines)
        noise_rate = (noise_count / len(raw_headlines)) if raw_headlines else 0.0
        
        # 3. Fetch Z-Score & Delta
        z_score_data = self._fetch_z_score(date_str)
        z_score = z_score_data.get('z_score', 0.0)
        prev_z = self._fetch_prev_z_score(date_str)
        delta_z = z_score - prev_z if prev_z is not None else 0.0
        
        # 4. Save Flattened
        return self._save_to_preprocess_daily_flattened(
            date_str=date_str,
            country=country,
            is_market_open=True,
            is_holiday=False,
            is_weekend=is_weekend_bool,
            headline_count=len(raw_headlines),
            valid_headline_count=len(clean_headlines),
            noise_rate=round(noise_rate, 2),
            zscore=z_score,
            delta_z=delta_z,
            headline_raw=raw_headlines,
            headline_clean=clean_headlines,
            meta_flags=meta_flags
        )

    def _save_to_preprocess_daily_flattened(self, date_str, country, is_market_open, is_holiday, is_weekend, 
                                     headline_count, valid_headline_count, noise_rate, zscore, delta_z, 
                                     headline_raw, headline_clean, meta_flags):
        try:
            payload = {
                "date": date_str,
                "country": country,
                "is_market_open": is_market_open,
                "is_holiday": is_holiday,
                "is_weekend": is_weekend,
                "headline_count": headline_count,
                "valid_headline_count": valid_headline_count,
                "noise_rate": noise_rate,
                "zscore": zscore,
                "delta_z": delta_z,
                "headline_raw": headline_raw,
                "headline_clean": headline_clean,
                "meta_flags": meta_flags,
                "created_at": "now()"
            }
            
            self.supabase.table("preprocess_daily").upsert(payload, on_conflict="date, country").execute()
            return True
        except Exception as e:
            print(f"   ❌ Save Error ({date_str}): {e}")
            return False

    def _filter_garbage(self, headlines: List[Dict]) -> List[Dict]:
        """
        Filters out meaningless headlines.
        """
        cleaned = []
        garbage_keywords = ["Click here", "Subscribe", "Login", "Sign up", "JavaScript"]
        
        for h in headlines:
            title = h.get("title", "")
            if not title: continue
            if len(title) < 10: continue # Too short
            if any(k in title for k in garbage_keywords): continue
            
            cleaned.append(h)
        return cleaned

    def _fetch_headlines(self, date_str: str, country: str) -> List[Dict]:
        try:
            query = self.supabase.table("ingest_news")\
                .select("title, summary, country, published_at")\
                .gte("published_at", f"{date_str}T00:00:00")\
                .lte("published_at", f"{date_str}T23:59:59")
                
            if country == "GLOBAL":
                query = query.in_("country", ["US", "KR", "JP", "CN"])
                query = query.limit(500) # Increased limit for raw
            else:
                query = query.eq("country", country).limit(300)
                
            res = query.execute()
            
            cleaned = []
            for item in (res.data or []):
                cleaned.append({
                    "title": item.get("title"),
                    "summary": item.get("summary"),
                    "country": item.get("country")
                })
            return cleaned
        except Exception as e:
            print(f"   ⚠️ Fetch Headlines Error: {e}")
            return []

    def _fetch_z_score(self, date_str: str) -> Dict:
        try:
            res = self.supabase.table("zscore_daily")\
                .select("z_score")\
                .eq("date", date_str)\
                .execute()
            if res.data:
                return res.data[0]
            return {"z_score": 0.0}
        except Exception as e:
            return {"z_score": 0.0}

    def _fetch_prev_z_score(self, date_str: str) -> float:
        try:
            # Simple previous day fetch
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            prev_dt = dt - timedelta(days=1)
            prev_date_str = prev_dt.strftime("%Y-%m-%d")
            
            res = self.supabase.table("zscore_daily")\
                .select("z_score")\
                .eq("date", prev_date_str)\
                .execute()
            if res.data:
                return res.data[0]['z_score']
            return 0.0
        except:
            return 0.0

    def _save_to_macro_daily(self, date_str: str, country: str, data: Dict) -> bool:
        try:
            payload = {
                "date": date_str,
                "country": country,
                "processed_json": json.dumps(data),
                "created_at": "now()"
            }
            self.supabase.table("macro_daily").upsert(payload, on_conflict="date, country").execute()
            return True
        except Exception as e:
            print(f"   ❌ Save Error ({date_str}): {e}")
            return False

if __name__ == "__main__":
    processor = DailyPreprocessor()
    processor.process("2000-01-03", "GLOBAL")
