
import pandas as pd
import json
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

INPUT_FILE = "processed/nba_regime_index_v1.json"
OUTPUT_REPORT = "reports/regime_analysis_v1.md"

def analyze_patterns():
    print(f"📊 Loading {INPUT_FILE}...")
    df = pd.read_json(INPUT_FILE)
    
    # 2. Define Edge Buckets
    def edge_bucket(score):
        if 45 <= score < 55:
            return "A_45_55"
        elif 55 <= score < 60:
            return "B_55_60"
        elif 60 <= score < 65:
            return "C_60_65"
        elif 65 <= score < 70:
            return "D_65_70"
        elif 70 <= score < 90: # Extended to cover 80+
            return "E_70_Plus"
        else:
            return None # Outliers

    df["edge_bucket"] = df["edge_score"].apply(edge_bucket)
    df = df[df["edge_bucket"].notnull()].copy()
    
    print(f"✅ Filtered to {len(df)} games in standard buckets.")

    # 3. Basic Outcome Metrics
    # Helper for rate calculation
    summary = (
        df
        .groupby("edge_bucket")
        .agg(
            games=("id", "count"),
            win_rate=("result", lambda x: (x == "Win").mean()),
            collapse_rate=("regime_type", lambda x: (x == "Favorite_Collapse").mean()),
            hold_rate=("regime_type", lambda x: (x == "Favorite_Hold").mean()),
            upset_rate=("regime_type", lambda x: (x == "Underdog_Upset").mean()), # Mapped
            blowout_win_rate=("regime_type", lambda x: (x == "Blowout_Win").mean())
        )
        .reset_index()
    )
    
    print("\n--------- EDGE BUCKET SUMMARY ---------")
    print(summary.to_string())

    # 4. Conditional: Flow State
    # Where does Collapse happen most?
    conditional = (
        df
        .groupby(["edge_bucket", "flow_state"])
        .agg(
            games=("id", "count"),
            collapse_rate=("regime_type", lambda x: (x == "Favorite_Collapse").mean()),
            win_rate=("result", lambda x: (x == "Win").mean()),
        )
        .reset_index()
        .sort_values(["edge_bucket", "collapse_rate"], ascending=[True, False])
    )
    
    # 5. Conditional: Fav Confidence
    df["fav_confidence"] = pd.cut(
        df["fav_pct"],
        bins=[0, 0.5, 0.6, 0.7, 1.0],
        labels=["LOW", "MID", "HIGH", "EXTREME"]
    )

    fav_conditional = (
        df
        .groupby(["edge_bucket", "fav_confidence"])
        .agg(
            games=("id", "count"),
            collapse_rate=("regime_type", lambda x: (x == "Favorite_Collapse").mean()),
            win_rate=("result", lambda x: (x == "Win").mean()),
        )
        .reset_index()
    )

    # 6. Generate Markdown Report
    with open(OUTPUT_REPORT, 'w') as f:
        f.write("# 📊 Regime Pattern Analysis\n")
        f.write(f"**Source**: {len(df)} games (2019-2025)\n\n")
        
        f.write("## 1. Edge Bucket Performance\n")
        f.write(summary.to_markdown(index=False, floatfmt=".1%"))
        f.write("\n\n")
        
        f.write("## 2. Danger Zones: Collapse Rate by Flow\n")
        f.write("When does a Favorite Collapse happen based on Momentum?\n\n")
        
        # Filter for meaningful sample size
        cond_filtered = conditional[conditional['games'] > 50]
        f.write(cond_filtered.to_markdown(index=False, floatfmt=".1%"))
        f.write("\n\n")
        
        f.write("## 3. The 'Trap' Matrix: Edge vs Confidence\n")
        f.write("Where does high confidence meet high failure?\n\n")
        fav_filtered = fav_conditional[fav_conditional['games'] > 30]
        f.write(fav_filtered.to_markdown(index=False, floatfmt=".1%"))
        
    print(f"\n📝 Report saved to {OUTPUT_REPORT}")

if __name__ == "__main__":
    analyze_patterns()
