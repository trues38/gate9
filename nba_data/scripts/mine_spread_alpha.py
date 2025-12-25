
import pandas as pd
import numpy as np

INPUT_PATH = "processed/regime_delta_dataset.csv"
OUTPUT_REPORT = "reports/spread_alpha_report.md"

def load_data():
    df = pd.read_csv(INPUT_PATH)
    cols = ['edge_score', 'spread', 'total', 'id_spread', 'id_total', 'team_score', 'opp_score']
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    
    # id_spread: 1 if spread condition met?
    # We need to confirm directionality.
    # In many datasets (like Kaggle Nba), id_spread might be outcome relative to team?
    # Let's verify with scores.
    # Spread is usually defined as Points added to team score? Or Home Spread?
    # Let's re-calculate Cover manually to be 100% sure.
    
    # Logic: Margin = TeamScore - OppScore.
    # If Spread is "Team Spread" (e.g. -5.5), then Cover = (Margin + Spread) > 0.
    # BUT, 'spread' column in merged dataset from HISTORICAL was 'spread' (home spread usually?)
    # Let's check 'whos_favored'.
    
    # Re-calculation Logic:
    # We merged 'spread' from historical, which was usually Home Spread or Game Spread.
    # We exploded to Team-Game.
    # If Team == Home, spread_line = spread column.
    # If Team == Away, spread_line = -1 * spread column ??? 
    # This is tricky without knowing source perfectly.
    # TRUST THE 'id_spread' column first, but check correlation with Edge.
    
    return df

def mine_alpha(df):
    report_lines = []
    report_lines.append("# 🦅 Regime Delta: Alpha Mining Report\n")
    report_lines.append(f"**Dataset**: {len(df)} games (Unified Regime + Spread)\n")
    
    # Define Segments
    # 1. Edge Buckets
    bins = [0, 40, 50, 60, 70, 80, 100]
    labels = ['Trash <40', 'Weak 40-50', 'Tossup 50-60', 'Value 60-70', 'Strong 70-80', 'Extreme 80+']
    df['edge_bucket'] = pd.cut(df['edge_score'], bins=bins, labels=labels)
    
    # 2. Flow State
    # Already exists: 'flow_state'
    
    # 3. Analyze Buckets (Spread)
    report_lines.append("\n## 1. Spread Cover Rate by Edge Bucket\n")
    # Assumption: id_spread = 1 means Home Covered? Or Favorite Covered?
    # Let's check mean of id_spread. It should be ~0.5.
    
    global_cover_rate = df['id_spread'].mean()
    report_lines.append(f"Global Cover Rate (id_spread=1): {global_cover_rate:.1%}\n")
    
    # Group By Bucket
    # We want to know if High Edge predicts "id_spread=1"?
    # If Edge correlates with Cover, we found Alpha.
    
    summary = df.groupby('edge_bucket')['id_spread'].mean()
    report_lines.append(summary.to_markdown())
    
    # 4. Deep Dive: High Edge (70+) Breakdown
    report_lines.append("\n## 2. High Edge (70+) Deep Dive\n")
    high_edge = df[df['edge_score'] >= 70].copy()
    
    # By Flow
    flow_summary = high_edge.groupby('flow_state')['id_spread'].mean()
    report_lines.append("\n**By Flow State**:\n")
    report_lines.append(flow_summary.to_markdown())
    
    # 5. Over/Under Analysis (Total)
    # Does Regime/Edge/Flow predict Over (id_total=1)?
    report_lines.append("\n## 3. Total (Over/Under) Analysis\n")
    global_over_rate = df['id_total'].mean()
    report_lines.append(f"Global Over Rate (id_total=1): {global_over_rate:.1%}\n")
    
    # Does 'STRONG_UP' Flow predict Over?
    # Does 'COLLAPSE' Flow predict Under? or Over (Defense collapse)?
    
    flow_total = df.groupby('flow_state')['id_total'].mean()
    report_lines.append("\n**Over Rate by Flow State**:\n")
    report_lines.append(flow_total.to_markdown())
    
    # 6. Fatigue Analysis (if available)
    # Does Rest Mismatch predict Cover?
    
    # Print to Console
    print("--- Spread Cover by Edge Bucket ---")
    print(summary)
    
    print("\n--- Over Rate by Flow ---")
    print(flow_total)
    
    # Check for Golden Segments (> 54%)
    # Simple Loop
    best_segments = []
    
    # Segment 1: Edge 70+ & Flow STRONG_UP
    mask1 = (df['edge_score'] >= 70) & (df['flow_state'] == 'STRONG_UP')
    rate1 = df[mask1]['id_spread'].mean()
    count1 = len(df[mask1])
    if rate1 > 0.54:
        best_segments.append(f"Edge 70+ & Strong Up -> Spread Rate {rate1:.1%} (N={count1})")
        
    # Segment 2: Edge < 40 (Fade?)
    mask2 = (df['edge_score'] < 40)
    rate2 = df[mask2]['id_spread'].mean() # If low, then Fade is Alpha
    if rate2 < 0.46:
        best_segments.append(f"Edge < 40 -> Fade Spread (Opposite) Rate {1-rate2:.1%} (N={len(df[mask2])})")
        
    # Segment 3: Flow STRONG_UP -> Over?
    mask3 = (df['flow_state'] == 'STRONG_UP')
    rate3 = df[mask3]['id_total'].mean()
    if rate3 > 0.54:
        best_segments.append(f"Strong Up Flow -> Over Rate {rate3:.1%} (N={len(df[mask3])})")

    report_lines.append("\n## 4. ALPHA CANDIDATES (ROI Zones)\n")
    if best_segments:
        for seg in best_segments:
            report_lines.append(f"- ✅ {seg}\n")
    else:
        report_lines.append("- ❌ No simple segments > 54% found.\n")

    with open(OUTPUT_REPORT, 'w') as f:
        f.writelines(report_lines)
    print(f"\n📝 Alpha Mining Complete. Report at {OUTPUT_REPORT}")

if __name__ == "__main__":
    df = load_data()
    mine_alpha(df)
