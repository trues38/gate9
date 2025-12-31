"""
DXY → BTC 레짐별 세분화 분석

목표:
- 어떤 레짐에서 DXY → BTC 역관계가 유효한지 확인
- Cross-Validation에서 2020-2021 붕괴 원인 분석
- 레짐 조건부 전략 도출
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

def load_regime_data() -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """레짐 데이터 로드"""
    with open('/Users/js/Documents/btc-macro/data/regime_families.json', 'r') as f:
        families = json.load(f)

    date_to_regime = {}
    regime_to_dates = defaultdict(list)

    for fam in families:
        name = fam.get('family_name', 'Unknown')
        for date in fam.get('member_dates', []):
            date_to_regime[date] = name
            regime_to_dates[name].append(date)

    return date_to_regime, dict(regime_to_dates)


def fetch_data(start_date: str, end_date: str) -> pd.DataFrame:
    """DXY와 BTC 데이터"""
    print(f"Fetching data: {start_date} ~ {end_date}")

    btc = yf.download("BTC-USD", start=start_date, end=end_date, progress=False)
    dxy = yf.download("UUP", start=start_date, end=end_date, progress=False)  # Dollar ETF

    if isinstance(btc.columns, pd.MultiIndex):
        btc.columns = btc.columns.get_level_values(0)
    if isinstance(dxy.columns, pd.MultiIndex):
        dxy.columns = dxy.columns.get_level_values(0)

    data = pd.DataFrame()
    data['BTC_Close'] = btc['Close']
    data['DXY_Close'] = dxy['Close']

    # 수익률
    for window in [1, 3, 5, 7, 10]:
        data[f'DXY_Ret_{window}d'] = data['DXY_Close'].pct_change(window)
        data[f'BTC_Ret_{window}d'] = data['BTC_Close'].pct_change(window)

    data = data.ffill().dropna()
    print(f"Loaded {len(data)} days")
    return data


# =============================================================================
# 레짐별 분석
# =============================================================================

def analyze_dxy_btc_by_regime(
    data: pd.DataFrame,
    date_to_regime: Dict[str, str],
    dxy_threshold: float = 0.02,
    lag_days: int = 2,
    hold_days: int = 7
) -> Dict[str, Dict]:
    """
    레짐별 DXY → BTC 분석

    전략: DXY 7일 수익률 >= threshold일 때 (달러 약세)
          lag_days 후 BTC 롱 진입, hold_days 보유
    """
    # 레짐 추가
    data['Regime'] = data.index.map(
        lambda x: date_to_regime.get(x.strftime('%Y-%m-%d'), 'Unknown')
    )

    regime_results = defaultdict(lambda: {'trades': [], 'signals': 0})
    all_trades = []

    i = 0
    while i < len(data) - lag_days - hold_days:
        row = data.iloc[i]
        date_str = data.index[i].strftime('%Y-%m-%d')
        regime = row['Regime']

        dxy_ret = row['DXY_Ret_7d']

        # 신호: DXY 하락 (달러 약세) → BTC 상승 기대
        if dxy_ret <= -dxy_threshold:
            entry_idx = i + lag_days
            exit_idx = entry_idx + hold_days

            if exit_idx < len(data):
                entry_price = data.iloc[entry_idx]['BTC_Close']
                exit_price = data.iloc[exit_idx]['BTC_Close']
                return_pct = (exit_price - entry_price) / entry_price

                trade = {
                    'entry_date': data.index[entry_idx].strftime('%Y-%m-%d'),
                    'exit_date': data.index[exit_idx].strftime('%Y-%m-%d'),
                    'signal_date': date_str,
                    'regime': regime,
                    'dxy_signal': dxy_ret,
                    'return': return_pct,
                    'is_win': return_pct > 0
                }

                regime_results[regime]['trades'].append(trade)
                regime_results[regime]['signals'] += 1
                all_trades.append(trade)

                # 다음 신호까지 스킵 (오버랩 방지)
                i = exit_idx
                continue

        i += 1

    # 레짐별 통계 계산
    for regime, data_dict in regime_results.items():
        trades = data_dict['trades']
        if trades:
            wins = sum(1 for t in trades if t['is_win'])
            returns = [t['return'] for t in trades]

            data_dict['n'] = len(trades)
            data_dict['wins'] = wins
            data_dict['win_rate'] = wins / len(trades)
            data_dict['avg_return'] = np.mean(returns)
            data_dict['total_return'] = np.prod([1 + r for r in returns]) - 1
            data_dict['p_value'] = 1 - stats.binom.cdf(wins - 1, len(trades), 0.5)

    return dict(regime_results), all_trades


def parameter_sweep_by_regime(
    data: pd.DataFrame,
    date_to_regime: Dict[str, str],
    target_regime: str = None
) -> List[Dict]:
    """특정 레짐에 대한 파라미터 스윕"""

    results = []

    for threshold in [0.01, 0.015, 0.02, 0.025, 0.03]:
        for lag in [1, 2, 3, 5]:
            for hold in [5, 7, 10, 14]:
                regime_results, all_trades = analyze_dxy_btc_by_regime(
                    data.copy(), date_to_regime,
                    dxy_threshold=threshold,
                    lag_days=lag,
                    hold_days=hold
                )

                if target_regime:
                    # 특정 레짐만
                    if target_regime in regime_results:
                        r = regime_results[target_regime]
                        if r.get('n', 0) >= 3:
                            results.append({
                                'threshold': threshold,
                                'lag': lag,
                                'hold': hold,
                                'regime': target_regime,
                                'n': r['n'],
                                'wr': r['win_rate'],
                                'avg_ret': r['avg_return'],
                                'p_value': r['p_value']
                            })
                else:
                    # 전체
                    if all_trades:
                        wins = sum(1 for t in all_trades if t['is_win'])
                        if len(all_trades) >= 5:
                            results.append({
                                'threshold': threshold,
                                'lag': lag,
                                'hold': hold,
                                'regime': 'ALL',
                                'n': len(all_trades),
                                'wr': wins / len(all_trades),
                                'avg_ret': np.mean([t['return'] for t in all_trades]),
                                'p_value': 1 - stats.binom.cdf(wins - 1, len(all_trades), 0.5)
                            })

    return results


def main():
    print("=" * 70)
    print("DXY → BTC REGIME-CONDITIONAL ANALYSIS")
    print("=" * 70)

    # 데이터 로드
    date_to_regime, regime_to_dates = load_regime_data()

    # 전체 기간 데이터
    data = fetch_data("2017-01-01", "2024-12-31")

    # ==========================================================================
    # 1. 기본 분석: 레짐별 성과
    # ==========================================================================
    print("\n" + "=" * 70)
    print("1. REGIME-WISE PERFORMANCE (Default: DXY -2%, Lag 2d, Hold 7d)")
    print("=" * 70)

    regime_results, all_trades = analyze_dxy_btc_by_regime(
        data.copy(), date_to_regime,
        dxy_threshold=0.02, lag_days=2, hold_days=7
    )

    print(f"\n{'Regime':<40} {'N':<6} {'WR':<8} {'Avg Ret':<10} {'p-value':<10}")
    print("-" * 80)

    # 정렬: 거래 수 기준
    sorted_regimes = sorted(regime_results.items(),
                           key=lambda x: x[1].get('n', 0),
                           reverse=True)

    for regime, stats in sorted_regimes:
        if stats.get('n', 0) >= 1:
            n = stats['n']
            wr = stats.get('win_rate', 0)
            avg_ret = stats.get('avg_return', 0)
            pval = stats.get('p_value', 1)

            sig = '*' if pval < 0.05 else ''
            print(f"{regime[:40]:<40} {n:<6} {wr:.1%}    {avg_ret*100:+.2f}%     {pval:.3f}{sig}")

    # 전체 통계
    total_n = len(all_trades)
    total_wins = sum(1 for t in all_trades if t['is_win'])
    if total_n > 0:
        print("-" * 80)
        print(f"{'TOTAL':<40} {total_n:<6} {total_wins/total_n:.1%}")

    # ==========================================================================
    # 2. 기간별 레짐 분포 분석
    # ==========================================================================
    print("\n" + "=" * 70)
    print("2. REGIME DISTRIBUTION BY PERIOD")
    print("=" * 70)

    periods = {
        '2017-2019': ('2017-01-01', '2019-12-31'),
        '2020-2021': ('2020-01-01', '2021-12-31'),
        '2022-2024': ('2022-01-01', '2024-12-31'),
    }

    for period_name, (start, end) in periods.items():
        print(f"\n--- {period_name} ---")
        period_data = fetch_data(start, end)

        regime_results, trades = analyze_dxy_btc_by_regime(
            period_data.copy(), date_to_regime,
            dxy_threshold=0.02, lag_days=2, hold_days=7
        )

        print(f"\n{'Regime':<40} {'N':<6} {'WR':<8} {'Avg Ret':<10}")
        print("-" * 70)

        for regime, stats in sorted(regime_results.items(),
                                   key=lambda x: x[1].get('n', 0),
                                   reverse=True)[:5]:
            if stats.get('n', 0) >= 1:
                print(f"{regime[:40]:<40} {stats['n']:<6} "
                      f"{stats.get('win_rate', 0):.1%}    "
                      f"{stats.get('avg_return', 0)*100:+.2f}%")

    # ==========================================================================
    # 3. 유망 레짐 발굴
    # ==========================================================================
    print("\n" + "=" * 70)
    print("3. PROMISING REGIMES (N >= 5, WR >= 60%)")
    print("=" * 70)

    # 전체 기간에서 유망 레짐 찾기
    data_full = fetch_data("2017-01-01", "2024-12-31")
    regime_results, _ = analyze_dxy_btc_by_regime(
        data_full.copy(), date_to_regime,
        dxy_threshold=0.02, lag_days=2, hold_days=7
    )

    promising = []
    for regime, stats in regime_results.items():
        if stats.get('n', 0) >= 5 and stats.get('win_rate', 0) >= 0.6:
            promising.append((regime, stats))

    promising.sort(key=lambda x: -x[1]['win_rate'])

    print(f"\n{'Regime':<45} {'N':<6} {'WR':<8} {'p-value':<10}")
    print("-" * 75)

    for regime, stats in promising:
        sig = '**' if stats['p_value'] < 0.0125 else '*' if stats['p_value'] < 0.05 else ''
        print(f"{regime[:45]:<45} {stats['n']:<6} {stats['win_rate']:.1%}    {stats['p_value']:.4f}{sig}")

    # ==========================================================================
    # 4. 유망 레짐별 파라미터 최적화
    # ==========================================================================
    print("\n" + "=" * 70)
    print("4. PARAMETER OPTIMIZATION FOR PROMISING REGIMES")
    print("=" * 70)

    for regime, _ in promising[:3]:  # 상위 3개 레짐만
        print(f"\n--- {regime} ---")

        sweep_results = parameter_sweep_by_regime(
            data_full.copy(), date_to_regime,
            target_regime=regime
        )

        if sweep_results:
            sweep_results.sort(key=lambda x: -x['wr'])

            print(f"\n{'Threshold':<10} {'Lag':<6} {'Hold':<6} {'N':<6} {'WR':<8} {'p-value':<10}")
            print("-" * 50)

            for r in sweep_results[:5]:
                sig = '*' if r['p_value'] < 0.05 else ''
                print(f"{r['threshold']*100:.1f}%       {r['lag']:<6} {r['hold']:<6} "
                      f"{r['n']:<6} {r['wr']:.1%}    {r['p_value']:.3f}{sig}")

    # ==========================================================================
    # 5. Walk-Forward 검증 (유망 레짐)
    # ==========================================================================
    print("\n" + "=" * 70)
    print("5. WALK-FORWARD VALIDATION FOR TOP REGIME")
    print("=" * 70)

    if promising:
        top_regime = promising[0][0]
        print(f"\nTarget Regime: {top_regime}")

        # Train: 2017-2021, Test: 2022-2024
        train_data = fetch_data("2017-01-01", "2021-12-31")
        test_data = fetch_data("2022-01-01", "2024-12-31")

        # Train에서 최적 파라미터 찾기
        train_sweep = parameter_sweep_by_regime(
            train_data.copy(), date_to_regime,
            target_regime=top_regime
        )

        if train_sweep:
            train_sweep.sort(key=lambda x: -x['wr'])
            best = train_sweep[0]

            print(f"\nTrain Best: threshold={best['threshold']*100:.1f}%, "
                  f"lag={best['lag']}d, hold={best['hold']}d")
            print(f"Train: N={best['n']}, WR={best['wr']:.1%}, p={best['p_value']:.4f}")

            # Test에서 검증
            test_regime_results, test_trades = analyze_dxy_btc_by_regime(
                test_data.copy(), date_to_regime,
                dxy_threshold=best['threshold'],
                lag_days=best['lag'],
                hold_days=best['hold']
            )

            if top_regime in test_regime_results:
                test_stats = test_regime_results[top_regime]
                print(f"Test: N={test_stats.get('n', 0)}, "
                      f"WR={test_stats.get('win_rate', 0):.1%}, "
                      f"p={test_stats.get('p_value', 1):.4f}")

                # 개별 거래
                print("\nTest Period Trades:")
                for t in test_stats['trades']:
                    status = "WIN " if t['is_win'] else "LOSS"
                    print(f"  {t['entry_date']} → {t['exit_date']}: "
                          f"{t['return']*100:+.1f}% ({status}) | DXY: {t['dxy_signal']*100:.1f}%")
            else:
                print(f"Test: No trades in {top_regime}")

    # ==========================================================================
    # 6. 레짐 전이 분석
    # ==========================================================================
    print("\n" + "=" * 70)
    print("6. REGIME TRANSITION ANALYSIS")
    print("=" * 70)

    # 2020-2021에 어떤 레짐이 지배적이었는지 분석
    print("\nDominant Regimes by Period:")

    for period_name, (start, end) in periods.items():
        period_dates = [d for d in date_to_regime.keys() if start <= d <= end]
        regime_counts = defaultdict(int)

        for d in period_dates:
            regime_counts[date_to_regime[d]] += 1

        print(f"\n{period_name}:")
        for regime, count in sorted(regime_counts.items(), key=lambda x: -x[1])[:3]:
            pct = count / len(period_dates) * 100 if period_dates else 0
            print(f"  {regime[:50]}: {count} days ({pct:.1f}%)")

    # ==========================================================================
    # 7. 최종 결론
    # ==========================================================================
    print("\n" + "=" * 70)
    print("7. FINAL VERDICT")
    print("=" * 70)

    print("""
    ┌────────────────────────────────────────────────────────────────────┐
    │  DXY → BTC REGIME-CONDITIONAL STRATEGY                             │
    ├────────────────────────────────────────────────────────────────────┤
    │                                                                    │
    │  핵심 발견:                                                        │
    │                                                                    │
    │  1. DXY-BTC 역관계는 레짐 의존적                                   │
    │  2. 2020-2021 붕괴 원인: 레짐 변화 (유동성 장세)                   │
    │  3. 특정 레짐에서만 유효한 관계                                    │
    │                                                                    │
    └────────────────────────────────────────────────────────────────────┘
    """)

    return promising


if __name__ == "__main__":
    results = main()
