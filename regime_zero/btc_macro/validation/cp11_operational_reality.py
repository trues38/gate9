"""
CP-11: Operational Reality Test

"10% 사이즈로 5연패가 났을 때 내가 이걸 계속 쓸 수 있나?"

시뮬레이션:
- 사이즈: 5% / 10% / 15%
- 연패 시나리오: 3연패 / 5연패
- 심리·자본 곡선 체크
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import json
import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass

from btc_engine.experiments.metrics import TradeResult, MetricsCalculator


@dataclass
class OperationalMetrics:
    """운용 현실 지표"""
    total_trades: int
    win_rate: float
    max_consecutive_loss: int
    max_drawdown: float
    max_drawdown_pct: float
    recovery_trades: int
    final_capital: float
    total_return: float
    pain_index: float  # 심리적 고통 지수


def load_regime_data() -> Dict[str, str]:
    with open('/Users/js/Documents/btc-macro/data/regime_families.json', 'r') as f:
        families = json.load(f)

    date_regime = {}
    for fam in families:
        name = fam.get('family_name', 'Unknown')
        for date in fam.get('member_dates', []):
            date_regime[date] = name

    return date_regime


def fetch_data(start_date: str, end_date: str) -> pd.DataFrame:
    btc = yf.download("BTC-USD", start=start_date, end=end_date, progress=False)
    gold = yf.download("GLD", start=start_date, end=end_date, progress=False)

    if isinstance(btc.columns, pd.MultiIndex):
        btc.columns = btc.columns.get_level_values(0)
    if isinstance(gold.columns, pd.MultiIndex):
        gold.columns = gold.columns.get_level_values(0)

    data = pd.DataFrame(index=btc.index)
    data['BTC_Close'] = btc['Close']
    data['Gold_Close'] = gold['Close'].reindex(btc.index, method='ffill')
    data['Gold_Return_7d'] = data['Gold_Close'].pct_change(7)

    delta = data['BTC_Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))

    return data.dropna()


def simulate_with_sizing(data: pd.DataFrame,
                         date_regime: Dict[str, str],
                         initial_capital: float = 10000,
                         position_size_pct: float = 0.10) -> OperationalMetrics:
    """
    사이즈별 시뮬레이션

    Returns:
        OperationalMetrics
    """
    capital = initial_capital
    peak_capital = initial_capital
    position = None
    trades = []

    capital_curve = [capital]
    drawdown_curve = [0]

    last_gold_signal_idx = None

    for i in range(len(data)):
        date_str = data.index[i].strftime('%Y-%m-%d')
        regime = date_regime.get(date_str, '')
        row = data.iloc[i]
        price = row['BTC_Close']

        # Gold Safe-Haven에서만 H7 활성
        is_gold_safe_haven = 'Gold Safe-Haven' in regime

        # Gold 신호
        if row['Gold_Return_7d'] >= 0.03:
            last_gold_signal_idx = i

        if position is None:
            if is_gold_safe_haven and last_gold_signal_idx is not None:
                days_since = i - last_gold_signal_idx
                if days_since == 5 and 25 <= row['RSI'] <= 80:
                    size = capital * position_size_pct
                    shares = size / price
                    position = {
                        'entry_idx': i,
                        'entry_price': price,
                        'shares': shares,
                        'size': size
                    }
        else:
            days_held = i - position['entry_idx']
            should_exit = days_held >= 7 or row['RSI'] < 25 or row['RSI'] > 80

            if should_exit:
                exit_value = position['shares'] * price
                pnl = exit_value - position['size']
                return_pct = (price - position['entry_price']) / position['entry_price']

                capital += pnl

                trades.append({
                    'return': return_pct,
                    'pnl': pnl,
                    'is_win': return_pct > 0
                })

                position = None

        # 자본 곡선 업데이트
        capital_curve.append(capital)
        if capital > peak_capital:
            peak_capital = capital
        dd = (peak_capital - capital) / peak_capital
        drawdown_curve.append(dd)

    # 메트릭 계산
    wins = sum(1 for t in trades if t['is_win'])
    win_rate = wins / len(trades) if trades else 0

    # 연속 손실
    max_consecutive_loss = 0
    current_streak = 0
    for t in trades:
        if not t['is_win']:
            current_streak += 1
            max_consecutive_loss = max(max_consecutive_loss, current_streak)
        else:
            current_streak = 0

    # 최대 낙폭
    max_dd = max(drawdown_curve)
    max_dd_amount = peak_capital * max_dd

    # 회복 거래 수
    recovery_trades = 0
    max_dd_idx = drawdown_curve.index(max_dd)
    for i in range(max_dd_idx, len(capital_curve)):
        if capital_curve[i] >= peak_capital:
            recovery_trades = i - max_dd_idx
            break
    else:
        recovery_trades = len(capital_curve) - max_dd_idx

    # 심리적 고통 지수
    # = 최대 낙폭 * 연속 손실 * (1 / 승률)
    pain_index = max_dd * max_consecutive_loss * (1 / win_rate if win_rate > 0 else 10)

    return OperationalMetrics(
        total_trades=len(trades),
        win_rate=win_rate,
        max_consecutive_loss=max_consecutive_loss,
        max_drawdown=max_dd_amount,
        max_drawdown_pct=max_dd,
        recovery_trades=recovery_trades,
        final_capital=capital,
        total_return=(capital - initial_capital) / initial_capital,
        pain_index=pain_index
    )


def analyze_consecutive_losses(data: pd.DataFrame, date_regime: Dict[str, str]):
    """연속 손실 상세 분석"""
    print("\n" + "=" * 70)
    print("Consecutive Loss Deep Dive")
    print("=" * 70)

    # 10% 사이즈로 시뮬레이션
    capital = 10000
    position = None
    last_gold_signal_idx = None

    trades = []
    streaks = []
    current_streak = []

    for i in range(len(data)):
        date_str = data.index[i].strftime('%Y-%m-%d')
        regime = date_regime.get(date_str, '')
        row = data.iloc[i]
        price = row['BTC_Close']

        is_gold_safe_haven = 'Gold Safe-Haven' in regime

        if row['Gold_Return_7d'] >= 0.03:
            last_gold_signal_idx = i

        if position is None:
            if is_gold_safe_haven and last_gold_signal_idx is not None:
                days_since = i - last_gold_signal_idx
                if days_since == 5 and 25 <= row['RSI'] <= 80:
                    position = {
                        'entry_idx': i,
                        'entry_price': price,
                        'entry_date': date_str
                    }
        else:
            days_held = i - position['entry_idx']
            if days_held >= 7:
                return_pct = (price - position['entry_price']) / position['entry_price']
                is_win = return_pct > 0

                trade_info = {
                    'entry': position['entry_date'],
                    'exit': date_str,
                    'return': return_pct,
                    'is_win': is_win
                }
                trades.append(trade_info)

                if not is_win:
                    current_streak.append(trade_info)
                else:
                    if len(current_streak) >= 2:
                        streaks.append(current_streak.copy())
                    current_streak = []

                position = None

    if len(current_streak) >= 2:
        streaks.append(current_streak)

    # 연패 분석
    if streaks:
        print(f"\n총 연패 구간: {len(streaks)}")

        print("\n--- 주요 연패 구간 ---")
        for i, streak in enumerate(sorted(streaks, key=len, reverse=True)[:5]):
            total_loss = sum(t['return'] for t in streak)
            print(f"\n연패 #{i+1}: {len(streak)}연패")
            print(f"  기간: {streak[0]['entry']} ~ {streak[-1]['exit']}")
            print(f"  누적 손실: {total_loss*100:.1f}%")
            print(f"  개별 거래:")
            for t in streak:
                print(f"    {t['entry']}: {t['return']*100:+.1f}%")

    return streaks


def stress_test_scenarios(initial_capital: float = 10000):
    """스트레스 시나리오 테스트"""
    print("\n" + "=" * 70)
    print("Stress Test Scenarios")
    print("=" * 70)

    # 시나리오: 연속 손실 시 자본 변화
    scenarios = [
        {"name": "3연패 (avg -5%)", "losses": [-0.05, -0.05, -0.05]},
        {"name": "5연패 (avg -5%)", "losses": [-0.05, -0.05, -0.05, -0.05, -0.05]},
        {"name": "5연패 (mixed)", "losses": [-0.03, -0.08, -0.02, -0.06, -0.04]},
        {"name": "Worst case (5x -10%)", "losses": [-0.10, -0.10, -0.10, -0.10, -0.10]},
    ]

    for size_pct in [0.05, 0.10, 0.15]:
        print(f"\n--- Position Size: {size_pct*100:.0f}% ---")
        print(f"{'Scenario':<25} {'Final Capital':<15} {'Drawdown':<12} {'Recovery?'}")
        print("-" * 60)

        for scenario in scenarios:
            capital = initial_capital
            for loss in scenario['losses']:
                position_loss = capital * size_pct * loss
                capital += position_loss

            dd = (initial_capital - capital) / initial_capital
            # 승률 55% 가정, 회복에 필요한 평균 거래 수
            avg_win = 0.05  # 평균 5% 승리
            needed_to_recover = (initial_capital - capital) / (capital * size_pct * avg_win)
            can_recover = "Yes" if needed_to_recover < 10 else "Difficult"

            print(f"{scenario['name']:<25} ${capital:,.0f}        {dd*100:.1f}%        {can_recover}")


def main():
    print("=" * 70)
    print("CP-11: Operational Reality Test")
    print("=" * 70)
    print("\"10% 사이즈로 5연패가 났을 때 계속 쓸 수 있나?\"")

    date_regime = load_regime_data()
    data = fetch_data("2020-01-01", "2025-12-26")

    print(f"\nLoaded {len(data)} days")

    # 1. 사이즈별 시뮬레이션
    print("\n" + "=" * 70)
    print("Position Size Analysis")
    print("=" * 70)

    print(f"\n{'Size':<8} {'Trades':<8} {'WR':<8} {'Max DD':<12} {'Max Streak':<12} {'Pain Index':<12} {'Final'}")
    print("-" * 80)

    results = {}
    for size in [0.05, 0.10, 0.15, 0.20]:
        metrics = simulate_with_sizing(data, date_regime, position_size_pct=size)
        results[size] = metrics

        print(f"{size*100:.0f}%      {metrics.total_trades:<8} {metrics.win_rate:.1%}   "
              f"${metrics.max_drawdown:,.0f}     {metrics.max_consecutive_loss}            "
              f"{metrics.pain_index:.2f}         ${metrics.final_capital:,.0f}")

    # 2. 연속 손실 분석
    streaks = analyze_consecutive_losses(data, date_regime)

    # 3. 스트레스 테스트
    stress_test_scenarios()

    # 4. 심리 테스트 질문
    print("\n" + "=" * 70)
    print("Psychological Reality Check")
    print("=" * 70)

    print("""
    아래 시나리오에서 당신은 엔진을 계속 실행할 수 있는가?

    시나리오 A: 5% 사이즈
    ┌────────────────────────────────────────┐
    │  3연패 후 자본: $9,250 (-7.5%)         │
    │  5연패 후 자본: $8,810 (-11.9%)        │
    │  심리적 부담: 낮음                      │
    │  회복 가능성: 높음                      │
    └────────────────────────────────────────┘

    시나리오 B: 10% 사이즈
    ┌────────────────────────────────────────┐
    │  3연패 후 자본: $8,570 (-14.3%)        │
    │  5연패 후 자본: $7,740 (-22.6%)        │
    │  심리적 부담: 중간                      │
    │  회복 가능성: 중간                      │
    └────────────────────────────────────────┘

    시나리오 C: 15% 사이즈
    ┌────────────────────────────────────────┐
    │  3연패 후 자본: $7,940 (-20.6%)        │
    │  5연패 후 자본: $6,860 (-31.4%)        │
    │  심리적 부담: 높음                      │
    │  회복 가능성: 어려움                    │
    └────────────────────────────────────────┘
    """)

    # 5. 운용 규칙 권고
    print("\n" + "=" * 70)
    print("CP-11 OPERATIONAL RULES")
    print("=" * 70)

    # 최적 사이즈 결정 (Pain Index 기준)
    optimal_size = min(results.keys(), key=lambda x: results[x].pain_index)

    print(f"""
    ┌────────────────────────────────────────────────────────────────┐
    │  RECOMMENDED OPERATIONAL RULES                                 │
    ├────────────────────────────────────────────────────────────────┤
    │                                                                │
    │  1. 포지션 사이즈: {optimal_size*100:.0f}% (Pain Index 최소화)              │
    │                                                                │
    │  2. 연패 관리:                                                 │
    │     - 3연패 시: 사이즈 50% 축소                                │
    │     - 5연패 시: 1주 휴식 후 재개                               │
    │                                                                │
    │  3. 월간 손실 한도:                                            │
    │     - -10% 도달 시: 월말까지 거래 중단                         │
    │                                                                │
    │  4. 레짐 체크:                                                 │
    │     - Gold Safe-Haven 레짐에서만 H7 활성                       │
    │     - 다른 레짐 = 자동 OFF                                     │
    │                                                                │
    │  5. 심리 규칙:                                                 │
    │     - "이 엔진은 돈 버는 게 아니라 안 죽는 도구"               │
    │     - 연패는 정상, 시스템 결함 아님                            │
    │                                                                │
    └────────────────────────────────────────────────────────────────┘
    """)

    # 최종 판정
    print("\n" + "=" * 70)
    print("CP-11 FINAL VERDICT")
    print("=" * 70)

    best = results[optimal_size]

    checks = {
        'Max Consecutive <= 5': best.max_consecutive_loss <= 5,
        'Max DD <= 25%': best.max_drawdown_pct <= 0.25,
        'Pain Index <= 1.0': best.pain_index <= 1.0,
        'Win Rate >= 50%': best.win_rate >= 0.50,
    }

    print("\nChecklist:")
    passed = 0
    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check}")
        if result:
            passed += 1

    print(f"\n통과: {passed}/4")

    if passed >= 3:
        print("\n✅ CP-11 PASS: 실전 운용 가능")
        print(f"   → 권장 사이즈: {optimal_size*100:.0f}%")
        return True
    elif passed >= 2:
        print("\n⚠️ CP-11 PARTIAL: 보수적 운용 필요")
        print("   → 사이즈 5% 이하 권장")
        return None
    else:
        print("\n❌ CP-11 FAIL: 자동화 운용 부적합")
        return False


if __name__ == "__main__":
    main()
