import json
import os
import argparse
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Import the Engine
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from matchup_engine import MatchupEngine

# CONFIG
import sqlite3
import duckdb
from typing import Optional, Dict, Any

# Environment Setup
load_dotenv("/Users/js/g9/.env")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

DATA_DIR = Path("/Users/js/g9/nba_data")

# Model List for Failover (Cost Optimized)
MODELS = [
    "openai/gpt-4o-mini",          # Primary: Most Stable & Fast
    "deepseek/deepseek-chat",      # Backup 1: V3 (High Efficiency)
    "x-ai/grok-2-1212",            # Backup 2: Grok 2
    "meta-llama/llama-3.3-70b-instruct" # Backup 3: Open Source
]

SYSTEM_PROMPT = """
You are REGIME PRO ANALYST (V2), a high-stakes predictive intelligence engine.
Your goal is to produce a **PREMIUM, DEEP-DIVE ALPHA MEMO** for a sophisticated investor.

**CRITICAL INSTRUCTIONS:**
1.  **NO PLACEHOLDER TEXT**: Never use "BOS vs TOR" or "Team A". Use the ACTUAL TEAMS from the input data.
2.  **DEPTH REQURIED**: This is a paid product. Summaries are unacceptable. Write at least 3-4 detailed paragraphs per section.
3.  **TONE**: Institutional. Hedge Fund Quality. Data-Driven but Narrative-Rich.
4.  **FORMAT**: Strict HTML body (Tailwind CSS).

**CONCEPTUAL FRAMEWORK:**
- **Regime Interaction**: How does 'Surging Momentum' (Team A) clash with 'Systematic Control' (Team B)?
- **Third Player (Refs)**: Treat the Crew Chief as a variable that modifies the game physics (Chaos vs Order).
- **Variance**: Where is the upset potential?

**OUTPUT STRUCTURE:**

1.  **THE ALPHA SIGNAL (Executive Threat Assessment)**
    - Synthesize the core market disconnect.
    - Example: "Market prices a blowout, but Regime Data indicates a 'Trap Game' due to Miami's falling volatility..."
    - *Write 2-3 powerful paragraphs explaining the edge.*

2.  **REGIME COLLISION MAP (Deep Dive)**
    - Detailed breakdown of Home vs Away styles.
    - Use the Momentum/Volatility scores to tell a story of "Force vs Object".
    - *Must be the longest section.*

3.  **THE THIRD PLAYER: OFFICIATING**
    - Analyze the Crew Chief's impact on this SPECIFIC matchup style.
    - "Referee X's tendency to swallow the whistle benefits the physical style of..."

4.  **SCENARIO TREE (The "If-Then" Alpha)**
    - **Scenario A (Base Case)**: Most likely outcome (>60%).
    - **Scenario B (Variance Case)**: The specific condition needed for an upset (e.g., "If Pace > 102").
    - *Be specific about win conditions.*

5.  **CLOSING VERDICT**
    - Final Narrative Forecast. Clear winner choice with "Structural Confidence" vs "Variance Risk".

**STYLE RULES:**
- Use `<div class="bg-gray-900 border-l-4 border-green-500 p-6 my-4">` for The Alpha Signal.
- Use `####` (Markdown style) or standard headers, but keep the HTML structure clean.
- **NO GENERIC ADVICE.**
"""

