
import os
import json
import datetime
import duckdb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Setup Client
api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
base_url = "https://openrouter.ai/api/v1" if os.environ.get("OPENROUTER_API_KEY") else "https://api.deepseek.com/v1"
client = OpenAI(api_key=api_key, base_url=base_url)

def get_today_games():
    print("      [DB] Connecting to nba_analytics.duckdb...")
    try:
        con = duckdb.connect('nba_analytics.duckdb', read_only=True)
        
        # 1. Fetch Latest Regimes (Team)
        regimes = con.sql("SELECT team_id, regime_label, momentum_score, volatility_score FROM fact_regimes ORDER BY date DESC LIMIT 10").df()
        
        # 2. Fetch Latest Injuries (If any)
        injuries = con.sql("SELECT player_name, status FROM fact_injuries WHERE status != 'Active' LIMIT 5").df()
        
        # 3. Fetch DEEP PLAYER REGIMES (The DNA)
        # Verify table exists first? It should.
        try:
             player_regimes = con.sql("SELECT player_name, regime_label, momentum_score, narrative FROM fact_player_regimes ORDER BY momentum_score DESC LIMIT 5").df()
        except:
             player_regimes = []
             
        # 4. Fetch REF DATA
        try:
             refs = con.sql("SELECT ref_name, regime, stats FROM fact_ref_regimes LIMIT 5").df()
        except:
             refs = []
             
        # 5. Fetch Vector Stats
        try:
             vector_count = con.sql("SELECT COUNT(*) FROM fact_story_vectors").fetchone()[0]
             vector_note = f"Analysis supported by {vector_count} historical game vectors."
        except:
             vector_note = "Vector Database offline."
        
        con.close()
        
        return {
            "team_regimes": regimes.to_dict(orient='records'),
            "injuries": injuries.to_dict(orient='records') if hasattr(injuries, 'to_dict') else [],
            "player_dna": player_regimes.to_dict(orient='records') if hasattr(player_regimes, 'to_dict') else [],
            "ref_intel": refs.to_dict(orient='records') if hasattr(refs, 'to_dict') else [],
            "vector_status": vector_note,
            "date": str(datetime.date.today())
        }
    except Exception as e:
        print(f"      [DB Error] {e}")
        return { "error": str(e), "note": "Fallback to Mock due to DB Read Error" }

def generate_md_report():
    print("🚀 Generating Daily Report (Markdown Mode)...")
    data = get_today_games()
    
    # Construct Rich Prompt
    context_str = json.dumps(data, indent=2)
    
    system_prompt = """You are REGIME PRO ANALYST.
    You have access to:
    1. Team Regimes (Momentum, Volatility)
    2. Deep Player DNA (Narratives, Regimes)
    3. Referee Psychology (Regime, Stats)
    4. Vector Database Stats
    
    Your job is to synthesize this into a "Global Market Situation" report for an NBA Bettor.
    
    Structure:
    # 🏀 Daily Regime Report
    ## 1. Market Pulse (Team Regimes)
    - Highlight top 3 teams with extreme momentum or volatility.
    
    ## 2. Player DNA deep-dive
    - Use the 'player_dna' section. Quote specific narratives provided in the JSON.
    - Explain why these players are outliers today.
    
    ## 3. The Zebra Factor (Referees)
    - Analyze the 'ref_intel' provided. Is there a rigging alert?
    
    ## 4. Vector Context
    - Acknowledge the historical depth (vector status).
    
    ## 5. Betting Edge
    - Synthesize all above into 1-2 key betting angles.
    
    Style: Professional, Data-Driven, slightly edgy (Wall Street bets style).
    """
    
    user_prompt = f"""CONTEXT DATA:
    {context_str}
    
    Recent Accuracy Note from User: "Accuracy was good last 2 days."
    Maintain high-quality, data-driven insights.
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        
        filename = f"Daily_Report_{datetime.date.today()}.md"
        with open(filename, "w") as f:
            f.write(content)
            
        print(f"✅ Report Saved to {filename}")
        return filename
        
    except Exception as e:
        print(f"❌ Generation Failed: {e}")
        return None

if __name__ == "__main__":
    generate_md_report()
