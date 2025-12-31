"""
CP-10: Multi-Regime Switch Design

"Gold Safe-Haven 말고, 다른 레짐에선 뭘 쓸 건데?"

각 레짐별로:
- 아무것도 안 함 (OFF)
- 단순 규칙 1개 (DCA, etc.)
- H7 활성

레짐별 툴박스 완성
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import json
import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from collections import defaultdict
from enum import Enum

from btc_engine.experiments.metrics import TradeResult, MetricsCalculator


class RegimeAction(Enum):
    H7_ACTIVE = "H7"       # H7 전략 활성
    DCA_ONLY = "DCA"       # 정액 매수만
    CASH = "CASH"          # 현금 보유
    OFF = "OFF"            # 완전 비활성


# 레짐별 권장 행동 (CP-8 결과 기반)
REGIME_ACTIONS = {
    "Gold Safe-Haven Fortress": RegimeAction.H7_ACTIVE,
    "Hawkish Tightening Grind": RegimeAction.CASH,
    "Equity Complacency Melt-Up": RegimeAction.OFF,
    "Reflation Rally": RegimeAction.DCA_ONLY,
    "Risk-Off Capitulation Crisis": RegimeAction.CASH,
    "Geopolitical Tension Fog": RegimeAction.CASH,
    "Strong Dollar Dominance": RegimeAction.OFF,
    "Goldilocks Equilibrium": RegimeAction.DCA_ONLY,
    "Weak Dollar Risk-On Boom": RegimeAction.DCA_ONLY,
}


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


def simulate_regime_toolbox(data: pd.DataFrame,
                            date_regime: Dict[str, str],
                            initial_capital: float = 10000,
                            position_size: float = 0.10) -> Dict:
    """
    레짐별 툴박스 시뮬레이션

    Returns:
        각 레짐별 성과 및 전체 포트폴리오 성과
    """
    capital = initial_capital
    position = None
    trades = []
    regime_stats = defaultdict(lambda: {
        'days': 0, 'trades': 0, 'wins': 0, 'pnl': 0
    })

    # H7 신호 추적
    last_gold_signal_idx = None

    for i in range(len(data)):
        date_str = data.index[i].strftime('%Y-%m-%d')
        regime = date_regime.get(date_str, 'Unknown')
        row = data.iloc[i]
        price = row['BTC_Close']

        # 레짐 통계
        regime_stats[regime]['days'] += 1

        # 레짐별 행동 결정
        action = REGIME_ACTIONS.get(regime, RegimeAction.OFF)

        # Gold 신호 추적 (H7용)
        if row['Gold_Return_7d'] >= 0.03:
            last_gold_signal_idx = i

        # === 포지션 관리 ===
        if position is None:
            # 진입 로직
            if action == RegimeAction.H7_ACTIVE:
                # H7: Gold 신호 후 5일
                if last_gold_signal_idx is not None:
                    days_since = i - last_gold_signal_idx
                    if days_since == 5 and 25 <= row['RSI'] <= 80:
                        size = capital * position_size
                        shares = size / price
                        position = {
                            'type': 'H7',
                            'entry_idx': i,
                            'entry_price': price,
                            'shares': shares,
                            'regime': regime
                        }

            elif action == RegimeAction.DCA_ONLY:
                # DCA: 매주 월요일 소액 매수
                if data.index[i].weekday() == 0:  # Monday
                    size = capital * 0.02  # 2% DCA
                    if size > 100:  # 최소 $100
                        shares = size / price
                        position = {
                            'type': 'DCA',
                            'entry_idx': i,
                            'entry_price': price,
                            'shares': shares,
                            'regime': regime
                        }

        else:
            # 청산 로직
            days_held = i - position['entry_idx']
            should_exit = False

            if position['type'] == 'H7':
                if days_held >= 7:
                    should_exit = True
                elif row['RSI'] < 25 or row['RSI'] > 80:
                    should_exit = True

            elif position['type'] == 'DCA':
                if days_held >= 14:  # DCA는 2주 보유
                    should_exit = True

            if should_exit:
                exit_value = position['shares'] * price
                entry_value = position['shares'] * position['entry_price']
                pnl = exit_value - entry_value
                return_pct = (price - position['entry_price']) / position['entry_price']

                capital += pnl

                # 통계 업데이트
                regime_stats[position['regime']]['trades'] += 1
                regime_stats[position['regime']]['pnl'] += pnl
                if return_pct > 0:
                    regime_stats[position['regime']]['wins'] += 1

                trades.append({
                    'type': position['type'],
                    'regime': position['regime'],
                    'return': return_pct,
                    'pnl': pnl
                })

                position = None

    return {
        'final_capital': capital,
        'total_return': (capital - initial_capital) / initial_capital,
        'trades': trades,
        'regime_stats': dict(regime_stats)
    }


def analyze_regime_performance(data: pd.DataFrame, date_regime: Dict[str, str]):
    """각 레짐에서의 BTC 성과 분석"""
    print("\n" + "=" * 70)
    print("Regime Performance Analysis (BTC Buy & Hold within regime)")
    print("=" * 70)

    regime_returns = defaultdict(list)

    prev_price = None
    prev_regime = None

    for i in range(len(data)):
        date_str = data.index[i].strftime('%Y-%m-%d')
        regime = date_regime.get(date_str, 'Unknown')
        price = data.iloc[i]['BTC_Close']

        if prev_price is not None and prev_regime == regime:
            daily_return = (price - prev_price) / prev_price
            regime_returns[regime].append(daily_return)

        prev_price = price
        prev_regime = regime

    print(f"\n{'Regime':<35} {'Days':<8} {'Avg Daily':<12} {'Total':<12} {'Action'}")
    print("-" * 80)

    for regime, returns in sorted(regime_returns.items(), key=lambda x: -len(x[1])):
        if len(returns) >= 10:
            avg_daily = np.mean(returns)
            total_ret = np.prod([1 + r for r in returns]) - 1
            action = REGIME_ACTIONS.get(regime, RegimeAction.OFF)

            print(f"{regime[:35]:<35} {len(returns):<8} {avg_daily*100:+.3f}%      "
                  f"{total_ret*100:+.1f}%      {action.value}")


def main():
    print("=" * 70)
    print("CP-10: Multi-Regime Toolbox Design")
    print("=" * 70)

    date_regime = load_regime_data()
    data = fetch_data("2020-01-01", "2025-12-26")

    print(f"\nLoaded {len(data)} days")

    # 1. 레짐별 BTC 성과 분석
    analyze_regime_performance(data, date_regime)

    # 2. 레짐 툴박스 설계
    print("\n" + "=" * 70)
    print("Regime Toolbox Configuration")
    print("=" * 70)

    print(f"\n{'Regime':<35} {'Action':<10} {'Rationale'}")
    print("-" * 80)

    rationales = {
        "Gold Safe-Haven Fortress": "Gold→BTC 래그 검증됨 (72.7% WR)",
        "Hawkish Tightening Grind": "긴축기 = 위험자산 약세",
        "Equity Complacency Melt-Up": "이미 과열, 추가 매수 위험",
        "Reflation Rally": "상승장이지만 BTC 후순위",
        "Risk-Off Capitulation Crisis": "공포 극단 = 현금 보유",
        "Geopolitical Tension Fog": "불확실성 = 관망",
        "Strong Dollar Dominance": "달러 강세 = BTC 약세",
        "Goldilocks Equilibrium": "안정기 = DCA 적합",
        "Weak Dollar Risk-On Boom": "달러 약세 = 위험자산 우호",
    }

    for regime, action in REGIME_ACTIONS.items():
        rationale = rationales.get(regime, "")
        print(f"{regime[:35]:<35} {action.value:<10} {rationale}")

    # 3. 툴박스 시뮬레이션
    print("\n" + "=" * 70)
    print("Toolbox Simulation (2020-2025)")
    print("=" * 70)

    result = simulate_regime_toolbox(data, date_regime)

    print(f"\n초기 자본: $10,000")
    print(f"최종 자본: ${result['final_capital']:,.0f}")
    print(f"총 수익률: {result['total_return']*100:+.1f}%")
    print(f"총 거래: {len(result['trades'])}")

    # 전략별 성과
    h7_trades = [t for t in result['trades'] if t['type'] == 'H7']
    dca_trades = [t for t in result['trades'] if t['type'] == 'DCA']

    print(f"\nH7 거래: {len(h7_trades)}")
    if h7_trades:
        h7_wr = sum(1 for t in h7_trades if t['return'] > 0) / len(h7_trades)
        print(f"  승률: {h7_wr:.1%}")

    print(f"\nDCA 거래: {len(dca_trades)}")
    if dca_trades:
        dca_wr = sum(1 for t in dca_trades if t['return'] > 0) / len(dca_trades)
        print(f"  승률: {dca_wr:.1%}")

    # 레짐별 성과
    print("\n--- 레짐별 성과 ---")
    print(f"{'Regime':<35} {'Days':<8} {'Trades':<8} {'WR':<10} {'PnL'}")
    print("-" * 70)

    for regime, stats in sorted(result['regime_stats'].items(),
                                key=lambda x: -x[1]['days']):
        if stats['trades'] > 0:
            wr = stats['wins'] / stats['trades']
            print(f"{regime[:35]:<35} {stats['days']:<8} {stats['trades']:<8} "
                  f"{wr:.1%}      ${stats['pnl']:+,.0f}")
        else:
            print(f"{regime[:35]:<35} {stats['days']:<8} 0")

    # 4. Buy & Hold 대비
    print("\n" + "=" * 70)
    print("vs Buy & Hold")
    print("=" * 70)

    bh_return = (data.iloc[-1]['BTC_Close'] - data.iloc[0]['BTC_Close']) / data.iloc[0]['BTC_Close']
    print(f"\nBuy & Hold: {bh_return*100:+.1f}%")
    print(f"Toolbox: {result['total_return']*100:+.1f}%")
    print(f"\n수익률 차이: {(result['total_return'] - bh_return)*100:+.1f}%p")

    # 결론
    print("\n" + "=" * 70)
    print("CP-10 CONCLUSION")
    print("=" * 70)

    print("""
    ┌────────────────────────────────────────────────────────────────┐
    │  REGIME TOOLBOX                                                │
    ├────────────────────────────────────────────────────────────────┤
    │                                                                │
    │  Gold Safe-Haven    → H7 활성 (72.7% WR)                       │
    │  Goldilocks/Weak$   → DCA (정액매수)                           │
    │  Reflation Rally    → DCA (소액)                               │
    │  Hawkish/Crisis     → CASH (현금 보유)                         │
    │  Melt-Up/Strong$    → OFF (완전 비활성)                        │
    │                                                                │
    │  핵심:                                                         │
    │  "만능 전략이 아니라 레짐별 도구 선택"                         │
    │                                                                │
    └────────────────────────────────────────────────────────────────┘
    """)


if __name__ == "__main__":
    main()
