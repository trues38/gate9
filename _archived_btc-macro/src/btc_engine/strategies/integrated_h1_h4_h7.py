"""
Integrated Strategy: H1 + H4 + H7

세 가지 검증된 가설을 통합한 BTC 진입 전략

H1 (Filter): D-Tier 패턴 회피
H4 (Context): 매크로 전이 직후 윈도우
H7 (Signal): Gold Safe-Haven에서 Gold 래그 추종

전략 구조:
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: H1 Filter (항상 활성)                              │
│  └─ D-Tier 패턴이면 진입 금지                                │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: H4 Context Window                                  │
│  └─ 레짐 전이 후 10일 = "기회 윈도우"                        │
│  └─ 특정 전이 조합은 가중치 부여                             │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: H7 Entry Signal                                    │
│  └─ Gold Safe-Haven + Gold +1.5% + 3일 대기                  │
│  └─ 가장 강력한 진입 신호                                    │
└─────────────────────────────────────────────────────────────┘

신호 강도:
- STRONG: H4 윈도우 + H7 신호 (둘 다 활성)
- MEDIUM: H4 윈도우만 활성 (유리한 전이)
- WEAK: H7 신호만 활성 (Gold Safe-Haven)
- AVOID: D-Tier 또는 불리한 전이
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from btc_engine.experiments.metrics import TradeResult, MetricsCalculator


class SignalStrength(Enum):
    STRONG = 3    # H4 + H7 동시 활성
    MEDIUM = 2    # H4만 활성 (유리한 전이)
    WEAK = 1      # H7만 활성
    NEUTRAL = 0   # 신호 없음
    AVOID = -1    # D-Tier 또는 불리한 전이


@dataclass
class MarketState:
    """현재 시장 상태"""
    date: str
    price: float

    # H1: Pattern Tier
    pattern_tier: str  # S, A, B, C, D

    # H4: Macro Transition
    current_regime: str
    previous_regime: Optional[str]
    days_since_transition: int
    is_favorable_transition: bool

    # H7: Gold Lag
    gold_return_7d: float
    days_since_gold_signal: int
    is_gold_safe_haven: bool

    # Computed
    signal_strength: SignalStrength
    entry_score: float


# H4: 유리한 전이 조합 (검증된 것들)
FAVORABLE_TRANSITIONS = {
    ("Reflation Rally", "Risk-Off Capitulation"): 1.0,
    ("Weak Dollar Risk-On Boom", "Reflation Rally"): 0.9,
    ("Goldilocks Equilibrium", "Gold Safe-Haven Fortress"): 0.85,
    ("Hawkish Tightening Grind", "Geopolitical Tension Fog"): 0.8,
    ("Equity Complacency Melt-Up", "Hawkish Tightening Grind"): 0.75,
    ("Equity Complacency Melt-Up", "Weak Dollar Risk-On Boom"): 0.75,
    ("Geopolitical Tension Fog", "Strong Dollar Dominance"): 0.7,
    ("Strong Dollar Dominance", "Geopolitical Tension Fog"): 0.7,
}

# H4: 불리한 전이 조합
UNFAVORABLE_TRANSITIONS = {
    ("Gold Safe-Haven Fortress", "Hawkish Tightening Grind"),
    ("Reflation Rally", "Hawkish Tightening Grind"),
    ("Risk-Off Capitulation", "Hawkish Tightening Grind"),
}


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI 계산"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def simulate_pattern_tier(rsi: float, volatility_zscore: float) -> str:
    """
    패턴 티어 시뮬레이션 (실제로는 Graph DB에서 가져와야 함)

    임시 로직:
    - D-Tier: RSI < 25 또는 RSI > 80 (극단적 상태)
    - S-Tier: RSI 40-60 + 낮은 변동성 (안정적)
    - A-Tier: RSI 35-65
    - B-Tier: RSI 30-70
    - C-Tier: 나머지
    """
    if rsi < 25 or rsi > 80:
        return "D"
    elif volatility_zscore > 2.5:
        return "D"  # 극단적 변동성도 D-Tier
    elif 40 <= rsi <= 60 and abs(volatility_zscore) < 1:
        return "S"
    elif 35 <= rsi <= 65:
        return "A"
    elif 30 <= rsi <= 70:
        return "B"
    else:
        return "C"


def simulate_macro_regime(date: pd.Timestamp, gold_return: float,
                          volatility: float, rsi: float) -> str:
    """
    매크로 레짐 시뮬레이션 (실제로는 Graph DB에서 가져와야 함)

    간단한 휴리스틱:
    - Gold +2% 이상: Gold Safe-Haven
    - 고변동성 + 하락: Risk-Off Capitulation
    - 저변동성 + 상승: Equity Complacency
    - 중간: 기타 레짐
    """
    if gold_return > 0.02:
        return "Gold Safe-Haven Fortress"
    elif volatility > 2 and rsi < 35:
        return "Risk-Off Capitulation"
    elif volatility < -1 and rsi > 55:
        return "Equity Complacency Melt-Up"
    elif rsi > 60:
        return "Reflation Rally"
    elif rsi < 40:
        return "Hawkish Tightening Grind"
    else:
        return "Goldilocks Equilibrium"


def fetch_data(start_date: str, end_date: str) -> pd.DataFrame:
    """BTC + Gold 데이터 가져오기"""
    print(f"Fetching data: {start_date} ~ {end_date}")

    btc = yf.download("BTC-USD", start=start_date, end=end_date, progress=False)
    gold = yf.download("GLD", start=start_date, end=end_date, progress=False)

    if isinstance(btc.columns, pd.MultiIndex):
        btc.columns = btc.columns.get_level_values(0)
    if isinstance(gold.columns, pd.MultiIndex):
        gold.columns = gold.columns.get_level_values(0)

    # Merge
    data = pd.DataFrame(index=btc.index)
    data['BTC_Close'] = btc['Close']
    data['Gold_Close'] = gold['Close'].reindex(btc.index, method='ffill')

    # BTC indicators
    data['RSI'] = calculate_rsi(data['BTC_Close'])
    data['BTC_Return_1d'] = data['BTC_Close'].pct_change()
    data['BTC_Return_7d'] = data['BTC_Close'].pct_change(7)
    data['Volatility'] = data['BTC_Return_1d'].rolling(20).std() * np.sqrt(365)
    data['Vol_Mean'] = data['Volatility'].rolling(60).mean()
    data['Vol_Std'] = data['Volatility'].rolling(60).std()
    data['Vol_Zscore'] = (data['Volatility'] - data['Vol_Mean']) / data['Vol_Std']

    # Gold indicators
    data['Gold_Return_1d'] = data['Gold_Close'].pct_change()
    data['Gold_Return_7d'] = data['Gold_Close'].pct_change(7)

    data = data.dropna()
    print(f"Loaded {len(data)} days of data")

    return data


def detect_regime_transitions(data: pd.DataFrame) -> pd.DataFrame:
    """레짐 전이 감지"""
    regimes = []

    for i in range(len(data)):
        row = data.iloc[i]
        regime = simulate_macro_regime(
            data.index[i],
            row['Gold_Return_7d'],
            row['Vol_Zscore'],
            row['RSI']
        )
        regimes.append(regime)

    data['Regime'] = regimes
    data['Regime_Prev'] = data['Regime'].shift(1)
    data['Is_Transition'] = data['Regime'] != data['Regime_Prev']

    # Days since last transition
    transition_indices = data[data['Is_Transition']].index
    days_since = []
    last_transition_idx = None

    for i, idx in enumerate(data.index):
        if idx in transition_indices:
            last_transition_idx = i
            days_since.append(0)
        elif last_transition_idx is not None:
            days_since.append(i - last_transition_idx)
        else:
            days_since.append(999)  # No transition yet

    data['Days_Since_Transition'] = days_since

    return data


def detect_gold_signals(data: pd.DataFrame) -> pd.DataFrame:
    """Gold 신호 감지 (H7)"""
    # Gold +1.5% 이상인 날 찾기
    data['Gold_Signal'] = data['Gold_Return_7d'] >= 0.015

    # 마지막 Gold 신호 이후 일수
    days_since_gold = []
    last_signal_idx = None

    for i in range(len(data)):
        if data['Gold_Signal'].iloc[i]:
            last_signal_idx = i
            days_since_gold.append(0)
        elif last_signal_idx is not None:
            days_since_gold.append(i - last_signal_idx)
        else:
            days_since_gold.append(999)

    data['Days_Since_Gold_Signal'] = days_since_gold

    return data


def calculate_signal_strength(row: pd.Series, prev_regime: Optional[str]) -> Tuple[SignalStrength, float]:
    """
    신호 강도 계산

    Returns:
        (SignalStrength, entry_score)
    """
    # H1: D-Tier 체크
    pattern_tier = simulate_pattern_tier(row['RSI'], row['Vol_Zscore'])
    if pattern_tier == "D":
        return SignalStrength.AVOID, -1.0

    # H4: 전이 윈도우 체크
    is_in_transition_window = row['Days_Since_Transition'] <= 10
    current_regime = row['Regime']

    transition_score = 0.0
    if is_in_transition_window and prev_regime:
        transition_key = (prev_regime, current_regime)
        if transition_key in UNFAVORABLE_TRANSITIONS:
            return SignalStrength.AVOID, -0.5
        if transition_key in FAVORABLE_TRANSITIONS:
            transition_score = FAVORABLE_TRANSITIONS[transition_key]

    # H7: Gold Safe-Haven + Gold 신호 체크
    is_gold_safe_haven = "Gold Safe-Haven" in current_regime
    gold_signal_active = (
        is_gold_safe_haven and
        3 <= row['Days_Since_Gold_Signal'] <= 10
    )

    # 신호 강도 결정
    if is_in_transition_window and gold_signal_active:
        # STRONG: H4 + H7 동시
        score = 0.5 + transition_score * 0.3 + 0.2
        return SignalStrength.STRONG, min(score, 1.0)

    elif is_in_transition_window and transition_score > 0:
        # MEDIUM: H4만 (유리한 전이)
        score = 0.3 + transition_score * 0.4
        return SignalStrength.MEDIUM, score

    elif gold_signal_active:
        # WEAK: H7만
        return SignalStrength.WEAK, 0.4

    else:
        return SignalStrength.NEUTRAL, 0.0


def generate_integrated_trades(data: pd.DataFrame,
                                min_signal: SignalStrength = SignalStrength.WEAK,
                                hold_days: int = 7) -> List[TradeResult]:
    """
    통합 전략으로 거래 생성

    Args:
        data: 시장 데이터
        min_signal: 최소 진입 신호 강도
        hold_days: 기본 보유 기간
    """
    trades = []
    position = None

    for i in range(1, len(data)):
        row = data.iloc[i]
        prev_row = data.iloc[i-1]
        date = data.index[i].strftime('%Y-%m-%d')
        price = row['BTC_Close']

        prev_regime = prev_row['Regime'] if i > 0 else None
        signal_strength, entry_score = calculate_signal_strength(row, prev_regime)

        if position is None:
            # 진입 조건
            if signal_strength.value >= min_signal.value and entry_score > 0:
                position = {
                    'entry_date': date,
                    'entry_price': price,
                    'entry_idx': i,
                    'signal': signal_strength.name,
                    'score': entry_score,
                    'regime': row['Regime']
                }
        else:
            # 청산 조건
            days_held = i - position['entry_idx']

            should_exit = False
            exit_reason = ""

            # 1. 기본 보유 기간 도달
            if days_held >= hold_days:
                should_exit = True
                exit_reason = "hold_days"

            # 2. 불리한 레짐으로 전이
            if row['Is_Transition']:
                transition_key = (prev_row['Regime'], row['Regime'])
                if transition_key in UNFAVORABLE_TRANSITIONS:
                    should_exit = True
                    exit_reason = "unfavorable_transition"

            # 3. D-Tier 진입 (손절)
            pattern_tier = simulate_pattern_tier(row['RSI'], row['Vol_Zscore'])
            if pattern_tier == "D":
                should_exit = True
                exit_reason = "d_tier_stop"

            # 4. 큰 손실 (-10%)
            current_return = (price - position['entry_price']) / position['entry_price']
            if current_return < -0.10:
                should_exit = True
                exit_reason = "stop_loss"

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
                    state_at_entry=f"{position['signal']}|{position['score']:.2f}|{position['regime'][:20]}"
                ))
                position = None

    return trades


def analyze_by_signal_strength(trades: List[TradeResult]) -> Dict:
    """신호 강도별 분석"""
    results = {}

    for strength in ['STRONG', 'MEDIUM', 'WEAK']:
        strength_trades = [t for t in trades if strength in t.state_at_entry]
        if strength_trades:
            wins = sum(1 for t in strength_trades if t.is_win)
            total_return = np.prod([1 + t.return_pct for t in strength_trades]) - 1
            results[strength] = {
                'trades': len(strength_trades),
                'win_rate': wins / len(strength_trades),
                'total_return': total_return,
                'avg_return': np.mean([t.return_pct for t in strength_trades])
            }

    return results


def run_walk_forward(data: pd.DataFrame, train_end: str = "2022-12-31"):
    """Walk-Forward 검증"""
    train_data = data[data.index <= train_end]
    test_data = data[data.index > train_end]

    calc = MetricsCalculator()

    print("\n" + "=" * 70)
    print("Walk-Forward Validation")
    print("=" * 70)

    for min_signal in [SignalStrength.STRONG, SignalStrength.MEDIUM, SignalStrength.WEAK]:
        print(f"\n--- Min Signal: {min_signal.name} ---")

        train_trades = generate_integrated_trades(train_data, min_signal=min_signal)
        test_trades = generate_integrated_trades(test_data, min_signal=min_signal)

        if len(train_trades) >= 5 and len(test_trades) >= 5:
            train_metrics = calc.calculate(train_trades, "train")
            test_metrics = calc.calculate(test_trades, "test")

            print(f"Train: {len(train_trades)} trades, WR {train_metrics.win_rate:.1%}, "
                  f"Return {train_metrics.total_return*100:+.1f}%")
            print(f"Test:  {len(test_trades)} trades, WR {test_metrics.win_rate:.1%}, "
                  f"Return {test_metrics.total_return*100:+.1f}%, p={test_metrics.p_value_vs_random:.4f}")

            # 신호 강도별 분석
            strength_analysis = analyze_by_signal_strength(test_trades)
            if strength_analysis:
                print("  Signal breakdown (Test):")
                for sig, stats in strength_analysis.items():
                    print(f"    {sig}: {stats['trades']} trades, "
                          f"WR {stats['win_rate']:.1%}, Ret {stats['total_return']*100:+.1f}%")
        else:
            print(f"  Not enough trades (Train: {len(train_trades)}, Test: {len(test_trades)})")


def main():
    print("=" * 70)
    print("Integrated Strategy: H1 + H4 + H7")
    print("=" * 70)

    # 1. 데이터 로드
    data = fetch_data("2020-01-01", "2025-12-26")

    # 2. 레짐 전이 감지
    data = detect_regime_transitions(data)

    # 3. Gold 신호 감지
    data = detect_gold_signals(data)

    # 4. 기본 테스트 (WEAK 이상 신호)
    print("\n" + "=" * 70)
    print("Basic Test: All Signals (WEAK+)")
    print("=" * 70)

    all_trades = generate_integrated_trades(data, min_signal=SignalStrength.WEAK)

    calc = MetricsCalculator()
    metrics = calc.calculate(all_trades, "all")

    print(f"\nTotal trades: {len(all_trades)}")
    print(f"Win rate: {metrics.win_rate:.1%}")
    print(f"Avg return: {metrics.avg_return*100:.2f}%")
    print(f"Total return: {metrics.total_return*100:.1f}%")
    print(f"Max drawdown: {metrics.max_drawdown:.1%}")
    print(f"Sharpe: {metrics.sharpe_ratio:.2f}")

    # 신호 강도별 분석
    print("\n--- By Signal Strength ---")
    strength_analysis = analyze_by_signal_strength(all_trades)
    for sig, stats in sorted(strength_analysis.items(), reverse=True):
        print(f"{sig}: {stats['trades']} trades, WR {stats['win_rate']:.1%}, "
              f"Total {stats['total_return']*100:+.1f}%")

    # 5. Walk-Forward 검증
    run_walk_forward(data)

    # 6. 년도별 분석
    print("\n" + "=" * 70)
    print("Year-by-Year Analysis (MEDIUM+ signals)")
    print("=" * 70)

    print(f"\n{'Year':<8} {'Trades':<8} {'Win Rate':<10} {'Return':<12} {'STRONG':<10} {'MEDIUM':<10}")
    print("-" * 60)

    for year in range(2020, 2026):
        year_data = data[data.index.year == year]
        if len(year_data) < 30:
            continue

        # 레짐/Gold 신호 재계산 (연도 내에서)
        year_data = detect_regime_transitions(year_data.copy())
        year_data = detect_gold_signals(year_data)

        year_trades = generate_integrated_trades(year_data, min_signal=SignalStrength.MEDIUM)

        if year_trades:
            wr = sum(1 for t in year_trades if t.is_win) / len(year_trades)
            ret = np.prod([1 + t.return_pct for t in year_trades]) - 1

            strong_count = sum(1 for t in year_trades if 'STRONG' in t.state_at_entry)
            medium_count = sum(1 for t in year_trades if 'MEDIUM' in t.state_at_entry)

            print(f"{year:<8} {len(year_trades):<8} {wr:.1%}      {ret*100:+.1f}%       "
                  f"{strong_count:<10} {medium_count:<10}")
        else:
            print(f"{year:<8} 0")

    # 7. 최적 설정 찾기
    print("\n" + "=" * 70)
    print("Optimal Configuration Search")
    print("=" * 70)

    train_end = "2022-12-31"
    test_data = data[data.index > train_end]
    test_data = detect_regime_transitions(test_data.copy())
    test_data = detect_gold_signals(test_data)

    results = []

    for min_signal in [SignalStrength.STRONG, SignalStrength.MEDIUM, SignalStrength.WEAK]:
        for hold_days in [5, 7, 10, 14]:
            trades = generate_integrated_trades(
                test_data,
                min_signal=min_signal,
                hold_days=hold_days
            )

            if len(trades) >= 10:
                wins = sum(1 for t in trades if t.is_win)
                wr = wins / len(trades)
                total_ret = np.prod([1 + t.return_pct for t in trades]) - 1

                results.append({
                    'min_signal': min_signal.name,
                    'hold_days': hold_days,
                    'trades': len(trades),
                    'win_rate': wr,
                    'total_return': total_ret
                })

    print(f"\n{'Signal':<10} {'Hold':<6} {'Trades':<8} {'Win Rate':<10} {'Return':<12}")
    print("-" * 50)

    for r in sorted(results, key=lambda x: -x['win_rate']):
        print(f"{r['min_signal']:<10} {r['hold_days']:<6} {r['trades']:<8} "
              f"{r['win_rate']:.1%}      {r['total_return']*100:+.1f}%")

    # Best
    if results:
        best = max(results, key=lambda x: x['win_rate'] if x['trades'] >= 15 else 0)
        print(f"\nOptimal: min_signal={best['min_signal']}, hold_days={best['hold_days']}")
        print(f"  Test WR: {best['win_rate']:.1%}, Return: {best['total_return']*100:+.1f}%")

    # 8. 결론
    print("\n" + "=" * 70)
    print("Strategy Summary")
    print("=" * 70)

    print("""
    ┌─────────────────────────────────────────────────────────────────┐
    │  INTEGRATED STRATEGY: H1 + H4 + H7                              │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                 │
    │  진입 조건:                                                     │
    │  ├─ [필수] H1: D-Tier 패턴이 아닐 것                            │
    │  ├─ [선호] H4: 레짐 전이 후 10일 이내                           │
    │  └─ [선호] H7: Gold Safe-Haven + Gold +1.5% 후 3-10일           │
    │                                                                 │
    │  신호 강도:                                                     │
    │  ├─ STRONG: H4 + H7 동시 → 풀 포지션                            │
    │  ├─ MEDIUM: H4만 (유리한 전이) → 절반 포지션                    │
    │  └─ WEAK: H7만 → 소량 포지션                                    │
    │                                                                 │
    │  청산 조건:                                                     │
    │  ├─ 보유 7-10일 도달                                            │
    │  ├─ 불리한 레짐 전이 발생                                       │
    │  ├─ D-Tier 진입 (즉시 청산)                                     │
    │  └─ -10% 손절                                                   │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘
    """)


if __name__ == "__main__":
    main()
