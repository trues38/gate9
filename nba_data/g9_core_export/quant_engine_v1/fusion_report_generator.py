
import argparse
import json
import os
import sys
from datetime import datetime

print("DEBUG: Script Starting...", flush=True)

# Import Engines
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant_engine_v1 import rdata_engine
# from quant_engine_v1 import find_twin_upset_v2 # LEGACY Phase 26
from quant_engine_v1 import vector_engine # NEW Phase 27
from quant_engine_v1.tag_engine import TagEngine


# Configuration
REPORT_DIR = "/Users/js/g9/nba_data/reports"
os.makedirs(REPORT_DIR, exist_ok=True)

def generate_html_report(date_str, matches):
    """
    Generates a high-quality HTML report for the day's games.
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Regime Zero Daily Report: {date_str}</title>
        <style>
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background-color: #f4f4f4; color: #333; max-width: 1200px; margin: 0 auto; padding: 20px; }}
            header {{ background: #1a1a1a; color: #fff; padding: 20px; text-align: center; border-radius: 8px; margin-bottom: 20px; }}
            h1 {{ margin: 0; font-weight: 300; letter-spacing: 1px; }}
            .card {{ background: #fff; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .match-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 15px; margin-bottom: 15px; }}
            .team-name {{ font-size: 1.5em; font-weight: bold; }}
            .vs {{ color: #888; font-weight: bold; font-size: 1.2em; }}
            .score-box {{ text-align: center; padding: 10px; background: #f9f9f9; border-radius: 5px; }}
            .score-val {{ font-size: 1.8em; font-weight: bold; color: #2c3e50; }}
            .score-label {{ font-size: 0.8em; text-transform: uppercase; color: #7f8c8d; }}
            .analysis-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
            .quant-section {{ border-right: 1px solid #eee; padding-right: 20px; }}
            .qual-section {{ padding-left: 20px; }}
            .layer-table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
            .layer-table td {{ padding: 5px; border-bottom: 1px solid #f0f0f0; }}
            .twin-card {{ background: #eef2f3; padding: 15px; border-radius: 5px; margin-top: 10px; border-left: 4px solid #3498db; }}
            .twin-title {{ font-weight: bold; color: #2980b9; margin-bottom: 5px; }}
            .confidence-high {{ color: #27ae60; font-weight: bold; }}
            .confidence-med {{ color: #f39c12; font-weight: bold; }}
            .confidence-low {{ color: #c0392b; font-weight: bold; }}
        </style>
    </head>
    <body>
        <header>
            <h1>REGIME ZERO DAILY BRIEFING</h1>
            <p>{date_str}</p>
        </header>
    """
    
    for match in matches:
        gid = match['game_id']
        home = match['home_id']
        away = match['away_id']
        h_score = match['home_score']
        a_score = match['away_score']
        
        # Determine Status
        diff = abs(h_score - a_score)
        
        # Qualitative Context
        qual_html = ""
        twin_data = match.get('twin_data')
        
        if twin_data:
            narrative_sim = round(twin_data.get('narrative_similarity', 0) * 100, 1)
            ctx_sim = round(twin_data.get('context_similarity', 0) * 100, 1)
            final_sim = round(twin_data.get('final_score', 0) * 100, 1)
            
            story = twin_data.get('twin_story', {})
            headline = story.get('headline', 'Historical Pattern Found')
            reasoning = story.get('reasoning', 'No reasoning available.')
            
            qual_html = f"""
            <div class="twin-card">
                <div class="twin-title">HISTORICAL TWIN: {story.get('date', 'Unknown')} {story.get('matchup','')}</div>
                <div style="font-size: 0.9em; color: #555; margin-bottom: 10px;">
                    Matched via <b>{twin_data.get('cause', 'Unknown')}</b>
                </div>
                <div style="margin-bottom: 10px;">
                    "{headline}"
                </div>
                <div style="font-style: italic; color: #666; font-size: 0.9em;">
                    {reasoning}
                </div>
                <div style="margin-top: 10px; font-size: 0.8em; color: #888;">
                    Narrative Match: {narrative_sim}% | Context Match: {ctx_sim}% | <b>Fusion Score: {final_sim}</b>
                </div>
            </div>
            """
        else:
            qual_html = "<p style='color: #999; font-style: italic;'>No significant historical twin detected.</p>"

        # Safe access to stats
        h_mom = match['home_stats'].get('momentum', 0)
        a_mom = match['away_stats'].get('momentum', 0)
        h_inj = match['home_stats'].get('injury_impact', 0)
        a_inj = match['away_stats'].get('injury_impact', 0)

        html_content += f"""
        <div class="card">
            <div class="match-header">
                <div class="team-name">HOME ({home})</div>
                <div class="score-box">
                    <div class="score-val">{h_score}</div>
                    <div class="score-label">Quant Score</div>
                </div>
                <div class="vs">VS</div>
                <div class="score-box">
                    <div class="score-val">{a_score}</div>
                    <div class="score-label">Quant Score</div>
                </div>
                <div class="team-name">AWAY ({away})</div>
            </div>
            
            <div class="analysis-grid">
                <div class="quant-section">
                    <h3>Quant Radar</h3>
                    <table class="layer-table">
                        <tr><td>Momentum</td><td>{h_mom}</td><td>{a_mom}</td></tr>
                        <tr><td>Pace</td><td>{match['home_stats'].get('pace')}</td><td>{match['away_stats'].get('pace')}</td></tr>
                        <tr><td>Star Form</td><td>{match['home_stats'].get('star_form')}</td><td>{match['away_stats'].get('star_form')}</td></tr>
                        <tr><td>Matchup Adv</td><td>{match['home_stats'].get('matchup')}</td><td>{match['away_stats'].get('matchup')}</td></tr>
                        <tr><td>Injury Impact</td><td>{h_inj}</td><td>{a_inj}</td></tr>
                        <tr><td>Sched Stress</td><td>{match['home_stats'].get('schedule_stress')}</td><td>{match['away_stats'].get('schedule_stress')}</td></tr>
                        <tr><td>Clutch Rating</td><td>{match['home_stats'].get('clutch')}</td><td>{match['away_stats'].get('clutch')}</td></tr>
                    </table>
                </div>
                <div class="qual-section">
                    <h3>Qualitative Twin Engine</h3>
                    {qual_html}
                </div>
            </div>
        </div>
        """
        
    html_content += """
    </body>
    </html>
    """
    
    filename = os.path.join(REPORT_DIR, f"fusion_report_{date_str}.html")
    with open(filename, 'w') as f:
        f.write(html_content)
    
    print(f"Report Generated: {filename}")
    return filename

