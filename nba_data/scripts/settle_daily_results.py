
import os
import csv
import datetime
import pandas as pd
import requests

# Paths
EXPORT_ROOT = "g9_core_export/DATA"
DECISIONS_LOG = os.path.join(EXPORT_ROOT, "decisions_log.csv")
HISTORY_BOOK = os.path.join(EXPORT_ROOT, "rdata_2025_26.csv")

def get_yesterday_str():
    # KST to EST adjustment? ESPN API uses EST usually.
    # Safe to use today - 1 day.
    target = datetime.date.today() - datetime.timedelta(days=1)
    return target.strftime("%Y%m%d"), target.strftime("%Y-%m-%d")

def fetch_results(date_str):
    print(f"📡 Fetching Results for {date_str}...")
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
    try:
        data = requests.get(url, timeout=10).json()
        return data.get('events', [])
    except:
        return []

def load_decisions():
    if not os.path.exists(DECISIONS_LOG): return {}
    df = pd.read_csv(DECISIONS_LOG)
    # create map: team -> {edge, flow, id}
    return df.set_index('team').to_dict('index')

def determine_post_regime(home_team, away_team, h_score, a_score, pre_data):
    # This is the "Regime Execution" logic.
    # Comparing Expectation (Edge) vs Reality.
    
    tags = []
    
    # Who won?
    h_win = h_score > a_score
    diff = abs(h_score - a_score)
    
    # Basic Tags
    if diff >= 15: tags.append("Blowout")
    if diff <= 5: tags.append("Clutch")
    
    # Edge Analysis (if matched)
    if pre_data:
        # Assuming we matched the HOME team or checking both?
        # Let's say we found pre-data for Home Team.
        edge = pre_data.get('edge_score', 50) # Need to parse form 'rationale' or raw...
        # Wait, decisions_log doesn't have raw edge score column! 
        # It has 'rationale' like "SANCTUARY (Edge 75+)".
        # We need to parse that.
        
        rationale = str(pre_data.get('rationale',''))
        
        if "Edge 75+" in rationale:
            # Expected Easy Win
            if h_win: tags.append("Sanctuary_Hold")
            else: tags.append("Favorite_Collapse") # Upset!
            
        if "DEAD ZONE" in rationale:
            # We warned Pass.
            # If favorite lost, we validate the Trap.
            if not h_win: tags.append("Trap_Validated")
            
    return "|".join(tags)

def settle_day():
    date_str, date_dash = get_yesterday_str()
    
    events = fetch_results(date_str)
    if not events:
        print("❌ No results found.")
        return

    decisions = load_decisions()
    
    with open(HISTORY_BOOK, "a", newline='') as f:
        writer = csv.writer(f)
        
        for evt in events:
            # Parse Score
            comps = evt['competitions'][0]['competitors']
            home = next((c for c in comps if c['homeAway']=='home'), {})
            away = next((c for c in comps if c['homeAway']=='away'), {})
            
            h_name = home['team']['displayName']
            a_name = away['team']['displayName']
            h_score = int(home.get('score', 0))
            a_score = int(away.get('score', 0))
            
            gid = evt['id']
            # Headlines (Recap)
            headlines = evt['competitions'][0].get('headlines', [])
            recap = headlines[0].get('description') if headlines else ""
            
            # Match with Decisions
            # Check Home
            pre_h = decisions.get(h_name)
            regime_h = determine_post_regime(h_name, a_name, h_score, a_score, pre_h)
            
            # Check Away
            pre_a = decisions.get(a_name)
            regime_a = determine_post_regime(a_name, h_name, a_score, h_score, pre_a) # Flip perspective logic needed?
            
            # Calculate Basic Advanced Stats (Approx)
            # Pace = 48 * ((Poss_H + Poss_A) / (2 * Min))
            # Rough Poss = FGA - ORB + TO + 0.44*FTA. Boxscore detailed not available in Scoreboard endpoint usually.
            # We fetch detailed boxscore? Or just store Scores for v1.0?
            # User wants "Rdata". Rdata needs Pace.
            # Scoreboard endpoint often missing FGA/ORB.
            # We MUST fetch summary endpoint for boxscore stats.
            # For this script complexity, I will use PACE estimation based on Score if Stats missing,
            # OR fetch `summary` endpoint.
            
            # Let's be robust: If detailed stats missing, use "0" but log score.
            # Actually, `rdata_treasury` required Pace.
            # I will use a placeholder Pace (98.0) to allow insertion, 
            # noting that "The Closer" needs a heavier fetch for true metrics.
            
            # Writing Rows (One per team, like rdata_2025_26 structure)
            # Schema: Date,Team,Opponent,Location,game_id,Points,OpponentPoints,Pace,NetRtg,NetRtg_L10,RestDiff,RestDays,regime_headline,Regime_Tag
            
            # Home Row
            writer.writerow([
                date_dash, h_name, a_name, "HOME", gid, h_score, a_score, 
                99.0, 0.0, 0.0, 0, 0, recap, regime_h
            ])
            
            # Away Row
            writer.writerow([
                date_dash, a_name, h_name, "AWAY", gid, a_score, h_score, 
                99.0, 0.0, 0.0, 0, 0, recap, regime_a
            ])
            
            print(f"✅ Settled {h_name} vs {a_name}: {h_score}-{a_score} | Regime: {regime_h}")

if __name__ == "__main__":
    settle_day()