def generate_report(game_id):
    print(f"🚀 Generating PREMIUM Unified Report for Game {game_id}...")
    
    # 1. Build Context
    engine = MatchupEngine()
    try:
        ctx = engine.build_context(game_id)
    except Exception as e:
        print(f"❌ Context Build Failed: {e}")
        return

    # 2. Call LLM with Failover
    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY)
    
    # Load Live Rosters (Recent Game Starters)
    roster_path = DATA_DIR / "regimes" / "current_regimes.json"
    home_starters = []
    away_starters = []
    
    if roster_path.exists():
        with open(roster_path, "r") as f:
            all_players = json.load(f)
            # Filter for last game starters
            home_starters = [p['name'] for p in all_players if str(p.get('team_id')) == str(ctx['teams']['home']['id']) and p.get('starter')]
            away_starters = [p['name'] for p in all_players if str(p.get('team_id')) == str(ctx['teams']['away']['id']) and p.get('starter')]
            
    # Apply Manual Overrides from DuckDB
    try:
        con = duckdb.connect("nba_analytics.duckdb", read_only=True)
        # Fetch overrides for today or recent
        overrides = con.execute("""
            SELECT entity_type, entity_id, field, new_value 
            FROM ops_overrides 
            WHERE target_date >= CURRENT_DATE - INTERVAL 1 DAY
        """).fetchall()
        con.close()
        
        if overrides:
            print(f"   ⚠️ Applying {len(overrides)} Manual Overrides...")
            for o_type, o_id, o_field, o_val in overrides:
                # Handle Player Status Override (e.g. "21:Devin Booker" -> "OUT")
                if o_type == "PLAYER" and o_field == "status" and o_val == "OUT":
                     # Remove from starters if present
                     p_name = o_id.split(":")[1]
                     if p_name in home_starters:
                         home_starters.remove(p_name)
                         print(f"      - Removing {p_name} from Home Starters (Manual Override)")
                     if p_name in away_starters:
                         away_starters.remove(p_name)
                         print(f"      - Removing {p_name} from Away Starters (Manual Override)")
                     
                     # Add to injury list context
                     # (Simplification: just ensure they aren't listed as playing)
    except Exception as e:
        print(f"   ⚠️ Failed to apply overrides: {e}")

    # optimize context size
    lean_ctx = clean_context_for_prompt(ctx)
    
    user_prompt = f"""
GENERATE PREMIUM LONG-FORM REPORT (>800 Words).
GAME ID: {ctx['game_id']} ({ctx['teams']['away']['name']} @ {ctx['teams']['home']['name']})

LATEST INTELLIGENCE (PREVIOUS GAME STARTERS):
- **{ctx['teams']['away']['name']}**: {", ".join(away_starters) if away_starters else "Data Unavailable"}
- **{ctx['teams']['home']['name']}**: {", ".join(home_starters) if home_starters else "Data Unavailable"}

DATA CONTEXT:
{json.dumps(lean_ctx, indent=2)}

REQUIREMENTS:
- **Include a 'ROSTER & ROTATION' Section**: Analyze the impact of the projected starters provided above.
- **Explicitly Mention Injuries**: {ctx['teams']['away']['name']} ({len(ctx['injuries']['away'])} injured), {ctx['teams']['home']['name']} ({len(ctx['injuries']['home'])} injured).
- **Focus on the specific Referee Impact**: {ctx['referee']['crew_chief']} ({ctx['referee']['regime'].get('style')}).
- **Matchup Narrative**: {ctx.get('matchup_narrative', 'Systematic Clash')}.

OUTPUT:
HTML Body Only. Use Tailwind classes.
DO NOT use Markdown triple backticks in the response.
"""
    
    content = None
    
    print(f"DEBUG: MODELS LIST = {MODELS}")
    for model in MODELS:
        print(f"  Attempting Model: {model}...")
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            if not response or not response.choices:
                print(f"  ⚠️ Invalid Response from {model}")
                continue
                
            content = response.choices[0].message.content
            
            # Validation: Ensure content is not None and has reasonable length
            if content and len(content) > 100:
                print(f"  ✅ Success with {model}")
                # Save to DB (Primary Storage)
                save_to_db(game_id, model, content)
                break # Exit loop on success
            else:
                print(f"  ⚠️ Content too short/empty with {model}")
                content = None # Reset for next try
                continue

        except Exception as e:
            print(f"  ⚠️ Failed with {model}: {e}")
            continue # Try next model

    # 3. Save Report (LLM or Fallback)
    save_path = Path("web/public/reports")
    save_path.mkdir(parents=True, exist_ok=True)
    filename = save_path / f"regime_report_{game_id}.html"

    if content:
        save_html(filename, content, ctx)
        print(f"✅ LLM Report Saved: {filename}")
    else:
        print("❌ All Models Failed. Switching to Fallback Template Engine...")
        content = generate_fallback_report(ctx)
        # Save Fallback to DB too
        save_to_db(game_id, "fallback-template", content)
        save_html(filename, content, ctx)
        print(f"✅ Fallback Report Saved: {filename}")

