"""
CP-9: False Positive Cost Test

"틀릴 때 얼마나 아프게 틀리나" 측정

테스트:
1. H7 단독 실패 손실
2. H7 + H1 적용 시 손실 감소
3. 연속 실패 시나리오
4. Buy & Hold / Random 대비
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import json
import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
import random

from btc_engine.experiments.metrics import TradeResult, MetricsCalculator


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


def generate_h7_trades(data: pd.DataFrame,
                       date_regime: Dict[str, str],
                       gold_threshold: float = 0.03,
                       lag_days: int = 5,
                       hold_days: int = 7,
                       use_h1_filter: bool = False) -> List[TradeResult]:
    """H7 거래 생성"""
    trades = []
    position = None
    last_signal_idx = None

    for i in range(len(data)):
        date_str = data.index[i].strftime('%Y-%m-%d')
        regime = date_regime.get(date_str, '')
        row = data.iloc[i]
        price = row['BTC_Close']

        # Gold 신호
        if row['Gold_Return_7d'] >= gold_threshold:
            last_signal_idx = i

        if position is None:
            if last_signal_idx is not None:
                days_since = i - last_signal_idx
                if days_since == lag_days:
                    # H1 필터 적용 여부
                    if use_h1_filter and (row['RSI'] < 25 or row['RSI'] > 80):
                        continue

                    position = {
                        'entry_date': date_str,
                        'entry_price': price,
                        'entry_idx': i,
                        'gold_ret': data.iloc[last_signal_idx]['Gold_Return_7d']
                    }
        else:
            days_held = i - position['entry_idx']
            if days_held >= hold_days:
                return_pct = (price - position['entry_price']) / position['entry_price']

                trades.append(TradeResult(
                    entry_date=position['entry_date'],
                    exit_date=date_str,
                    entry_price=position['entry_price'],
                    exit_price=price,
                    return_pct=return_pct,
                    is_win=return_pct > 0,
                    hold_days=days_held,
                    state_at_entry=f"gold{position['gold_ret']*100:.1f}%"
                ))
                position = None

    return trades


def generate_random_trades(data: pd.DataFrame, n_trades: int, hold_days: int = 7) -> List[TradeResult]:
    """랜덤 진입 거래"""
    trades = []
    random.seed(42)

    available_indices = list(range(len(data) - hold_days - 1))
    entry_indices = sorted(random.sample(available_indices, min(n_trades * 2, len(available_indices))))

    position = None
    for i in range(len(data)):
        if position is None:
            if i in entry_indices and len(trades) < n_trades:
                position = {
                    'entry_idx': i,
                    'entry_price': data.iloc[i]['BTC_Close'],
                    'entry_date': data.index[i].strftime('%Y-%m-%d')
                }
        else:
            days_held = i - position['entry_idx']
            if days_held >= hold_days:
                price = data.iloc[i]['BTC_Close']
                return_pct = (price - position['entry_price']) / position['entry_price']

                trades.append(TradeResult(
                    entry_date=position['entry_date'],
                    exit_date=data.index[i].strftime('%Y-%m-%d'),
                    entry_price=position['entry_price'],
                    exit_price=price,
                    return_pct=return_pct,
                    is_win=return_pct > 0,
                    hold_days=days_held,
                    state_at_entry="random"
                ))
                position = None

    return trades


def calculate_drawdown(returns: List[float]) -> Tuple[float, int]:
    """최대 낙폭 및 회복 기간 계산"""
    cumulative = [1.0]
    for r in returns:
        cumulative.append(cumulative[-1] * (1 + r))

    peak = cumulative[0]
    max_dd = 0
    max_dd_idx = 0

    for i, val in enumerate(cumulative):
        if val > peak:
            peak = val
        dd = (peak - val) / peak
        if dd > max_dd:
            max_dd = dd
            max_dd_idx = i

    # 회복 기간
    recovery_periods = 0
    for i in range(max_dd_idx, len(cumulative)):
        if cumulative[i] >= peak:
            recovery_periods = i - max_dd_idx
            break
    else:
        recovery_periods = len(cumulative) - max_dd_idx

    return max_dd, recovery_periods


def analyze_failures(trades: List[TradeResult]) -> Dict:
    """실패 거래 분석"""
    failures = [t for t in trades if not t.is_win]

    if not failures:
        return {'count': 0}

    losses = [t.return_pct for t in failures]

    # 연속 실패 분석
    max_consecutive = 0
    current_streak = 0
    consecutive_losses = []

    for t in trades:
        if not t.is_win:
            current_streak += 1
            if current_streak > max_consecutive:
                max_consecutive = current_streak
        else:
            if current_streak > 0:
                consecutive_losses.append(current_streak)
            current_streak = 0

    if current_streak > 0:
        consecutive_losses.append(current_streak)

    return {
        'count': len(failures),
        'avg_loss': np.mean(losses),
        'max_loss': min(losses),
        'median_loss': np.median(losses),
        'max_consecutive': max_consecutive,
        'avg_consecutive': np.mean(consecutive_losses) if consecutive_losses else 0
    }


def test_h7_standalone_failures(trades: List[TradeResult]):
    """CP-9 Test 1: H7 단독 실패 손실"""
    print("\n" + "=" * 70)
    print("CP-9 Test 1: H7 Standalone Failure Analysis")
    print("=" * 70)

    failure_stats = analyze_failures(trades)

    print(f"\n총 거래: {len(trades)}")
    print(f"실패 거래: {failure_stats['count']} ({failure_stats['count']/len(trades)*100:.1f}%)")

    if failure_stats['count'] > 0:
        print(f"\n손실 통계:")
        print(f"  평균 손실: {failure_stats['avg_loss']*100:.2f}%")
        print(f"  최대 손실: {failure_stats['max_loss']*100:.2f}%")
        print(f"  중간값 손실: {failure_stats['median_loss']*100:.2f}%")

        print(f"\n연속 실패:")
        print(f"  최대 연속 실패: {failure_stats['max_consecutive']}")
        print(f"  평균 연속 실패: {failure_stats['avg_consecutive']:.1f}")

    returns = [t.return_pct for t in trades]
    max_dd, recovery = calculate_drawdown(returns)
    print(f"\n낙폭:")
    print(f"  최대 낙폭: {max_dd*100:.1f}%")
    print(f"  회복 거래 수: {recovery}")

    return failure_stats


def test_h1_filter_effect(data: pd.DataFrame, date_regime: Dict[str, str]):
    """CP-9 Test 2: H1 필터 효과"""
    print("\n" + "=" * 70)
    print("CP-9 Test 2: H1 Filter Effect (D-Tier Avoidance)")
    print("=" * 70)

    # H7 단독
    h7_only = generate_h7_trades(data, date_regime, use_h1_filter=False)
    h7_only_failures = analyze_failures(h7_only)

    # H7 + H1
    h7_h1 = generate_h7_trades(data, date_regime, use_h1_filter=True)
    h7_h1_failures = analyze_failures(h7_h1)

    print(f"\n{'Metric':<25} {'H7 Only':<15} {'H7 + H1':<15} {'Δ'}")
    print("-" * 60)

    print(f"{'Total Trades':<25} {len(h7_only):<15} {len(h7_h1):<15}")

    h7_wr = sum(1 for t in h7_only if t.is_win) / len(h7_only) if h7_only else 0
    h7h1_wr = sum(1 for t in h7_h1 if t.is_win) / len(h7_h1) if h7_h1 else 0
    print(f"{'Win Rate':<25} {h7_wr:.1%}          {h7h1_wr:.1%}          {(h7h1_wr-h7_wr)*100:+.1f}%p")

    if h7_only_failures['count'] > 0 and h7_h1_failures['count'] > 0:
        avg_loss_delta = h7_h1_failures['avg_loss'] - h7_only_failures['avg_loss']
        max_loss_delta = h7_h1_failures['max_loss'] - h7_only_failures['max_loss']

        print(f"{'Avg Loss':<25} {h7_only_failures['avg_loss']*100:.2f}%         {h7_h1_failures['avg_loss']*100:.2f}%         {avg_loss_delta*100:+.2f}%")
        print(f"{'Max Loss':<25} {h7_only_failures['max_loss']*100:.2f}%        {h7_h1_failures['max_loss']*100:.2f}%        {max_loss_delta*100:+.2f}%")
        print(f"{'Max Consecutive':<25} {h7_only_failures['max_consecutive']:<15} {h7_h1_failures['max_consecutive']:<15}")

    # H1 필터 효과 판정
    if h7h1_wr > h7_wr or (h7_h1_failures.get('avg_loss', 0) > h7_only_failures.get('avg_loss', -1)):
        print("\n✅ H1 필터가 손실 감소에 기여")
        return True
    else:
        print("\n⚠️ H1 필터 효과 미미")
        return False


def test_vs_benchmarks(data: pd.DataFrame, date_regime: Dict[str, str]):
    """CP-9 Test 4: Buy & Hold / Random 대비"""
    print("\n" + "=" * 70)
    print("CP-9 Test 4: Benchmark Comparison")
    print("=" * 70)

    # H7 엔진
    h7_trades = generate_h7_trades(data, date_regime, use_h1_filter=True)
    h7_returns = [t.return_pct for t in h7_trades]
    h7_max_dd, _ = calculate_drawdown(h7_returns)
    h7_total_ret = np.prod([1 + r for r in h7_returns]) - 1 if h7_returns else 0

    # CAGR 계산 (약 5년)
    years = 5
    h7_cagr = (1 + h7_total_ret) ** (1/years) - 1 if h7_total_ret > -1 else -1

    # Buy & Hold
    start_price = data.iloc[0]['BTC_Close']
    end_price = data.iloc[-1]['BTC_Close']
    bh_total_ret = (end_price - start_price) / start_price
    bh_cagr = (1 + bh_total_ret) ** (1/years) - 1

    # Buy & Hold Max DD
    cumulative_bh = data['BTC_Close'] / data['BTC_Close'].iloc[0]
    rolling_max = cumulative_bh.expanding().max()
    bh_dd = (rolling_max - cumulative_bh) / rolling_max
    bh_max_dd = bh_dd.max()

    # Random Entry
    random_trades = generate_random_trades(data, len(h7_trades))
    random_returns = [t.return_pct for t in random_trades]
    random_max_dd, _ = calculate_drawdown(random_returns)
    random_total_ret = np.prod([1 + r for r in random_returns]) - 1 if random_returns else 0
    random_cagr = (1 + random_total_ret) ** (1/years) - 1 if random_total_ret > -1 else -1
    random_wr = sum(1 for t in random_trades if t.is_win) / len(random_trades) if random_trades else 0

    print(f"\n{'Strategy':<20} {'Max DD':<12} {'Total Ret':<12} {'CAGR':<12} {'Win Rate'}")
    print("-" * 70)

    h7_wr = sum(1 for t in h7_trades if t.is_win) / len(h7_trades) if h7_trades else 0
    print(f"{'1-4-7 Engine':<20} {h7_max_dd*100:.1f}%        {h7_total_ret*100:+.1f}%       {h7_cagr*100:.1f}%        {h7_wr:.1%}")
    print(f"{'Buy & Hold':<20} {bh_max_dd*100:.1f}%        {bh_total_ret*100:+.1f}%      {bh_cagr*100:.1f}%        N/A")
    print(f"{'Random Entry':<20} {random_max_dd*100:.1f}%        {random_total_ret*100:+.1f}%       {random_cagr*100:.1f}%        {random_wr:.1%}")

    # 핵심 비교
    print(f"\n핵심 비교:")
    dd_reduction = (bh_max_dd - h7_max_dd) / bh_max_dd * 100
    print(f"  Max DD 감소 (vs B&H): {dd_reduction:.1f}%")

    if h7_max_dd < bh_max_dd * 0.7:
        print("  ✅ 엔진이 Tail Risk를 30%+ 감소시킴")
        return True
    elif h7_max_dd < bh_max_dd:
        print("  ⚠️ 엔진이 Tail Risk를 일부 감소시킴")
        return None
    else:
        print("  ❌ 엔진이 Tail Risk 관리에 실패")
        return False


def main():
    print("=" * 70)
    print("CP-9: False Positive Cost Test")
    print("=" * 70)
    print("\"틀릴 때 얼마나 아프게 틀리나\" 측정")

    date_regime = load_regime_data()
    data = fetch_data("2020-01-01", "2025-12-26")

    print(f"\nLoaded {len(data)} days")

    # Test 1: H7 단독 실패 분석
    h7_trades = generate_h7_trades(data, date_regime, use_h1_filter=True)
    failure_stats = test_h7_standalone_failures(h7_trades)

    # Test 2: H1 필터 효과
    h1_effect = test_h1_filter_effect(data, date_regime)

    # Test 4: 벤치마크 대비
    tail_risk_managed = test_vs_benchmarks(data, date_regime)

    # 최종 판정
    print("\n" + "=" * 70)
    print("CP-9 FINAL VERDICT")
    print("=" * 70)

    checks = {
        'Tail Risk 관리': tail_risk_managed,
        '연속 실패 제한 (<=3)': failure_stats.get('max_consecutive', 99) <= 3,
        '평균 손실 제한 (>=-5%)': failure_stats.get('avg_loss', -1) >= -0.05,
        'H1 필터 효과': h1_effect
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
        print("\n✅ CP-9 PASS: 운용 가능")
        print("   → 실패 시 손실이 관리 가능한 수준")
        return True
    elif passed >= 2:
        print("\n⚠️ CP-9 PARTIAL: 조건부 운용")
        print("   → 사이즈 제한 필요")
        return None
    else:
        print("\n❌ CP-9 FAIL: 자동화 불가")
        print("   → 실패 비용이 너무 높음")
        return False


if __name__ == "__main__":
    main()
