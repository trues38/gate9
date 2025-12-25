
import json
import datetime
import os
import fetch_live

# ---------------- CONFIG ----------------
REPORT_DIR = "../REPORTS"
TARGET_DATE = "2025-12-14"

# ----------------- REUSED PIPELINE LOGIC -----------------
# (Ideally we import these from g9_pipeline, but for stability in script execution, 
#  I will replicate the classes here or import if modular. 
#  Since g9_pipeline.py is a script, importing might trigger run_pipeline().
#  So I will redefine the Logic Classes here to ensure isolation.)

class RegimeTagger:
    @staticmethod
    def tag_game(game_data):
        text = game_data.get('preview_text', '').lower()
        candidates = []
        if "out" in text and "fatigued" in text: candidates.append("Favorite_Hold") 
        if "rolling" in text and "fatigued" in text: candidates.append("Grind_Game")
        if "firepower" in text and "struggling" in text: candidates.append("Blowout_Win")
        if "gritty" in text: candidates.append("Underdog_Resilience")
        if "revenge" in text: candidates.append("Blowout_Win")
        if "streak" in text: candidates.append("Favorite_Collapse") # Adding logic from Spec? No, keep simple.
        
        # Spec 1-2 examples:
        # "Underdog_Resilience" if Dog is Gritty
        # "Grind_Game"
        
        return candidates

class DecisionEngine:
    @staticmethod
    def evaluate(game, regimes):
        edge = game['rdata']['edge_score']
        flow = game['rdata']['flow_state']
        spread_line = game['odds']['spread']['line'] # e.g. -5.5
        fav = game['odds']['spread']['fav']
        
        # 1. DEAD ZONE
        if (60 <= edge <= 70) and (flow == "STRONG_UP"):
            return {"action": "PASS", "reason": "DEAD ZONE (Edge 60-70 + Strong Up)", "confidence": 0.0}
            
        # 2. SANCTUARY
        if edge >= 75:
             return {"action": "BET", "market": "MONEYLINE", "side": fav, "reason": "SANCTUARY (Edge 75+)", "confidence": 0.95}

        # 3. REGIME LOGIC
        for r in regimes:
            if r == "Underdog_Resilience":
                return {"action": "BET", "market": "SPREAD", "side": "UNDERDOG (+)", "reason": f"Regime: {r}", "confidence": 0.78}
            if r == "Blowout_Win":
                return {"action": "BET", "market": "SPREAD", "side": f"{fav} (-)", "reason": f"Regime: {r}", "confidence": 0.82}
            if r == "Grind_Game":
                return {"action": "BET", "market": "TOTAL", "side": "UNDER", "reason": f"Regime: {r}", "confidence": 0.75}
        
        return {"action": "PASS", "reason": "No strong signal", "confidence": 0.0}

class Reporter:
    @staticmethod
    def generate(results, date_str):
        lines = []
        lines.append(f"# 🦅 G9 Time Machine Report ({date_str})\n")
        lines.append("> **Replay Analysis:** Applying Spec v1.0 to Historical Data.\n\n")
        
        picks = [r for r in results if r['decision']['action'] == "BET"]
        traps = [r for r in results if "DEAD ZONE" in r['decision']['reason']]
        
        lines.append("## 🎯 G9 Picks (Replay)\n")
        if picks:
            for p in picks:
                d = p['decision']
                lines.append(f"### {p['game_id']}: {d['market']} {d['side']}\n")
                lines.append(f"- **Regime:** {p['regimes']}\n")
                lines.append(f"- **Rationale:** {d['reason']}\n\n")
        else:
            lines.append("No actionable signals.\n\n")
            
        lines.append("## 🚫 PASS / TRAP ALERT\n")
        if traps:
            for t in traps:
                d = t['decision']
                lines.append(f"- **{t['game_id']}**: {d['reason']}\n")
        else:
            lines.append("No traps detected.\n")
            
        return "\n".join(lines)

# ----------------- REPLAY ORCHESTRATOR -----------------
def run_replay():
    print(f"⏳ Spinning up Time Machine for {TARGET_DATE}...")
    
    # 1. Ingest (Historical)
    games = fetch_live.fetch_live_data(TARGET_DATE)
    
    if not games:
        print("❌ No games found for target date.")
        return

    pipeline_results = []
    
    for game in games:
        # 2. Tag
        regimes = RegimeTagger.tag_game(game)
        
        # 3. Decide
        decision = DecisionEngine.evaluate(game, regimes)
        
        pipeline_results.append({
            "game_id": game['game_id'],
            "regimes": regimes,
            "decision": decision
        })
        
    # 4. Report
    report_content = Reporter.generate(pipeline_results, TARGET_DATE)
    
    output_path = os.path.join(REPORT_DIR, "g9_replay_dec14.md")
    if not os.path.exists(REPORT_DIR):
         os.makedirs(REPORT_DIR)
         
    with open(output_path, "w") as f:
        f.write(report_content)
        
    print(f"✅ Replay Complete. Output: {output_path}")
    print("\n--- REPLAY RESULT ---\n")
    print(report_content)

if __name__ == "__main__":
    run_replay()
