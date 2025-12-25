
import pandas as pd
import numpy as np

INPUT_PATH = "processed/nba_validation_dataset.csv"
OUTPUT_REPORT = "reports/alpha_search_results.md"

def load_data():
    df = pd.read_csv(INPUT_PATH)
    cols = ['edge_score', 'fav_pct', 'r_odds_team', 'r_odds_opp']
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df['win'] = df['result'].str.lower() == 'win'
    df['date'] = pd.to_datetime(df['date'])
    return df

def calculate_fade_pnl(row):
    # FADE: Bet on Opponent
    odds = row['r_odds_opp']
    if pd.isna(odds) or odds <= 1.0: return 0.0
    
    # If Team Won -> We Lost (-1)
    # If Team Lost -> We Won (Odds - 1)
    if row['win']:
        return -1.0
    else:
        return (odds - 1.0)

def search_alpha(df):
    report_lines = []
    report_lines.append("# 🔍 Anti-Gravity Alpha Search Report\n")
    report_lines.append(f"**Dataset**: {len(df)} games (Merged RData)\n")
    
    # 1. Define the Candidate Zone
    # Edge: [55, 65] (Grey Zone)
    # Market Confidence: Implied Prob >= 70% (Odds <= 1.43)
    # Dislocation: Flow == STABLE (Relative Weakness) OR just raw Fade?
    
    # Let's try 2 versions
    
    scenarios = [
        {
            "id": "ALPHA_ZONE_STRICT",
            "desc": "Edge 55-65, Mkt Prob > 70% (Odds<=1.43)",
            "mask": (df['edge_score'] >= 55) & (df['edge_score'] <= 65) & (df['r_odds_team'] <= 1.43)
        },
        {
            "id": "ALPHA_ZONE_RELAXED",
            "desc": "Edge 50-60 (Toss-Up), Mkt Prob > 60% (Odds<=1.67)",
            "mask": (df['edge_score'] >= 50) & (df['edge_score'] <= 60) & (df['r_odds_team'] <= 1.67)
        },
        {
             # The "Fake Strong"
            "id": "FAKE_STRONG",
            "desc": "Edge < 65, Mkt Prob > 75% (Odds<=1.33)",
            "mask": (df['edge_score'] < 65) & (df['r_odds_team'] <= 1.33)
        }
    ]
    
    for sc in scenarios:
        subset = df[sc['mask']].copy()
        subset['pnl'] = subset.apply(calculate_fade_pnl, axis=1)
        
        n_bets = len(subset)
        total_pnl = subset['pnl'].sum()
        roi = (total_pnl / n_bets * 100) if n_bets > 0 else 0.0
        
        # Calculate Win Rate (Opponent Wins / Total)
        opp_win_rate = (~subset['win']).mean()
        avg_fade_odds = subset['r_odds_opp'].mean()
        
        # Drawdown
        subset['cum_pnl'] = subset['pnl'].cumsum()
        subset['peak'] = subset['cum_pnl'].cummax()
        subset['dd'] = subset['cum_pnl'] - subset['peak']
        max_dd = subset['dd'].min() if not subset.empty else 0
        
        print(f"--- {sc['id']} ---")
        print(f"Bets: {n_bets} | Profit: {total_pnl:.2f}u | ROI: {roi:.2f}% | OppWin%: {opp_win_rate:.1%} | AvgOdds: {avg_fade_odds:.2f}")
        
        report_lines.append(f"\n## {sc['id']}\n")
        report_lines.append(f"- **Desc**: {sc['desc']}\n")
        report_lines.append(f"- **Bets**: {n_bets}\n")
        report_lines.append(f"- **ROI**: {roi:.2f}%\n")
        report_lines.append(f"- **Total Profit**: {total_pnl:.2f}u\n")
        report_lines.append(f"- **Max Drawdown**: {max_dd:.2f}u\n")
        report_lines.append(f"- **Opponent Win Rate**: {opp_win_rate:.1%}\n")

    with open(OUTPUT_REPORT, 'w') as f:
        f.writelines(report_lines)
    print(f"\n📝 Search complete. Saved to {OUTPUT_REPORT}")

if __name__ == "__main__":
    df = load_data()
    search_alpha(df)