# Helper: Load Team Map
def load_team_map():
    roster_path = "/Users/js/g9/nba_data/players/roster_2025.json"
    if not os.path.exists(roster_path): return {}
    with open(roster_path, 'r') as f:
        roster = json.load(f)
    # ID -> Abbr/Name
    tmap = {}
    for p in roster:
        tid = p.get('TEAM_ID')
        if tid:
            tmap[tid] = f"{p.get('TEAM_CITY')} {p.get('TEAM_NAME')}"
    return tmap


def generate_regime_interpretation(game_type, upset_prob, quant_margin, market_line, injury_adj, volatility, regime_context=None):
    """
    Implements Interpretation Framework v1.0
    Returns markdown string for 🧠 REGIME INTERPRETATION section.
    """
    
    # 1. Market Assumption Identification
    assumptions = []
    abs_line = abs(market_line)
    is_fav = game_type in ['A_SAFE_FAVORITE', 'B_RISKY_FAVORITE']
    
    if abs_line > 9.5:
        assumptions.append("Home court dominance is overwhelming")
        assumptions.append("Talent disparity overcomes any volatility")
    elif abs_line > 4.5:
        assumptions.append("Standard home advantage holds")
        assumptions.append("Key rotations perform to season average")
    else:
        assumptions.append("Game is a coin-flip determined by clutch execution")
        assumptions.append("No significant structural edge exists")

    if injury_adj != 0:
        assumptions.append(f"Market has priced in known injury impacts ({injury_adj:+.1f})")

    # 2. Stress Test (Cracks in the Assumption)
    stress_points = []
    delta = quant_margin - market_line
    
    if upset_prob > 40.0:
        stress_points.append(f"⚠️ Upset Probability {upset_prob:.1f}% signals structural instability")
    elif upset_prob > 25.0:
        stress_points.append(f"⚠️ Upset Risk {upset_prob:.1f}% exceeds safe tolerance")
        
    if abs(injury_adj) > 4.0:
         stress_points.append(f"🚑 Injury Adjustment ({injury_adj}) is a dominant variable")
         
    if volatility > 13.0:
        stress_points.append("📉 High Volatility Environment undermines consistency assumptions")

    if not stress_points and abs(delta) < 2.0:
        stress_points.append("✅ No significant structural cracks detected (Market aligned)")

    
    # 3. Question Generation
    questions = []
    
    # Context Trigger Questions
    if injury_adj < -2.0:
        questions.append("Is the market underestimating the cascading impact of the key injury?")
    elif injury_adj > 2.0:
        questions.append("Is the market overreacting to the return/absence, ignoring roster depth?")
        
    if volatility > 15:
        questions.append("With such high volatility, is the safer play simply avoiding the spread?")
    
    # Limit questions based on Game Type
    max_q = 3
    if game_type in ['A_SAFE_FAVORITE', 'E_SAFE_UNDERDOG']: max_q = 1
    
    final_questions = questions[:max_q]
    if not final_questions:
        final_questions.append("Does the Quant projection align with the eye test?")
        
    # --- RENDER MARKDOWN ---
    md = "### 🧠 REGIME INTERPRETATION\n"
    
    # Historical Context (New G9 Features)
    if regime_context:
        tier = regime_context.get('tier')
        label = regime_context.get('label', 'Standard')
        b_rate = regime_context.get('base_rate', 0.0)
        f_rate = regime_context.get('final_rate', 0.0)
        active = regime_context.get('active_regime', 'Standard')
        
        md += f"#### 📚 Historical Context: {label} (Tier {tier})\n"
        md += f"> **Regime**: `{active}`\n"
        md += f"> **Upset Prob**: `{b_rate}%` (Base) → **`{f_rate}%`** (Adjusted)\n"
        
        if active == "Fatigue Trap":
             md += "> *Warning: Favorite is tired (Rest<=1) vs Fresh Underdog. Upset risk elevated.*\n"
        elif active == "Hot Underdog":
             md += "> *Warning: Underdog is in peak form (3+ wins in 4). Momentum danger.*\n"
        elif tier == "1":
             md += "> *Note: This is a 'Trap' zone. Favorites often struggle to cover -5.0 lines locally.*\n"
             
        md += "\n"
    
    md += "**Market Assumption:**\n"
    for a in assumptions:
        md += f"- {a}\n"
    md += "\n"
    
    md += "**Stress Points:**\n"
    for s in stress_points:
        md += f"- {s}\n"
    md += "\n"
    
    md += "**Key Questions:**\n"
    for q in final_questions:
        md += f"- {q}\n"

    return md

