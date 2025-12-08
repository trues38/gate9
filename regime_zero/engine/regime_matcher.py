import json
import os
import pandas as pd
from datetime import datetime
from utils.openrouter_client import ask_llm
from regime_zero.engine.vector_indexer import VectorIndexer

class RegimeMatcher:
    def __init__(self, master_file="regime_zero/data/regimes/master_regime_history.jsonl", price_file="regime_zero/data/market_data/BTC_price_history.csv"):
        self.master_file = master_file
        self.price_file = price_file
        self.history = self._load_history()
        self.price_data = self._load_price_data()
        self.indexer = VectorIndexer()
        
    def _load_history(self):
        """Loads master regime history."""
        records = []
        if os.path.exists(self.master_file):
            with open(self.master_file, 'r') as f:
                for line in f:
                    try:
                        records.append(json.loads(line))
                    except:
                        continue
        return records

    def _load_price_data(self):
        """Loads BTC price history for return calculation."""
        if not os.path.exists(self.price_file):
            return {}
        df = pd.read_csv(self.price_file)
        # Ensure Date is string YYYY-MM-DD
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        return df.set_index('Date')['Close'].to_dict()

    def _calculate_returns(self, start_date, days=30):
        """Calculates future returns from start_date."""
        if start_date not in self.price_data:
            return None
            
        start_price = self.price_data[start_date]
        
        # Find price N days later
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        target_dt = start_dt + pd.Timedelta(days=days)
        target_date_str = target_dt.strftime("%Y-%m-%d")
        
        # Look for exact date or closest future date
        future_dates = sorted([d for d in self.price_data.keys() if d >= target_date_str])
        if not future_dates:
            return None
            
        end_price = self.price_data[future_dates[0]]
        return ((end_price - start_price) / start_price) * 100

    def find_structural_twins(self, target_date, top_k=3):
        """Finds the most similar historical dates (Structural Twins) using Vector Search."""
        target_record = next((r for r in self.history if r['date'] == target_date), None)
        
        if not target_record:
            print(f"❌ No regime data found for {target_date}")
            return []
            
        print(f"🔍 Finding twins for {target_date} (Total History: {len(self.history)} days)...")
        
        # 1. Vector Search
        # Search for similar regimes excluding future dates
        results = self.indexer.search(target_record['summary_text'], top_k=10, filter_date=target_date)
        
        if not results:
            print("⚠️ No historical candidates found.")
            return []
            
        # 2. Prepare Candidate Data with Outcomes
        candidate_data = []
        for score, cand in results:
            ret_7d = self._calculate_returns(cand['date'], 7)
            ret_30d = self._calculate_returns(cand['date'], 30)
            
            outcome_str = "Outcome: Data Unavailable"
            if ret_7d is not None and ret_30d is not None:
                outcome_str = f"Outcome: +7d: {ret_7d:.1f}%, +30d: {ret_30d:.1f}%"
                
            candidate_data.append({
                "record": cand,
                "outcome": outcome_str,
                "similarity_score": score
            })
        
        # 3. Final LLM Verdict
        prompt = self._build_matcher_prompt(target_record, candidate_data)
        
        try:
            response = ask_llm(prompt, system_prompt="You are a Historical Regime Matcher. Output JSON.")
            clean_resp = response.replace("```json", "").replace("```", "").strip()
            result = json.loads(clean_resp)
            return result.get('matches', [])
        except Exception as e:
            print(f"❌ Matcher Error: {e}")
            return []

    def _build_matcher_prompt(self, target, candidate_data):
        candidates_str = ""
        for i, item in enumerate(candidate_data):
            cand = item['record']
            outcome = item['outcome']
            score = item['similarity_score']
            candidates_str += f"""
[Candidate {i+1}] Date: {cand['date']} (Vector Similarity: {score:.2f})
Summary:
{cand['summary_text']}
{outcome}
--------------------------------------------------
"""
        
        return f"""
Target Date: {target['date']}
Target Regime Summary:
{target['summary_text']}

--------------------------------------------------
Historical Candidates:
{candidates_str}

[Task]
Identify the top {3} "Structural Twins" from the candidates above.
A "Structural Twin" is a date where the **underlying causal drivers** (e.g., "Rate Cut Expectation" + "Oil Supply Shock") are most similar to the Target.

For each match, provide a detailed analysis in the following format:
1. **Why**: Bullet points explaining the structural similarity.
2. **Outcome**: What happened to BTC price afterwards (use the provided Outcome data).
3. **Difference**: Key nuances that differ (e.g., "War vs Peace", "Inflation Level").
4. **Conclusion**: Actionable insight based on the comparison.

Output JSON format:
{{
  "matches": [
    {{
      "rank": 1,
      "date": "YYYY-MM-DD",
      "similarity_score": "87%",
      "analysis": {{
        "why": ["Reason 1", "Reason 2"],
        "outcome": "3 weeks +15%, then correction...",
        "difference": ["Diff 1", "Diff 2"],
        "conclusion": "Short-term bullish but watch for..."
      }}
    }},
    ...
  ]
}}
"""

if __name__ == "__main__":
    matcher = RegimeMatcher()
    matches = matcher.find_structural_twins("2025-12-03")
    print(json.dumps(matches, indent=2))
