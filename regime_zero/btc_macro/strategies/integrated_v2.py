"""
Integrated Strategy V2: H1 + H4 + H7

실제 검증된 로직을 그대로 사용하는 버전

H4 로직: test_h4_h7.py에서 검증된 전이 윈도우 (10일)
H7 로직: Gold +1.5% 후 3-10일 대기 (Gold Safe-Haven 레짐)
H1 로직: 극단적 RSI (<25 또는 >80) 회피

핵심: 두 신호가 겹칠 때 더 강한 진입
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from btc_engine.experiments.metrics import TradeResult, MetricsCalculator


class SignalType(Enum):
    H4_TRANSITION = "H4"
    H7_GOLD_LAG = "H7"
    H4_AND_H7 = "H4+H7"
    NONE = "NONE"


@dataclass
class Signal:
    date: str
    signal_type: SignalType
    score: float
    details: str


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI 계산"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


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

    # BTC indicators
    data['RSI'] = calculate_rsi(data['BTC_Close'])
    data['BTC_Return_1d'] = data['BTC_Close'].pct_change()
    data['Volatility'] = data['BTC_Return_1d'].rolling(20).std() * np.sqrt(365)

    # Gold indicators
    data['Gold_Return_7d'] = data['Gold_Close'].pct_change(7)

    data = data.dropna()
    print(f"Loaded {len(data)} days")

    return data


def detect_simple_regime(gold_7d: float, volatility: float) -> str:
    """
    단순 레짐 분류 (H4/H7 테스트와 동일)
    """
    if gold_7d >= 0.02:
        return "Gold Safe-Haven"
    elif gold_7d >= 0.01:
        return "Moderate Safe-Haven"
    elif volatility > 0.8:
        return "High Volatility"
    else:
        return "Normal"


def add_regime_info(data: pd.DataFrame) -> pd.DataFrame:
    """레짐 정보 추가"""
    regimes = []
    for i in range(len(data)):
        row = data.iloc[i]
        regime = detect_simple_regime(row['Gold_Return_7d'], row['Volatility'])
        regimes.append(regime)

    data['Regime'] = regimes
    data['Regime_Prev'] = data['Regime'].shift(1)
    data['Is_Transition'] = data['Regime'] != data['Regime_Prev']

    # Days since transition
    days_since = []
    last_trans_idx = None
    for i in range(len(data)):
        if data['Is_Transition'].iloc[i]:
            last_trans_idx = i
            days_since.append(0)
        elif last_trans_idx is not None:
            days_since.append(i - last_trans_idx)
        else:
            days_since.append(999)

    data['Days_Since_Transition'] = days_since

    return data


def add_gold_signal_info(data: pd.DataFrame) -> pd.DataFrame:
    """Gold 신호 정보 추가 (H7)"""
    # Gold +1.5% 이상 = 신호
    data['Gold_Signal'] = data['Gold_Return_7d'] >= 0.015

    days_since = []
    last_signal_idx = None
    for i in range(len(data)):
        if data['Gold_Signal'].iloc[i]:
            last_signal_idx = i
            days_since.append(0)
        elif last_signal_idx is not None:
            days_since.append(i - last_signal_idx)
        else:
            days_since.append(999)

    data['Days_Since_Gold_Signal'] = days_since

    return data


def check_h1_filter(rsi: float) -> bool:
    """
    H1: D-Tier 패턴 회피

    극단적 RSI = D-Tier로 간주
    진입 가능하면 True
    """
    if rsi < 25 or rsi > 80:
        return False  # D-Tier, 진입 금지
    return True


def check_h4_signal(days_since_transition: int, from_regime: str, to_regime: str) -> Tuple[bool, float]:
    """
    H4: 매크로 전이 직후 윈도우

    Returns:
        (is_active, score)
    """
    # 전이 후 10일 이내
    if days_since_transition > 10:
        return False, 0.0

    # 유리한 전이인지 확인
    favorable_patterns = [
        # to Gold Safe-Haven (방어적 전환)
        ("Normal", "Gold Safe-Haven"),
        ("High Volatility", "Gold Safe-Haven"),
        ("Moderate Safe-Haven", "Gold Safe-Haven"),

        # to Normal (안정화)
        ("Gold Safe-Haven", "Normal"),
        ("High Volatility", "Normal"),
    ]

    for from_r, to_r in favorable_patterns:
        if from_r in (from_regime or "") and to_r in to_regime:
            # 전이 직후일수록 높은 점수
            score = 1.0 - (days_since_transition / 10) * 0.3
            return True, score

    # 일반 전이도 약한 신호
    if days_since_transition <= 5:
        return True, 0.5

    return False, 0.0


def check_h7_signal(regime: str, days_since_gold_signal: int) -> Tuple[bool, float]:
    """
    H7: Gold Safe-Haven에서 Gold 급등 후 BTC 추종

    Returns:
        (is_active, score)
    """
    # Gold Safe-Haven 레짐이어야 함
    if "Safe-Haven" not in regime:
        return False, 0.0

    # Gold +1.5% 후 3-10일 대기
    if 3 <= days_since_gold_signal <= 10:
        # 3-5일이 최적
        if days_since_gold_signal <= 5:
            return True, 1.0
        else:
            return True, 0.7

    return False, 0.0


def generate_signals(data: pd.DataFrame) -> List[Signal]:
    """모든 신호 생성"""
    signals = []

    for i in range(1, len(data)):
        row = data.iloc[i]
        prev_row = data.iloc[i-1]
        date = data.index[i].strftime('%Y-%m-%d')

        # H1 체크 (필터)
        if not check_h1_filter(row['RSI']):
            continue  # D-Tier, 스킵

        # H4 체크
        h4_active, h4_score = check_h4_signal(
            row['Days_Since_Transition'],
            prev_row.get('Regime'),
            row['Regime']
        )

        # H7 체크
        h7_active, h7_score = check_h7_signal(
            row['Regime'],
            row['Days_Since_Gold_Signal']
        )

        # 신호 조합
        if h4_active and h7_active:
            # 가장 강력: H4 + H7 동시
            combined_score = (h4_score + h7_score) / 2 + 0.2  # 보너스
            signals.append(Signal(
                date=date,
                signal_type=SignalType.H4_AND_H7,
                score=min(combined_score, 1.0),
                details=f"H4:{h4_score:.2f}+H7:{h7_score:.2f}|{row['Regime']}"
            ))
        elif h4_active and h4_score >= 0.7:
            # H4만 (강한 전이)
            signals.append(Signal(
                date=date,
                signal_type=SignalType.H4_TRANSITION,
                score=h4_score,
                details=f"H4:{h4_score:.2f}|{row['Regime']}"
            ))
        elif h7_active:
            # H7만
            signals.append(Signal(
                date=date,
                signal_type=SignalType.H7_GOLD_LAG,
                score=h7_score,
                details=f"H7:{h7_score:.2f}|{row['Regime']}"
            ))

    return signals


def generate_trades(data: pd.DataFrame,
                    min_signal_type: SignalType = SignalType.H7_GOLD_LAG,
                    hold_days: int = 7) -> List[TradeResult]:
    """
    통합 전략으로 거래 생성
    """
    # 신호 생성
    data = add_regime_info(data.copy())
    data = add_gold_signal_info(data)

    trades = []
    position = None

    for i in range(1, len(data)):
        row = data.iloc[i]
        prev_row = data.iloc[i-1]
        date = data.index[i].strftime('%Y-%m-%d')
        price = row['BTC_Close']

        if position is None:
            # 진입 조건
            if not check_h1_filter(row['RSI']):
                continue

            h4_active, h4_score = check_h4_signal(
                row['Days_Since_Transition'],
                prev_row.get('Regime'),
                row['Regime']
            )

            h7_active, h7_score = check_h7_signal(
                row['Regime'],
                row['Days_Since_Gold_Signal']
            )

            should_enter = False
            signal_type = SignalType.NONE
            score = 0.0

            if h4_active and h7_active:
                should_enter = True
                signal_type = SignalType.H4_AND_H7
                score = (h4_score + h7_score) / 2 + 0.2
            elif h4_active and h4_score >= 0.7:
                if min_signal_type in [SignalType.H4_TRANSITION, SignalType.H7_GOLD_LAG]:
                    should_enter = True
                    signal_type = SignalType.H4_TRANSITION
                    score = h4_score
            elif h7_active:
                if min_signal_type == SignalType.H7_GOLD_LAG:
                    should_enter = True
                    signal_type = SignalType.H7_GOLD_LAG
                    score = h7_score

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

            # 1. 보유 기간
            if days_held >= hold_days:
                should_exit = True

            # 2. D-Tier 진입
            if not check_h1_filter(row['RSI']):
                should_exit = True

            # 3. 손절 -10%
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
                    state_at_entry=f"{position['signal_type'].value}|{position['score']:.2f}"
                ))
                position = None

    return trades


def analyze_by_signal_type(trades: List[TradeResult]) -> Dict:
    """신호 유형별 분석"""
    results = {}

    for sig_type in ["H4+H7", "H4", "H7"]:
        type_trades = [t for t in trades if t.state_at_entry.startswith(sig_type)]
        if type_trades:
            wins = sum(1 for t in type_trades if t.is_win)
            total_return = np.prod([1 + t.return_pct for t in type_trades]) - 1
            results[sig_type] = {
                'trades': len(type_trades),
                'win_rate': wins / len(type_trades),
                'total_return': total_return,
                'avg_return': np.mean([t.return_pct for t in type_trades])
            }

    return results


def main():
    print("=" * 70)
    print("Integrated Strategy V2: H1 + H4 + H7")
    print("=" * 70)

    # 데이터 로드
    data = fetch_data("2020-01-01", "2025-12-26")
    data = add_regime_info(data)
    data = add_gold_signal_info(data)

    calc = MetricsCalculator()

    # 레짐 분포
    print("\n--- Regime Distribution ---")
    regime_counts = data['Regime'].value_counts()
    for regime, count in regime_counts.items():
        print(f"  {regime}: {count} ({count/len(data)*100:.1f}%)")

    # 전이 수
    transitions = data['Is_Transition'].sum()
    print(f"\n  Total transitions: {transitions}")

    # Walk-Forward 분할
    train_end = "2022-12-31"
    train_data = data[data.index <= train_end].copy()
    test_data = data[data.index > train_end].copy()

    print(f"\n  Train: {len(train_data)} days")
    print(f"  Test: {len(test_data)} days")

    # 전략 테스트
    print("\n" + "=" * 70)
    print("Strategy Test: All Signals")
    print("=" * 70)

    all_trades = generate_trades(data)

    if all_trades:
        metrics = calc.calculate(all_trades, "all")

        print(f"\nTotal trades: {len(all_trades)}")
        print(f"Win rate: {metrics.win_rate:.1%}")
        print(f"Avg return: {metrics.avg_return*100:.2f}%")
        print(f"Total return: {metrics.total_return*100:.1f}%")
        print(f"Max drawdown: {metrics.max_drawdown:.1%}")

        # 신호 유형별
        print("\n--- By Signal Type ---")
        analysis = analyze_by_signal_type(all_trades)
        for sig, stats in sorted(analysis.items(), key=lambda x: -x[1]['win_rate']):
            print(f"  {sig}: {stats['trades']} trades, WR {stats['win_rate']:.1%}, "
                  f"Return {stats['total_return']*100:+.1f}%")

    # Walk-Forward
    print("\n" + "=" * 70)
    print("Walk-Forward Validation")
    print("=" * 70)

    train_trades = generate_trades(train_data)
    test_trades = generate_trades(test_data)

    print(f"\nTrain (2020-2022):")
    if train_trades:
        train_metrics = calc.calculate(train_trades, "train")
        print(f"  Trades: {len(train_trades)}, WR: {train_metrics.win_rate:.1%}, "
              f"Return: {train_metrics.total_return*100:+.1f}%")

    print(f"\nTest (2023-2025):")
    if test_trades:
        test_metrics = calc.calculate(test_trades, "test")
        print(f"  Trades: {len(test_trades)}, WR: {test_metrics.win_rate:.1%}, "
              f"Return: {test_metrics.total_return*100:+.1f}%")
        print(f"  p-value: {test_metrics.p_value_vs_random:.4f}")

        # 신호별
        print("\n  By Signal Type (Test):")
        test_analysis = analyze_by_signal_type(test_trades)
        for sig, stats in sorted(test_analysis.items(), key=lambda x: -x[1]['win_rate']):
            print(f"    {sig}: {stats['trades']} trades, WR {stats['win_rate']:.1%}")

    # 최적 파라미터 검색
    print("\n" + "=" * 70)
    print("Parameter Optimization (Test Period)")
    print("=" * 70)

    results = []
    for hold_days in [5, 7, 10, 14]:
        trades = generate_trades(test_data, hold_days=hold_days)
        if len(trades) >= 5:
            wins = sum(1 for t in trades if t.is_win)
            wr = wins / len(trades)
            total_ret = np.prod([1 + t.return_pct for t in trades]) - 1

            results.append({
                'hold_days': hold_days,
                'trades': len(trades),
                'win_rate': wr,
                'total_return': total_ret
            })

    print(f"\n{'Hold':<8} {'Trades':<8} {'Win Rate':<10} {'Return':<12}")
    print("-" * 40)
    for r in sorted(results, key=lambda x: -x['win_rate']):
        print(f"{r['hold_days']:<8} {r['trades']:<8} {r['win_rate']:.1%}      {r['total_return']*100:+.1f}%")

    # 년도별 분석
    print("\n" + "=" * 70)
    print("Year-by-Year Analysis")
    print("=" * 70)

    print(f"\n{'Year':<8} {'Trades':<8} {'WR':<10} {'Return':<12} {'H4+H7':<8} {'H4':<8} {'H7':<8}")
    print("-" * 70)

    for year in range(2020, 2026):
        year_data = data[data.index.year == year].copy()
        if len(year_data) < 30:
            continue

        year_trades = generate_trades(year_data)

        if year_trades:
            wr = sum(1 for t in year_trades if t.is_win) / len(year_trades)
            ret = np.prod([1 + t.return_pct for t in year_trades]) - 1

            h4h7 = sum(1 for t in year_trades if "H4+H7" in t.state_at_entry)
            h4 = sum(1 for t in year_trades if t.state_at_entry.startswith("H4|"))
            h7 = sum(1 for t in year_trades if t.state_at_entry.startswith("H7|"))

            print(f"{year:<8} {len(year_trades):<8} {wr:.1%}      {ret*100:+.1f}%       "
                  f"{h4h7:<8} {h4:<8} {h7:<8}")
        else:
            print(f"{year:<8} 0")

    # 최종 전략 요약
    print("\n" + "=" * 70)
    print("Final Strategy")
    print("=" * 70)

    print("""
    ┌────────────────────────────────────────────────────────────────┐
    │  INTEGRATED STRATEGY V2                                        │
    ├────────────────────────────────────────────────────────────────┤
    │                                                                │
    │  진입 조건 (AND):                                              │
    │  1. [필수] H1 Filter: RSI 25-80 범위 (D-Tier 회피)             │
    │  2. [신호] 다음 중 하나:                                       │
    │     - H4+H7: 레짐 전이 10일 내 + Gold Safe-Haven + Gold 래그   │
    │     - H4: 유리한 레짐 전이 직후 (score >= 0.7)                 │
    │     - H7: Gold Safe-Haven + Gold +1.5% 후 3-10일               │
    │                                                                │
    │  포지션 크기:                                                  │
    │  - H4+H7: 100%                                                 │
    │  - H4 only: 70%                                                │
    │  - H7 only: 50%                                                │
    │                                                                │
    │  청산 조건:                                                    │
    │  - 보유 7일 도달                                               │
    │  - D-Tier 진입 (RSI <25 or >80)                                │
    │  - 손절 -10%                                                   │
    │                                                                │
    └────────────────────────────────────────────────────────────────┘
    """)

    # 검증 결과 요약
    if test_trades:
        print("\n  Validation Summary:")
        print(f"  - Test WR: {test_metrics.win_rate:.1%}")
        print(f"  - Test Return: {test_metrics.total_return*100:+.1f}%")
        print(f"  - p-value: {test_metrics.p_value_vs_random:.4f}")

        if test_metrics.win_rate >= 0.55 and test_metrics.p_value_vs_random <= 0.1:
            print("\n  Status: VALIDATED")
        elif test_metrics.win_rate >= 0.50:
            print("\n  Status: MARGINAL - 추가 검증 필요")
        else:
            print("\n  Status: NEEDS IMPROVEMENT")


if __name__ == "__main__":
    main()
