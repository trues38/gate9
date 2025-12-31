"""
Law Decision System

법칙을 "의사결정 시스템"으로 완성

STEP 1: Law Priority Matrix (동시 활성 충돌 해결)
STEP 2: Law Coverage Analysis (공백 구간 파악)
STEP 3: 추가 Law 후보 (1개만)
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import json
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

# =============================================================================
# 현재 Law Registry
# =============================================================================

LAWS = {
    'GOLD_BTC': {
        'name': 'Gold Safe-Haven Flow',
        'cause': 'GLD',
        'effect': 'BTC-USD',
        'asset_class': 'crypto',
        'direction': 'positive',
        'threshold': 0.03,
        'lag': 5,
        'hold': 7,
        'regime_gate': ['Gold Safe-Haven'],
        'oos_wr': 0.727,
        'p_value': 0.033,
        'priority': 1,  # 가장 높은 우선순위 (가장 잘 검증됨)
    },
    'TLT_TECH': {
        'name': 'Rate-Sensitive Growth',
        'cause': 'TLT',
        'effect': 'XLK',
        'asset_class': 'equity',
        'direction': 'positive',
        'threshold': 0.05,
        'lag': 1,
        'hold': 7,
        'regime_gate': None,  # 전체 기간
        'oos_wr': 0.944,
        'p_value': 0.0001,
        'priority': 1,
    },
    'VIX_CREDIT': {
        'name': 'VIX-Credit Spread',
        'cause': '^VIX',
        'effect': 'HYG',
        'asset_class': 'credit',
        'direction': 'negative',
        'threshold': 0.04,
        'lag': 4,
        'hold': 10,
        'regime_gate': ['Goldilocks', 'Equity Complacency'],
        'oos_wr': 0.727,
        'p_value': 0.026,
        'priority': 2,
    },
}


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


def fetch_data(tickers: List[str], start: str, end: str) -> pd.DataFrame:
    """데이터 다운로드"""
    data = pd.DataFrame()
    for ticker in tickers:
        try:
            df = yf.download(ticker, start=start, end=end, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            clean = ticker.replace('-', '_').replace('^', '')
            if len(df) > 0:
                data[f'{clean}_Close'] = df['Close']
        except:
            pass
    return data.ffill().dropna()


# =============================================================================
# STEP 1: Law Priority Matrix
# =============================================================================

def build_priority_matrix():
    """
    Law 간 동시 활성 충돌 매트릭스

    질문: 두 개 이상의 Law가 동시에 켜지면?
    - 같은 자산군 → 우선순위 높은 것만
    - 다른 자산군 → 비중 분배
    """
    print("\n" + "=" * 70)
    print("STEP 1: LAW PRIORITY MATRIX")
    print("=" * 70)

    # 자산군별 그룹핑
    by_asset_class = defaultdict(list)
    for law_id, law in LAWS.items():
        by_asset_class[law['asset_class']].append((law_id, law))

    print("\n1.1 Asset Class Grouping")
    print("-" * 50)
    for asset_class, laws in by_asset_class.items():
        print(f"\n  {asset_class.upper()}:")
        for law_id, law in sorted(laws, key=lambda x: x[1]['priority']):
            print(f"    P{law['priority']}: {law['name']} (WR={law['oos_wr']:.0%})")

    # 충돌 규칙 정의
    print("\n1.2 Conflict Resolution Rules")
    print("-" * 50)

    rules = """
    ┌─────────────────────────────────────────────────────────────────┐
    │  PRIORITY RULES                                                 │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                 │
    │  Rule 1: 같은 자산군 충돌                                       │
    │    → 우선순위(P) 높은 Law만 실행                                │
    │    → 동일 P면 p-value 낮은 것 우선                              │
    │                                                                 │
    │  Rule 2: 다른 자산군 동시 활성                                  │
    │    → 모든 Law 실행 (비중 분배)                                  │
    │    → 기본 비중: 균등 (33% each)                                 │
    │    → WR 가중 비중: WR 비례 배분                                 │
    │                                                                 │
    │  Rule 3: 레짐 불일치                                            │
    │    → 해당 Law 비활성화                                          │
    │    → "아무것도 안 함"이 정답일 수 있음                          │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘
    """
    print(rules)

    # 시나리오 예시
    print("\n1.3 Scenario Examples")
    print("-" * 50)

    scenarios = [
        {
            'name': 'Gold Safe-Haven + Goldilocks (불가능)',
            'regime': 'Gold Safe-Haven Fortress',
            'active': ['GOLD_BTC'],
            'action': 'BTC만 진입 (100%)',
        },
        {
            'name': 'Goldilocks 단독',
            'regime': 'Goldilocks Equilibrium',
            'active': ['TLT_TECH', 'VIX_CREDIT'],
            'action': 'XLK 50% + HYG 50% (다른 자산군)',
        },
        {
            'name': 'Equity Melt-Up',
            'regime': 'Equity Complacency Melt-Up',
            'active': ['TLT_TECH', 'VIX_CREDIT'],
            'action': 'XLK 50% + HYG 50%',
        },
        {
            'name': 'Hawkish Tightening',
            'regime': 'Hawkish Tightening Grind',
            'active': ['TLT_TECH'],  # VIX_CREDIT 레짐 불일치
            'action': 'XLK만 (TLT 신호 시)',
        },
        {
            'name': 'Risk-Off Capitulation',
            'regime': 'Risk-Off Capitulation',
            'active': [],  # 모든 Law 비활성
            'action': '⚠️ CASH - 아무것도 하지 않음',
        },
    ]

    for s in scenarios:
        print(f"\n  Scenario: {s['name']}")
        print(f"    Regime: {s['regime']}")
        print(f"    Active Laws: {s['active'] if s['active'] else 'None'}")
        print(f"    → Action: {s['action']}")

    return by_asset_class


# =============================================================================
# STEP 2: Law Coverage Analysis
# =============================================================================

def analyze_coverage(date_to_regime: Dict[str, str], data: pd.DataFrame):
    """
    Law Coverage 분석

    각 Law가:
    - 전체 시간의 몇 %를 커버하는지
    - 공백 구간이 언제인지
    """
    print("\n" + "=" * 70)
    print("STEP 2: LAW COVERAGE ANALYSIS")
    print("=" * 70)

    # 분석 기간 설정
    start_date = "2020-01-01"
    end_date = "2024-12-31"

    dates = sorted([d for d in date_to_regime.keys()
                   if start_date <= d <= end_date])

    total_days = len(dates)
    print(f"\n  Analysis Period: {start_date} ~ {end_date}")
    print(f"  Total Days: {total_days}")

    # 각 Law의 레짐 커버리지
    print("\n2.1 Regime Coverage by Law")
    print("-" * 70)

    coverage = {}

    for law_id, law in LAWS.items():
        regime_gate = law.get('regime_gate')

        if regime_gate is None:
            # 전체 기간 적용
            covered_days = total_days
            covered_dates = dates
        else:
            # 특정 레짐만
            covered_dates = [d for d in dates
                           if any(g in date_to_regime.get(d, '') for g in regime_gate)]
            covered_days = len(covered_dates)

        pct = covered_days / total_days * 100
        coverage[law_id] = {
            'days': covered_days,
            'pct': pct,
            'dates': covered_dates
        }

        regime_str = ', '.join(regime_gate) if regime_gate else 'ALL'
        print(f"  {law['name']:<30} {covered_days:>5} days ({pct:>5.1f}%) | {regime_str[:30]}")

    # 전체 커버리지 (하나 이상의 Law 활성)
    print("\n2.2 Combined Coverage")
    print("-" * 70)

    any_law_active = set()
    for law_id, cov in coverage.items():
        any_law_active.update(cov['dates'])

    combined_pct = len(any_law_active) / total_days * 100
    gap_days = total_days - len(any_law_active)
    gap_pct = gap_days / total_days * 100

    print(f"  At least 1 Law active:  {len(any_law_active)} days ({combined_pct:.1f}%)")
    print(f"  ⚠️ GAP (no Law active): {gap_days} days ({gap_pct:.1f}%)")

    # 공백 구간 상세
    print("\n2.3 Gap Analysis (No Law Active)")
    print("-" * 70)

    gap_dates = [d for d in dates if d not in any_law_active]
    gap_by_regime = defaultdict(int)

    for d in gap_dates:
        regime = date_to_regime.get(d, 'Unknown')
        gap_by_regime[regime] += 1

    print("\n  Gap days by regime:")
    for regime, count in sorted(gap_by_regime.items(), key=lambda x: -x[1]):
        pct = count / len(gap_dates) * 100 if gap_dates else 0
        print(f"    {regime[:40]:<40} {count:>4} days ({pct:>5.1f}%)")

    # 공백 구간 = 새 Law 후보 영역
    print("\n2.4 Gap Regimes → New Law Opportunity")
    print("-" * 70)

    top_gap_regimes = sorted(gap_by_regime.items(), key=lambda x: -x[1])[:3]
    print("\n  Top 3 uncovered regimes:")
    for regime, count in top_gap_regimes:
        print(f"    • {regime}: {count} days")
        print(f"      → 이 레짐에서 작동하는 Law 후보 필요")

    return coverage, gap_by_regime


# =============================================================================
# STEP 3: New Law Candidate (1개만)
# =============================================================================

def propose_new_law(gap_by_regime: Dict[str, int]):
    """
    추가 Law 후보 (1개만, 다른 자산군/메커니즘)

    조건:
    - 기존 Law와 다른 자산군
    - Gap regime 커버 가능
    - 메커니즘 설명 가능
    """
    print("\n" + "=" * 70)
    print("STEP 3: NEW LAW CANDIDATE (1개만)")
    print("=" * 70)

    # 기존 커버리지
    existing = {
        'crypto': 'GOLD_BTC',
        'equity': 'TLT_TECH',
        'credit': 'VIX_CREDIT',
    }

    print("\n  현재 커버된 자산군:")
    for ac, law in existing.items():
        print(f"    ✓ {ac}: {law}")

    print("\n  미커버 자산군:")
    uncovered = ['commodities', 'fx', 'em_equity', 'real_assets']
    for ac in uncovered:
        print(f"    ○ {ac}")

    # 후보 제안
    print("\n3.1 New Law Candidates")
    print("-" * 70)

    candidates = [
        {
            'id': 'REAL_RATES_GOLD',
            'name': 'Real Rates → Gold',
            'cause': 'TIP',           # TIPS (실질금리 proxy: TIP 상승 = 실질금리 하락)
            'effect': 'GLD',
            'asset_class': 'commodities',
            'direction': 'positive',  # 실질금리 하락 → Gold 상승
            'mechanism': '실질금리 하락 → 금 보유 기회비용 감소 → 금 수요 증가',
            'expected_lag': (5, 10),
            'regime_gate': ['Dovish Pivot', 'Risk-Off'],
            'gap_coverage': ['Dovish Pivot', 'Risk-Off'],
            'rationale': '기존 Law가 커버 못하는 Dovish/Risk-Off 구간 타겟',
        },
        {
            'id': 'USD_LIQUIDITY_EM',
            'name': 'USD Liquidity → EM',
            'cause': 'UUP',           # Dollar Index
            'effect': 'EEM',          # EM ETF
            'asset_class': 'em_equity',
            'direction': 'negative',  # 달러 약세 → EM 상승
            'mechanism': '달러 유동성 확대 → 신흥국 자본 유입 → EM 상승',
            'expected_lag': (7, 14),
            'regime_gate': ['Reflation Rally', 'Goldilocks'],
            'gap_coverage': ['Reflation Rally'],
            'rationale': '글로벌 자금 흐름, 다른 자산군',
        },
    ]

    for c in candidates:
        print(f"\n  Candidate: {c['name']}")
        print(f"    {c['cause']} → {c['effect']} ({c['direction']})")
        print(f"    Asset Class: {c['asset_class']}")
        print(f"    Mechanism: {c['mechanism'][:60]}...")
        print(f"    Gap Coverage: {c['gap_coverage']}")
        print(f"    Rationale: {c['rationale']}")

    # 추천
    print("\n3.2 Recommendation")
    print("-" * 70)

    print("""
    ┌─────────────────────────────────────────────────────────────────┐
    │  RECOMMENDED: Real Rates → Gold                                 │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                 │
    │  이유:                                                          │
    │  1. 기존 Law와 다른 자산군 (commodities)                        │
    │  2. Gap regime (Dovish Pivot, Risk-Off) 커버                   │
    │  3. 메커니즘 명확 (실질금리 ↔ 금)                               │
    │  4. 데이터 충분 (TIP, GLD 모두 유동성 높음)                     │
    │                                                                 │
    │  다음 단계:                                                     │
    │  → Law Pipeline으로 검증                                        │
    │  → 5대 조건 테스트                                              │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘
    """)

    return candidates[0]  # REAL_RATES_GOLD


# =============================================================================
# 현재 상태 대시보드
# =============================================================================

def current_status_dashboard(date_to_regime: Dict[str, str]):
    """현재 시점 Law 상태 대시보드"""
    print("\n" + "=" * 70)
    print("CURRENT STATUS DASHBOARD")
    print("=" * 70)

    # 최신 날짜
    today = datetime.now().strftime('%Y-%m-%d')
    regime = date_to_regime.get(today, 'Unknown')

    # 어제 데이터로 대체 (오늘 데이터 없을 수 있음)
    recent_dates = sorted([d for d in date_to_regime.keys() if d <= today])
    if recent_dates:
        latest_date = recent_dates[-1]
        regime = date_to_regime.get(latest_date, 'Unknown')
    else:
        latest_date = today

    print(f"\n  Date: {latest_date}")
    print(f"  Current Regime: {regime}")

    # 활성 Law 체크
    print("\n  Law Activation Status:")
    print("-" * 50)

    active_laws = []

    for law_id, law in LAWS.items():
        regime_gate = law.get('regime_gate')

        if regime_gate is None:
            status = "🟢 STANDBY (waiting for signal)"
            active_laws.append(law_id)
        elif any(g in regime for g in regime_gate):
            status = "🟢 ACTIVE REGIME"
            active_laws.append(law_id)
        else:
            status = "⚫ DISABLED (wrong regime)"

        print(f"    {law['name']:<30} {status}")

    # 행동 지침
    print("\n  Action Guidance:")
    print("-" * 50)

    if not active_laws:
        print("""
    ⚠️ NO LAW ACTIVE

    Current regime does not match any Law's gate.
    → STAY IN CASH
    → Monitor for regime transition
        """)
    else:
        print(f"\n    Active Laws: {active_laws}")
        print(f"    → Monitor {', '.join([LAWS[l]['cause'] for l in active_laws])} for signals")
        print(f"    → Ready to deploy into {', '.join([LAWS[l]['effect'] for l in active_laws])}")


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 70)
    print("LAW DECISION SYSTEM")
    print("=" * 70)

    # 데이터 로드
    date_to_regime = load_regime_data()

    # STEP 1: Priority Matrix
    by_asset_class = build_priority_matrix()

    # STEP 2: Coverage Analysis
    tickers = ['GLD', 'BTC-USD', 'TLT', 'XLK', '^VIX', 'HYG']
    data = fetch_data(tickers, "2020-01-01", "2024-12-31")
    coverage, gap_by_regime = analyze_coverage(date_to_regime, data)

    # STEP 3: New Law Candidate
    new_law = propose_new_law(gap_by_regime)

    # Current Status
    current_status_dashboard(date_to_regime)

    # 최종 요약
    print("\n" + "=" * 70)
    print("SUMMARY: LAW DECISION SYSTEM")
    print("=" * 70)

    print("""
    ┌─────────────────────────────────────────────────────────────────┐
    │  현재 Law Registry (3개)                                        │
    │    • GOLD_BTC:   Gold Safe-Haven → BTC (crypto)                │
    │    • TLT_TECH:   TLT → XLK (equity)                            │
    │    • VIX_CREDIT: VIX → HYG (credit)                            │
    ├─────────────────────────────────────────────────────────────────┤
    │  Priority Rules                                                 │
    │    • 같은 자산군 충돌 → P 높은 것만                              │
    │    • 다른 자산군 → 비중 분배                                    │
    │    • 레짐 불일치 → CASH                                        │
    ├─────────────────────────────────────────────────────────────────┤
    │  Coverage                                                       │
    │    • Gap regime: Dovish Pivot, Risk-Off                        │
    │    • 추천 추가 Law: Real Rates → Gold                          │
    └─────────────────────────────────────────────────────────────────┘
    """)

    return {
        'priority_matrix': by_asset_class,
        'coverage': coverage,
        'gap_regimes': gap_by_regime,
        'new_law_candidate': new_law
    }


if __name__ == "__main__":
    results = main()
