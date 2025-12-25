
import pandas as pd
import numpy as np

INPUT_PATH = "processed/nba_validation_dataset.csv"
OUTPUT_REPORT = "reports/rdata_refined_validation.md"

def load_data():
    df = pd.read_csv(INPUT_PATH)
    cols = ['edge_score', 'fav_pct', 'r_odds_team', 'r_odds_opp']
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df['win'] = df['result'].str.lower() == 'win'
    df['date'] = pd.to_datetime(df['date'])
    df.sort_values('date', inplace=True)
    return df

def calculate_pnl(row, bet_type="TEAM"):
    if bet_type == "TEAM":
        result = row['win']
        odds = row['r_odds_team']
    elif bet_type == "OPPONENT":
        result = not row['win']
        odds = row['r_odds_opp']
    else: return 0.0

    if pd.isna(odds) or odds <= 1.0: return 0.0
    return (odds - 1.0) if result else -1.0

def validate_refined(df):
    report_lines = []
    report_lines.append("# 📊 Refined Rules Validation (Searching for Alpha)\n")
    
    # Thresholds to test
    scenarios = [
        # The "Money" Tier from Backtest?
        ("CORE_VALUE_80_EXTREME", (df['edge_score'] >= 80) & (df['fav_pct'] >= 0.75), "TEAM"),
        
        # Slightly wider value
        ("VALUE_75_HIGH", (df['edge_score'] >= 75) & (df['fav_pct'] >= 0.65), "TEAM"),
        
        # Strict Trap (Maybe only Extreme Flow + Low Gap?)
        # Proxy: Edge [70, 80) + STRONG_UP + High Confidence
        ("HARD_TRAP_PROXY", (df['edge_score'] >= 70) & (df['edge_score'] < 80) & (df['flow_state'] == 'STRONG_UP') & (df['fav_pct'] >= 0.60), "OPPONENT")
    ]
    
    for name, mask, side in scenarios:
        subset = df[mask].copy()
        subset['pnl'] = subset.apply(lambda r: calculate_pnl(r, side), axis=1)
        
        n_bets = len(subset)
        total_pnl = subset['pnl'].sum()
        roi = (total_pnl / n_bets * 100) if n_bets > 0 else 0.0
        
        win_rate = subset['win'].mean() if side == "TEAM" else (~subset['win']).mean()
        avg_odds = subset['r_odds_team'].mean() if side == "TEAM" else subset['r_odds_opp'].mean()
        
        print(f"--- {name} ---")
        print(f"Bets: {n_bets} | Profit: {total_pnl:.2f}u | ROI: {roi:.2f}% | WinRate: {win_rate:.1%} | AvgOdds: {avg_odds:.2f}")
        
        report_lines.append(f"\n## {name}\nROI: {roi:.2f}% | Profit: {total_pnl:.2f}u | N: {n_bets}\n")

    with open(OUTPUT_REPORT, 'w') as f:
        f.writelines(report_lines)

if __name__ == "__main__":
    df = load_data()
    validate_refined(df)
