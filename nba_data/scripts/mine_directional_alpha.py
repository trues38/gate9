
import pandas as pd
import numpy as np

INPUT_PATH = "processed/regime_directional_dataset.csv"
OUTPUT_SPREAD_CSV = "reports/spread_directional_alpha.csv"
OUTPUT_TOTAL_CSV = "reports/total_directional_alpha.csv"
OUTPUT_SUMMARY = "reports/alpha_survivors_summary.md"

def load_data():
    df = pd.read_csv(INPUT_PATH)
    return df

def mine_alpha(df):
    print("⛏️ Mining Directional Alpha...")
    
    report_lines = []
    report_lines.append("# 🔥 Regime Alpha Survivors Summary\n")
    report_lines.append(f"**Dataset**: {len(df)} games\n")
    report_lines.append("**Criteria**: N >= 30, WinRate >= 55%, ROI > +2%\n")
    
    survivors = []
    
    # 1. Spread Mining
    # Group Keys: edge_bucket, flow_state, spread_side
    # We want to see if specific combinations yield high win rates for one side.
    
    # Filter out PUSH
    spread_df = df[df['spread_side'] != 'PUSH/UNKNOWN'].copy()
    
    # Grouping
    spread_groups = spread_df.groupby(['edge_bucket', 'flow_state', 'spread_side'], observed=True).size().reset_index(name='count')
    
    # Calculate Wins per Group?
    # Actually, the 'spread_side' is the RESULT.
    # We need to calculate the probability of that result given the condition.
    
    # Correct Approach:
    # Denominator: Count of games in (Edge, Flow).
    # Numerator: Count of games where Result = Target Side.
    
    # Let's iterate through Conditions (Edge, Flow) and calculate Rate for EACH Side.
    conditions = spread_df.groupby(['edge_bucket', 'flow_state'], observed=True)
    
    spread_results = []
    
    for (edge, flow), group in conditions:
        total_n = len(group)
        if total_n < 30: continue
        
        for side in ['FAVORITE_COVER', 'UNDERDOG_COVER']:
            wins = len(group[group['spread_side'] == side])
            rate = wins / total_n
            roi = (rate * 0.909) - (1 - rate) # Odds -110 (1.909 payout) => Profit = 0.909, Loss = 1
            # ROI = (Rate * 0.909) - ((1-Rate) * 1) = Rate*1.909 - 1
            
            row = {
                "market": "SPREAD",
                "edge_bucket": edge,
                "flow_state": flow,
                "bet_side": side,
                "count": total_n,
                "wins": wins,
                "win_rate": round(rate, 4),
                "roi": round(roi * 100, 2)
            }
            spread_results.append(row)
            
            if rate >= 0.55 and row['roi'] > 2.0:
                survivors.append(row)

    spread_results_df = pd.DataFrame(spread_results)
    spread_results_df.sort_values(by='roi', ascending=False, inplace=True)
    spread_results_df.to_csv(OUTPUT_SPREAD_CSV, index=False)
    
    # 2. Total Mining
    total_df = df.dropna(subset=['id_total']).copy()
    total_groups = total_df.groupby(['flow_state', 'edge_bucket'], observed=True) # Maybe Edge bucket matters for pace?
    
    # Or simplified logic: Flow -> Over/Under
    # User asked for: (flow_state, tempo_bucket, fatigue_state, total_side)
    # We lack tempo/fatigue buckets in enriched dataset (need to add if critical).
    # Using Flow + Edge for now.
    
    total_results = []
    
    for (flow, edge), group in total_groups:
        total_n = len(group)
        if total_n < 30: continue
        
        for side in ['OVER', 'UNDER']:
            wins = len(group[group['total_side'] == side])
            rate = wins / total_n
            roi = (rate * 0.909) - (1 - rate)
            
            row = {
                "market": "TOTAL",
                "flow_state": flow,
                "edge_bucket": edge, # Proxy for game quality
                "bet_side": side,
                "count": total_n,
                "wins": wins,
                "win_rate": round(rate, 4),
                "roi": round(roi * 100, 2)
            }
            total_results.append(row)
            
            if rate >= 0.55 and row['roi'] > 2.0:
                survivors.append(row)

    total_results_df = pd.DataFrame(total_results)
    total_results_df.sort_values(by='roi', ascending=False, inplace=True)
    total_results_df.to_csv(OUTPUT_TOTAL_CSV, index=False)
    
    # Write Summary
    if survivors:
        report_lines.append("\n## ✅ Valid Alpha Strategies\n")
        
        survivor_df = pd.DataFrame(survivors)
        survivor_df.sort_values(by='roi', ascending=False, inplace=True)
        
        report_lines.append(survivor_df.to_markdown(index=False))
        
        # Dead Zones
        report_lines.append("\n\n## 💀 Dead Zones (Avoid)\n")
        dead_spread = spread_results_df[spread_results_df['win_rate'] < 0.48].head(5)
        report_lines.append("**Top Spread Fades (Avoid Betting THIS Side):**\n")
        report_lines.append(dead_spread.to_markdown(index=False))
        
    else:
        report_lines.append("❌ No strategies met the criteria (N>=30, ROI>2%). Market is efficient.\n")

    # Always Report Dead Zones
    report_lines.append("\n\n## 💀 Dead Zones (Avoid)\n")
    report_lines.append("Conditions where Win Rate < 48% (Systematic Loss).\n")
    
    dead_spread = spread_results_df[spread_results_df['win_rate'] < 0.48].head(10)
    report_lines.append("\n**Top Spread Fades (Avoid/Fade THIS Side):**\n")
    if not dead_spread.empty:
        report_lines.append(dead_spread[['edge_bucket', 'flow_state', 'bet_side', 'count', 'win_rate', 'roi']].to_markdown(index=False))
    else:
        report_lines.append("None found.")
        
    dead_total = total_results_df[total_results_df['win_rate'] < 0.48].head(10)
    report_lines.append("\n\n**Top Total Fades (Avoid/Fade THIS Side):**\n")
    if not dead_total.empty:
        report_lines.append(dead_total[['flow_state', 'edge_bucket', 'bet_side', 'count', 'win_rate', 'roi']].to_markdown(index=False))
    else:
        report_lines.append("None found.")

    with open(OUTPUT_SUMMARY, 'w') as f:
        f.writelines(report_lines)
    
    # Save Dead Zones to specific file as requested
    with open("reports/dead_zones.md", 'w') as f:
        f.write("# 💀 Regime Dead Zones (Avoid / Fade)\n\n")
        f.write("Strategic Action: **AVOID** or **FADE** (Bet Opposite).\n\n")
        if not dead_spread.empty:
            f.write("## SPREAD FADES\n")
            f.write(dead_spread[['edge_bucket', 'flow_state', 'bet_side', 'count', 'win_rate', 'roi']].to_markdown(index=False))
            f.write("\n\n")
        if not dead_total.empty:
            f.write("## TOTAL FADES\n")
            f.write(dead_total[['flow_state', 'edge_bucket', 'bet_side', 'count', 'win_rate', 'roi']].to_markdown(index=False))

if __name__ == "__main__":
    df = load_data()
    mine_alpha(df)
