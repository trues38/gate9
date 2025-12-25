import duckdb
import chromadb
import json
import os
import re
import numpy as np
import argparse
from datetime import datetime, timedelta

# Configuration
DUCKDB_PATH = "nba_analytics.duckdb"
PERSONA_DIR = "nba_data/persona_vectors"
CHROMA_DB_DIR = "nba_data/chroma_db"
COLLECTION_NAME = "nba_narratives"

def normalize_name(name):
    # "LeBron James" -> "lebronjames"
    return re.sub(r'[^a-zA-Z0-9]', '', name.lower())

def get_quant_layer(con, team_id, date_str):
    """
    Layer 1: QUANT CORE (DuckDB)
    Fetches momentum and regime label from fact_regimes.
    """
    try:
        # Get latest regime BEFORE or ON this date
        query = f"""
            SELECT momentum_score, regime_label, record, streak
            FROM fact_regimes 
            WHERE team_id={team_id} AND date <= '{date_str}'
            ORDER BY date DESC LIMIT 1
        """
        regime = con.sql(query).fetchone()
        
        if not regime:
            return None
            
        return {
            "momentum": float(regime[0]),
            "label": regime[1],
            "record": regime[2],
            "streak": regime[3]
        }
    except Exception as e:
        print(f"⚠️ Quant Layer Error: {e}")
        return None

def get_story_layer(con, team_id, date_str):
    """
    Layer 2: STORY ENGINE (Personas)
    Aggregates sentiment from Key Players' recent narrative history.
    """
    # 1. Get Roster (Top 3 Players by some heuristic, or just all starters?)
    # For now, we fetch ALL players on the roster and filter for those with Personas.
    roster_query = f"SELECT name FROM fact_rosters WHERE team_id={team_id}"
    try:
        players = [row[0] for row in con.sql(roster_query).fetchall()]
    except:
        players = []
        
    if not players:
        return {"description": "No Roster Data", "score": 0.0, "details": []}

    total_score = 0
    count = 0
    details = []
    player_details_objs = [] # Init structured list
    
    date_dt = datetime.strptime(date_str, "%Y-%m-%d")
    
    # Weighting: Star players might matter more, but we treat equal for V1.
    for p in players:
        fname = normalize_name(p) + ".json"
        fpath = os.path.join(PERSONA_DIR, fname)
        
        if os.path.exists(fpath):
            with open(fpath, 'r') as f:
                data = json.load(f)
                
            # Analyze History relative to date
            history = data.get('history', [])
            
            # Re-parse dates to be sure
            valid_recent_items = []
            for h in history:
                try:
                    # Handle "Oct 30, 2025" vs "2025-10-30" formats
                    if "," in h['date']:
                        h_dt = datetime.strptime(h['date'], "%b %d, %Y")
                    else:
                        h_dt = datetime.strptime(h['date'], "%Y-%m-%d")
                        
                    if h_dt < date_dt:
                        valid_recent_items.append((h_dt, h))
                except:
                    pass
            
            # Sort by date desc
            valid_recent_items.sort(key=lambda x: x[0], reverse=True)
            last_3 = [x[1] for x in valid_recent_items[:3]]
            
            if not last_3:
                continue
                
            # Calculate Sentiment
            # Euphoric/Resilient/Dominant = +1
            # Frustrated/Tension/Sluggish = -1
            # Neutral = 0
            p_score = 0
            tones = [h['tone'] for h in last_3]
            for t in tones:
                t_lower = t.lower()
                if any(x in t_lower for x in ['euphoric', 'resilient', 'dominant', 'confident', 'electrifying']):
                    p_score += 1
                elif any(x in t_lower for x in ['frustrated', 'tension', 'sluggish', 'disjointed', 'struggling']):
                    p_score -= 1
            
            # Normalize to -1.0 to 1.0 range
            if last_3:
                p_score /= len(last_3)
                
            total_score += p_score
            count += 1
            details.append(f"{p}: {p_score:.1f} ({', '.join(tones)})")
            player_details_objs.append({'name': p, 'score': p_score, 'vibes': tones})

    # Aggregate Team Narrative Score
    team_narrative_score = (total_score / count) if count > 0 else 0.0
    
    # Vibe Check
    main_vibe = "중립 (Neutral)"
    if team_narrative_score > 0.5: main_vibe = "열광적 (Electrifying)"
    elif team_narrative_score > 0.2: main_vibe = "긍정적 (Optimistic)"
    elif team_narrative_score < -0.5: main_vibe = "붕괴 직전 (Toxic)"
    elif team_narrative_score < -0.2: main_vibe = "긴장감 (Tense)"
    
    # ---------------------------------------------------------
    # TUNING 1: Story Weight Adjustment (-15%)
    # ---------------------------------------------------------
    final_score = team_narrative_score * 0.85
    
    # Collect top vibes from player details for raw_vibes
    top_vibes = []
    for pd in player_details_objs:
        top_vibes.extend(pd['vibes'])
    
    # ---------------------------------------------------------
    # TUNING 3: Psyche Vector Diversity (Unlock Negative Emotions)
    # ---------------------------------------------------------
    # Logic: Inject specific tags if conditions are met
    if final_score < 0.6 and "Agitated" not in top_vibes:
        top_vibes.append("Agitated")
    
    # We don't have quant momentum here easily, so we handle "Drained" in Conflict Layer or pass context?
    # Actually, we can move the "Drained" logic to Conflict Layer or just check score.
    # User said: if quant_momentum < 0 -> Drained. We only have narrative here.
    # Let's add "Drained" if score is very low (< 0.4) as a proxy, OR handle it in get_conflict_layer where we have both.
    
    return {
        "vibe": main_vibe, 
        "score": final_score, 
        "details": [f"{p['name']}: {p['score']:.1f} ({', '.join(p['vibes'])})" for p in player_details_objs],
        "raw_vibes": top_vibes # Pass raw vibes for conflict layer usage
    }

