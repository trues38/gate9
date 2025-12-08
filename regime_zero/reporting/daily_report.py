import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from regime_zero.ingest.fetch_market_data import get_market_vector
from regime_zero.ingest.fetch_headlines import get_daily_headlines
from regime_zero.embedding.vectorizer import vectorize_market_state
from regime_zero.engine.matcher import match_regime
from regime_zero.engine.explainer import explain_regime_match
from regime_zero.reporting.predictor import calculate_regime_stats
from regime_zero.universe.generate_regimes import generate_regime_for_date
from regime_zero.visualization.prepare_viz_data import prepare_data
from regime_zero.engine.council import run_council_meeting

OUTPUT_DIR = "regime_zero/reports"
REGIME_OBJECTS_FILE = "regime_zero/data/regime_objects.jsonl"

def _format_list(items):
    if not items: return "None"
    return "\n".join([f"- {item}" for item in items])

def generate_daily_report(target_date, ticker="BTC"):
    print(f"🚀 [Regime Zero] Generating Report for {target_date} (Ticker: {ticker})...")
    
    # 1. Data Input
    # For Bitcoin, we might not have 'market_vector' from standard sources yet, 
    # but we will rely heavily on News (Headlines) as per user request.
    market_data = get_market_vector(target_date) # This might be empty for BTC specific data, but useful for macro context.
    headlines = get_daily_headlines(target_date, ticker=ticker)
    
    using_macro_fallback = False
    if not headlines:
        print(f"⚠️ No specific headlines for {ticker}. Falling back to Global Macro News.")
        headlines = get_daily_headlines(target_date, ticker=None)
        using_macro_fallback = True
        
    if not headlines:
        print(f"❌ No headlines available for {ticker} or Global Macro.")
        return
        
    # 2. Embedding & Matching
    # Note: We are using Macro Market Data + Bitcoin News to find the Regime.
    # This is "Macro-Regime" mapping for Bitcoin.
    # If using fallback, we prepend a context note.
    context_headlines = headlines
    if using_macro_fallback:
        context_headlines = [f"[NOTE: Analyzing {ticker} using Global Macro News]"] + headlines

    vector, prompt = vectorize_market_state(target_date, market_data, context_headlines)
    matched_historical, score = match_regime(vector)
    
    similarity_score = score if matched_historical else 0.0
    print(f"🔍 [Regime Zero] Similarity Score: {similarity_score:.4f}")

    # 3. Council of Historians Meeting
    print("🏛️ Convening the Council of Historians...")
    # Pass similarity_score to the Council
    council_result = run_council_meeting(target_date, market_data, headlines, similarity_score)
    
    if not council_result:
        print("❌ Council failed to reach consensus.")
        return
        
    consensus_regime = council_result['consensus']
    final_reports = council_result['reports']
    audit = council_result['audit']

    # 4. Save Reports
    print("📝 [Regime Zero] Saving Two-Track Reports...")
    
    CONSENSUS_DIR = "regime_zero/reports/consensus"
    DAILY_DIR = "regime_zero/reports/daily"
    
    if not os.path.exists(CONSENSUS_DIR): os.makedirs(CONSENSUS_DIR)
    if not os.path.exists(DAILY_DIR): os.makedirs(DAILY_DIR)

    # Save Retail Report
    retail_filename = f"{DAILY_DIR}/Retail_Report_{ticker}_{target_date}.md"
    with open(retail_filename, "w") as f:
        f.write(final_reports['retail_report'])
    print(f"✅ Retail Report saved to {retail_filename}")

    # Save Institutional Report
    inst_header = f"""**Institutional Investment Memorandum**

**Confidential**

**Date:** {datetime.strptime(target_date, "%Y-%m-%d").strftime("%B %d, %Y")}

**Prepared by:** Regime Zero Institutional Investment Division

---

"""
    inst_footer = """

---

*This report is intended for the exclusive use of Regime Zero's institutional partners and accredited investors. Distribution or dissemination of this information without explicit authorization is strictly prohibited.*

**Prepared by:** Senior Chief Investment Officer, Regime Zero
"""
    
    inst_content = inst_header + final_reports['institutional_report'] + inst_footer
    
    inst_filename = f"{CONSENSUS_DIR}/Institutional_Report_{target_date}.md"
    with open(inst_filename, "w") as f:
        f.write(inst_content)
    print(f"✅ Institutional Report saved to {inst_filename}")
    
    # 7. Visualization Update (Universe Expansion)
    print(f"🌌 [Regime Zero] Updating Universe for {target_date}...")
    
    # Check if we already have this date in objects
    exists = False
    if os.path.exists(REGIME_OBJECTS_FILE):
        with open(REGIME_OBJECTS_FILE, "r") as f:
            for line in f:
                if f'"date": "{target_date}"' in line:
                    exists = True
                    break
    
    if not exists:
        regime_obj = generate_regime_for_date(target_date)
        if regime_obj:
            with open(REGIME_OBJECTS_FILE, "a") as f:
                f.write(json.dumps(regime_obj) + "\n")
            print(f"✅ Added {target_date} to Regime Universe.")
            
            # Refresh Viz Data
            prepare_data()
        else:
            print("⚠️ Failed to generate regime object.")
    else:
        print(f"ℹ️ {target_date} already in Universe. Refreshing viz data anyway...")
        prepare_data()

    return [retail_filename, inst_filename]

if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")
    generate_daily_report(today, ticker="BTC")
