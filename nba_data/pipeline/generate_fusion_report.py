import os
import json
import duckdb
import argparse
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Load Fusion Logic
# Load Fusion Logic
from fusion_engine_prototype import get_story_layer, get_conflict_layer
from rag_engine import search_narratives, format_rag_context

# Setup
load_dotenv("/Users/js/g9/.env")
API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1" if os.getenv("OPENROUTER_API_KEY") else None

if not API_KEY:
    print("⚠️ No API Key found in .env (OPENROUTER_API_KEY or OPENAI_API_KEY)")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

CONN = duckdb.connect('nba_analytics.duckdb', read_only=True)

def get_team_id(team_name, abbr=None):
    try:
        if abbr:
            res = CONN.sql(f"SELECT team_id FROM dim_teams WHERE name = '{abbr}'").fetchone()
            if res: return res[0]
        res = CONN.sql(f"SELECT team_id FROM dim_teams WHERE abbreviation = '{team_name}'").fetchone()
        if res: return res[0]
        res = CONN.sql(f"SELECT team_id FROM dim_teams WHERE abbreviation LIKE '%{team_name}%'").fetchone()
        if res: return res[0]
        res = CONN.sql(f"SELECT team_id FROM dim_teams WHERE name LIKE '%{team_name}%'").fetchone()
        if res: return res[0]
    except:
        pass
    return None

def get_latest_quant(team_id):
    if not team_id: return {"momentum": 0.0, "label": "Unknown", "record": "0-0", "streak": "-"}
    try:
        q = f"""
        SELECT momentum_score, regime_label, record, streak 
        FROM fact_regimes 
        WHERE team_id={team_id} 
        ORDER BY date DESC LIMIT 1
        """
        res = CONN.sql(q).fetchone()
        if res:
            return {"momentum": float(res[0]), "label": res[1], "record": res[2], "streak": res[3]}
    except:
        pass
    return {"momentum": 0.0, "label": "No Data", "record": "0-0", "streak": "-"}

def build_matchup_context(home_name, away_name):
    h_id = get_team_id(home_name)
    a_id = get_team_id(away_name)
    
    if not h_id or not a_id:
        print(f"❌ Team lookup failed for {home_name} or {away_name}")
        return None

    target_date = "2025-12-10" # Use latest data
    
    # Layers
    q_home = get_latest_quant(h_id)
    q_away = get_latest_quant(a_id)
    
    s_home = get_story_layer(CONN, h_id, target_date)
    s_away = get_story_layer(CONN, a_id, target_date)
    
    c_home = get_conflict_layer(q_home, s_home)
    c_away = get_conflict_layer(q_away, s_away)
    
    # -------------------------------------------------------------
    # NEW: RAG Context Injection (Reality Check)
    # -------------------------------------------------------------
    print(f"🔍 RAG: Searching narratives for {home_name} & {away_name}...")
    
    # Narrative Queries
    # We want "Conflict", "Momentum", "Key Player Issues"
    h_hits = search_narratives(f"{home_name} recent conflict injury momentum story", n_results=5)
    a_hits = search_narratives(f"{away_name} recent conflict injury momentum story", n_results=5)
    
    h_rag = format_rag_context(h_hits)
    a_rag = format_rag_context(a_hits)
    
    return {
        "matchup": f"{away_name} @ {home_name}",
        "date": target_date,
        "home": {
            "name": home_name,
            "quant": q_home,
            "story": s_home,
            "fusion": c_home,
            "rag_context": h_rag
        },
        "away": {
            "name": away_name,
            "quant": q_away,
            "story": s_away,
            "fusion": c_away,
            "rag_context": a_rag
        }
    }

SYSTEM_PROMPT = """
You are the **FUSION ENGINE AI**, a hyper-advanced NBA predictive system.
Your goal is to generate the **"11-Layer Fusion Report"** for a specific matchup.

**DATA SOURCES PROVIDED:**
1. **Quant Data**: Momentum scores, records.
2. **Story Data**: Persona vectors, vibe tags.
3. **RAG Context (CRITICAL)**: Real-world narrative snippets retrieved from the database. Use this to grounding specific claims (e.g. mention specific injuries, quotes, or game events found in the text).

**THE 11 LAYERS OF ANALYSIS:**
1. **Quant Momentum**: Is the team surging or crashing? (Momentum Score)
2. **Regime Type**: Juggernaut, Crisis, Sleeping Giant? (Regime Label)
3. **Story Vibe**: The emotional state of the locker room.
4. **Story Score**: 0.0 to 1.0 Sentiment Intensity.
5. **Key Player Psyche**: How are the stars feeling? (Resilient, Frustrated, Euphoric)
6. **Unified Diagnosis**: The "Fusion" result of Quant + Story.
7. **Conflict Check**: Do data and story agree? (Coherent vs Dissonant).
8. **Risk Assessment**: Volatility risk.
9. **Matchup Dynamics**: How do these two fusion profiles interact?
10. **Win Condition**: What must happen for Victory?
11. **Final Verdict**: Confidence Level & Predicted flow.

**INSTRUCTIONS:**
- **Compare Home vs Away** across all layers.
- **Synthesize RAG Context**: When describing the "Story Vibe" or "Conflict", explicitly cite details from the `rag_context` provided (e.g. "Similar to the recent loss against...").
- **Output Style**: Korean (Expert Tone), Markdown, Insightful.
- **Verdict**: Clear and Bold.
"""

def generate_llm_report(context):
    print(f"🧠 Fusion Engine: Generating Report for {context['matchup']}...")
    
    user_prompt = f"""
    ANALYZE THIS MATCHUP DATA:
    
    {json.dumps(context, indent=2, ensure_ascii=False)}
    
    Write the 11-Layer Fusion Report in Korean.
    Identify the key narrative arc (e.g., Clash of Titans, Trap Game, Desperation Match).
    """
    
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-4o-mini", # Or deepseek/deepseek-chat
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return "Report Generation Failed."

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True)
    parser.add_argument("--away", required=True)
    args = parser.parse_args()
    
    ctx = build_matchup_context(args.home, args.away)
    if ctx:
        report = generate_llm_report(ctx)
        
        # Save
        filename = f"backtest/reports/fusion_report_{args.away}_vs_{args.home}_{datetime.now().strftime('%Y%m%d')}.md".replace(" ", "_")
        with open(filename, "w") as f:
            f.write(report)
        print(f"✅ Saved Report: {filename}")
        print(report)
