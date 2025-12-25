
import json
import pandas as pd
import numpy as np

INPUT_PATH = "processed/nba_regime_index_v1.json"   # Adjusted path
OUT_PREFIX = "reports/season_backtest"            # Adjusted prefix to reports/

SEASONS_TARGET = ["2022-23", "2023-24", "2024-25"]

# --- Helpers ---
def season_label(d):
    # NBA 시즌: 10월~다음해 6월(대략). month>=10이면 다음해가 시즌 끝
    y = d.year
    end = y + 1 if d.month >= 10 else y
    start = end - 1
    return f"{start}-{str(end)[-2:]}"

def edge_bucket(edge):
    if pd.isna(edge): return None
    if 45 <= edge < 55: return "A_45_55"
    if 55 <= edge < 60: return "B_55_60"
    if 60 <= edge < 65: return "C_60_65"
    if 65 <= edge < 70: return "D_65_70"
    if 70 <= edge < 80: return "E_70_80"
    if edge >= 80:      return "F_80_PLUS"
    return None

def fav_confidence(p):
    # 확률 구간(원하면 바꿔도 됨)
    if pd.isna(p): return "NA"
    if p >= 0.75:  return "EXTREME"
    if p >= 0.65:  return "HIGH"
    if p >= 0.55:  return "MID"
    return "LOW"

# --- Load ---
print(f"📂 Loading {INPUT_PATH}...")
with open(INPUT_PATH, "r") as f:
    data = json.load(f)

df = pd.DataFrame(data)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["edge_score"] = pd.to_numeric(df.get("edge_score"), errors="coerce")
df["fav_pct"] = pd.to_numeric(df.get("fav_pct"), errors="coerce")
df["flow_state"] = df.get("flow_state", "NA").fillna("NA")
df["result"] = df.get("result", "").astype(str).str.lower()
df["win"] = df["result"].eq("win")
df["season"] = df["date"].apply(season_label)
df["edge_bucket"] = df["edge_score"].apply(edge_bucket)
df["fav_confidence"] = df["fav_pct"].apply(fav_confidence)

# regime_type 없을 수도 있으니 방어
if "regime_type" not in df.columns:
    df["regime_type"] = None

# --- Filter to target seasons that exist ---
avail = sorted(df["season"].dropna().unique().tolist())
missing = [s for s in SEASONS_TARGET if s not in avail]
use_seasons = [s for s in SEASONS_TARGET if s in avail]

print("Available seasons in file:", avail[-10:])
if missing:
    print("WARNING: Missing seasons in file ->", missing)
if not use_seasons:
    raise SystemExit("No target seasons found in this file. Check INPUT_PATH / data range.")

x = df[df["season"].isin(use_seasons)].copy()

# --- Define "bet candidates" (전략 후보) ---
# 기본안: Edge >= 70
x["bet_edge70"] = x["edge_score"] >= 70

# 강화안: Edge>=70 + 확신(HIGH/EXTREME)
x["bet_edge70_highplus"] = x["bet_edge70"] & x["fav_confidence"].isin(["HIGH", "EXTREME"])

# 보수안: Edge>=70 + EXTREME만
x["bet_edge70_extreme"] = x["bet_edge70"] & (x["fav_confidence"] == "EXTREME")

# (옵션) Trap 회피 예시: STRONG_UP만 고집한다면
x["bet_edge70_strongup"] = x["bet_edge70"] & (x["flow_state"] == "STRONG_UP")

# --- Summary: 시즌별 "몇 경기 베팅 후보가 나오나" + 실제 승률 ---
def summarize(mask_col):
    g = x.groupby("season").apply(lambda d: pd.Series({
        "games": len(d),
        "bets": int(d[mask_col].sum()),
        "bet_rate": float(d[mask_col].mean()),
        "win_rate_on_bets": float(d.loc[d[mask_col], "win"].mean()) if d[mask_col].any() else np.nan,
        "win_rate_all": float(d["win"].mean()),
    }))
    return g.reset_index().rename(columns={"index": "season"})

summary_70 = summarize("bet_edge70")
summary_70_hp = summarize("bet_edge70_highplus")
summary_70_ex = summarize("bet_edge70_extreme")
summary_70_su = summarize("bet_edge70_strongup")

# --- Edge Bucket Performance by season ---
def bucket_perf(season):
    d = x[x["season"] == season].copy()
    if d.empty:
        return pd.DataFrame()
    grp = d.groupby("edge_bucket")
    out = grp.apply(lambda g: pd.Series({
        "games": len(g),
        "win_rate": g["win"].mean(),
        "collapse_rate": (g["regime_type"] == "Favorite_Collapse").mean(),
        "hold_rate": (g["regime_type"] == "Favorite_Hold").mean(),
        "upset_rate": (g["regime_type"] == "Underdog_Upset").mean(),
        "blowout_win_rate": (g["regime_type"] == "Blowout_Win").mean(),
    })).reset_index().sort_values("edge_bucket")
    out.insert(0, "season", season)
    return out

bucket_tables = pd.concat([bucket_perf(s) for s in use_seasons], ignore_index=True)

# --- Save outputs ---
def save(df_, name):
    csv_path = f"{OUT_PREFIX}_{name}.csv"
    df_.to_csv(csv_path, index=False)
    print("Saved:", csv_path)

save(summary_70, "summary_edge70")
save(summary_70_hp, "summary_edge70_highplus")
save(summary_70_ex, "summary_edge70_extreme")
save(summary_70_su, "summary_edge70_strongup")
save(bucket_tables, "bucket_perf")

# --- Print quick view ---
print("\n=== SUMMARY (Edge>=70) ===")
print(summary_70.to_string(index=False))

print("\n=== SUMMARY (Edge>=70 + HIGH/EXTREME) ===")
print(summary_70_hp.to_string(index=False))

print("\n=== SUMMARY (Edge>=70 + EXTREME) ===")
print(summary_70_ex.to_string(index=False))

print("\n=== BUCKET PERFORMANCE (per season) ===")
print(bucket_tables.to_string(index=False))
