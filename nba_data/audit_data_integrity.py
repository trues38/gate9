import pandas as pd
import os

def audit_csv(path, name, header=0):
    print(f"\n🔍 Auditing {name} ({path})...")
    if not os.path.exists(path):
        print(f"❌ File Not Found: {path}")
        return

    try:
        if header is None:
             df = pd.read_csv(path, header=None)
        else:
             df = pd.read_csv(path, header=0)
             
        print(f"   Rows: {len(df)}")
        print(f"   Columns: {len(df.columns)}")
        
        # Null Check
        nulls = df.isnull().sum()
        with_nulls = nulls[nulls > 0]
        
        if with_nulls.empty:
            print("   ✅ COMPLETE: No null values found in any column.")
        else:
            print("   ⚠️ MISSING DATA FOUND:")
            for col, count in with_nulls.items():
                pct = (count / len(df)) * 100
                print(f"      - {col}: {count} missing ({pct:.1f}%)")
                
        # Head Preview
        print("   headers:", list(df.columns)[:5], "...")
        
    except Exception as e:
        print(f"   ❌ Read Error: {e}")

if __name__ == "__main__":
    # 1. Audit RData Treasury (Header is Row 0 based on recent discovery)
    audit_csv("processed/rdata_treasury.csv", "RData Treasury (DuckDB Export)", header=0)
    
    # 2. Audit Odds 2025 (Gap Data)
    audit_csv("processed/odds_2025.csv", "Odds 2025 (Gap Data)", header=0)
    
    # 3. Audit The Unified Output
    audit_csv("processed/features_2025.csv", "Features 2025 (SSOT)", header=0)
