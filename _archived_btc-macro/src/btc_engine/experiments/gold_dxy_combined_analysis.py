"""
Gold ↔ DXY 통합 분석

1. Gold ↔ DXY 상관관계: 두 신호가 독립적인가?
2. 복합 신호 테스트: Gold +3% AND DXY -1.5% 동시 발생
3. Equity Melt-Up 레짐에서 반대 전략
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import json
import yfinance as yf
import pandas as pd
import numpy as np
from scipy import stats
from collections import defaultdict
from typing import Dict, List, Tuple

# =============================================================================
# 데이터 로드
# =============================================================================

def load_regime_data() -> Dict[str, str]:
    """날짜 → 레짐 매핑"""
    with open('/Users/js/Documents/btc-macro/data/regime_families.json', 'r') as f:
        families = json.load(f)

    date_to_regime = {}
    for fam in families:
        name = fam.get('family_name', 'Unknown')
        for date in fam.get('member_dates', []):
            date_to_regime[date] = name

    return date_to_regime


def fetch_data(start_date: str, end_date: str) -> pd.DataFrame:
    """Gold, DXY, BTC 데이터"""
    print(f"Fetching data: {start_date} ~ {end_date}")

    btc = yf.download("BTC-USD", start=start_date, end=end_date, progress=False)
    gold = yf.download("GLD", start=start_date, end=end_date, progress=False)
    dxy = yf.download("UUP", start=start_date, end=end_date, progress=False)

    for df in [btc, gold, dxy]:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

    data = pd.DataFrame()
    data['BTC_Close'] = btc['Close']
    data['Gold_Close'] = gold['Close']
    data['DXY_Close'] = dxy['Close']

    # 수익률
    for window in [1, 5, 7, 10]:
        data[f'BTC_Ret_{window}d'] = data['BTC_Close'].pct_change(window, fill_method=None)
        data[f'Gold_Ret_{window}d'] = data['Gold_Close'].pct_change(window, fill_method=None)
        data[f'DXY_Ret_{window}d'] = data['DXY_Close'].pct_change(window, fill_method=None)

    data = data.ffill().dropna()
    print(f"Loaded {len(data)} days")
    return data


# =============================================================================
# 1. Gold ↔ DXY 상관관계 분석
# =============================================================================

def analyze_gold_dxy_correlation(data: pd.DataFrame) -> Dict:
    """Gold와 DXY의 상관관계 분석"""
    print("\n" + "=" * 70)
    print("1. GOLD ↔ DXY CORRELATION ANALYSIS")
    print("=" * 70)

    results = {}

    # 다양한 윈도우에서 상관관계
    print("\n1.1 Rolling Correlation (Gold vs DXY)")
    print("-" * 50)

    for window in [7, 30, 90, 180]:
        corr = data['Gold_Ret_7d'].rolling(window).corr(data['DXY_Ret_7d']).dropna()
        results[f'corr_{window}d'] = {
            'mean': corr.mean(),
            'std': corr.std(),
            'min': corr.min(),
            'max': corr.max()
        }
        print(f"  {window}d window: mean={corr.mean():.3f}, std={corr.std():.3f}, "
              f"range=[{corr.min():.3f}, {corr.max():.3f}]")

    # 전체 기간 상관관계
    overall_corr = data['Gold_Ret_7d'].corr(data['DXY_Ret_7d'])
    print(f"\n  Overall correlation: {overall_corr:.3f}")
    results['overall_corr'] = overall_corr

    # 신호 동시 발생 분석
    print("\n1.2 Signal Co-occurrence Analysis")
    print("-" * 50)

    gold_signal = data['Gold_Ret_7d'] >= 0.03
    dxy_signal = data['DXY_Ret_7d'] <= -0.015

    both_signals = (gold_signal & dxy_signal).sum()
    only_gold = (gold_signal & ~dxy_signal).sum()
    only_dxy = (~gold_signal & dxy_signal).sum()
    neither = (~gold_signal & ~dxy_signal).sum()

    total = len(data)
    print(f"  Gold +3% only:     {only_gold:4d} ({only_gold/total*100:.1f}%)")
    print(f"  DXY -1.5% only:    {only_dxy:4d} ({only_dxy/total*100:.1f}%)")
    print(f"  BOTH signals:      {both_signals:4d} ({both_signals/total*100:.1f}%)")
    print(f"  Neither:           {neither:4d} ({neither/total*100:.1f}%)")

    # 독립성 검정 (기대값 vs 실제값)
    p_gold = gold_signal.mean()
    p_dxy = dxy_signal.mean()
    expected_both = p_gold * p_dxy * total

    print(f"\n  Expected co-occurrence (if independent): {expected_both:.1f}")
    print(f"  Actual co-occurrence: {both_signals}")

    if expected_both > 0:
        ratio = both_signals / expected_both
        print(f"  Ratio (actual/expected): {ratio:.2f}x")

        if ratio > 1.5:
            print("  → Signals are POSITIVELY correlated (redundant)")
        elif ratio < 0.67:
            print("  → Signals are NEGATIVELY correlated (complementary)")
        else:
            print("  → Signals are roughly INDEPENDENT")

    results['co_occurrence'] = {
        'both': both_signals,
        'only_gold': only_gold,
        'only_dxy': only_dxy,
        'expected': expected_both
    }

    return results


# =============================================================================
# 2. 복합 신호 테스트
# =============================================================================

def test_combined_signals(
    data: pd.DataFrame,
    date_to_regime: Dict[str, str]
) -> Dict:
    """Gold AND DXY 복합 신호 테스트"""
    print("\n" + "=" * 70)
    print("2. COMBINED SIGNAL TEST (Gold +3% AND DXY -1.5%)")
    print("=" * 70)

    data['Regime'] = data.index.map(
        lambda x: date_to_regime.get(x.strftime('%Y-%m-%d'), 'Unknown')
    )

    results = {
        'gold_only': [],
        'dxy_only': [],
        'combined': [],
        'either': []
    }

    # 파라미터
    GOLD_TH = 0.03
    DXY_TH = -0.015
    LAG = 3  # 평균 래그
    HOLD = 7

    i = 0
    while i < len(data) - LAG - HOLD:
        row = data.iloc[i]
        date_str = data.index[i].strftime('%Y-%m-%d')
        regime = row['Regime']

        # Gold Safe-Haven만
        if 'Gold Safe-Haven' not in regime:
            i += 1
            continue

        gold_sig = row['Gold_Ret_7d'] >= GOLD_TH
        dxy_sig = row['DXY_Ret_7d'] <= DXY_TH

        entry_idx = i + LAG
        exit_idx = entry_idx + HOLD

        if exit_idx >= len(data):
            break

        entry_price = data.iloc[entry_idx]['BTC_Close']
        exit_price = data.iloc[exit_idx]['BTC_Close']
        return_pct = (exit_price - entry_price) / entry_price

        trade = {
            'date': date_str,
            'return': return_pct,
            'is_win': return_pct > 0,
            'gold_ret': row['Gold_Ret_7d'],
            'dxy_ret': row['DXY_Ret_7d']
        }

        if gold_sig and dxy_sig:
            results['combined'].append(trade)
            results['either'].append(trade)
            i = exit_idx
        elif gold_sig:
            results['gold_only'].append(trade)
            results['either'].append(trade)
            i = exit_idx
        elif dxy_sig:
            results['dxy_only'].append(trade)
            results['either'].append(trade)
            i = exit_idx
        else:
            i += 1

    # 결과 출력
    print("\n2.1 Performance by Signal Type (Gold Safe-Haven Only)")
    print("-" * 70)
    print(f"{'Signal Type':<20} {'N':<6} {'WR':<8} {'Avg Ret':<12} {'Total Ret':<12} {'p-value'}")
    print("-" * 70)

    for sig_type, trades in results.items():
        if trades:
            wins = sum(1 for t in trades if t['is_win'])
            wr = wins / len(trades)
            avg_ret = np.mean([t['return'] for t in trades])
            total_ret = np.prod([1 + t['return'] for t in trades]) - 1
            pval = 1 - stats.binom.cdf(wins - 1, len(trades), 0.5)
            sig = '*' if pval < 0.05 else ''

            print(f"{sig_type:<20} {len(trades):<6} {wr:.1%}    {avg_ret*100:+.2f}%       "
                  f"{total_ret*100:+.1f}%        {pval:.3f}{sig}")

    # 복합 신호 개별 거래
    if results['combined']:
        print("\n2.2 Combined Signal Trades (Both Gold AND DXY)")
        print("-" * 70)
        for t in results['combined']:
            status = "WIN " if t['is_win'] else "LOSS"
            print(f"  {t['date']}: {t['return']*100:+.1f}% ({status}) | "
                  f"Gold: {t['gold_ret']*100:+.1f}%, DXY: {t['dxy_ret']*100:+.1f}%")
    else:
        print("\n  No combined signal trades found")

    return results


# =============================================================================
# 3. Equity Melt-Up 반대 전략
# =============================================================================

def test_meltup_contrarian(
    data: pd.DataFrame,
    date_to_regime: Dict[str, str]
) -> Dict:
    """Equity Melt-Up에서 DXY 하락 → BTC 숏 전략"""
    print("\n" + "=" * 70)
    print("3. EQUITY MELT-UP CONTRARIAN STRATEGY")
    print("=" * 70)

    data['Regime'] = data.index.map(
        lambda x: date_to_regime.get(x.strftime('%Y-%m-%d'), 'Unknown')
    )

    # 3가지 전략 비교
    strategies = {
        'DXY_weak_short': {  # DXY 하락 → BTC 숏
            'dxy_condition': lambda x: x <= -0.015,
            'direction': 'short',
            'trades': []
        },
        'DXY_strong_long': {  # DXY 상승 → BTC 롱
            'dxy_condition': lambda x: x >= 0.015,
            'direction': 'long',
            'trades': []
        },
        'baseline_long': {  # 기준선: 그냥 롱
            'dxy_condition': lambda x: True,
            'direction': 'long',
            'trades': []
        }
    }

    LAG = 2
    HOLD = 7

    for strat_name, strat in strategies.items():
        i = 0
        while i < len(data) - LAG - HOLD:
            row = data.iloc[i]
            regime = row['Regime']

            if 'Equity Complacency Melt-Up' not in regime:
                i += 1
                continue

            if strat['dxy_condition'](row['DXY_Ret_7d']):
                entry_idx = i + LAG
                exit_idx = entry_idx + HOLD

                if exit_idx >= len(data):
                    break

                entry_price = data.iloc[entry_idx]['BTC_Close']
                exit_price = data.iloc[exit_idx]['BTC_Close']

                if strat['direction'] == 'long':
                    return_pct = (exit_price - entry_price) / entry_price
                else:  # short
                    return_pct = (entry_price - exit_price) / entry_price

                strat['trades'].append({
                    'date': data.index[i].strftime('%Y-%m-%d'),
                    'return': return_pct,
                    'is_win': return_pct > 0,
                    'dxy_ret': row['DXY_Ret_7d']
                })

                i = exit_idx
            else:
                i += 1

    # 결과 출력
    print("\n3.1 Strategy Comparison (Equity Melt-Up Only)")
    print("-" * 70)
    print(f"{'Strategy':<25} {'N':<6} {'WR':<8} {'Avg Ret':<12} {'Total Ret'}")
    print("-" * 70)

    for strat_name, strat in strategies.items():
        trades = strat['trades']
        if trades:
            wins = sum(1 for t in trades if t['is_win'])
            wr = wins / len(trades)
            avg_ret = np.mean([t['return'] for t in trades])
            total_ret = np.prod([1 + t['return'] for t in trades]) - 1

            print(f"{strat_name:<25} {len(trades):<6} {wr:.1%}    {avg_ret*100:+.2f}%       {total_ret*100:+.1f}%")
        else:
            print(f"{strat_name:<25} 0")

    # DXY_weak_short 개별 거래
    if strategies['DXY_weak_short']['trades']:
        print("\n3.2 DXY Weak → Short BTC Trades")
        print("-" * 70)
        for t in strategies['DXY_weak_short']['trades']:
            status = "WIN " if t['is_win'] else "LOSS"
            print(f"  {t['date']}: {t['return']*100:+.1f}% ({status}) | DXY: {t['dxy_ret']*100:+.1f}%")

    return strategies


# =============================================================================
# 4. 종합 전략 제안
# =============================================================================

def propose_integrated_strategy(
    correlation_results: Dict,
    combined_results: Dict,
    contrarian_results: Dict
):
    """분석 결과 기반 통합 전략 제안"""
    print("\n" + "=" * 70)
    print("4. INTEGRATED STRATEGY PROPOSAL")
    print("=" * 70)

    # 상관관계 해석
    overall_corr = correlation_results.get('overall_corr', 0)
    co_occ = correlation_results.get('co_occurrence', {})

    print("\n4.1 Key Findings")
    print("-" * 70)

    # 1. 신호 독립성
    if co_occ:
        ratio = co_occ['both'] / co_occ['expected'] if co_occ['expected'] > 0 else 0
        if ratio > 1.5:
            print(f"  • Gold/DXY signals are REDUNDANT (co-occur {ratio:.1f}x expected)")
            print("    → Use EITHER signal, not both")
            signal_strategy = "EITHER"
        elif ratio < 0.67:
            print(f"  • Gold/DXY signals are COMPLEMENTARY (co-occur {ratio:.1f}x expected)")
            print("    → Combined signal is rare but powerful")
            signal_strategy = "COMBINED"
        else:
            print(f"  • Gold/DXY signals are INDEPENDENT (co-occur {ratio:.1f}x expected)")
            print("    → Can use both for coverage")
            signal_strategy = "BOTH"

    # 2. 복합 신호 성과
    combined_trades = combined_results.get('combined', [])
    either_trades = combined_results.get('either', [])

    if combined_trades:
        comb_wr = sum(1 for t in combined_trades if t['is_win']) / len(combined_trades)
        print(f"\n  • Combined signal (Gold AND DXY): {len(combined_trades)} trades, {comb_wr:.0%} WR")
    if either_trades:
        either_wr = sum(1 for t in either_trades if t['is_win']) / len(either_trades)
        print(f"  • Either signal (Gold OR DXY): {len(either_trades)} trades, {either_wr:.0%} WR")

    # 3. Melt-Up 반대 전략
    short_strat = contrarian_results.get('DXY_weak_short', {})
    if short_strat.get('trades'):
        short_wr = sum(1 for t in short_strat['trades'] if t['is_win']) / len(short_strat['trades'])
        print(f"\n  • Melt-Up + DXY weak → Short: {len(short_strat['trades'])} trades, {short_wr:.0%} WR")

    # 통합 전략 제안
    print("\n4.2 Proposed Strategy")
    print("-" * 70)

    print("""
    ┌────────────────────────────────────────────────────────────────────┐
    │  REGIME-CONDITIONAL DXY-GOLD-BTC STRATEGY                          │
    ├────────────────────────────────────────────────────────────────────┤
    │                                                                    │
    │  Gold Safe-Haven Fortress:                                         │
    │    IF Gold +3% (7d) OR DXY -1.5% (7d):                            │
    │      → BTC LONG after 3d lag, hold 7d                             │
    │      → Size: 10% (single signal) / 15% (both signals)             │
    │                                                                    │
    │  Equity Complacency Melt-Up:                                       │
    │    IF DXY -1.5% (7d):                                              │
    │      → BTC SHORT after 2d lag, hold 7d                            │
    │      → Size: 5% (experimental)                                     │
    │                                                                    │
    │  Other Regimes:                                                    │
    │    → CASH / DCA only                                              │
    │                                                                    │
    └────────────────────────────────────────────────────────────────────┘
    """)

    return {
        'signal_strategy': signal_strategy if 'signal_strategy' in dir() else 'UNKNOWN',
        'correlation': overall_corr
    }


def main():
    print("=" * 70)
    print("GOLD ↔ DXY COMBINED ANALYSIS")
    print("=" * 70)

    # 데이터 로드
    date_to_regime = load_regime_data()
    data = fetch_data("2017-01-01", "2024-12-31")

    # 1. 상관관계 분석
    corr_results = analyze_gold_dxy_correlation(data)

    # 2. 복합 신호 테스트
    combined_results = test_combined_signals(data.copy(), date_to_regime)

    # 3. Melt-Up 반대 전략
    contrarian_results = test_meltup_contrarian(data.copy(), date_to_regime)

    # 4. 통합 전략 제안
    proposal = propose_integrated_strategy(corr_results, combined_results, contrarian_results)

    return {
        'correlation': corr_results,
        'combined': combined_results,
        'contrarian': contrarian_results,
        'proposal': proposal
    }


if __name__ == "__main__":
    results = main()
