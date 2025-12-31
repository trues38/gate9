"""
CP-8: Regime Drift Test

H7(Gold → BTC lag)가 "시대 한정 현상"인지 "구조적 자본 이동 법칙"인지 판별

테스트:
1. 레짐 패밀리별 H7 성능 분해
2. 파라미터 안정성 (Lag/Hold 변화에 따른 성능)
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import json
import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from collections import defaultdict

from btc_engine.experiments.metrics import TradeResult, MetricsCalculator


def load_regime_data() -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """레짐 데이터 로드"""
    with open('/Users/js/Documents/btc-macro/data/regime_families.json', 'r') as f:
        families = json.load(f)

    date_regime = {}
    regime_dates = defaultdict(list)

    for fam in families:
        name = fam.get('family_name', 'Unknown')
        for date in fam.get('member_dates', []):
            date_regime[date] = name
            regime_dates[name].append(date)

    return date_regime, dict(regime_dates)


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


def generate_h7_trades_by_regime(data: pd.DataFrame,
                                  date_regime: Dict[str, str],
                                  gold_threshold: float = 0.03,
                                  lag_days: int = 5,
                                  hold_days: int = 7) -> Dict[str, List[TradeResult]]:
    """레짐별로 H7 거래 분류"""
    trades_by_regime = defaultdict(list)
    position = None
    last_signal_idx = None
    last_signal_regime = None

    for i in range(len(data)):
        date_str = data.index[i].strftime('%Y-%m-%d')
        regime = date_regime.get(date_str, 'Unknown')
        row = data.iloc[i]
        price = row['BTC_Close']

        # Gold 신호 체크 (모든 레짐에서)
        gold_breakout = row['Gold_Return_7d'] >= gold_threshold
        if gold_breakout:
            last_signal_idx = i
            last_signal_regime = regime

        if position is None:
            if last_signal_idx is not None:
                days_since = i - last_signal_idx
                if days_since == lag_days:
                    if 25 <= row['RSI'] <= 80:
                        position = {
                            'entry_date': date_str,
                            'entry_price': price,
                            'entry_idx': i,
                            'entry_regime': last_signal_regime,
                            'gold_ret': data.iloc[last_signal_idx]['Gold_Return_7d']
                        }
        else:
            days_held = i - position['entry_idx']
            if days_held >= hold_days:
                return_pct = (price - position['entry_price']) / position['entry_price']

                trade = TradeResult(
                    entry_date=position['entry_date'],
                    exit_date=date_str,
                    entry_price=position['entry_price'],
                    exit_price=price,
                    return_pct=return_pct,
                    is_win=return_pct > 0,
                    hold_days=days_held,
                    state_at_entry=f"{position['entry_regime']}|gold{position['gold_ret']*100:.1f}%"
                )

                trades_by_regime[position['entry_regime']].append(trade)
                position = None

    return dict(trades_by_regime)


def test_regime_breakdown(data: pd.DataFrame, date_regime: Dict[str, str]):
    """CP-8 Test 1: 레짐 패밀리별 분해"""
    print("\n" + "=" * 70)
    print("CP-8 Test 1: Regime Family Breakdown")
    print("=" * 70)

    trades_by_regime = generate_h7_trades_by_regime(data, date_regime)

    print(f"\n{'Regime Family':<35} {'Trades':<8} {'WR':<10} {'Avg Ret':<12} {'Direction'}")
    print("-" * 80)

    regime_results = []
    for regime, trades in sorted(trades_by_regime.items(), key=lambda x: -len(x[1])):
        if len(trades) >= 3:
            wins = sum(1 for t in trades if t.is_win)
            wr = wins / len(trades)
            avg_ret = np.mean([t.return_pct for t in trades])
            direction = "LONG ↑" if avg_ret > 0 else "SHORT ↓"

            regime_results.append({
                'regime': regime,
                'trades': len(trades),
                'wr': wr,
                'avg_ret': avg_ret,
                'consistent': wr >= 0.55 and avg_ret > 0
            })

            print(f"{regime[:35]:<35} {len(trades):<8} {wr:.1%}      {avg_ret*100:+.2f}%      {direction}")

    # 통과 판정
    consistent_regimes = [r for r in regime_results if r['consistent']]
    print(f"\n일관된 레짐 (WR>=55%, 양수 수익): {len(consistent_regimes)}/{len(regime_results)}")

    if len(consistent_regimes) >= 2:
        print("✅ CP-8.1 PASS: 2개 이상 레짐에서 구조적 일관성 확인")
        return True
    else:
        print("❌ CP-8.1 FAIL: 국지적 현상 - 특정 레짐에서만 작동")
        return False


def test_parameter_stability(data: pd.DataFrame, date_regime: Dict[str, str]):
    """CP-8 Test 2: 파라미터 안정성"""
    print("\n" + "=" * 70)
    print("CP-8 Test 2: Parameter Stability")
    print("=" * 70)

    calc = MetricsCalculator()

    # 최적값 기준: Lag=5, Hold=7
    base_lag, base_hold = 5, 7

    # Lag 변화 테스트
    print("\n--- Lag Sensitivity (Hold=7 fixed) ---")
    print(f"{'Lag':<8} {'Trades':<8} {'WR':<10} {'Δ from opt'}")
    print("-" * 40)

    lag_results = []
    for lag in [3, 4, 5, 6, 7]:
        trades = []
        for regime_trades in generate_h7_trades_by_regime(
            data, date_regime, lag_days=lag, hold_days=base_hold
        ).values():
            trades.extend(regime_trades)

        if len(trades) >= 5:
            wr = sum(1 for t in trades if t.is_win) / len(trades)
            lag_results.append({'lag': lag, 'wr': wr, 'trades': len(trades)})
            delta = wr - lag_results[2]['wr'] if len(lag_results) > 2 else 0
            print(f"{lag:<8} {len(trades):<8} {wr:.1%}      {delta:+.1%}")

    # Hold 변화 테스트
    print("\n--- Hold Sensitivity (Lag=5 fixed) ---")
    print(f"{'Hold':<8} {'Trades':<8} {'WR':<10} {'Δ from opt'}")
    print("-" * 40)

    hold_results = []
    for hold in [5, 6, 7, 8, 9, 10]:
        trades = []
        for regime_trades in generate_h7_trades_by_regime(
            data, date_regime, lag_days=base_lag, hold_days=hold
        ).values():
            trades.extend(regime_trades)

        if len(trades) >= 5:
            wr = sum(1 for t in trades if t.is_win) / len(trades)
            hold_results.append({'hold': hold, 'wr': wr, 'trades': len(trades)})
            base_idx = 2 if len(hold_results) > 2 else 0
            delta = wr - hold_results[base_idx]['wr'] if hold_results else 0
            print(f"{hold:<8} {len(trades):<8} {wr:.1%}      {delta:+.1%}")

    # 안정성 판정
    if lag_results and hold_results:
        lag_wrs = [r['wr'] for r in lag_results]
        hold_wrs = [r['wr'] for r in hold_results]

        lag_std = np.std(lag_wrs)
        hold_std = np.std(hold_wrs)

        print(f"\nLag WR 표준편차: {lag_std:.3f}")
        print(f"Hold WR 표준편차: {hold_std:.3f}")

        # 표준편차 0.1 이하면 안정적
        if lag_std <= 0.1 and hold_std <= 0.1:
            print("✅ CP-8.2 PASS: 파라미터 변화에 완만한 성능 변화 (구조적)")
            return True
        else:
            print("❌ CP-8.2 FAIL: 특정 값에서만 성능 폭등 (과적합 의심)")
            return False

    return False


def main():
    print("=" * 70)
    print("CP-8: Regime Drift Test")
    print("=" * 70)
    print("H7이 '구조적 자본 래그'인지 '시대 한정 현상'인지 판별")

    date_regime, regime_dates = load_regime_data()
    data = fetch_data("2020-01-01", "2025-12-26")

    print(f"\nLoaded {len(data)} days, {len(regime_dates)} regime families")

    # Test 1: 레짐 분해
    test1_pass = test_regime_breakdown(data, date_regime)

    # Test 2: 파라미터 안정성
    test2_pass = test_parameter_stability(data, date_regime)

    # 최종 판정
    print("\n" + "=" * 70)
    print("CP-8 FINAL VERDICT")
    print("=" * 70)

    if test1_pass and test2_pass:
        print("\n✅ CP-8 PASS: H7 = 구조적 자본 래그")
        print("   → 다중 레짐에서 작동, 파라미터 안정적")
        return True
    elif test1_pass or test2_pass:
        print("\n⚠️ CP-8 PARTIAL: 특정 레짐 전용 전략")
        print("   → 조건부 운용 가능")
        return None
    else:
        print("\n❌ CP-8 FAIL: 2023-25 한정 현상")
        print("   → 실전 운용 불가")
        return False


if __name__ == "__main__":
    main()