def get_conflict_layer(quant, story):
    """
    Layer 3: CONFLICT ENGINE
    Fusion Logic.
    TUNING 2: Conflict Engine Sensitivity (+30%)
    """
    if not quant:
        return {"result": "데이터 부족", "conflict": "N/A", "risk": "N/A"}
        
    q_score = quant.get('momentum', 0.0) # Scale roughly -10 to 10? No, usually -3 to 5.
    s_score = story.get('score', 0.5)    # Scale 0.0 to 1.0
    
    # Normalize Quant to 0-1 for comparison (Approximate)
    # Assume Quant Range -5 to +5 maps to 0.0 to 1.0 (0=0.5)
    # Sigmoid or Linear? Let's use simple linear clamping for prototype.
    # -5 -> 0.0, 0 -> 0.5, +5 -> 1.0
    q_norm = (q_score + 5) / 10
    q_norm = max(0.0, min(1.0, q_norm))
    
    diff = abs(q_norm - s_score)
    
    # Default State
    result = "일관성 (Coherent)"
    conflict = "낮음"
    risk = "안정적 (Stable)"
    
    # ---------------------------------------------------------
    # TUNING 2: Sensitivity Update (Threshold 0.15)
    # ---------------------------------------------------------
    if diff > 0.15:
        result = "Discord (Conflict)"
        conflict = "높음 (불협화음)" # Keep original conflict description for consistency
        risk = "High (Elevated)"
        
        # Determine Direction
        if q_norm > s_score:
            result += " - Reality > Hype" # Quant high, Story low
        else:
            result += " - Hype > Reality" # Story high, Quant low (Trap Game)

    # 1. The "Fake Good" (Quant High, Story Bad)
    elif q_score > 2.0 and s_score < -0.3:
        conflict = "높음 (불협화음)"
        result = "불안한 독주 (Fragile Juggernaut)"
        risk = "내부 갈등으로 인한 붕괴 가능성 높음"
        
    # 2. The "Sleeping Giant" (Quant Low/Bad, Story Good)
    elif q_score < -1.0 and s_score > 0.3:
        conflict = "높음 (불협화음)"
        result = "잠자는 거인 (Sleeping Giant)"
        risk = "반등 가능성 높음 (상승 조짐)"
        
    # 3. The "True Contender" (Both Good)
    elif q_score > 1.0 and s_score > 0.2:
        conflict = "낮음 (조화)"
        result = "진격의 거인 (True Juggernaut)"
        risk = "낮음. 완전한 조화."
        
    # 4. The "Trainwreck" (Both Bad)
    elif q_score < -1.0 and s_score < -0.2:
        conflict = "낮음 (조화)"
        result = "총체적 난국 (Total Collapse)"
        risk = "높음. 끝없는 추락."
        
    return {
        "quant_score": q_score,
        "story_score": s_score,
        "conflict": conflict,
        "result": result,
        "risk": risk
    }

