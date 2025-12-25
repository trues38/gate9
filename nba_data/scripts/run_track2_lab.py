
import pandas as pd
import numpy as np

INPUT_PATH = "processed/regime_directional_dataset.csv"
OUTPUT_REPORT = "reports/track2_lab_results.md"

def load_data():
    df = pd.read_csv(INPUT_PATH)
    return df

def run_lab(df):
    report_lines = []
    report_lines.append("# 🧪 Track 2: Regime x Market Research Lab\n")
    report_lines.append(f"**Dataset**: {len(df)} games\n")
    
    # Analyze Regime Types available
    regime_counts = df['regime_type'].value_counts()
    report_lines.append("\n## Available Regimes\n")
    report_lines.append(regime_counts.head(10).to_markdown())
    
    # --- Experiment A: Spread (Regime Impact) ---
    report_lines.append("\n\n## 🧪 Experiment A: Spread (Regime Impact)\n")
    report_lines.append("Does Regime Type predict Spread Cover better than Edge Score?\n")
    
    # Filter: Spread Magnitude 4.5 - 9.5 (Standard Lines)
    # bucket: Med (4-8) or Large (8-12)
    # Let's just use numeric range
    mask_a = (df['spread_mag'] >= 4.5) & (df['spread_mag'] <= 12.5)
    df_a = df[mask_a]
    
    # Group by Regime Type -> Spread Side
    # We want to know: For each regime, what is the Fav Cover Rate?
    # (Assuming we bet ON the narrative implies betting on the 'Winner' of the regime?)
    # e.g. Favorite_Collapse -> Bet Underdog?
    
    regime_spread = df_a.groupby('regime_type').apply(
        lambda x: pd.Series({
            'count': len(x),
            'fav_cover_rate': (x['spread_side'] == 'FAVORITE_COVER').mean(),
            'dog_cover_rate': (x['spread_side'] == 'UNDERDOG_COVER').mean()
        })
    ).reset_index()
    
    # Filter N > 20
    regime_spread = regime_spread[regime_spread['count'] >= 20].sort_values(by='dog_cover_rate', ascending=False)
    
    report_lines.append("\n**Spread Cover Rates by Regime (Line 4.5 - 12.5)**:\n")
    report_lines.append(regime_spread.to_markdown(index=False))
    
    # --- Experiment B: Total (Regime Impact) ---
    report_lines.append("\n\n## 🧪 Experiment B: Total (Regime Impact)\n")
    report_lines.append("Does Regime Type predict Over/Under?\n")
    
    # Filter: Total Standard 210-240
    mask_b = (df['total'] >= 210) & (df['total'] <= 240)
    df_b = df[mask_b]
    
    regime_total = df_b.groupby('regime_type').apply(
        lambda x: pd.Series({
            'count': len(x),
            'over_rate': (x['total_side'] == 'OVER').mean(),
            'under_rate': (x['total_side'] == 'UNDER').mean()
        })
    ).reset_index()
    
    regime_total = regime_total[regime_total['count'] >= 20].sort_values(by='under_rate', ascending=False)
    
    report_lines.append("\n**Over/Under Rates by Regime (Total 210-240)**:\n")
    report_lines.append(regime_total.to_markdown(index=False))
    
    # --- Experiment C: Dead Zone Flip ---
    report_lines.append("\n\n## 🧪 Experiment C: Dead Zone Flip\n")
    report_lines.append("Can specific Regimes save us from the 'Dead Zones'?\n")
    
    # Dead Zone: Edge 60-70 + Strong Up -> Fav Cover Rate (47.7%)
    # Let's filter for this condition
    mask_c = (df['edge_bucket'] == 'Value 60-70') & (df['flow_state'] == 'STRONG_UP')
    dead_zone_df = df[mask_c]
    
    base_rate = (dead_zone_df['spread_side'] == 'FAVORITE_COVER').mean()
    report_lines.append(f"**Baseline Dead Zone (Fav Cover Rate)**: {base_rate:.1%} (N={len(dead_zone_df)})\n")
    
    # Now breakdown by Regime
    dz_breakdown = dead_zone_df.groupby('regime_type').apply(
        lambda x: pd.Series({
            'count': len(x),
            'fav_cover_rate': (x['spread_side'] == 'FAVORITE_COVER').mean()
        })
    ).reset_index()
    
    dz_breakdown = dz_breakdown[dz_breakdown['count'] >= 10].sort_values(by='fav_cover_rate', ascending=False)
    
    report_lines.append("\n**Dead Zone Breakdown by Regime**:\n")
    report_lines.append(dz_breakdown.to_markdown(index=False))
    
    # Interpretation
    report_lines.append("\n\n## 💡 Insights for Track 1 Tuning\n")
    
    # Identify strong signals
    valid_dog_triggers = regime_spread[regime_spread['dog_cover_rate'] > 0.60]['regime_type'].tolist()
    valid_under_triggers = regime_total[regime_total['under_rate'] > 0.60]['regime_type'].tolist()
    
    report_lines.append(f"- **Dog Triggers (>60%)**: {valid_dog_triggers}\n")
    report_lines.append(f"- **Under Triggers (>60%)**: {valid_under_triggers}\n")
    
    with open(OUTPUT_REPORT, 'w') as f:
        f.writelines(report_lines)
    
    print(f"🧪 Lab Analysis Complete. Report at {OUTPUT_REPORT}")

if __name__ == "__main__":
    df = load_data()
    run_lab(df)