def generate_markdown_report(date_str, matches):
    team_map = load_team_map()
    md_content = f"# REGIME ZERO DAILY BRIEFING: {date_str}\n\n"
    
    for m in matches:
        hid = m['home_id']
        aid = m['away_id']
        h_name = team_map.get(hid, f"Team {hid}")
        a_name = team_map.get(aid, f"Team {aid}")
        
        # V2 Metrics
        h_mom = m.get('home_momentum', 0)
        edge = m.get('edge_score', 'N/A')
        risk = m.get('risk_score', 'N/A')
        twin = m.get('twin_alert', 'None') # Renamed from 'alert' to 'twin' for clarity in new block
        
        # Extracting new variables for the new markdown structure
        game_id = m['game_id']
        matchup = f"{h_name} vs {a_name}"
        gm_type = m.get('game_type', 'N/A')
        
        md = m.get('market_data', {})
        
        vol_h = m.get('home_volatility')
        vol_a = m.get('away_volatility')
        pace_h = m.get('home_pace')
        pace_a = m.get('away_pace')

        md['season_data'] = f"VOL: {vol_h} vs {vol_a} | PACE: {pace_h} vs {pace_a}"
        
        # --- MARKDOWN GENERATION ---
        md_content += f"## {matchup}\n"
        md_content += f"**Game ID**: `{game_id}`\n"
        if md.get('headline'):
            md_content += f"> *📰 {md['headline']}*\n"
        md_content += "\n"
        
        # Header Signal
        # raw_delta = md.get('raw_delta', 0.0) # Not used in the provided snippet, but kept for context if needed later
        final_delta = md.get('delta', 0.0)
        signal = md.get('signal', 'RATIONAL')
        
        icon = "✅"
        if signal == "HOME_UNDERVALUED": icon = "🟢 VALUE DETECTED"
        elif signal == "HOME_OVERVALUED": icon = "🔴 CAUTION"
        elif signal == "AWAY_UNDERVALUED": icon = "🟢 VALUE DETECTED" # Rare
        
        md_content += f"### {icon}: {signal} (Delta: {final_delta:+.1f})\n\n"
        
        # --- REPORT V3: NARRATIVE ENGINE ---
        # --- REPORT V4: PROFILE ENGINE ---
        if m.get('profiles'):
             md_content += "### 🧩 Game Profile Analysis (Engine v4)\n"
             md_content += "> *Deterministically generated from RData V4*\n\n"
             
             profiles = m['profiles']
             # Order: FLOW, FATIGUE, MEMORY, LUCK (Market), TEMPO
             order = ['FLOW', 'FATIGUE', 'MEMORY', 'LUCK', 'TEMPO']
             
             md_content += "| Profile | State | Strength | Evidence |\n"
             md_content += "| :--- | :--- | :--- | :--- |\n"
             
             for key in order:
                 p = profiles.get(key)
                 if p:
                     # Icon mapping
                     state = p['state']
                     icon = "⚪"
                     if "STRONG" in state or "DOM" in state or "BUBBLE" in state or "DEAD" in state: icon = "🔴"
                     elif "UP" in state or "ADV" in state or "EDGE" in state: icon = "🟢"
                     elif "COLLAPSE" in state or "DIS" in state or "PREY" in state: icon = "📉"
                     
                     md_content += f"| **{key}** | {icon} `{state}` | {p['strength']} | {p['evidence']} |\n"
             
             md_content += "\n"
        
        # FUSION SUMMARY
        md_content += "### 🎯 Fusion Summary\n"
        md_content += "| Metric | Value | Interpretation |\n| :--- | :---: | :--- |\n"
        md_content += f"| **Game Type** | **{gm_type}** | Context Class |\n"
        md_content += f"| **Edge Score** | **{edge}** | Score > 60 implies Home Advantage |\n"
        md_content += f"| **Risk Score** | {risk} | < 30 Low, > 60 High |\n"
        md_content += f"| **Twin Alert** | {twin} | Structural similarity to upsets |\n\n"
        
        # Market Validation Section
        if md.get('is_active'):
             md_content += "### ⚖️ Market Validation\n"
             md_content += f"> **Line**: {md['market_line']} | **Quant**: {md['expected_margin']} | **Delta**: {final_delta}\n"
             md_content += f"> **Signal**: `{signal}`\n\n"
             
             # DECOMPOSITION BOARD
             deco = md.get('decomposition', {})
             if deco:
                 md_content += "### 📐 Margin Decomposition\n"
                 md_content += "| Component | Value | Notes |\n| :--- | :---: | :--- |\n"
                 md_content += f"| **1. Base Power** | {deco['base_power']:+.1f} | Hybrid (60% Sea / 40% L10) |\n"
                 md_content += f"| **2. Pace Adj** | {deco['pace_impact']:+.1f} | Impact of Speed |\n"
                 md_content += f"| **3. Home Court** | {deco['hca']:+.1f} | Standard HCA |\n"
                 md_content += f"| **4. Rest Adj** | {deco['rest_impact']:+.1f} | Fatigue / Advantage |\n"
                 
                 inj = deco.get('injury_impact', 0.0)
                 raw_inj = deco.get('raw_injury_impact', inj)
                 if abs(raw_inj) > 0.1: # Trigger if Raw Shock is significant
                      md_content += f"| **5. Injury Adj** | {inj:+.1f} | *Shock {raw_inj:+.1f} (Alpha 0.3)* |\n"
                 

                 # 5. Volatility (Explicit from Logic)
                 # Note: In log, penalty shrinks margin towards 0.
                 vol_pen = deco.get('vol_penalty', 0.0)
                  
                 # Calculate Raw Sum (Pre-Vol) to determine direction
                 inj = deco.get('injury_impact', 0.0)
                 raw_sum_est = deco['base_power'] + deco['pace_impact'] + deco['hca'] + deco['rest_impact'] + inj
                  
                 # Apply Volatility in correct direction (Shrink to 0)
                 if raw_sum_est > 0:
                      current_sum = raw_sum_est - vol_pen
                      vol_display = -vol_pen
                 else:
                      current_sum = raw_sum_est + vol_pen
                      vol_display = vol_pen
                  
                 if vol_pen > 0:
                     md_content += f"| **5. Volatility** | {vol_display:+.1f} | Uncertainty Penalty (Risk > 13) |\n"
                  
                 # Clamp Adjustment (Closing the Gap)
                 # Expected = RawSum +/- Vol + ClampAdj
                 clamp_adj = md['expected_margin'] - current_sum
                  
                 # Show Clamp Row if it did work
                 if abs(clamp_adj) > 0.1:
                      md_content += f"| **6. Safety Clamp** | {clamp_adj:+.1f} | *Elasticity Guardrail Triggered* |\n"
                  
                 md_content += f"| **= EXPECTED** | **{md['expected_margin']:+.1f}** | **Quant Projection** |\n"
                 md_content += f"| *Market Line* | *{md['market_line']:+.1f}* | *(Implied Margin)* |\n\n"
             

             # DISTRIBUTION & REALITY CHECK
             probs = md.get('prob_dist', {})
             rc = md.get('reality_check', {})
             
             if probs:
                 md_content += "### 📈 Margin Outcome Distribution\n"
                 md_content += "| Outcome Range | Probability | Meaning |\n| :--- | :---: | :--- |\n"
                 md_content += f"| **Favorite 10+ Win** | {probs.get('blowout',0)}% | Blowout Zone |\n"
                 md_content += f"| **Favorite 1-9 Win** | {probs.get('close',0)}% | Market-Aligned |\n"
                 md_content += f"| **Upset / Close** | {probs.get('upset',0)}% | Danger Zone |\n\n"
             
             # 5. Regime Interpretation (Framework v1.0)
             # 5. Regime Interpretation (Framework v1.0)
             # Extract needed values
             upset_prob = probs.get('upset', 0.0)
             quant_margin = md['expected_margin']
             market_line = md['market_line']
             injury_adj = deco.get('injury_impact', 0.0) if deco else 0.0
             
             # G9 Upset Engine
             regime_context = deco.get('regime_context')
             
             interpretation_md = generate_regime_interpretation(gm_type, upset_prob, quant_margin, market_line, injury_adj, max(vol_h, vol_a), regime_context)
             md_content += f"{interpretation_md}\n\n"
                 
             # CONTEXT TRIGGERS
             triggers = md.get('triggers', [])
             if triggers:
                 md_content += "### ⚠️ Context Triggers\n"
                 for t in triggers:
                     md_content += f"- {t}\n"
                 md_content += "\n"
                     

        
        # md_content += "### 📊 Quant Radar (Repaired Core)\n"  <-- REMOVED as requested
        # Keeping stats for reference in a smaller footer or simplified table if needed,
        # but User said "Replace". Let's keep a small stats box for context.
        
        md_content += "#### 🔍 Key Stats Context\n"
        md_content += f"VOL: {m.get('home_volatility')} vs {m.get('away_volatility')} | PACE: {m.get('home_pace')} vs {m.get('away_pace')}\n\n"
        md_content += "\n"
        
        # Qualitative Section
        md_content += "### 🧬 Qualitative Twin Engine\n"
        if m.get('twin_data'):
            t = m['twin_data']
            sim_pct = t.get('final_score',0)*100
            
            if m.get('twin_alert') == 'ACTIVE':
                story = t.get('twin_story', {})
                md_content += f"> **Twin Detected**: {t.get('date')} {t.get('matchup')}\n>\n"
                md_content += f"> *{story.get('headline')}*\n>\n"
                md_content += f"> **Structural Similarity: {t.get('similarity',0):.1f}%**\n"
                md_content += f"> Reasoning: {story.get('reasoning')}\n"
                
                # md_content += f"> Narrative Sim: {t.get('narrative_score',0)*100:.1f}%\n"
                # md_content += f"> Context Sim: {t.get('context_score',0)*100:.1f}%\n"
                md_content += f"> **Fusion Score: {t.get('similarity',0):.1f}**\n"
            else:
                # Quiet Mode (Similarity < 80%)
                md_content += f"> *Twin Engine: QUIET (Sim {t.get('similarity',0):.1f}% < 80%)*\n"
        else:
             md_content += "> *Twin Engine: QUIET (No matches found)*\n"
            
        md_content += "\n---\n\n"
        
    filename = os.path.join(REPORT_DIR, f"fusion_report_{date_str}.md")
    with open(filename, 'w') as f:
        f.write(md_content)
        
    print(f"MD Report Generated: {filename}")
    return filename

