import duckdb
import pandas as pd
import os
from openai import OpenAI
from dotenv import load_dotenv

# CONFIG
DB_PATH = "nba_sql.duckdb"
ENV_PATH = "g9_core_export/.env"

# SEARCH DATA (Manual Injection from Web Search)
GAME_INFO = {
    "date": "2025-12-16",
    "home": "New York Knicks", # Neutral but let's treat Knicks as Fav? Search said Knicks -2.5.
    "away": "San Antonio Spurs",
    "spread": 2.5, # Knicks -2.5 (Wait, usually home is negative. If Knicks favored, spread is 2.5 from NYK persp?)
    # Pipeline Standard: Spread is absolute. Fav is Explicit.
    "fav_team": "New York Knicks", 
    "total": 228.5,
    "preview": """
    The 2025 NBA Cup Final features the New York Knicks vs San Antonio Spurs in Las Vegas.
    Knicks are slight favorites (-2.5). Analysis suggests a potential playoff preview.
    Knicks have won 9 of last 10, led by Jalen Brunson (40 pts in semi).
    Spurs upset OKC (ending 16-game win streak) and Lakers. Victor Wembanyama returned from calf strain in semis and was crucial.
    Both teams 18-7 record. High stakes ($500k/player).
    Knicks offense elite recent, Spurs defense resilient.
    """
}

def get_latest_stats(team_name):
    con = duckdb.connect(DB_PATH, read_only=True)
    # Use LIKE for safety (Case Insensitive if possible, but standard SQL usually case sensitive for string literals)
    # DuckDB ILIKE is case insensitive.
    # Pattern: '%Knicks%' for NYK.
    if "Knicks" in team_name: pattern = "%Knicks%"
    elif "Spurs" in team_name: pattern = "%Spurs%"
    else: pattern = team_name
    
    query = f"""
        SELECT * FROM rdata_treasury 
        WHERE Team ILIKE '{pattern}' 
        ORDER BY Date DESC 
        LIMIT 1
    """
    df = con.execute(query).fetchdf()
    if df.empty:
        # Debug: check what teams exist
        print(f"Debug: No stats for {team_name}. Checking available teams...")
        teams = con.execute("SELECT DISTINCT Team FROM rdata_treasury LIMIT 10").fetchdf()
        print(teams)
        return None
    return df.iloc[0]

def analyze_game():
    # Load ENV
    load_dotenv(ENV_PATH)
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY")
    )
    
    # Get Stats
    nyk_stats = get_latest_stats("New York Knicks")
    sas_stats = get_latest_stats("San Antonio Spurs")
    
    if nyk_stats is None or sas_stats is None:
        print("Error: Could not find stats in DB.")
        return

    # Construct Prompt
    # Using G9 Standard Logic
    system_prompt = """You are G9, an elite NBA Structural Analyst.
    Your job is to predict the 'Pre-Game Regime' and the likely 'Game Script'.
    Do NOT predict the winner directly. Predict the TEXTURE of the game.
    
    Inputs:
    1. Quantitative Profile (NetRtg, Pace, Volatility, Rest).
    2. Market State (Odds, Total).
    3. Narrative Context (Preview, Injuries, Stakes).
    
    Output Format:
    ## 🏷️ Predicted Regime: [Choose from: SHOOTOUT, GRIND, BLOWOUT, CLUTCH]
    ## 📜 Game Script Narrative:
    (Description of how the flow evolves. Mention specific matchups like Brunson vs Wemby.)
    ## 🔑 Key Factor:
    (The single variable that decides the outcome.)
    ## ⚠️ Watch for:
    (A specific signal that indicates your thesis is wrong.)
    """
    
    user_prompt = f"""
    MATCHUP: {GAME_INFO['away']} (Underdog) vs {GAME_INFO['home']} (Favorite)
    CONTEXT: NBA Cup Final (Las Vegas). Neutral Court.
    ODDS: Knicks -{GAME_INFO['spread']}, Total {GAME_INFO['total']}.
    
    [NYK PROFILE]
    NetRtg L10: {nyk_stats.get('NetRtg_L10', 'N/A')}
    Pace L4: {nyk_stats.get('avg_P_4', 'N/A')}
    Volatility: {nyk_stats.get('Vol_Sea', 'N/A')}
    Rest: {nyk_stats.get('days_since_last', 'N/A')} days
    
    [SAS PROFILE]
    NetRtg L10: {sas_stats.get('NetRtg_L10', 'N/A')}
    Pace L4: {sas_stats.get('avg_P_4', 'N/A')}
    Volatility: {sas_stats.get('Vol_Sea', 'N/A')}
    Rest: {sas_stats.get('days_since_last', 'N/A')} days
    
    [PREVIEW INTEL]
    {GAME_INFO['preview']}
    
    Analyze:
    """
    
    print("Sending to LLM...")
    response = client.chat.completions.create(
        model="openai/gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7
    )
    
    print("\n" + "="*40)
    print(response.choices[0].message.content)
    print("="*40 + "\n")

if __name__ == "__main__":
    analyze_game()
