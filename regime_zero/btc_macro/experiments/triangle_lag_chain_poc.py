"""
3각 래그 체인 PoC

타겟 체인: Gold → (5d) → BTC → (2d) → ETH

검증 내용:
1. 금 상승이 BTC와 ETH를 순차적으로 밀어 올리는가?
2. 이 패턴이 p < 0.05 수준에서 유의미하게 반복되는가?
3. 현재 시점에서 이 체인이 가동될 확률은 몇 %인가?
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import json
import yfinance as yf
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
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
    """Gold, BTC, ETH 데이터"""
    print(f"Fetching data: {start_date} ~ {end_date}")

    gold = yf.download("GLD", start=start_date, end=end_date, progress=False)
    btc = yf.download("BTC-USD", start=start_date, end=end_date, progress=False)
    eth = yf.download("ETH-USD", start=start_date, end=end_date, progress=False)

    for df in [gold, btc, eth]:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

    data = pd.DataFrame()
    data['Gold_Close'] = gold['Close']
    data['BTC_Close'] = btc['Close']
    data['ETH_Close'] = eth['Close']

    # 수익률
    for window in [1, 3, 5, 7, 10, 14]:
        data[f'Gold_Ret_{window}d'] = data['Gold_Close'].pct_change(window, fill_method=None)
        data[f'BTC_Ret_{window}d'] = data['BTC_Close'].pct_change(window, fill_method=None)
        data[f'ETH_Ret_{window}d'] = data['ETH_Close'].pct_change(window, fill_method=None)

    data = data.ffill().dropna()
    print(f"Loaded {len(data)} days")
    return data


# =============================================================================
# 1. 개별 래그 관계 검증
# =============================================================================

def verify_individual_lags(data: pd.DataFrame, date_to_regime: Dict[str, str]) -> Dict:
    """
    1단계: 개별 래그 관계 검증
    - Gold → BTC (5일 래그)
    - BTC → ETH (2일 래그)
    """
    print("\n" + "=" * 70)
    print("1. INDIVIDUAL LAG VERIFICATION")
    print("=" * 70)

    data['Regime'] = data.index.map(
        lambda x: date_to_regime.get(x.strftime('%Y-%m-%d'), 'Unknown')
    )

    results = {}

    # 1.1 Gold → BTC (5일 래그)
    print("\n1.1 Gold → BTC Lag Analysis")
    print("-" * 50)

    gold_btc_results = []
    for lag in range(1, 11):
        # Gold 상승 후 lag일 뒤 BTC 수익률
        shifted_btc = data['BTC_Ret_7d'].shift(-lag)
        valid_mask = (data['Gold_Ret_7d'] >= 0.03) & shifted_btc.notna()

        if valid_mask.sum() >= 10:
            btc_returns = shifted_btc[valid_mask]
            wr = (btc_returns > 0).mean()
            avg_ret = btc_returns.mean()
            pval = 1 - stats.binom.cdf(int(wr * len(btc_returns)) - 1, len(btc_returns), 0.5)

            gold_btc_results.append({
                'lag': lag,
                'n': len(btc_returns),
                'wr': wr,
                'avg_ret': avg_ret,
                'p_value': pval
            })

    print(f"{'Lag':<6} {'N':<8} {'WR':<10} {'Avg Ret':<12} {'p-value'}")
    print("-" * 50)
    for r in gold_btc_results:
        sig = '*' if r['p_value'] < 0.05 else ''
        print(f"{r['lag']}d     {r['n']:<8} {r['wr']:.1%}      {r['avg_ret']*100:+.2f}%       {r['p_value']:.3f}{sig}")

    results['gold_btc'] = gold_btc_results

    # 1.2 BTC → ETH (2일 래그)
    print("\n1.2 BTC → ETH Lag Analysis")
    print("-" * 50)

    btc_eth_results = []
    for lag in range(0, 6):
        # BTC 상승 후 lag일 뒤 ETH 수익률
        shifted_eth = data['ETH_Ret_7d'].shift(-lag)
        valid_mask = (data['BTC_Ret_7d'] >= 0.05) & shifted_eth.notna()

        if valid_mask.sum() >= 10:
            eth_returns = shifted_eth[valid_mask]
            wr = (eth_returns > 0).mean()
            avg_ret = eth_returns.mean()
            pval = 1 - stats.binom.cdf(int(wr * len(eth_returns)) - 1, len(eth_returns), 0.5)

            btc_eth_results.append({
                'lag': lag,
                'n': len(eth_returns),
                'wr': wr,
                'avg_ret': avg_ret,
                'p_value': pval
            })

    print(f"{'Lag':<6} {'N':<8} {'WR':<10} {'Avg Ret':<12} {'p-value'}")
    print("-" * 50)
    for r in btc_eth_results:
        sig = '*' if r['p_value'] < 0.05 else ''
        print(f"{r['lag']}d     {r['n']:<8} {r['wr']:.1%}      {r['avg_ret']*100:+.2f}%       {r['p_value']:.3f}{sig}")

    results['btc_eth'] = btc_eth_results

    return results


# =============================================================================
# 2. 체인 전체 검증
# =============================================================================

def verify_full_chain(
    data: pd.DataFrame,
    date_to_regime: Dict[str, str],
    gold_threshold: float = 0.03,
    gold_btc_lag: int = 5,
    btc_eth_lag: int = 2,
    hold_days: int = 7
) -> Dict:
    """
    2단계: 전체 체인 검증
    Gold +3% → (5d) → BTC 진입 → (2d) → ETH 진입
    """
    print("\n" + "=" * 70)
    print("2. FULL CHAIN VERIFICATION")
    print(f"   Gold +{gold_threshold*100:.0f}% → ({gold_btc_lag}d) → BTC → ({btc_eth_lag}d) → ETH")
    print("=" * 70)

    data['Regime'] = data.index.map(
        lambda x: date_to_regime.get(x.strftime('%Y-%m-%d'), 'Unknown')
    )

    chains = []

    i = 0
    while i < len(data) - gold_btc_lag - btc_eth_lag - hold_days:
        row = data.iloc[i]
        date_str = data.index[i].strftime('%Y-%m-%d')
        regime = row['Regime']

        # Gold Safe-Haven 조건
        if 'Gold Safe-Haven' not in regime:
            i += 1
            continue

        # Gold 신호
        if row['Gold_Ret_7d'] >= gold_threshold:
            # BTC 진입 시점
            btc_entry_idx = i + gold_btc_lag
            # ETH 진입 시점
            eth_entry_idx = btc_entry_idx + btc_eth_lag
            # 공통 청산 시점
            exit_idx = eth_entry_idx + hold_days

            if exit_idx >= len(data):
                break

            # BTC 성과 (gold_btc_lag 후 진입, hold_days 보유)
            btc_entry = data.iloc[btc_entry_idx]['BTC_Close']
            btc_exit = data.iloc[exit_idx]['BTC_Close']
            btc_return = (btc_exit - btc_entry) / btc_entry

            # ETH 성과 (추가 btc_eth_lag 후 진입, hold_days 보유)
            eth_entry = data.iloc[eth_entry_idx]['ETH_Close']
            eth_exit = data.iloc[exit_idx]['ETH_Close']
            eth_return = (eth_exit - eth_entry) / eth_entry

            # 체인 성과 (순차 진입, 가중 평균)
            # 50% BTC + 50% ETH
            chain_return = 0.5 * btc_return + 0.5 * eth_return

            chains.append({
                'signal_date': date_str,
                'btc_entry_date': data.index[btc_entry_idx].strftime('%Y-%m-%d'),
                'eth_entry_date': data.index[eth_entry_idx].strftime('%Y-%m-%d'),
                'exit_date': data.index[exit_idx].strftime('%Y-%m-%d'),
                'gold_signal': row['Gold_Ret_7d'],
                'btc_return': btc_return,
                'eth_return': eth_return,
                'chain_return': chain_return,
                'btc_win': btc_return > 0,
                'eth_win': eth_return > 0,
                'chain_win': chain_return > 0,
                'regime': regime
            })

            i = exit_idx  # 다음 신호까지 스킵
        else:
            i += 1

    if not chains:
        print("  No chain signals found")
        return {}

    # 결과 분석
    n = len(chains)
    btc_wins = sum(1 for c in chains if c['btc_win'])
    eth_wins = sum(1 for c in chains if c['eth_win'])
    chain_wins = sum(1 for c in chains if c['chain_win'])

    btc_wr = btc_wins / n
    eth_wr = eth_wins / n
    chain_wr = chain_wins / n

    btc_avg = np.mean([c['btc_return'] for c in chains])
    eth_avg = np.mean([c['eth_return'] for c in chains])
    chain_avg = np.mean([c['chain_return'] for c in chains])

    btc_total = np.prod([1 + c['btc_return'] for c in chains]) - 1
    eth_total = np.prod([1 + c['eth_return'] for c in chains]) - 1
    chain_total = np.prod([1 + c['chain_return'] for c in chains]) - 1

    # p-values
    btc_pval = 1 - stats.binom.cdf(btc_wins - 1, n, 0.5)
    eth_pval = 1 - stats.binom.cdf(eth_wins - 1, n, 0.5)
    chain_pval = 1 - stats.binom.cdf(chain_wins - 1, n, 0.5)

    print(f"\n2.1 Chain Performance Summary (N={n})")
    print("-" * 70)
    print(f"{'Asset':<10} {'WR':<10} {'Avg Ret':<12} {'Total Ret':<14} {'p-value'}")
    print("-" * 70)

    for asset, wr, avg, total, pval in [
        ('BTC', btc_wr, btc_avg, btc_total, btc_pval),
        ('ETH', eth_wr, eth_avg, eth_total, eth_pval),
        ('CHAIN', chain_wr, chain_avg, chain_total, chain_pval)
    ]:
        sig = '**' if pval < 0.01 else '*' if pval < 0.05 else ''
        print(f"{asset:<10} {wr:.1%}      {avg*100:+.2f}%       {total*100:+.1f}%          {pval:.4f}{sig}")

    # 개별 체인 거래
    print(f"\n2.2 Individual Chain Trades")
    print("-" * 90)
    print(f"{'Signal':<12} {'BTC Entry':<12} {'ETH Entry':<12} {'Exit':<12} {'BTC':<10} {'ETH':<10} {'Chain'}")
    print("-" * 90)

    for c in chains:
        btc_status = "+" if c['btc_win'] else "-"
        eth_status = "+" if c['eth_win'] else "-"
        chain_status = "WIN" if c['chain_win'] else "LOSS"
        print(f"{c['signal_date']:<12} {c['btc_entry_date']:<12} {c['eth_entry_date']:<12} "
              f"{c['exit_date']:<12} {btc_status}{c['btc_return']*100:+.1f}%    "
              f"{eth_status}{c['eth_return']*100:+.1f}%    {chain_status}")

    return {
        'chains': chains,
        'stats': {
            'n': n,
            'btc': {'wr': btc_wr, 'avg': btc_avg, 'total': btc_total, 'pval': btc_pval},
            'eth': {'wr': eth_wr, 'avg': eth_avg, 'total': eth_total, 'pval': eth_pval},
            'chain': {'wr': chain_wr, 'avg': chain_avg, 'total': chain_total, 'pval': chain_pval}
        }
    }


# =============================================================================
# 3. 현재 시점 체인 가동 확률
# =============================================================================

def check_current_chain_probability(
    data: pd.DataFrame,
    date_to_regime: Dict[str, str],
    chain_results: Dict
) -> Dict:
    """
    3단계: 현재 시점에서 체인 가동 확률
    """
    print("\n" + "=" * 70)
    print("3. CURRENT CHAIN ACTIVATION PROBABILITY")
    print("=" * 70)

    # 최신 데이터
    latest = data.iloc[-1]
    latest_date = data.index[-1].strftime('%Y-%m-%d')
    regime = date_to_regime.get(latest_date, 'Unknown')

    print(f"\n  Current Date: {latest_date}")
    print(f"  Current Regime: {regime}")

    # 조건 체크
    conditions = {
        'gold_safe_haven': 'Gold Safe-Haven' in regime,
        'gold_rising': latest['Gold_Ret_7d'] >= 0.03 if 'Gold_Ret_7d' in data.columns else False,
        'gold_near_threshold': 0.02 <= latest['Gold_Ret_7d'] < 0.03 if 'Gold_Ret_7d' in data.columns else False,
    }

    print(f"\n  Current Conditions:")
    print(f"    Gold 7d Return: {latest['Gold_Ret_7d']*100:+.2f}%")
    print(f"    BTC 7d Return:  {latest['BTC_Ret_7d']*100:+.2f}%")
    print(f"    ETH 7d Return:  {latest['ETH_Ret_7d']*100:+.2f}%")

    print(f"\n  Chain Activation Checklist:")
    print(f"    [{'✓' if conditions['gold_safe_haven'] else '✗'}] Gold Safe-Haven Regime")
    print(f"    [{'✓' if conditions['gold_rising'] else '✗'}] Gold >= +3% (7d)")

    # 확률 계산
    if conditions['gold_safe_haven'] and conditions['gold_rising']:
        activation_status = "ACTIVE"
        chain_stats = chain_results.get('stats', {}).get('chain', {})
        expected_wr = chain_stats.get('wr', 0.5)
        expected_ret = chain_stats.get('avg', 0)
        print(f"\n  ┌─────────────────────────────────────────┐")
        print(f"  │  CHAIN STATUS: 🟢 {activation_status:<26}│")
        print(f"  │                                         │")
        print(f"  │  Expected Win Rate: {expected_wr:.0%}                │")
        print(f"  │  Expected Return: {expected_ret*100:+.1f}%                │")
        print(f"  │                                         │")
        print(f"  │  Action: BTC entry in 5d, ETH in 7d     │")
        print(f"  └─────────────────────────────────────────┘")

    elif conditions['gold_safe_haven'] and conditions['gold_near_threshold']:
        gap = 0.03 - latest['Gold_Ret_7d']
        print(f"\n  ┌─────────────────────────────────────────┐")
        print(f"  │  CHAIN STATUS: 🟡 NEAR ACTIVATION       │")
        print(f"  │                                         │")
        print(f"  │  Gold needs +{gap*100:.1f}% more to trigger      │")
        print(f"  │  Monitor closely                        │")
        print(f"  └─────────────────────────────────────────┘")
        activation_status = "NEAR"

    elif conditions['gold_safe_haven']:
        print(f"\n  ┌─────────────────────────────────────────┐")
        print(f"  │  CHAIN STATUS: 🔴 INACTIVE              │")
        print(f"  │                                         │")
        print(f"  │  Regime OK, waiting for Gold signal     │")
        print(f"  └─────────────────────────────────────────┘")
        activation_status = "INACTIVE"

    else:
        print(f"\n  ┌─────────────────────────────────────────┐")
        print(f"  │  CHAIN STATUS: ⚫ DISABLED              │")
        print(f"  │                                         │")
        print(f"  │  Wrong regime ({regime[:20]}...)        │")
        print(f"  │  Chain only works in Gold Safe-Haven    │")
        print(f"  └─────────────────────────────────────────┘")
        activation_status = "DISABLED"

    # 과거 신호 패턴 분석
    print("\n  Recent Gold Signals (last 30 days):")
    print("-" * 50)

    recent_data = data.tail(30)
    for idx, row in recent_data.iterrows():
        date_str = idx.strftime('%Y-%m-%d')
        reg = date_to_regime.get(date_str, 'Unknown')
        gold_ret = row['Gold_Ret_7d']

        if gold_ret >= 0.03 and 'Gold Safe-Haven' in reg:
            print(f"    {date_str}: Gold {gold_ret*100:+.1f}% | {reg[:30]} | 🟢 SIGNAL")
        elif gold_ret >= 0.02:
            print(f"    {date_str}: Gold {gold_ret*100:+.1f}% | {reg[:30]} | 🟡 Near")

    return {
        'status': activation_status,
        'conditions': conditions,
        'current_values': {
            'gold_ret': latest['Gold_Ret_7d'],
            'btc_ret': latest['BTC_Ret_7d'],
            'eth_ret': latest['ETH_Ret_7d'],
            'regime': regime
        }
    }


# =============================================================================
# 4. Walk-Forward 검증
# =============================================================================

def walk_forward_validation(
    data: pd.DataFrame,
    date_to_regime: Dict[str, str]
) -> Dict:
    """Train/Test 분리 검증"""
    print("\n" + "=" * 70)
    print("4. WALK-FORWARD VALIDATION")
    print("=" * 70)

    train_end = "2022-12-31"
    train_data = data[data.index <= train_end].copy()
    test_data = data[data.index > train_end].copy()

    print(f"\n  Train: 2017-01-01 ~ {train_end} ({len(train_data)} days)")
    print(f"  Test:  2023-01-01 ~ 2024-12-31 ({len(test_data)} days)")

    # Train
    print("\n  --- TRAIN PERIOD ---")
    train_results = verify_full_chain(train_data, date_to_regime)

    # Test
    print("\n  --- TEST PERIOD (OOS) ---")
    test_results = verify_full_chain(test_data, date_to_regime)

    # 비교
    print("\n4.1 Train vs Test Comparison")
    print("-" * 70)
    print(f"{'Metric':<20} {'Train':<20} {'Test (OOS)':<20}")
    print("-" * 70)

    if train_results and test_results:
        train_s = train_results['stats']['chain']
        test_s = test_results['stats']['chain']

        print(f"{'N':<20} {train_results['stats']['n']:<20} {test_results['stats']['n']:<20}")
        print(f"{'Win Rate':<20} {train_s['wr']:.1%}{'':<16} {test_s['wr']:.1%}")
        print(f"{'Avg Return':<20} {train_s['avg']*100:+.2f}%{'':<15} {test_s['avg']*100:+.2f}%")
        print(f"{'p-value':<20} {train_s['pval']:.4f}{'':<15} {test_s['pval']:.4f}")

        # OOS 판정
        if test_s['pval'] < 0.05 and test_s['wr'] >= 0.55:
            verdict = "✅ VALIDATED"
        elif test_s['pval'] < 0.1:
            verdict = "⚠️ MARGINAL"
        else:
            verdict = "❌ NOT SIGNIFICANT"

        print(f"\n  OOS Verdict: {verdict}")

    return {
        'train': train_results,
        'test': test_results
    }


# =============================================================================
# 5. 최종 요약
# =============================================================================

def final_summary(
    individual_results: Dict,
    chain_results: Dict,
    current_status: Dict,
    wf_results: Dict
):
    """최종 요약"""
    print("\n" + "=" * 70)
    print("5. FINAL SUMMARY: TRIANGLE LAG CHAIN")
    print("=" * 70)

    print("""
    ┌────────────────────────────────────────────────────────────────────┐
    │                                                                    │
    │      GOLD ────(5d lag)────> BTC ────(2d lag)────> ETH             │
    │       │                      │                     │               │
    │       │     +3% signal       │    follows BTC      │               │
    │       └──────────────────────┴─────────────────────┘               │
    │                                                                    │
    └────────────────────────────────────────────────────────────────────┘
    """)

    # 체인 통계
    if chain_results and chain_results.get('stats'):
        stats = chain_results['stats']

        print("  Chain Statistics (Full Period):")
        print("-" * 50)
        print(f"    Total Signals: {stats['n']}")
        print(f"    BTC Win Rate:  {stats['btc']['wr']:.1%} (p={stats['btc']['pval']:.4f})")
        print(f"    ETH Win Rate:  {stats['eth']['wr']:.1%} (p={stats['eth']['pval']:.4f})")
        print(f"    Chain Win Rate: {stats['chain']['wr']:.1%} (p={stats['chain']['pval']:.4f})")

    # OOS 결과
    if wf_results and wf_results.get('test'):
        test_stats = wf_results['test'].get('stats', {}).get('chain', {})
        print(f"\n  Out-of-Sample (2023-2024):")
        print("-" * 50)
        print(f"    N: {wf_results['test']['stats']['n']}")
        print(f"    Win Rate: {test_stats.get('wr', 0):.1%}")
        print(f"    p-value: {test_stats.get('pval', 1):.4f}")

    # 현재 상태
    print(f"\n  Current Status:")
    print("-" * 50)
    print(f"    Chain: {current_status.get('status', 'UNKNOWN')}")

    # 결론
    print("\n" + "=" * 70)
    print("  CONCLUSION")
    print("=" * 70)

    if chain_results and chain_results.get('stats'):
        chain_pval = chain_results['stats']['chain']['pval']
        chain_wr = chain_results['stats']['chain']['wr']

        if chain_pval < 0.05 and chain_wr >= 0.6:
            print("""
    ✅ Triangle Lag Chain VALIDATED

    The cascade effect is statistically significant:
    - Gold leads BTC by ~5 days
    - BTC leads ETH by ~2 days
    - Combined chain shows consistent alpha

    Graph DB Implication:
    - This pattern can be encoded as edges in the asset graph
    - Real-time monitoring possible via graph traversal
            """)
        elif chain_pval < 0.1:
            print("""
    ⚠️ Triangle Lag Chain MARGINALLY SIGNIFICANT

    The pattern shows promise but needs more data:
    - Effect is present but not robust
    - Consider regime conditioning for stronger signal
            """)
        else:
            print("""
    ❌ Triangle Lag Chain NOT SIGNIFICANT

    The cascade effect is not reliably exploitable:
    - Individual lags may exist but don't combine well
    - Or sample size is insufficient
            """)


def main():
    print("=" * 70)
    print("TRIANGLE LAG CHAIN PoC")
    print("Gold → (5d) → BTC → (2d) → ETH")
    print("=" * 70)

    # 데이터 로드
    date_to_regime = load_regime_data()
    data = fetch_data("2017-01-01", "2024-12-31")

    # 1. 개별 래그 검증
    individual_results = verify_individual_lags(data.copy(), date_to_regime)

    # 2. 전체 체인 검증
    chain_results = verify_full_chain(data.copy(), date_to_regime)

    # 3. 현재 상태 확인
    current_status = check_current_chain_probability(data.copy(), date_to_regime, chain_results)

    # 4. Walk-Forward 검증
    wf_results = walk_forward_validation(data.copy(), date_to_regime)

    # 5. 최종 요약
    final_summary(individual_results, chain_results, current_status, wf_results)

    return {
        'individual': individual_results,
        'chain': chain_results,
        'current': current_status,
        'walk_forward': wf_results
    }


if __name__ == "__main__":
    results = main()
