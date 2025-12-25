
import pandas as pd
import numpy as np

INPUT_PATH = "processed/regime_directional_dataset.csv"
OUTPUT_PATH = "reports/scorecard_example_output.csv"

def run_scorecard():
    print("📋 Running Scorecard System (Track 1)...")
    df = pd.read_csv(INPUT_PATH)
    
    # 1. Base Probability (Edge Bucket Rule)
    # 80+ -> 75%
    # 70-80 -> 65%
    # 60-70 -> 58%
    # 50-60 -> 50%
    # <50 -> 45%
    
    def get_base_prob(score):
        if score >= 80: return 0.75
        elif score >= 70: return 0.65
        elif score >= 60: return 0.58
        elif score >= 50: return 0.50
        else: return 0.45
        
    df['base_prob'] = df['edge_score'].apply(get_base_prob)
    
    # 2. Dead Zone Auto-Correction (FADE Logic)
    # Rule: Edge 60-70 AND Flow STRONG_UP -> FADE SPREAD (Bet Dog)
    # We treat this as a negative adjustment to "Favorite Cover Prob".
    
    def get_auto_adjust(row):
        adj = 0.0
        reason = []
        
        # Dead Zone 1: Spread Fade (Edge 60-70 + Strong Up)
        if (60 <= row['edge_score'] < 70) and (row['flow_state'] == 'STRONG_UP'):
            adj -= 0.15 # -15% penalty to Favorite
            reason.append("DEAD_ZONE_SPREAD")
            
        # Dead Zone 2: Total Fade (Tossup + Strong Up -> Under?)
        # Adjusting Spread Score? No, this is separate.
        # Let's focus on Action Output.
        
        return adj, ";".join(reason)
        
    adjustment_results = df.apply(get_auto_adjust, axis=1)
    df['auto_adjust'] = [x[0] for x in adjustment_results]
    df['adjust_reason'] = [x[1] for x in adjustment_results]
    
    # 3. Final Probability
    # Narrative Adjustment is 0 for now (Manual Input in Product)
    df['final_prob'] = df['base_prob'] + df['auto_adjust']
    
    # 4. Action Logic
    # Market Implied Prob (Standard -110 = 52.4%)
    # If Final > 57% -> BET (Cover)
    # If Final < 40% -> FADE (Bet Opposite)
    # Else -> PASS
    
    conditions = [
        (df['final_prob'] >= 0.57),
        (df['final_prob'] <= 0.40)
    ]
    choices = ['BET_FAVORITE', 'BET_UNDERDOG']
    df['action'] = np.select(conditions, choices, default='PASS')
    
    # Select cols for report
    cols = ['date', 'team', 'matchup', 'edge_score', 'flow_state', 'base_prob', 'auto_adjust', 'adjust_reason', 'final_prob', 'action', 'result', 'spread_side']
    
    # Take a sample of 50 recent games
    sample = df.sort_values(by='date', ascending=False).head(50)[cols]
    
    sample.to_csv(OUTPUT_PATH, index=False)
    print(f"✅ Scorecard Generated. Saved to {OUTPUT_PATH}")
    print("Sample Actions:\n", sample['action'].value_counts())

if __name__ == "__main__":
    run_scorecard()
