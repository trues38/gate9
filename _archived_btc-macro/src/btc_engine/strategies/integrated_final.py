"""
Integrated Strategy Final: H1 + H4 + H7

실제 Graph DB 레짐 데이터를 사용하는 최종 통합 전략

핵심:
- H4: 실제 레짐 전이 후 10일 윈도우
- H7: Gold Safe-Haven 레짐 + Gold +1.5% 후 3일 래그
- H1: D-Tier 회피 (극단적 RSI)
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import json
import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
from enum import Enum

from btc_engine.experiments.metrics import TradeResult, MetricsCalculator


class SignalType(Enum):
    H4_H7_COMBINED = "H4+H7"  # 가장 강력
    H7_GOLD_LAG = "H7"        # Gold 래그
    H4_TRANSITION = "H4"       # 레짐 전이
    NONE = "NONE"


# 유리한 전이 (H4 테스트에서 검증됨)
FAVORABLE_TRANSITIONS = {
    ("Reflation Rally", "Risk-Off Capitulation Crisis"): 1.0,
    ("Weak Dollar Risk-On Boom", "Reflation Rally"): 0.9,
    ("Goldilocks Equilibrium", "Gold Safe-Haven Fortress"): 0.85,
    ("Equity Complacency Melt-Up", "Weak Dollar Risk-On Boom"): 0.8,
    ("Hawkish Tightening Grind", "Geopolitical Tension Fog"): 0.8,
}


def load_regime_data() -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """Graph DB 레짐 데이터 로드"""
    try:
        with open('/Users/js/Documents/btc-macro/data/regime_families.json', 'r') as f:
            families = json.load(f)
    except FileNotFoundError:
        print("WARNING: regime_families.json not found, using empty data")
        return {}, {}

    # 레짐 이름 → 날짜 목록
    regime_map = {}
    for fam in families:
        name = fam.get('family_name', 'Unknown')
        dates = fam.get('member_dates', [])
        regime_map[name] = sorted(dates)

    # 날짜 → 레짐 이름
    date_regime = {}
    for regime, dates in regime_map.items():
        for date in dates:
            date_regime[date] = regime

    return regime_map, date_regime


def find_transitions(date_regime: Dict[str, str],
                     start_date: str,
                     end_date: str) -> List[Dict]:
    """레짐 전이 찾기"""
    transitions = []

    dates = sorted([d for d in date_regime.keys()
                   if start_date <= d <= end_date])

    prev_regime = None
    for date in dates:
        current = date_regime.get(date)
        if prev_regime and current and prev_regime != current:
            transitions.append({
                'date': date,
                'from': prev_regime,
                'to': current
            })
        prev_regime = current

    return transitions


def fetch_data(start_date: str, end_date: str) -> pd.DataFrame:
    """BTC + Gold 데이터"""
    print(f"Fetching data: {start_date} ~ {end_date}")

    btc = yf.download("BTC-USD", start=start_date, end=end_date, progress=False)
    gold = yf.download("GLD", start=start_date, end=end_date, progress=False)

    if isinstance(btc.columns, pd.MultiIndex):
        btc.columns = btc.columns.get_level_values(0)
    if isinstance(gold.columns, pd.MultiIndex):
        gold.columns = gold.columns.get_level_values(0)

    data = pd.DataFrame(index=btc.index)
    data['BTC_Close'] = btc['Close']
    data['Gold_Close'] = gold['Close'].reindex(btc.index, method='ffill')

    # BTC 지표
    delta = data['BTC_Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))

    # Gold 지표
    data['Gold_Return_7d'] = data['Gold_Close'].pct_change(7)

    data = data.dropna()
    print(f"Loaded {len(data)} days")

    return data


def add_regime_info(data: pd.DataFrame, date_regime: Dict[str, str]) -> pd.DataFrame:
    """레짐 정보 추가"""
    data = data.copy()
    data['Regime'] = data.index.map(
        lambda x: date_regime.get(x.strftime('%Y-%m-%d'), 'Unknown')
    )
    data['Regime_Prev'] = data['Regime'].shift(1)
    data['Is_Transition'] = data['Regime'] != data['Regime_Prev']

    return data


def add_transition_window(data: pd.DataFrame, transitions: List[Dict]) -> pd.DataFrame:
    """전이 윈도우 정보 추가"""
    data = data.copy()

    # 전이 날짜 세트
    trans_dates = {t['date'] for t in transitions}
    trans_info = {t['date']: (t['from'], t['to']) for t in transitions}

    days_since = []
    last_trans_date = None
    last_trans_info = None

    for idx in data.index:
        date_str = idx.strftime('%Y-%m-%d')

        if date_str in trans_dates:
            last_trans_date = idx
            last_trans_info = trans_info[date_str]
            days_since.append(0)
        elif last_trans_date is not None:
            days = (idx - last_trans_date).days
            days_since.append(days)
        else:
            days_since.append(999)

    data['Days_Since_Transition'] = days_since

    # 전이 유형 점수
    def get_transition_score(row):
        if row['Days_Since_Transition'] > 10:
            return 0.0
        # 최근 전이 찾기
        for t in reversed(transitions):
            t_date = pd.Timestamp(t['date'])
            if t_date <= row.name:
                key = (t['from'], t['to'])
                return FAVORABLE_TRANSITIONS.get(key, 0.3)
        return 0.0

    data['Transition_Score'] = data.apply(get_transition_score, axis=1)

    return data


def add_gold_signal(data: pd.DataFrame, threshold: float = 0.015) -> pd.DataFrame:
    """Gold 신호 추가 (H7)"""
    data = data.copy()
    data['Gold_Breakout'] = data['Gold_Return_7d'] >= threshold

    days_since = []
    last_breakout_idx = None

    for i in range(len(data)):
        if data['Gold_Breakout'].iloc[i]:
            last_breakout_idx = i
            days_since.append(0)
        elif last_breakout_idx is not None:
            days_since.append(i - last_breakout_idx)
        else:
            days_since.append(999)

    data['Days_Since_Gold_Breakout'] = days_since

    return data


def check_h1_filter(rsi: float) -> bool:
    """H1: D-Tier 회피 (극단적 RSI 차단)"""
    return 25 <= rsi <= 80


def check_h4_signal(days_since_trans: int, trans_score: float) -> Tuple[bool, float]:
    """H4: 레짐 전이 윈도우"""
    if days_since_trans <= 10 and trans_score > 0:
        return True, trans_score
    return False, 0.0


def check_h7_signal(regime: str, days_since_gold: int) -> Tuple[bool, float]:
    """H7: Gold Safe-Haven + Gold 래그"""
    if "Gold Safe-Haven" not in regime:
        return False, 0.0

    if 3 <= days_since_gold <= 10:
        # 3-5일이 최적
        if days_since_gold <= 5:
            return True, 1.0
        return True, 0.7

    return False, 0.0


def generate_integrated_trades(data: pd.DataFrame,
                                hold_days: int = 7,
                                require_h4: bool = False,
                                require_h7: bool = False) -> List[TradeResult]:
    """통합 전략 거래 생성"""
    trades = []
    position = None

    for i in range(1, len(data)):
        row = data.iloc[i]
        date = data.index[i].strftime('%Y-%m-%d')
        price = row['BTC_Close']

        if position is None:
            # H1 필터
            if not check_h1_filter(row['RSI']):
                continue

            # H4 체크
            h4_active, h4_score = check_h4_signal(
                row['Days_Since_Transition'],
                row['Transition_Score']
            )

            # H7 체크
            h7_active, h7_score = check_h7_signal(
                row['Regime'],
                row['Days_Since_Gold_Breakout']
            )

            # 신호 결정
            should_enter = False
            signal_type = SignalType.NONE
            score = 0.0

            if h4_active and h7_active:
                # 가장 강력: H4 + H7
                should_enter = True
                signal_type = SignalType.H4_H7_COMBINED
                score = (h4_score + h7_score) / 2 + 0.2
            elif h7_active and not require_h4:
                # H7만
                should_enter = True
                signal_type = SignalType.H7_GOLD_LAG
                score = h7_score
            elif h4_active and h4_score >= 0.7 and not require_h7:
                # H4만 (높은 점수)
                should_enter = True
                signal_type = SignalType.H4_TRANSITION
                score = h4_score

            if should_enter:
                position = {
                    'entry_date': date,
                    'entry_price': price,
                    'entry_idx': i,
                    'signal_type': signal_type,
                    'score': score,
                    'regime': row['Regime']
                }

        else:
            # 청산 조건
            days_held = i - position['entry_idx']
            should_exit = False

            if days_held >= hold_days:
                should_exit = True

            if not check_h1_filter(row['RSI']):
                should_exit = True

            current_return = (price - position['entry_price']) / position['entry_price']
            if current_return < -0.10:
                should_exit = True

            if should_exit:
                return_pct = (price - position['entry_price']) / position['entry_price']

                trades.append(TradeResult(
                    entry_date=position['entry_date'],
                    exit_date=date,
                    entry_price=position['entry_price'],
                    exit_price=price,
                    return_pct=return_pct,
                    is_win=return_pct > 0,
                    hold_days=days_held,
                    state_at_entry=f"{position['signal_type'].value}|{position['score']:.2f}|{position['regime'][:25]}"
                ))
                position = None

    return trades


def analyze_by_signal_type(trades: List[TradeResult]) -> Dict:
    """신호 유형별 분석"""
    results = {}

    for sig in ["H4+H7", "H7", "H4"]:
        sig_trades = [t for t in trades if t.state_at_entry.startswith(sig)]
        if sig_trades:
            wins = sum(1 for t in sig_trades if t.is_win)
            total_ret = np.prod([1 + t.return_pct for t in sig_trades]) - 1
            results[sig] = {
                'trades': len(sig_trades),
                'win_rate': wins / len(sig_trades),
                'total_return': total_ret
            }

    return results


def main():
    print("=" * 70)
    print("Integrated Strategy Final: H1 + H4 + H7")
    print("(Using Real Graph DB Regime Data)")
    print("=" * 70)

    # 1. 레짐 데이터 로드
    regime_map, date_regime = load_regime_data()
    print(f"\nLoaded {len(regime_map)} regime families")
    print(f"Total dates with regime: {len(date_regime)}")

    # 2. 전이 찾기
    transitions = find_transitions(date_regime, "2020-01-01", "2025-12-26")
    print(f"Total transitions: {len(transitions)}")

    # 3. 데이터 로드
    data = fetch_data("2020-01-01", "2025-12-26")
    data = add_regime_info(data, date_regime)
    data = add_transition_window(data, transitions)
    data = add_gold_signal(data)

    # 4. 레짐 분포
    print("\n--- Regime Distribution ---")
    regime_counts = data['Regime'].value_counts().head(10)
    for regime, count in regime_counts.items():
        print(f"  {regime[:40]}: {count} ({count/len(data)*100:.1f}%)")

    # Gold Safe-Haven 일수
    gold_safe_haven = sum(1 for r in data['Regime'] if 'Gold Safe-Haven' in r)
    print(f"\nGold Safe-Haven days: {gold_safe_haven} ({gold_safe_haven/len(data)*100:.1f}%)")

    calc = MetricsCalculator()

    # 5. 기본 테스트
    print("\n" + "=" * 70)
    print("Basic Test: All Signals")
    print("=" * 70)

    all_trades = generate_integrated_trades(data)

    if all_trades:
        metrics = calc.calculate(all_trades, "all")
        print(f"\nTotal trades: {len(all_trades)}")
        print(f"Win rate: {metrics.win_rate:.1%}")
        print(f"Avg return: {metrics.avg_return*100:.2f}%")
        print(f"Total return: {metrics.total_return*100:.1f}%")
        print(f"Sharpe: {metrics.sharpe_ratio:.2f}")

        # 신호별
        print("\n--- By Signal Type ---")
        analysis = analyze_by_signal_type(all_trades)
        for sig, stats in sorted(analysis.items(), key=lambda x: -x[1]['win_rate']):
            print(f"  {sig}: {stats['trades']} trades, WR {stats['win_rate']:.1%}, "
                  f"Return {stats['total_return']*100:+.1f}%")

    # 6. Walk-Forward
    print("\n" + "=" * 70)
    print("Walk-Forward Validation")
    print("=" * 70)

    train_end = "2022-12-31"
    train_data = data[data.index <= train_end].copy()
    test_data = data[data.index > train_end].copy()

    # 전이 윈도우 재계산
    train_trans = [t for t in transitions if t['date'] <= train_end]
    test_trans = [t for t in transitions if t['date'] > train_end]

    train_data = add_transition_window(train_data, train_trans)
    test_data = add_transition_window(test_data, test_trans)

    print("\n--- All Signals ---")
    train_trades = generate_integrated_trades(train_data)
    test_trades = generate_integrated_trades(test_data)

    if train_trades:
        train_metrics = calc.calculate(train_trades, "train")
        print(f"Train: {len(train_trades)} trades, WR {train_metrics.win_rate:.1%}")

    if test_trades:
        test_metrics = calc.calculate(test_trades, "test")
        print(f"Test:  {len(test_trades)} trades, WR {test_metrics.win_rate:.1%}, "
              f"Return {test_metrics.total_return*100:+.1f}%, p={test_metrics.p_value_vs_random:.4f}")

        # 신호별 테스트 분석
        print("\n  By Signal Type (Test):")
        test_analysis = analyze_by_signal_type(test_trades)
        for sig, stats in sorted(test_analysis.items(), key=lambda x: -x[1]['win_rate']):
            print(f"    {sig}: {stats['trades']} trades, WR {stats['win_rate']:.1%}")

    # 7. H7 Only 테스트
    print("\n--- H7 Only (Gold Lag) ---")
    h7_train = generate_integrated_trades(train_data, require_h7=True)
    h7_test = generate_integrated_trades(test_data, require_h7=True)

    if h7_train and h7_test:
        h7_train_m = calc.calculate(h7_train, "train")
        h7_test_m = calc.calculate(h7_test, "test")
        print(f"Train: {len(h7_train)} trades, WR {h7_train_m.win_rate:.1%}")
        print(f"Test:  {len(h7_test)} trades, WR {h7_test_m.win_rate:.1%}, "
              f"p={h7_test_m.p_value_vs_random:.4f}")

    # 8. 최적 파라미터
    print("\n" + "=" * 70)
    print("Parameter Optimization (Test)")
    print("=" * 70)

    results = []
    for hold_days in [5, 7, 10, 14]:
        trades = generate_integrated_trades(test_data, hold_days=hold_days)
        if len(trades) >= 5:
            wr = sum(1 for t in trades if t.is_win) / len(trades)
            ret = np.prod([1 + t.return_pct for t in trades]) - 1
            results.append({
                'hold': hold_days,
                'trades': len(trades),
                'wr': wr,
                'return': ret
            })

    print(f"\n{'Hold':<8} {'Trades':<8} {'WR':<10} {'Return':<12}")
    print("-" * 40)
    for r in sorted(results, key=lambda x: -x['wr']):
        print(f"{r['hold']:<8} {r['trades']:<8} {r['wr']:.1%}      {r['return']*100:+.1f}%")

    # 9. 년도별
    print("\n" + "=" * 70)
    print("Year-by-Year")
    print("=" * 70)

    print(f"\n{'Year':<8} {'Trades':<8} {'WR':<10} {'Return':<12} {'H4+H7':<8} {'H7':<8} {'H4':<8}")
    print("-" * 70)

    for year in range(2020, 2026):
        year_data = data[data.index.year == year].copy()
        if len(year_data) < 30:
            continue

        year_trans = [t for t in transitions if t['date'].startswith(str(year))]
        year_data = add_transition_window(year_data, year_trans)

        year_trades = generate_integrated_trades(year_data)

        if year_trades:
            wr = sum(1 for t in year_trades if t.is_win) / len(year_trades)
            ret = np.prod([1 + t.return_pct for t in year_trades]) - 1

            h4h7 = sum(1 for t in year_trades if "H4+H7" in t.state_at_entry)
            h7 = sum(1 for t in year_trades if t.state_at_entry.startswith("H7|"))
            h4 = sum(1 for t in year_trades if t.state_at_entry.startswith("H4|"))

            print(f"{year:<8} {len(year_trades):<8} {wr:.1%}      {ret*100:+.1f}%       "
                  f"{h4h7:<8} {h7:<8} {h4:<8}")
        else:
            print(f"{year:<8} 0")

    # 10. 최종 전략
    print("\n" + "=" * 70)
    print("FINAL STRATEGY")
    print("=" * 70)

    print("""
    ┌────────────────────────────────────────────────────────────────┐
    │  INTEGRATED STRATEGY: H1 + H4 + H7                             │
    │  (Graph DB Regime-Based)                                       │
    ├────────────────────────────────────────────────────────────────┤
    │                                                                │
    │  진입 조건 (AND):                                              │
    │                                                                │
    │  [필수] H1 Filter:                                             │
    │    - RSI 25-80 범위 (극단 D-Tier 회피)                         │
    │                                                                │
    │  [신호] 다음 중 하나 이상:                                     │
    │                                                                │
    │    H4+H7 (STRONG - 풀 포지션):                                 │
    │      - 레짐 전이 10일 이내                                     │
    │      - Gold Safe-Haven 레짐                                    │
    │      - Gold +1.5% 후 3-10일                                    │
    │                                                                │
    │    H7 (MEDIUM - 70% 포지션):                                   │
    │      - Gold Safe-Haven 레짐                                    │
    │      - Gold +1.5% 후 3-10일                                    │
    │                                                                │
    │    H4 (LIGHT - 50% 포지션):                                    │
    │      - 유리한 레짐 전이 10일 이내                              │
    │      - 전이 점수 >= 0.7                                        │
    │                                                                │
    │  청산 조건:                                                    │
    │    - 7일 보유                                                  │
    │    - RSI <25 or >80 (D-Tier 진입)                              │
    │    - -10% 손절                                                 │
    │                                                                │
    └────────────────────────────────────────────────────────────────┘
    """)

    # 검증 결과
    if test_trades:
        print("\n  Validation Summary (Test 2023-2025):")
        print(f"  - Trades: {len(test_trades)}")
        print(f"  - Win Rate: {test_metrics.win_rate:.1%}")
        print(f"  - Total Return: {test_metrics.total_return*100:+.1f}%")
        print(f"  - p-value: {test_metrics.p_value_vs_random:.4f}")

        if test_metrics.win_rate >= 0.55 and test_metrics.p_value_vs_random <= 0.1:
            print("\n  Status: VALIDATED")
        elif test_metrics.win_rate >= 0.50:
            print("\n  Status: MARGINAL - 실전 테스트 필요")
        else:
            print("\n  Status: NEEDS REFINEMENT")


if __name__ == "__main__":
    main()