def run_fusion_engine(game_id, date_str):
    print(f"\n🔮 Spinning up Fusion Engine for Game {game_id} on {date_str}...\n")
    
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    
    # 1. Get Game Metadata from DB
    try:
        game = con.sql(f"SELECT home_team_id, home_team_score, away_team_id, away_team_score FROM fact_game_results WHERE game_id='{game_id}' OR date='{date_str}' LIMIT 1").fetchone()
        if not game:
            # Try searching by ESPN ID from Chroma?
            # For now, let's assume we pass a valid date and we iterate ALL games for that date.
            pass
    except:
        pass
        
    # Let's pivot: The script accepts a DATE and runs for ALL games on that date.
    query = f"""
        SELECT 
            g.game_id, 
            ht.team_id as home_id, 
            g.home_team, 
            awt.team_id as away_id, 
            g.away_team 
        FROM fact_game_results g
        LEFT JOIN dim_teams ht ON g.home_team = ht.name
        LEFT JOIN dim_teams awt ON g.away_team = awt.name
        WHERE g.game_date = '{date_str}'
    """
    try:
        games = con.sql(query).fetchall()
    except Exception as e:
        print(f"Error fetching games: {e}")
        con.close()
        return

    print(f"총 {len(games)} 경기 발견.\n")

    for g in games:
        gid, hid, h_abbr, aid, a_abbr = g
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"🏟️  매치업: {h_abbr} (홈) vs {a_abbr} (원정)")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # Analyze HOME Team
        q_home = get_quant_layer(con, hid, date_str)
        s_home = get_story_layer(con, hid, date_str)
        
        if q_home and s_home:
            f_home = get_conflict_layer(q_home, s_home)
            print(f"\n🏠  [홈팀] {h_abbr} 분석 리포트")
            print(f"    ----------------------------------------")
            print(f"    📊 퀀트 (Quant)    | {q_home['momentum']:.1f} ({q_home['label']}) | L10: {q_home['record']} | {q_home['streak']}")
            print(f"    🧠 스토리 (Story)  | {s_home['vibe']} (점수: {s_home['score']:.2f})")
            print(f"       ↳ 주요 선수: {', '.join(s_home['details'])}")
            print(f"    ⚡ 퓨전 진단       | {f_home['result']}")
            print(f"    ⚠️ 리스크          | {f_home['risk']}")
        else:
            print(f"\n🏠  [홈팀] {h_abbr}: ⚠️ 데이터 부족")
            
        # Analyze AWAY Team
        q_away = get_quant_layer(con, aid, date_str)
        s_away = get_story_layer(con, aid, date_str)
        
        if q_away and s_away:
            f_away = get_conflict_layer(q_away, s_away)
            print(f"\n✈️  [원정팀] {a_abbr} 분석 리포트")
            print(f"    ----------------------------------------")
            print(f"    📊 퀀트 (Quant)    | {q_away['momentum']:.1f} ({q_away['label']}) | L10: {q_away['record']} | {q_away['streak']}")
            print(f"    🧠 스토리 (Story)  | {s_away['vibe']} (점수: {s_away['score']:.2f})")
            print(f"       ↳ 주요 선수: {', '.join(s_away['details'])}")
            print(f"    ⚡ 퓨전 진단       | {f_away['result']}")
            print(f"    ⚠️ 리스크          | {f_away['risk']}")
        else:
             print(f"\n✈️  [원정팀] {a_abbr}: ⚠️ 데이터 부족")
             
        print("\n")
        
    con.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, default="2025-12-09", help="YYYY-MM-DD")
    args = parser.parse_args()
    
    run_fusion_engine(None, args.date)
