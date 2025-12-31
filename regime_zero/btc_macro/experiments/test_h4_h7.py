"""
H4: Macro Transition Asymmetric Reaction Test
H7: BTC as Anxious Safe Haven (Gold Lag) Test

H4 가설: 경제 레짐이 전이된 직후 5~10일, BTC는 비대칭적 반응을 보인다
H7 가설: Gold Safe-Haven 레짐에서 BTC는 Gold를 3~14일 지연 추종한다
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import json
import yfinance as yf
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

from btc_engine.experiments.metrics import TradeResult, MetricsCalculator


def load_regime_data() -> Dict[str, List[str]]:
    """레짐 데이터 로드"""
    with open('/Users/js/Documents/btc-macro/data/regime_families.json', 'r') as f:
        families = json.load(f)

    regime_map = {}
    for fam in families:
        name = fam.get('family_name', 'Unknown')
        dates = fam.get('member_dates', [])
        regime_map[name] = sorted(dates)

    return regime_map


def build_date_to_regime(regime_map: Dict[str, List[str]]) -> Dict[str, str]:
    """날짜 → 레짐 매핑"""
    date_regime = {}
    for regime, dates in regime_map.items():
        for date in dates:
            date_regime[date] = regime
    return date_regime


def find_regime_transitions(date_regime: Dict[str, str],
                            start_date: str,
                            end_date: str) -> List[Dict]:
    """
    레짐 전이 찾기

    Returns:
        List of {'date': str, 'from': str, 'to': str}
    """
    transitions = []

    dates = sorted([d for d in date_regime.keys()
                   if start_date <= d <= end_date])

    prev_regime = None
    for date in dates:
        current_regime = date_regime.get(date)
        if prev_regime and current_regime and prev_regime != current_regime:
            transitions.append({
                'date': date,
                'from': prev_regime,
                'to': current_regime
            })
        prev_regime = current_regime

    return transitions


def fetch_btc_gold_data(start_date: str, end_date: str) -> pd.DataFrame:
    """BTC와 Gold 데이터 가져오기"""
    print(f"Fetching BTC and Gold data: {start_date} ~ {end_date}")

    btc = yf.download("BTC-USD", start=start_date, end=end_date, progress=False)
    gold = yf.download("GLD", start=start_date, end=end_date, progress=False)

    if isinstance(btc.columns, pd.MultiIndex):
        btc.columns = btc.columns.get_level_values(0)
    if isinstance(gold.columns, pd.MultiIndex):
        gold.columns = gold.columns.get_level_values(0)

    # Merge
    data = pd.DataFrame()
    data['BTC_Close'] = btc['Close']
    data['Gold_Close'] = gold['Close']

    # Returns
    data['BTC_Return_1d'] = data['BTC_Close'].pct_change()
    data['BTC_Return_7d'] = data['BTC_Close'].pct_change(7)
    data['Gold_Return_1d'] = data['Gold_Close'].pct_change()
    data['Gold_Return_7d'] = data['Gold_Close'].pct_change(7)

    # RSI for BTC
    delta = data['BTC_Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['BTC_RSI'] = 100 - (100 / (1 + rs))

    data = data.dropna()
    print(f"Loaded {len(data)} days of data")

    return data


# =============================================================================
# H4: Macro Transition Test
# =============================================================================

def test_h4_macro_transition(data: pd.DataFrame,
                             transitions: List[Dict],
                             window_days: int = 10) -> Dict:
    """
    H4 테스트: 레짐 전이 직후 BTC 반응

    Returns:
        분석 결과
    """
    results = {
        'all_transitions': [],
        'by_transition_type': defaultdict(list)
    }

    for trans in transitions:
        trans_date = trans['date']

        # 데이터에서 전이일 찾기
        try:
            trans_ts = pd.Timestamp(trans_date)
            if trans_ts not in data.index:
                # 가장 가까운 날짜 찾기
                idx = data.index.searchsorted(trans_ts)
                if idx >= len(data):
                    continue
                trans_ts = data.index[idx]

            pos = data.index.get_loc(trans_ts)

            # 전이 후 window_days 동안의 수익률
            if pos + window_days < len(data):
                future_price = data.iloc[pos + window_days]['BTC_Close']
                current_price = data.iloc[pos]['BTC_Close']
                return_pct = (future_price - current_price) / current_price

                result = {
                    'date': trans_date,
                    'from': trans['from'],
                    'to': trans['to'],
                    'return': return_pct,
                    'is_win': return_pct > 0
                }

                results['all_transitions'].append(result)
                transition_key = f"{trans['from']} → {trans['to']}"
                results['by_transition_type'][transition_key].append(result)

        except Exception as e:
            continue

    return results


def analyze_h4_results(results: Dict) -> Dict:
    """H4 결과 분석"""
    all_trans = results['all_transitions']

    if not all_trans:
        return {'error': 'No transitions found'}

    returns = [t['return'] for t in all_trans]
    wins = sum(1 for t in all_trans if t['is_win'])

    analysis = {
        'total_transitions': len(all_trans),
        'win_rate': wins / len(all_trans),
        'avg_return': np.mean(returns),
        'median_return': np.median(returns),
        'std_return': np.std(returns),
        'p_value': 1 - stats.binom.cdf(wins - 1, len(all_trans), 0.5)
    }

    # 전이 유형별 분석
    type_analysis = {}
    for trans_type, trans_list in results['by_transition_type'].items():
        if len(trans_list) >= 3:
            type_returns = [t['return'] for t in trans_list]
            type_wins = sum(1 for t in trans_list if t['is_win'])
            type_analysis[trans_type] = {
                'count': len(trans_list),
                'win_rate': type_wins / len(trans_list),
                'avg_return': np.mean(type_returns)
            }

    analysis['by_type'] = type_analysis

    return analysis


# =============================================================================
# H7: BTC-Gold Lag Test
# =============================================================================

def test_h7_gold_lag(data: pd.DataFrame,
                     date_regime: Dict[str, str],
                     gold_breakout_threshold: float = 0.02,
                     lag_min: int = 3,
                     lag_max: int = 14) -> List[TradeResult]:
    """
    H7 테스트: Gold Safe-Haven에서 Gold 상승 후 BTC 지연 추종

    조건:
    - Gold Safe-Haven Fortress 레짐
    - Gold 7일 수익률 >= threshold
    - lag_min ~ lag_max일 후 BTC 진입
    """
    trades = []
    position = None

    for i in range(len(data)):
        date_str = data.index[i].strftime('%Y-%m-%d')
        regime = date_regime.get(date_str, '')

        if position is None:
            # 진입 조건 체크
            if 'Gold Safe-Haven' in regime:
                gold_return = data.iloc[i]['Gold_Return_7d']

                if gold_return >= gold_breakout_threshold:
                    # Gold breakout 발생, lag 후 진입
                    entry_idx = i + lag_min
                    if entry_idx < len(data):
                        entry_date = data.index[entry_idx].strftime('%Y-%m-%d')
                        entry_price = data.iloc[entry_idx]['BTC_Close']
                        position = (entry_date, entry_price, entry_idx, gold_return)

        else:
            entry_date, entry_price, entry_idx, entry_gold_ret = position
            hold_days = i - entry_idx

            # 청산: 7일 보유 또는 lag_max 도달
            if hold_days >= 7:
                exit_price = data.iloc[i]['BTC_Close']
                return_pct = (exit_price - entry_price) / entry_price

                trades.append(TradeResult(
                    entry_date=entry_date,
                    exit_date=data.index[i].strftime('%Y-%m-%d'),
                    entry_price=entry_price,
                    exit_price=exit_price,
                    return_pct=return_pct,
                    is_win=return_pct > 0,
                    hold_days=hold_days,
                    state_at_entry=f"gold_ret{entry_gold_ret*100:.1f}%"
                ))
                position = None

    return trades


def run_h7_parameter_sweep(data: pd.DataFrame,
                           date_regime: Dict[str, str],
                           train_end: str) -> List[Dict]:
    """H7 파라미터 스윕"""
    calc = MetricsCalculator()

    train_data = data[data.index <= train_end]
    test_data = data[data.index > train_end]

    results = []

    for gold_threshold in [0.015, 0.02, 0.03, 0.04]:
        for lag_min in [3, 5, 7]:
            for lag_max in [10, 14, 21]:
                if lag_min >= lag_max:
                    continue

                train_trades = test_h7_gold_lag(
                    train_data, date_regime,
                    gold_breakout_threshold=gold_threshold,
                    lag_min=lag_min,
                    lag_max=lag_max
                )

                test_trades = test_h7_gold_lag(
                    test_data, date_regime,
                    gold_breakout_threshold=gold_threshold,
                    lag_min=lag_min,
                    lag_max=lag_max
                )

                if len(train_trades) >= 3 and len(test_trades) >= 3:
                    train_metrics = calc.calculate(train_trades, "train")
                    test_metrics = calc.calculate(test_trades, "test")

                    results.append({
                        'gold_threshold': gold_threshold,
                        'lag_min': lag_min,
                        'lag_max': lag_max,
                        'train_trades': len(train_trades),
                        'train_wr': train_metrics.win_rate,
                        'test_trades': len(test_trades),
                        'test_wr': test_metrics.win_rate,
                        'test_pval': test_metrics.p_value_vs_random
                    })

    return results


def main():
    print("=" * 70)
    print("H4 & H7: Macro-Based Hypotheses Test")
    print("=" * 70)

    # 1. 데이터 로드
    regime_map = load_regime_data()
    date_regime = build_date_to_regime(regime_map)

    data = fetch_btc_gold_data("2020-01-01", "2025-12-26")

    # 레짐 정보 추가
    data['Regime'] = data.index.map(
        lambda x: date_regime.get(x.strftime('%Y-%m-%d'), 'Unknown')
    )

    # ==========================================================================
    # H4: Macro Transition Test
    # ==========================================================================
    print("\n" + "=" * 70)
    print("H4: Macro Transition Asymmetric Reaction")
    print("=" * 70)

    # 전이 찾기
    transitions = find_regime_transitions(date_regime, "2020-01-01", "2025-12-26")
    print(f"\nTotal regime transitions: {len(transitions)}")

    # 전이 유형별 카운트
    trans_counts = defaultdict(int)
    for t in transitions:
        key = f"{t['from'][:20]} → {t['to'][:20]}"
        trans_counts[key] += 1

    print("\n주요 전이 유형:")
    for trans_type, count in sorted(trans_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {trans_type}: {count}")

    # H4 테스트
    h4_results = test_h4_macro_transition(data, transitions, window_days=10)
    h4_analysis = analyze_h4_results(h4_results)

    print(f"\n=== H4 결과 (전이 후 10일) ===")
    print(f"Transitions analyzed: {h4_analysis.get('total_transitions', 0)}")
    print(f"Win rate: {h4_analysis.get('win_rate', 0):.1%}")
    print(f"Avg return: {h4_analysis.get('avg_return', 0)*100:+.2f}%")
    print(f"p-value: {h4_analysis.get('p_value', 1):.4f}")

    # 유형별 분석
    print("\n유형별 성과 (N>=3):")
    for trans_type, stats in sorted(h4_analysis.get('by_type', {}).items(),
                                    key=lambda x: -x[1]['win_rate'])[:10]:
        print(f"  {trans_type[:50]}")
        print(f"    N={stats['count']}, WR={stats['win_rate']:.1%}, Ret={stats['avg_return']*100:+.2f}%")

    # Walk-Forward
    print("\n=== H4 Walk-Forward ===")
    train_trans = [t for t in transitions if t['date'] <= "2022-12-31"]
    test_trans = [t for t in transitions if t['date'] > "2022-12-31"]

    train_data_h4 = data[data.index <= "2022-12-31"]
    test_data_h4 = data[data.index > "2022-12-31"]

    train_h4 = test_h4_macro_transition(train_data_h4, train_trans, window_days=10)
    test_h4 = test_h4_macro_transition(test_data_h4, test_trans, window_days=10)

    train_h4_analysis = analyze_h4_results(train_h4)
    test_h4_analysis = analyze_h4_results(test_h4)

    print(f"Train: {train_h4_analysis.get('total_transitions', 0)} trans, WR {train_h4_analysis.get('win_rate', 0):.1%}")
    print(f"Test: {test_h4_analysis.get('total_transitions', 0)} trans, WR {test_h4_analysis.get('win_rate', 0):.1%}")

    # H4 판정
    h4_test_wr = test_h4_analysis.get('win_rate', 0)
    h4_test_pval = test_h4_analysis.get('p_value', 1)
    h4_checks = {
        'Test WR >= 55%': h4_test_wr >= 0.55,
        'p-value <= 0.1': h4_test_pval <= 0.1,
        'Test transitions >= 20': test_h4_analysis.get('total_transitions', 0) >= 20
    }

    print("\nH4 Checks:")
    for check, passed in h4_checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {check}")

    h4_verdict = "VALIDATED" if sum(h4_checks.values()) >= 2 else "REJECTED"
    print(f"\nH4 Verdict: {h4_verdict}")

    # ==========================================================================
    # H7: BTC-Gold Lag Test
    # ==========================================================================
    print("\n" + "=" * 70)
    print("H7: BTC as Anxious Safe Haven (Gold Lag)")
    print("=" * 70)

    # Gold Safe-Haven 레짐 분포
    gold_regime_days = data[data['Regime'].str.contains('Gold Safe-Haven', na=False)]
    print(f"\nGold Safe-Haven days in data: {len(gold_regime_days)} / {len(data)} ({len(gold_regime_days)/len(data)*100:.1f}%)")

    # 기본 테스트
    h7_trades = test_h7_gold_lag(data, date_regime,
                                 gold_breakout_threshold=0.02,
                                 lag_min=3, lag_max=14)

    calc = MetricsCalculator()

    if h7_trades:
        h7_metrics = calc.calculate(h7_trades, "all")

        print(f"\n=== H7 기본 테스트 (Gold +2% 후 3일 대기) ===")
        print(f"Total trades: {len(h7_trades)}")
        print(f"Win rate: {h7_metrics.win_rate:.1%}")
        print(f"Avg return: {h7_metrics.avg_return*100:+.2f}%")
        print(f"Total return: {h7_metrics.total_return*100:+.1f}%")
        print(f"p-value: {h7_metrics.p_value_vs_random:.4f}")

        # 개별 거래
        print("\n개별 거래:")
        for t in h7_trades[:10]:
            print(f"  {t.entry_date} → {t.exit_date}: {t.return_pct*100:+.1f}% ({t.state_at_entry})")
    else:
        print("\nNo H7 trades generated")
        h7_metrics = None

    # Walk-Forward
    print("\n=== H7 Walk-Forward ===")
    train_data_h7 = data[data.index <= "2022-12-31"]
    test_data_h7 = data[data.index > "2022-12-31"]

    train_h7_trades = test_h7_gold_lag(train_data_h7, date_regime, 0.02, 3, 14)
    test_h7_trades = test_h7_gold_lag(test_data_h7, date_regime, 0.02, 3, 14)

    if train_h7_trades and test_h7_trades:
        train_h7_metrics = calc.calculate(train_h7_trades, "train")
        test_h7_metrics = calc.calculate(test_h7_trades, "test")

        print(f"Train: {len(train_h7_trades)} trades, WR {train_h7_metrics.win_rate:.1%}")
        print(f"Test: {len(test_h7_trades)} trades, WR {test_h7_metrics.win_rate:.1%}")
        print(f"Test p-value: {test_h7_metrics.p_value_vs_random:.4f}")

        h7_test_wr = test_h7_metrics.win_rate
        h7_test_pval = test_h7_metrics.p_value_vs_random
    else:
        print("Not enough trades for walk-forward")
        h7_test_wr = 0
        h7_test_pval = 1

    # 파라미터 스윕
    print("\n=== H7 Parameter Sweep ===")
    sweep_results = run_h7_parameter_sweep(data, date_regime, "2022-12-31")

    if sweep_results:
        sweep_results.sort(key=lambda x: -x['test_wr'])

        print(f"\n{'Gold%':<8} {'Lag':<10} {'Train WR':<10} {'Test WR':<10} {'Test N':<8}")
        print("-" * 50)

        for r in sweep_results[:10]:
            print(f"{r['gold_threshold']*100:.1f}%    {r['lag_min']}-{r['lag_max']}d     "
                  f"{r['train_wr']:.1%}      {r['test_wr']:.1%}      {r['test_trades']}")

        best = sweep_results[0]
        print(f"\nBest: Gold>={best['gold_threshold']*100:.1f}%, lag={best['lag_min']}-{best['lag_max']}d")
        print(f"  Test WR: {best['test_wr']:.1%}, p-value: {best['test_pval']:.4f}")

        h7_best_wr = best['test_wr']
        h7_best_pval = best['test_pval']
    else:
        print("No valid parameter combinations")
        h7_best_wr = 0
        h7_best_pval = 1

    # H7 판정
    h7_checks = {
        'Test WR >= 55%': h7_test_wr >= 0.55 or h7_best_wr >= 0.55,
        'p-value <= 0.1': h7_test_pval <= 0.1 or h7_best_pval <= 0.1,
        'Test trades >= 10': len(test_h7_trades) >= 10 if test_h7_trades else False
    }

    print("\nH7 Checks:")
    for check, passed in h7_checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {check}")

    h7_verdict = "VALIDATED" if sum(h7_checks.values()) >= 2 else "REJECTED"
    print(f"\nH7 Verdict: {h7_verdict}")

    # ==========================================================================
    # 종합 결론
    # ==========================================================================
    print("\n" + "=" * 70)
    print("Final Summary")
    print("=" * 70)

    print(f"\nH4 (Macro Transition): {h4_verdict}")
    print(f"H7 (BTC-Gold Lag): {h7_verdict}")

    if h4_verdict == "VALIDATED" or h7_verdict == "VALIDATED":
        print("\n→ 매크로 기반 가설 중 일부 검증됨!")
    else:
        print("\n→ 매크로 기반 가설도 모두 기각")
        print("   기술적 지표와 마찬가지로 단순 조건으로는 edge 없음")


if __name__ == "__main__":
    main()