def main():
    parser = argparse.ArgumentParser(description="Regime Zero: Fusion Report Generator")
    parser.add_argument("--date", type=str, required=True, help="Target Date (YYYY-MM-DD)")
    args = parser.parse_args()
    
    print(f"Starting Fusion Pipeline for {args.date}...")
    
    # --- PHASE 1: QUANT ENGINE (Direct JSON) ---
    print(f">>> Phase 1: Quant Engine Scan (Direct JSON)")
    
    # Load Schedule (JSON)
    schedule_path = "/Users/js/g9/nba_data/schedule_2025.json"
    with open(schedule_path, 'r') as f:
        schedule = json.load(f)
        
    matches = []
    for s in schedule:
        # Normalize Date
        d_raw = s['date'].split(' ')[0]
        try:
             parts = d_raw.split('/')
             if len(parts) == 3:
                 iso = f"{parts[2]}-{parts[0]}-{parts[1]}"
             else:
                 iso = d_raw
        except:
             iso = d_raw
             
        if iso == args.date:
             matches.append(s)
             
    print(f"Found {len(matches)} games.")
    
    if not matches:
        print("No games found.")
        return

    # Run Fusion Engine (RData V4)
    import sys
    sys.path.append("/Users/js/g9/nba_data/quant_engine_v1")
    from rdata_engine import RDataEngine
    print(f"DEBUG IMPORTS: RDataEngine loaded from {RDataEngine.__module__} file: {sys.modules['rdata_engine'].__file__}")
    engine = RDataEngine()
    
    # Analyze each match
    results = []
    for m in matches:
        game_id = m['game_id']
        hid = m['home_id']
        aid = m['away_id']
        odds = m.get('odds')
        
        # Call Quant Engine with game_id
        analysis = engine.analyze_matchup(hid, aid, args.date, odds, game_id=game_id)
        
        # Run Profile Engine
        from quant_engine_v1.profile_engine import ProfileEngine
        prof_engine = ProfileEngine()
        raw_row = analysis.get('raw_row', {})
        p_data = prof_engine.build_profiles(raw_row)
        
        # Merge analysis
        m.update({
            "edge_score": analysis['edge_score'],
            "risk_score": analysis['risk_score'],
            "twin_alert": analysis['twin_alert'],
            "market_data": analysis['market_analysis'],
            
            "home_net_rating": analysis['home_stats']['net_rating'],
            "away_net_rating": analysis['away_stats']['net_rating'],
            
            "home_pace": analysis['home_stats']['pace'],
            "away_pace": analysis['away_stats']['pace'],
            
            "home_volatility": analysis['home_stats']['volatility'],
            "away_volatility": analysis['away_stats']['volatility'],
            "home_rest": analysis['home_stats']['rest_days'],
            "away_rest": analysis['away_stats']['rest_days'],
            "game_type": analysis['game_type'],
            "profiles": p_data
        })
        results.append(m)
        
    matches = results
    
    matches = results
    
    # --- PHASE 2: VECTOR REGIME ENGINE (Phase 27) ---
    print(f">>> Phase 2: Vector Regime Scan (Euclidean Search)")
    try:
        vec_engine = vector_engine.VectorEngine()
    except Exception as e:
        print(f"⚠️ Vector Engine Init Failed: {e}")
        vec_engine = None
    
    for match in matches:
        print(f"Scanning Vector Space for {match['game_id']}...")
        
        # Extract Vector from Profile
        # ProfileEngine built 'score' into each profile dict
        try:
            p = match['profiles']
            # [Flow, Fatigue, Memory, Luck, Tempo]
            target_vector = [
                p['FLOW'].get('score', 0),
                p['FATIGUE'].get('score', 0),
                p['MEMORY'].get('score', 0),
                p['LUCK'].get('score', 0),
                p['TEMPO'].get('score', 0)
            ]
            
            if vec_engine:
                print(f"DEBUG: Search Target: {target_vector}")
                twins = vec_engine.find_twins(target_vector, n=1)
                print(f"DEBUG: Twins Found: {len(twins)}")
                
                if twins:
                    best_twin = twins[0]
                    # Structure: {'game_id', 'matchup', 'distance', 'similarity'}
                    match['twin_data'] = best_twin
                    match['twin_data']['twin_story'] = {
                        "headline": f"Structural Twin: {best_twin['matchup']}",
                        "reasoning": f"Dist {best_twin['distance']} (Flow/Fatigue/Mem/Luck match)",
                        "date": best_twin['date'],
                        "matchup": best_twin['matchup']
                    }
                    
                    # Twin Alert Logic (Vector Sim %)
                    # Threshold: 90%? 85%? Heuristic.
                    sim_pct = best_twin.get('similarity', 0)
                    if sim_pct >= 80.0:
                        match['twin_alert'] = "ACTIVE"
                    else:
                        match['twin_alert'] = "QUIET"
            else:
                 match['twin_alert'] = "QUIET" # Engine failed
                 
        except Exception as e:
            print(f"⚠️ Vector Search Failed to {match['game_id']}: {e}")
            match['twin_alert'] = "QUIET"
            
    # --- PHASE 3: REPORT GENERATION ---
    print(f">>> Phase 3: Report Generation")
    rpt_path = generate_markdown_report(args.date, matches)
    print(f"MD Report Generated: {rpt_path}")
    print("Done.")

if __name__ == "__main__":
    main()
