
import pandas as pd
import datetime
import os

OUTPUT_REPORT = "reports/daily_g9_report_sample.md"

# MOCK: Live Data Input (In production, replace with API fetch)
TODAY_GAMES = [
    {
        "team": "Boston Celtics", "opp": "Miami Heat", 
        "edge_score": 82.0, "flow_state": "STABLE", "regime_type": "Blowout_Win", 
        "spread": -7.5, "total": 215.0, "headline": "Celtics seeking revenge after playoff exit."
    },
    {
        "team": "Milwaukee Bucks", "opp": "Indiana Pacers", 
        "edge_score": 62.0, "flow_state": "STRONG_UP", "regime_type": "Favorite_Collapse", 
        "spread": -5.5, "total": 242.0, "headline": "Bucks dealing with internal chemistry issues despite winning streak."
    },
    {
        "team": "Denver Nuggets", "opp": "Minnesota Timberwolves", 
        "edge_score": 55.0, "flow_state": "STRONG_UP", "regime_type": "Star_Takeover", 
        "spread": -2.5, "total": 228.0, "headline": "Jokic vs Gobert: Clash of Titans."
    },
    {
        "team": "Phoenix Suns", "opp": "Dallas Mavericks", 
        "edge_score": 72.0, "flow_state": "STRONG_UP", "regime_type": "Favorite_Hold", 
        "spread": -6.0, "total": 230.0, "headline": "Suns offense exploitable on back-to-back."
    },
    {
        "team": "Golden State Warriors", "opp": "Memphis Grizzlies", 
        "edge_score": 45.0, "flow_state": "STABLE", "regime_type": "Underdog_Resilience", 
        "spread": 4.5, "total": 222.0, "headline": "Grizzlies gritty defense proving tough."
    }
]

def generate_report():
    print("🏭 G9 Factory: Spinning up Daily Report...")
    
    report_lines = []
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    report_lines.append(f"# 🦅 G9 Morning Report ({today_str})\n\n")
    report_lines.append("> **\"Market is Efficient. Shape is Not.\"**\n\n")
    
    # Bucket Lists
    sanctuary = []
    traps = []
    snipers = [] # Spread Fades
    controllers = [] # Total Fades/Picks
    
    for game in TODAY_GAMES:
        team = game['team']
        opp = game['opp']
        edge = game['edge_score']
        flow = game['flow_state']
        regime = game['regime_type']
        spread = game['spread']
        
        # --- LOGIC CORE ---
        
        # 1. Sanctuary (Edge 70+ & Extreme Conf)
        # Assuming Edge 80+ is Extreme. 70-80 is High.
        if edge >= 75:
            sanctuary.append(game)
            
        # 2. Trap Zone (Edge 60-65)
        # Or Edge 65-80 + Strong Up (Collapse Risk)
        if (60 <= edge <= 65):
            traps.append(game)
        
        # 3. Icarus (Spread Fade): Edge 55-70 + Strong Up
        if (55 <= edge <= 70) and (flow == 'STRONG_UP'):
            snipers.append(game)
            
        # 4. Total Controller (Under): Edge 50-60 + Strong Up
        if (50 <= edge <= 60) and (flow == 'STRONG_UP'):
            controllers.append(game)
            
        # 5. Regime Specifics
        if regime == "Favorite_Collapse" and edge >= 60:
            # Override to Sniper (Fade Fav)
            if game not in snipers: snipers.append(game)
            
        if regime == "Underdog_Resilience" and spread > 0:
            # Bet Dog Spread
            # Add to Sniper list as "Dog Cover"
            pass # Simplified for report structure
            
    # --- RENDER SECTIONS ---
    
    # SECTION 1: THE SANCTUARY
    report_lines.append("## 🛡️ The Sanctuary (Safe Picks)\n")
    report_lines.append("Conditions: Edge 75+ (High Confidence). **Action: Moneyline (Win)**.\n\n")
    if sanctuary:
        for g in sanctuary:
            report_lines.append(f"### ✅ {g['team']} (vs {g['opp']})\n")
            report_lines.append(f"- **Edge:** {g['edge_score']} | **Flow:** {g['flow_state']}\n")
            report_lines.append(f"- **Narrative:** {g['headline']}\n")
            report_lines.append(f"- **Oracle:** \"The numbers are aligned. Market efficiency demands this win.\"\n\n")
    else:
        report_lines.append("*No Sanctuary picks today. Safety first.*\n\n")
        
    # SECTION 2: THE TRAP ZONE
    report_lines.append("## 🕳️ The Trap Zone (Danger)\n")
    report_lines.append("Conditions: Edge 60-65 (Fragile Favs) or Collapse Signals. **Action: PASS**.\n\n")
    if traps:
         for g in traps:
            report_lines.append(f"### ⚠️ {g['team']} (Spread {g['spread']})\n")
            report_lines.append(f"- **Edge:** {g['edge_score']} | **Regime:** {g['regime_type']}\n")
            report_lines.append(f"- **Warning:** This is the 'Killing Zone'. Collapse rate is high.\n\n")
    else:
        report_lines.append("*No obvious traps detected.*\n\n")
        
    # SECTION 3: SPREAD SNIPER (Alpha)
    report_lines.append("## 💣 Spread Sniper (Fades)\n")
    report_lines.append("Conditions: Overheated Flow (Strong Up) or Resilience Regime. **Action: Bet Opposite Spread**.\n\n")
    if snipers:
        for g in snipers:
            bet_target = g['opp'] # Fade Team
            report_lines.append(f"### 🎯 Bet {bet_target} ({g['spread'] * -1 if g['spread']<0 else g['spread']} Spread)\n")
            report_lines.append(f"- **Target:** Fading {g['team']} ({g['flow_state']})\n")
            report_lines.append(f"- **Reason:** Icarus Paradox. Market believes the hype. We bet the crash.\n\n")
    else:
        report_lines.append("*No sniper opportunities.*\n\n")
        
    # SECTION 4: TOTAL CONTROLLER
    report_lines.append("## 📉 Total Controller\n")
    report_lines.append("Conditions: Fake Firepower. **Action: UNDER**.\n\n")
    if controllers:
        for g in controllers:
             report_lines.append(f"### 📉 {g['team']} vs {g['opp']} (Under {g['total']})\n")
             report_lines.append(f"- **Reason:** Both teams Strong Up + Tossup Edge = Defensive Grind likely.\n\n")
    else:
        report_lines.append("*No total plays.*\n\n")
        
    report_lines.append("---\n")
    report_lines.append("**Disclaimer:** This report is generated by G9 Engine v1.0. Use responsibly.\n")
    
    with open(OUTPUT_REPORT, 'w') as f:
        f.writelines(report_lines)
    
    print(f"✅ Daily Product Generated: {OUTPUT_REPORT}")

if __name__ == "__main__":
    generate_report()
