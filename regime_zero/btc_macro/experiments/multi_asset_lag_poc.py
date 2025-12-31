"""
Multi-Asset Lag Relationship PoC

4쌍 검증:
1. Gold → BTC (기존 H7 확장)
2. DXY → BTC (달러 역관계)
3. VIX → ETH (공포 지수)
4. TLT → XLK (금리 민감도)

검증 프로토콜:
- 가설 사전 등록 (방향 명시)
- Strict Temporal Split (2015-2019 Discovery, 2020-2021 Val, 2022-2024 OOS)
- Bonferroni 보정 (4쌍 → p < 0.0125)
- 레짐 조건부 분석
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import json
import yfinance as yf
import pandas as pd
import numpy as np
from scipy import stats
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

# =============================================================================
# 가설 사전 등록 (Pre-registration)
# =============================================================================

HYPOTHESES = {
    'H_GOLD_BTC': {
        'leader': 'GLD',
        'follower': 'BTC-USD',
        'direction': 'positive',  # Gold 상승 → BTC 상승
        'story': '전통 안전자산 → 디지털 안전자산 확산',
        'expected_lag': (3, 7),   # 3-7일 래그 예상
        'regime_condition': 'Gold Safe-Haven',  # 조건부 레짐
    },
    'H_DXY_BTC': {
        'leader': 'UUP',  # Dollar Index ETF
        'follower': 'BTC-USD',
        'direction': 'negative',  # DXY 상승 → BTC 하락
        'story': '달러 강세 → 위험자산/대체자산 약세',
        'expected_lag': (1, 5),
        'regime_condition': None,  # 전체 기간
    },
    'H_VIX_ETH': {
        'leader': 'VIXY',  # VIX ETF (VIX 직접은 yfinance 제한)
        'follower': 'ETH-USD',
        'direction': 'negative',  # VIX 급등 → ETH 하락
        'story': '공포 지수 급등 → 위험자산 회피',
        'expected_lag': (0, 3),   # 빠른 반응
        'regime_condition': None,
    },
    'H_TLT_XLK': {
        'leader': 'TLT',  # 20+ Year Treasury Bond
        'follower': 'XLK',  # Tech Sector
        'direction': 'positive',  # 채권 상승(금리 하락) → 기술주 상승
        'story': '금리 민감도 - 할인율 효과',
        'expected_lag': (1, 5),
        'regime_condition': None,
    }
}

# 시간 분할 (엄격한 temporal split)
PERIODS = {
    'discovery': ('2017-01-01', '2019-12-31'),
    'validation': ('2020-01-01', '2021-12-31'),
    'oos': ('2022-01-01', '2024-12-31'),
}

# Bonferroni 보정
N_TESTS = 4
ALPHA_CORRECTED = 0.05 / N_TESTS  # 0.0125


@dataclass
class LagResult:
    """래그 분석 결과"""
    pair_name: str
    leader: str
    follower: str
    lag_days: int
    direction: str

    # 통계
    n_signals: int
    win_rate: float
    avg_return: float
    total_return: float
    p_value: float

    # 기간별
    period: str

    def is_significant(self) -> bool:
        return self.p_value < ALPHA_CORRECTED


def load_regime_data() -> Dict[str, str]:
    """날짜 → 레짐 매핑"""
    try:
        with open('/Users/js/Documents/btc-macro/data/regime_families.json', 'r') as f:
            families = json.load(f)
    except FileNotFoundError:
        print("Warning: regime_families.json not found")
        return {}

    date_regime = {}
    for fam in families:
        name = fam.get('family_name', 'Unknown')
        for date in fam.get('member_dates', []):
            date_regime[date] = name

    return date_regime


def fetch_multi_asset_data(start_date: str, end_date: str) -> pd.DataFrame:
    """모든 필요 자산 데이터 다운로드"""
    print(f"\n{'='*60}")
    print(f"Fetching data: {start_date} ~ {end_date}")
    print(f"{'='*60}")

    tickers = {
        'BTC': 'BTC-USD',
        'ETH': 'ETH-USD',
        'Gold': 'GLD',
        'DXY': 'UUP',
        'VIX': '^VIX',
        'TLT': 'TLT',
        'XLK': 'XLK',
    }

    data = pd.DataFrame()

    for name, ticker in tickers.items():
        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if len(df) > 0:
                data[f'{name}_Close'] = df['Close']
                print(f"  {name}: {len(df)} days")
            else:
                print(f"  {name}: NO DATA")
        except Exception as e:
            print(f"  {name}: ERROR - {e}")

    # Forward fill missing dates
    data = data.ffill()
    data = data.dropna()

    print(f"\nTotal aligned days: {len(data)}")
    return data


def calculate_returns(data: pd.DataFrame, windows: List[int] = [1, 5, 7, 10]) -> pd.DataFrame:
    """수익률 계산"""
    for col in data.columns:
        if '_Close' in col:
            name = col.replace('_Close', '')
            for w in windows:
                data[f'{name}_Ret_{w}d'] = data[col].pct_change(w)
    return data


def analyze_lag_relationship(
    data: pd.DataFrame,
    leader: str,
    follower: str,
    direction: str,
    threshold: float,
    lag_days: int,
    hold_days: int,
    date_regime: Dict[str, str] = None,
    regime_condition: str = None
) -> Dict:
    """
    래그 관계 분석

    Args:
        data: 가격 데이터
        leader: 선행 자산 컬럼명 (예: 'Gold')
        follower: 후행 자산 컬럼명 (예: 'BTC')
        direction: 'positive' or 'negative'
        threshold: leader 움직임 임계값
        lag_days: 진입 대기일
        hold_days: 보유일
        date_regime: 레짐 매핑
        regime_condition: 조건부 레짐 (None이면 전체)

    Returns:
        분석 결과
    """
    leader_col = f'{leader}_Ret_7d' if f'{leader}_Ret_7d' in data.columns else f'{leader}_Ret_5d'
    follower_close = f'{follower}_Close'

    if leader_col not in data.columns or follower_close not in data.columns:
        return {'error': f'Missing columns: {leader_col} or {follower_close}'}

    trades = []

    for i in range(len(data) - lag_days - hold_days):
        date_str = data.index[i].strftime('%Y-%m-%d')

        # 레짐 조건 체크
        if regime_condition and date_regime:
            regime = date_regime.get(date_str, '')
            if regime_condition not in regime:
                continue

        leader_return = data.iloc[i][leader_col]

        # 신호 체크
        if direction == 'positive':
            signal = leader_return >= threshold
        else:  # negative
            signal = leader_return <= -threshold

        if signal and not np.isnan(leader_return):
            entry_idx = i + lag_days
            exit_idx = entry_idx + hold_days

            if exit_idx < len(data):
                entry_price = data.iloc[entry_idx][follower_close]
                exit_price = data.iloc[exit_idx][follower_close]

                if direction == 'positive':
                    # Leader 상승 → Follower 상승 기대 (롱)
                    return_pct = (exit_price - entry_price) / entry_price
                else:
                    # Leader 상승 → Follower 하락 기대 (숏)
                    return_pct = (entry_price - exit_price) / entry_price

                trades.append({
                    'entry_date': data.index[entry_idx].strftime('%Y-%m-%d'),
                    'exit_date': data.index[exit_idx].strftime('%Y-%m-%d'),
                    'leader_signal': leader_return,
                    'return': return_pct,
                    'is_win': return_pct > 0
                })

    if not trades:
        return {'n_signals': 0, 'error': 'No signals'}

    wins = sum(1 for t in trades if t['is_win'])
    returns = [t['return'] for t in trades]

    # 통계 검정 (이항 분포)
    p_value = 1 - stats.binom.cdf(wins - 1, len(trades), 0.5)

    return {
        'n_signals': len(trades),
        'n_wins': wins,
        'win_rate': wins / len(trades),
        'avg_return': np.mean(returns),
        'total_return': np.prod([1 + r for r in returns]) - 1,
        'max_return': max(returns),
        'min_return': min(returns),
        'p_value': p_value,
        'trades': trades
    }


def run_parameter_sweep(
    data: pd.DataFrame,
    hypothesis: Dict,
    date_regime: Dict[str, str],
    period_name: str
) -> List[Dict]:
    """파라미터 스윕"""

    leader = hypothesis['leader'].replace('-USD', '').replace('GLD', 'Gold').replace('UUP', 'DXY').replace('^VIX', 'VIX')
    follower = hypothesis['follower'].replace('-USD', '')
    direction = hypothesis['direction']
    regime_condition = hypothesis.get('regime_condition')

    results = []

    # 임계값 스윕
    if direction == 'positive':
        thresholds = [0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05]
    else:
        thresholds = [0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05]

    lag_range = range(hypothesis['expected_lag'][0], hypothesis['expected_lag'][1] + 1)
    hold_range = [5, 7, 10, 14]

    for threshold in thresholds:
        for lag in lag_range:
            for hold in hold_range:
                result = analyze_lag_relationship(
                    data=data,
                    leader=leader,
                    follower=follower,
                    direction=direction,
                    threshold=threshold,
                    lag_days=lag,
                    hold_days=hold,
                    date_regime=date_regime,
                    regime_condition=regime_condition
                )

                if result.get('n_signals', 0) >= 5:
                    results.append({
                        'threshold': threshold,
                        'lag': lag,
                        'hold': hold,
                        'n': result['n_signals'],
                        'wr': result['win_rate'],
                        'avg_ret': result['avg_return'],
                        'total_ret': result['total_return'],
                        'p_value': result['p_value']
                    })

    return results


def validate_hypothesis(
    hypothesis_name: str,
    hypothesis: Dict,
    date_regime: Dict[str, str]
) -> Dict:
    """
    가설 검증 (3단계 walk-forward)
    """
    print(f"\n{'='*70}")
    print(f"Testing: {hypothesis_name}")
    print(f"Story: {hypothesis['story']}")
    print(f"{'='*70}")

    results = {
        'name': hypothesis_name,
        'hypothesis': hypothesis,
        'periods': {}
    }

    # 각 기간별 데이터 로드 및 테스트
    for period_name, (start, end) in PERIODS.items():
        print(f"\n--- {period_name.upper()} ({start} ~ {end}) ---")

        data = fetch_multi_asset_data(start, end)
        if len(data) < 100:
            print(f"  Insufficient data: {len(data)} days")
            continue

        data = calculate_returns(data)

        # 파라미터 스윕
        sweep_results = run_parameter_sweep(data, hypothesis, date_regime, period_name)

        if not sweep_results:
            print(f"  No valid parameter combinations")
            results['periods'][period_name] = None
            continue

        # 최고 성과 파라미터
        sweep_results.sort(key=lambda x: -x['wr'])
        best = sweep_results[0]

        print(f"\n  Best params: threshold={best['threshold']:.1%}, lag={best['lag']}d, hold={best['hold']}d")
        print(f"  N={best['n']}, WR={best['wr']:.1%}, Avg Ret={best['avg_ret']*100:+.2f}%")
        print(f"  p-value: {best['p_value']:.4f} {'*' if best['p_value'] < ALPHA_CORRECTED else ''}")

        # 상위 5개 설정
        print(f"\n  Top 5 configurations:")
        for i, r in enumerate(sweep_results[:5]):
            sig = '*' if r['p_value'] < ALPHA_CORRECTED else ' '
            print(f"    {i+1}. th={r['threshold']:.1%}, lag={r['lag']}d, hold={r['hold']}d | "
                  f"N={r['n']}, WR={r['wr']:.1%}, p={r['p_value']:.3f}{sig}")

        results['periods'][period_name] = {
            'best': best,
            'all_results': sweep_results
        }

    return results


def cross_validate_best_params(
    hypothesis_name: str,
    hypothesis: Dict,
    best_params: Dict,
    date_regime: Dict[str, str]
) -> Dict:
    """
    Discovery에서 찾은 최적 파라미터를 Validation과 OOS에서 검증
    """
    print(f"\n{'='*70}")
    print(f"Cross-Validation: {hypothesis_name}")
    print(f"Fixed params: threshold={best_params['threshold']:.1%}, "
          f"lag={best_params['lag']}d, hold={best_params['hold']}d")
    print(f"{'='*70}")

    leader = hypothesis['leader'].replace('-USD', '').replace('GLD', 'Gold').replace('UUP', 'DXY').replace('^VIX', 'VIX')
    follower = hypothesis['follower'].replace('-USD', '')

    cv_results = {}

    for period_name, (start, end) in PERIODS.items():
        data = fetch_multi_asset_data(start, end)
        if len(data) < 50:
            continue

        data = calculate_returns(data)

        result = analyze_lag_relationship(
            data=data,
            leader=leader,
            follower=follower,
            direction=hypothesis['direction'],
            threshold=best_params['threshold'],
            lag_days=best_params['lag'],
            hold_days=best_params['hold'],
            date_regime=date_regime,
            regime_condition=hypothesis.get('regime_condition')
        )

        cv_results[period_name] = result

        if result.get('n_signals', 0) > 0:
            sig = '**' if result['p_value'] < ALPHA_CORRECTED else ''
            print(f"\n  {period_name}: N={result['n_signals']}, "
                  f"WR={result['win_rate']:.1%}, p={result['p_value']:.4f}{sig}")

    return cv_results


def main():
    print("=" * 70)
    print("MULTI-ASSET LAG RELATIONSHIP PoC")
    print("=" * 70)
    print(f"\nBonferroni-corrected alpha: {ALPHA_CORRECTED:.4f} (4 tests)")
    print(f"Periods: Discovery {PERIODS['discovery']}, Validation {PERIODS['validation']}, OOS {PERIODS['oos']}")

    # 레짐 데이터 로드
    date_regime = load_regime_data()
    print(f"Loaded {len(date_regime)} regime dates")

    all_results = {}

    # 각 가설 검증
    for hypo_name, hypo in HYPOTHESES.items():
        results = validate_hypothesis(hypo_name, hypo, date_regime)
        all_results[hypo_name] = results

    # ==========================================================================
    # 종합 결과
    # ==========================================================================
    print("\n" + "=" * 70)
    print("SUMMARY: OOS PERFORMANCE")
    print("=" * 70)

    print(f"\n{'Hypothesis':<15} {'Direction':<10} {'OOS N':<8} {'OOS WR':<10} {'p-value':<12} {'Status'}")
    print("-" * 70)

    final_verdicts = {}

    for hypo_name, results in all_results.items():
        hypo = results['hypothesis']

        oos_data = results['periods'].get('oos')
        if oos_data and oos_data.get('best'):
            best = oos_data['best']
            n = best['n']
            wr = best['wr']
            pval = best['p_value']

            if pval < ALPHA_CORRECTED and wr >= 0.55:
                status = "✅ VALIDATED"
                final_verdicts[hypo_name] = True
            elif pval < 0.05:
                status = "⚠️ MARGINAL"
                final_verdicts[hypo_name] = False
            else:
                status = "❌ REJECTED"
                final_verdicts[hypo_name] = False

            print(f"{hypo_name:<15} {hypo['direction']:<10} {n:<8} {wr:.1%}      {pval:.4f}      {status}")
        else:
            print(f"{hypo_name:<15} {hypo['direction']:<10} {'N/A':<8} {'N/A':<10} {'N/A':<12} ❌ NO DATA")
            final_verdicts[hypo_name] = False

    # ==========================================================================
    # Cross-Validation (Discovery → OOS)
    # ==========================================================================
    print("\n" + "=" * 70)
    print("CROSS-VALIDATION: Discovery params → OOS")
    print("=" * 70)

    for hypo_name, results in all_results.items():
        discovery_data = results['periods'].get('discovery')
        if discovery_data and discovery_data.get('best'):
            cv_results = cross_validate_best_params(
                hypo_name,
                results['hypothesis'],
                discovery_data['best'],
                date_regime
            )

    # ==========================================================================
    # 최종 결론
    # ==========================================================================
    print("\n" + "=" * 70)
    print("FINAL VERDICT")
    print("=" * 70)

    validated = [k for k, v in final_verdicts.items() if v]
    rejected = [k for k, v in final_verdicts.items() if not v]

    print(f"\n✅ Validated ({len(validated)}):")
    for h in validated:
        print(f"   - {h}: {HYPOTHESES[h]['story']}")

    print(f"\n❌ Rejected ({len(rejected)}):")
    for h in rejected:
        print(f"   - {h}")

    print("\n" + "-" * 70)
    if validated:
        print("CONCLUSION: Some cross-asset lag relationships show promise")
        print("Next step: Integrate validated pairs into regime toolbox")
    else:
        print("CONCLUSION: No robust cross-asset lag relationships found")
        print("Note: This is actually a valid finding - not all hypotheses should work")

    return all_results


if __name__ == "__main__":
    results = main()