def save_to_db(game_id, model, content):
    try:
        con = sqlite3.connect("nba_state.db")
        cur = con.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO reports (game_id, model_used, content_html)
            VALUES (?, ?, ?)
        """, (game_id, model, content))
        con.commit()
        con.close()
        print(f"  💾 Saved Report to SQLite (nba_state.db) | Model: {model}")
    except Exception as e:
        print(f"  ❌ DB Save Failed: {e}")

def generate_fallback_report(ctx):
    # Rule-Based Narrative Generation
    home = ctx['teams']['home']
    away = ctx['teams']['away']
    
    h_mom = home['regime'].get('momentum', 0)
    a_mom = away['regime'].get('momentum', 0)
    
    # Narrative Logic
    if h_mom > 0.6 and a_mom > 0.6:
        headline = "Systematic Collision"
        narrative = "Two high-momentum forces collide. Expect tight execution and low variance."
        var_color = "text-blue-400"
    elif abs(h_mom - a_mom) > 0.4:
        headline = "Mismatch Alert"
        narrative = "One side is surging while the other struggles. The regime data points to a potential blowout."
        var_color = "text-red-400"
    else:
        headline = "Grinder's Ball"
        narrative = "Both teams show mixed signals. Expect a volatile, chaotic affair determined by clutch variance."
        var_color = "text-yellow-500"
        
    ref_style = ctx['referee']['regime'].get('style', 'Standard')
    
    html = f"""
    <!-- FALLBACK GENERATED CONTENT -->
    <h2 class="text-2xl text-blue-400 border-l-4 border-blue-500 pl-4 mb-6">1. Executive Overview: {headline}</h2>
    <p>{narrative}</p>
    
    <h2 class="text-2xl text-yellow-500 border-l-4 border-yellow-500 pl-4 mb-6">2. Regime Snapshot</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div class="bg-[#111] p-6 rounded-lg border border-gray-800">
            <h3 class="text-xl font-bold text-green-500 mb-2">{home['name']} (Home)</h3>
            <ul class="space-y-2 text-sm font-mono text-gray-400">
                <li>Momentum: <span class="text-green-400">{h_mom}</span></li>
                <li>Label: {home['regime'].get('regime_label', 'Unknown')}</li>
            </ul>
        </div>
        <div class="bg-[#111] p-6 rounded-lg border border-gray-800">
             <h3 class="text-xl font-bold text-green-500 mb-2">{away['name']} (Away)</h3>
             <ul class="space-y-2 text-sm font-mono text-gray-400">
                <li>Momentum: <span class="text-green-400">{a_mom}</span></li>
                <li>Label: {away['regime'].get('regime_label', 'Unknown')}</li>
            </ul>
        </div>
    </div>
    
    <h2 class="text-2xl text-red-500 border-l-4 border-red-500 pl-4 mb-6">3. Referee Impact</h2>
    <p>Crew Chief: <strong>{ctx['referee']['crew_chief']}</strong> ({ref_style})</p>
    <p class="text-gray-400 mt-2">{ctx['referee']['regime'].get('notes', 'No specific data.')}</p>
    
    <h2 class="text-2xl text-white border-b-2 border-white pb-2 mb-6 mt-12">4. Closing Signal</h2>
    <p class="text-xl font-light text-gray-200">
        Regime Mismatch indicates a <strong>{headline}</strong> scenario. Monitor in-game momentum shift.
    </p>
    """
    return html
    
def clean_context_for_prompt(ctx):
    # Recursively remove heavy keys (vector, embedding, history frames)
    # create a deep copy or just traverse
    
    if isinstance(ctx, dict):
        new_dict = {}
        for k, v in ctx.items():
            if k in ['vector', 'embedding', 'history_raw', 'chunks', 'story_vector', 'latent_vector']:
                continue
            new_dict[k] = clean_context_for_prompt(v)
        return new_dict
    elif isinstance(ctx, list):
        return [clean_context_for_prompt(i) for i in ctx]
    else:
        return ctx

def save_html(filepath, content, ctx):
    # Wrapper HTML
    teams = ctx['teams']
    title = f"{teams['away']['name']} vs {teams['home']['name']}"
    
    clean_content = content.replace("```html", "").replace("```", "")
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>REGIME REPORT: {title}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>body {{ background: #050505; color: #e5e5e5; font-family: 'Inter', sans-serif; }}</style>
</head>
<body class="max-w-4xl mx-auto p-6 md:p-12">
    <div class="mb-8 border-b border-gray-800 pb-6">
        <h1 class="text-3xl md:text-5xl font-black text-white tracking-tight mb-2">{title}</h1>
        <div class="flex items-center gap-4 text-sm text-gray-500 font-mono">
            <span>GAME ID: {ctx['game_id']}</span>
            <span class="text-[#00FF94]">● REGIME PRO LIVE</span>
        </div>
    </div>
    
    <div class="prose prose-invert prose-lg max-w-none prose-headings:font-bold prose-headings:text-white prose-p:text-gray-300 prose-strong:text-white">
        {clean_content}
    </div>
    
    <div class="mt-16 pt-8 border-t border-gray-800 text-center text-xs text-gray-600 font-mono">
        GENERATED BY REGIME ENGINE V2 | DATA ENRICHED (ODDS/INJURY/REF)
    </div>
</body>
</html>"""

    with open(filepath, "w") as f:
        f.write(html)
        
    # Also save as Markdown for user readability
    md_filename = filepath.with_suffix(".md")
    md_content = convert_html_to_md(clean_content, title, ctx)
    with open(md_filename, "w") as f:
        f.write(md_content)
    print(f"✅ MarkDown Report Saved: {md_filename}")

def convert_html_to_md(html, title, ctx):
    import re
    
    # Basic HTML to Markdown converter
    text = html
    
    # Headers
    text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n', text)
    text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n', text)
    text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n', text)
    text = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1\n', text)
    text = re.sub(r'<h5[^>]*>(.*?)</h5>', r'##### \1\n', text)
    
    # Formatting
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text)
    text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text)
    text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text)
    text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text)
    
    # Lists
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', text)
    text = re.sub(r'<ul[^>]*>', '', text)
    text = re.sub(r'</ul>', '\n', text)
    
    # Clean all other tags but keep content
    text = re.sub(r'<[^>]+>', '', text)
    
    # Cleanup empty lines
    lines = [line.strip() for line in text.split('\n')]
    clean_text = '\n'.join([l for l in lines if l])
    
    # Header
    header = f"""# REGIME REPORT: {title}
GAME ID: {ctx['game_id']}
DATE: {ctx.get('date', '2025-12-08')}
------------------------------------------------------------
"""
    return header + clean_text

if __name__ == "__main__":
    # Test
    generate_report("401810213")
