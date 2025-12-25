
import pandas as pd
import numpy as np

INPUT_PATH = "processed/nba_validation_dataset.csv"
OUTPUT_REPORT = "reports/rdata_validation_report.md"

def load_data():
    df = pd.read_csv(INPUT_PATH)
    # Ensure numeric columns
    cols = ['edge_score', 'fav_pct', 'r_odds_team', 'r_odds_opp']
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    
    # Win boolean
    df['win'] = df['result'].str.lower() == 'win'
    
    # Sort by date
    df['date'] = pd.to_datetime(df['date'])
    df.sort_values('date', inplace=True)
    return df

def calculate_pnl(row, bet_type="TEAM"):
    """
    Calculate Profit/Loss for a 1-unit bet.
    """
    if bet_type == "TEAM":
        result = row['win'] # True if Team Won
        odds = row['r_odds_team']
    elif bet_type == "OPPONENT": # Betting against the team (Fade/Trap)
        result = not row['win'] # True if Team Lost
        odds = row['r_odds_opp']
    else:
        return 0.0

    if pd.isna(odds) or odds <= 1.0:
        return 0.0 # No action if odds missing

    if result:
        return (odds - 1.0)
    else:
        return -1.0

def validate_rules(df):
    results = []
    
    # --- Definition of Rules ---
    
    # 1. VALUE RULE (The Golden Goose)
    # Edge >= 70 AND Confidence HIGH (0.65+)
    # Action: Bet Team
    mask_value = (df['edge_score'] >= 70) & (df['fav_pct'] >= 0.65)
    
    # 2. TRAP RULE (The Short)
    # 65 <= Edge < 80 AND Trap Indicator (Proxy: STRONG_UP)
    # Action: Bet Opponent (Fade)
    # Using Proxy Logic from Phase 37
    mask_trap = (df['edge_score'] >= 65) & (df['edge_score'] < 80) & (df['flow_state'] == 'STRONG_UP')
    
    # 3. NO-BET RULE (The Shield)
    # Edge 55-60 (The Noise)
    # Action: Track hypothetical performance if we bet Team (Expect Negative ROI)
    mask_nobet = (df['edge_score'] >= 55) & (df['edge_score'] < 60)
    
    # 4. BENCHMARK: Blind Favorite
    mask_fav = (df['fav_pct'] > 0.50)
    
    # --- Evaluation ---
    
    scenarios = [
        ("VALUE_RULE", mask_value, "TEAM"),
        ("TRAP_RULE", mask_trap, "OPPONENT"), # Fading!
        ("NO_BET_ZONE", mask_nobet, "TEAM"),
        ("BENCHMARK_FAV", mask_fav, "TEAM")
    ]
    
    report_lines = []
    report_lines.append("# 📊 RData Odds Validation Report\n")
    report_lines.append(f"**Dataset**: {len(df)} games (Merged RData)\n")
    
    for name, mask, side in scenarios:
        subset = df[mask].copy()
        subset['pnl'] = subset.apply(lambda r: calculate_pnl(r, side), axis=1)
        
        n_bets = len(subset)
        total_pnl = subset['pnl'].sum()
        roi = (total_pnl / n_bets * 100) if n_bets > 0 else 0.0
        max_dd = 0 # Todo: calc drawdown
        
        # Cumulative PnL for Drawdown
        subset['cum_pnl'] = subset['pnl'].cumsum()
        subset['peak'] = subset['cum_pnl'].cummax()
        subset['dd'] = subset['cum_pnl'] - subset['peak']
        max_dd = subset['dd'].min() if not subset.empty else 0
        
        # Formatting
        line = f"\n## {name} ({side} BET)\n"
        line += f"- **N Bets**: {n_bets}\n"
        line += f"- **Total Profit**: {total_pnl:.2f} Units\n"
        line += f"- **ROI**: {roi:.2f}%\n"
        line += f"- **Max Drawdown**: {max_dd:.2f} Units\n"
        
        report_lines.append(line)
        
        # Console Output
        print(f"--- {name} ---")
        print(f"Bets: {n_bets} | Profit: {total_pnl:.2f}u | ROI: {roi:.2f}% | MDD: {max_dd:.2f}u")
        
    with open(OUTPUT_REPORT, 'w') as f:
        f.writelines(report_lines)
        
    print(f"\n📝 Report saved to {OUTPUT_REPORT}")

if __name__ == "__main__":
    df = load_data()
    validate_rules(df)
