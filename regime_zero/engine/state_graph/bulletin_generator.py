#!/usr/bin/env python3
"""
⚠️ DEPRECATED - 2025-12-30
==========================
이 파일은 더 이상 사용되지 않습니다.

대체: engine/unified_pipeline.py + engine/generate_bulletin.py

문제:
- SQLite (market_stress.db) 읽기 → 1년 전 오염 데이터
- Neo4j 읽기 → 17시간 전 stale 데이터
- Validation 데이터와 State 계산이 분리됨

새 아키텍처:
  Yahoo Finance → DVSS → State Engine → Bulletin
  (단일 소스, 실시간, 일관성 보장)

===========================

G9 State Adjudication Bulletin Generator v3.4 [LEGACY]
==============================================
Decision ≠ Prediction / Adjudication ≠ Classification

v3.4 Changes:
- DVSS v2.0: 4-Layer Data Validation Scoring System
  L1: Completeness (20%) - 데이터 완결성
  L2: Range (20%) - 물리적 가능 범위
  L3: Rate of Change (35%) - 일간 변화율 ⭐핵심
  L4: Cross-Validation (25%) - 멀티소스 검증
- L3 CRITICAL: >2x threshold = automatic block (DXY -9.4% 차단)
- Grade system: A/B = publish, C = manual, F = blocked

v3.3 Changes:
- DATA VALIDATION GATE: Must pass validation before publishing
- Multi-source cross-validation (yfinance, FRED, local)
- Sanity checks for impossible daily moves (e.g., DXY -9.4%)
- Validation report embedded in bulletin

v3.2 Changes:
- REAL MEASURED VALUES from FRED/Market Data
- Market Stress Snapshot table with Current/Threshold/Status
- Historical context (T-7, T-1, T+0 comparison)

v3.1 Changes:
- Added Summary Layer (human-readable 2-3 sentences)
- Default Action when SUSPENDED
- Input transparency (data sources for each state)
- Transition Zone threshold basis
- Time frame indicators
- CONTESTED status with resolution ETA
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, '.env'))

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hybrid_rag_engine import HybridRAGEngine
from adjudication_engine import AdjudicationEngine, ResolutionStatus

# Data Validator (DVSS v2.0)
try:
    from data_validator import DataValidator, ValidationStatus, DVSSGrade
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False
    print("⚠️ data_validator not available - validation disabled")


# Data source mappings for transparency
STATE_DATA_SOURCES = {
    'LIQUIDITY_STRESS': ['TED Spread', 'Repo Rate', 'FRA-OIS Spread', 'Commercial Paper Rate'],
    'CORRELATION_REGIME_BREAK': ['SPX-Bond Correlation (60d)', 'Cross-Asset R²', 'DXY-Gold Correlation'],
    'DOLLAR_LIQUIDITY_TIGHTENING': ['DXY Index', 'EUR/USD Basis Swap', 'EM Currency Index', 'Offshore USD Rate'],
    'RISK_APPETITE_EXPANSION': ['VIX Level', 'High Yield Spreads', 'Equity Put/Call Ratio'],
    'RISK_APPETITE_SUPPRESSED': ['VIX Term Structure', 'Credit Spreads', 'Safe Haven Flows'],
    'SAFE_HAVEN_DIVERGENCE': ['Gold vs USD', 'JPY vs CHF', 'Treasury vs Bund Spread'],
    'DELEVERAGING_PRESSURE': ['Margin Debt Change', 'Hedge Fund Beta', 'Prime Broker Lending'],
    'MARKET_STRUCTURE_STRAIN': ['Bid-Ask Spreads', 'Market Depth', 'Flash Crash Indicators'],
}

# Transition Zone thresholds (backtest basis)
TZ_THRESHOLDS = {
    'LOW': (0, 2.5),
    'MEDIUM': (2.5, 4.5),
    'HIGH': (4.5, float('inf')),
    'basis': '2018-2024 regime transition events (n=47)'
}

# Default actions per resolution status
DEFAULT_ACTIONS = {
    'RESOLUTION_SUSPENDED': {
        'action': 'Defensive Positioning',
        'allocation': 'Cash 50%, Gold 20%, Short-dated Treasuries 20%, Tail Hedges 10%',
        'rationale': 'Unresolved contradictions = elevated tail risk. Preserve optionality.'
    },
    'RESOLUTION_COMPLETED': {
        'action': 'Standard Risk',
        'allocation': 'Follow strategic allocation',
        'rationale': 'No structural contradictions detected.'
    },
    'RESOLUTION_ACTIVE': {
        'action': 'Reduced Exposure',
        'allocation': 'Reduce risk 30%, increase liquidity buffer',
        'rationale': 'Transition in progress. Wait for resolution direction.'
    }
}

# Market Stress Database Path (VPS or Local)
STRESS_DB_PATHS = [
    '/opt/g9/domains/economy/data/market_stress.db',  # VPS
    os.path.join(BASE_DIR, 'data', 'market_stress.db'),  # Local
]

# Stress indicator display names and thresholds
STRESS_DISPLAY = {
    'VIX': {'name': 'VIX', 'threshold': 25, 'unit': '', 'stress_above': True},
    'IG_SPREAD': {'name': 'IG Credit Spread', 'threshold': 1.5, 'unit': '%', 'stress_above': True},
    'HY_SPREAD': {'name': 'HY Credit Spread', 'threshold': 5.0, 'unit': '%', 'stress_above': True},
    'TED_SPREAD': {'name': 'TED Spread', 'threshold': 0.4, 'unit': '%', 'stress_above': True},
    'REPO_RATE': {'name': 'SOFR (Repo)', 'threshold': 5.5, 'unit': '%', 'stress_above': True},
    'DXY': {'name': 'Dollar Index', 'threshold': 105, 'unit': '', 'stress_above': True},
    '10Y2Y_SPREAD': {'name': '10Y-2Y Spread', 'threshold': 0, 'unit': '%', 'stress_above': False},
    'FED_FUNDS': {'name': 'Fed Funds Rate', 'threshold': 5.0, 'unit': '%', 'stress_above': True},
}


def get_stress_db_path() -> Optional[str]:
    """Find available stress database"""
    for path in STRESS_DB_PATHS:
        if os.path.exists(path):
            return path
    return None


def fetch_market_stress(target_date: str) -> List[Dict]:
    """Fetch market stress data from SQLite"""
    db_path = get_stress_db_path()
    if not db_path:
        return []

    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute('''
            SELECT indicator, value, threshold, unit, is_stressed
            FROM market_stress
            WHERE date = ?
            ORDER BY indicator
        ''', (target_date,)).fetchall()
        conn.close()

        return [
            {
                'indicator': r[0],
                'value': r[1],
                'threshold': r[2],
                'unit': r[3],
                'is_stressed': bool(r[4])
            }
            for r in rows
        ]
    except Exception as e:
        print(f"Warning: Could not fetch stress data: {e}")
        return []


def fetch_stress_history(target_date: str) -> Dict[str, List]:
    """Fetch T-7, T-1, T+0 for trend analysis"""
    db_path = get_stress_db_path()
    if not db_path:
        return {}

    try:
        from datetime import datetime as dt
        target = dt.strptime(target_date, '%Y-%m-%d').date()
        dates = [
            (target - timedelta(days=7)).isoformat(),
            (target - timedelta(days=1)).isoformat(),
            target_date
        ]

        conn = sqlite3.connect(db_path)
        history = {}

        for indicator in STRESS_DISPLAY.keys():
            values = []
            for d in dates:
                row = conn.execute(
                    'SELECT value FROM market_stress WHERE indicator = ? AND date = ?',
                    (indicator, d)
                ).fetchone()
                values.append(row[0] if row else None)
            history[indicator] = values

        conn.close()
        return history
    except Exception as e:
        print(f"Warning: Could not fetch stress history: {e}")
        return {}


def generate_stress_table(stress_data: List[Dict]) -> str:
    """Generate markdown table for stress snapshot"""
    if not stress_data:
        return "*Market stress data not available. Run market_stress_collector.py first.*"

    lines = [
        "| Metric | Current | Threshold | Status |",
        "|--------|---------|-----------|--------|"
    ]

    stressed_count = 0
    for item in stress_data:
        indicator = item['indicator']
        display = STRESS_DISPLAY.get(indicator, {'name': indicator, 'unit': ''})

        value = item['value']
        threshold = item['threshold']
        unit = display.get('unit', item.get('unit', ''))
        is_stressed = item['is_stressed']

        if is_stressed:
            stressed_count += 1
            status = "🔴 STRESSED"
        else:
            status = "✅ Normal"

        name = display.get('name', indicator)
        lines.append(f"| {name} | {value}{unit} | {threshold}{unit} | {status} |")

    lines.append("")
    lines.append(f"**Stressed Indicators:** {stressed_count}/{len(stress_data)}")

    return '\n'.join(lines)


def generate_trend_table(history: Dict[str, List]) -> str:
    """Generate T-7/T-1/T+0 trend table"""
    if not history:
        return "*Historical data not available.*"

    lines = [
        "| Metric | T-7 | T-1 | T+0 | Trend |",
        "|--------|-----|-----|-----|-------|"
    ]

    for indicator, values in history.items():
        if not any(values):
            continue

        display = STRESS_DISPLAY.get(indicator, {'name': indicator})
        name = display.get('name', indicator)

        t7 = f"{values[0]:.2f}" if values[0] else "-"
        t1 = f"{values[1]:.2f}" if values[1] else "-"
        t0 = f"{values[2]:.2f}" if values[2] else "-"

        # Determine trend
        if values[2] and values[0]:
            change = values[2] - values[0]
            if abs(change) < 0.1:
                trend = "➡️ Stable"
            elif change > 0:
                trend = "⬆️ Rising" if display.get('stress_above', True) else "⬆️ Improving"
            else:
                trend = "⬇️ Falling" if display.get('stress_above', True) else "⬇️ Deteriorating"
        else:
            trend = "-"

        lines.append(f"| {name} | {t7} | {t1} | {t0} | {trend} |")

    return '\n'.join(lines)


class BulletinGeneratorV3:
    """State Adjudication Engine v3.2 - Now with Real Measured Values"""

    def __init__(self):
        self.rag = HybridRAGEngine()
        self.adjudicator = AdjudicationEngine()

    def close(self):
        self.rag.close()
        self.adjudicator.close()

    def generate(self, date: str) -> str:
        """Generate full adjudication bulletin with summary"""

        rag_context = self.rag.query(date)
        states = self.adjudicator.get_active_states(date)
        interactions = self.adjudicator.get_interactions(date)
        contradictions = self.adjudicator.detect_contradictions(states, date)
        resolution_status, resolution_reason = self.adjudicator.determine_resolution_status(contradictions)
        tz_level, tz_score, tz_math = self.adjudicator.compute_transition_zone(states, interactions)
        lies = self.adjudicator.identify_lies(states, tz_level, tz_score, contradictions)
        path_a, path_b, asymmetry = self.adjudicator.generate_resolution_paths(states, contradictions)
        watch_conditions = self.adjudicator.generate_watch_conditions(states, contradictions)

        return self._build_bulletin(
            date=date,
            rag_context=rag_context,
            states=states,
            interactions=interactions,
            contradictions=contradictions,
            resolution_status=resolution_status,
            resolution_reason=resolution_reason,
            tz_level=tz_level,
            tz_score=tz_score,
            lies=lies,
            path_a=path_a,
            path_b=path_b,
            asymmetry=asymmetry,
            watch_conditions=watch_conditions,
        )

    def _generate_summary(self, resolution_status, states, contradictions, tz_level, tz_score) -> str:
        """Generate human-readable 2-3 sentence summary"""

        dominant = [s for s in states if s.intensity >= 0.5]
        unresolved = len([c for c in contradictions if c.winner is None])

        if resolution_status == ResolutionStatus.SUSPENDED:
            if tz_score >= 5.0:
                return f"""**오늘의 판단: 보류 (Defensive)**

시장이 이상합니다. {len(dominant)}개의 스트레스 신호가 동시에 발생했는데, {unresolved}개의 구조적 모순이 해결되지 않고 있습니다.

지금 방향성 베팅은 동전 던지기입니다. 시스템이 "모르겠다"고 할 때는 보통 전환점입니다. **현금 비중 높이고 1-2일 기다리세요.**"""
            else:
                return f"""**오늘의 판단: 보류 (관망)**

{unresolved}개의 신호가 서로 충돌 중입니다. 방향이 잡히지 않았습니다.

전환점 리스크가 중간 수준이므로 **기존 포지션 유지하되, 신규 진입은 보류하세요.**"""

        elif resolution_status == ResolutionStatus.COMPLETED:
            return f"""**오늘의 판단: 정상 (Standard Risk)**

구조적 모순이 없습니다. 시스템이 안정 상태입니다.

**전략적 자산배분을 따르세요.** 단, 새로운 스트레스 신호 출현 시 재평가 필요."""

        else:
            return f"""**오늘의 판단: 전환 중 (Reduced Exposure)**

레짐 전환이 진행 중입니다. 방향이 아직 확정되지 않았습니다.

**리스크 30% 축소, 유동성 버퍼 확대하세요.** 해결 방향 확인 후 재진입."""

    def _build_bulletin(self, date: str, rag_context: Dict, states: List,
                        interactions: List, contradictions: List,
                        resolution_status: ResolutionStatus, resolution_reason: str,
                        tz_level, tz_score: float, lies: List,
                        path_a, path_b, asymmetry: str, watch_conditions: List) -> str:

        dominant = [s for s in states if s.intensity >= 0.5]
        undecided = [c for c in contradictions if c.winner is None]

        # Get default action
        default = DEFAULT_ACTIONS.get(resolution_status.value, DEFAULT_ACTIONS['RESOLUTION_SUSPENDED'])

        # Compute metrics
        elevated_count = len([s for s in states if s.level in ["ELEVATED", "HIGH", "PEAK"]])
        peak_count = len([s for s in states if s.level == "PEAK"])
        interaction_count = len(interactions)

        # Generate summary
        summary = self._generate_summary(resolution_status, states, contradictions, tz_level, tz_score)

        # Fetch real market stress data (v3.2)
        stress_data = fetch_market_stress(date)
        stress_table = generate_stress_table(stress_data)
        stress_history = fetch_stress_history(date)
        trend_table = generate_trend_table(stress_history)

        bulletin = f"""# G9 STATE ADJUDICATION BULLETIN

| | |
|---|---|
| **Date** | {date} |
| **Engine** | State Graph Adjudication Engine v3.4 (DVSS) |
| **Time Frame** | Daily Snapshot (T+0) |
| **Resolution** | {resolution_status.value} |

---

## 📋 SUMMARY (의사결정용)

{summary}

### Default Action

| | |
|---|---|
| **Action** | {default['action']} |
| **Suggested Allocation** | {default['allocation']} |
| **Rationale** | {default['rationale']} |

---

## 📊 MARKET STRESS SNAPSHOT (실측값)

{stress_table}

---

## 📈 HISTORICAL CONTEXT (7일 추세)

{trend_table}

---

<details>
<summary><strong>🔍 DETAIL (검증/디버깅용) - 클릭하여 펼치기</strong></summary>

---

## 1️⃣ DOMINANT STATE PRESSURES

"""
        if not dominant:
            bulletin += "*No dominant states detected (all intensities < 0.5)*\n\n"
        else:
            for s in dominant:
                activation = "FULL" if s.is_full_activation else f"PARTIAL ({s.mechanism_count}/3)"
                level_emoji = "🔴" if s.level == "PEAK" else "🟠" if s.level in ["ELEVATED", "HIGH"] else "🟡"

                # Get data sources for this state
                sources = STATE_DATA_SOURCES.get(s.state_id, ['Internal calculation'])
                sources_str = ', '.join(sources)

                bulletin += f"""### {level_emoji} {s.state_id}

| Metric | Value |
|--------|-------|
| Intensity | **{s.intensity:.2f}** |
| Level | {s.level} |
| Activation | {activation} |
| Time Frame | Daily (T+0) |

**Data Sources:** `{sources_str}`

**Active Mechanisms:**
"""
                for m in s.mechanisms:
                    bulletin += f"- `{m}`\n"

                if s.is_full_activation:
                    bulletin += "\n⚠️ **WARNING: ALL MECHANISMS FIRING SIMULTANEOUSLY**\n"
                bulletin += "\n"

        bulletin += f"""---

## 2️⃣ STRUCTURAL CONTRADICTIONS

**Contradiction Count:** {len(contradictions)}
**Unresolved:** {len(undecided)}

"""
        if not contradictions:
            bulletin += "*No structural contradictions detected. System appears coherent.*\n\n"
        else:
            for c in contradictions:
                if c.winner:
                    status = "RESOLVED"
                    status_emoji = "✅"
                    eta = "N/A"
                else:
                    status = "CONTESTED"
                    status_emoji = "⏳"
                    eta = "24-48h or next major data release"

                bulletin += f"""### {status_emoji} [{c.id}]

| | |
|---|---|
| **States Involved** | {', '.join(c.states_involved)} |
| **Status** | **{status}** |
| **Resolution ETA** | {eta} |

**Description:** {c.description}

**Why This Cannot Persist:**
> {c.why_cannot_persist}

**What Must Break:**
> {c.what_must_break}

"""

        bulletin += f"""---

## 3️⃣ RESOLUTION STATUS

```
┌─────────────────────────────────────────┐
│  STATUS: {resolution_status.value:^30} │
└─────────────────────────────────────────┘
```

**Assessment:**
{resolution_reason}

"""
        if resolution_status == ResolutionStatus.SUSPENDED:
            bulletin += """**⚠️ SUSPENSION IS NOT NEUTRALITY**

Suspension = structural inability to resolve, not "waiting to decide."
This state is unstable. Resolution will be forced within 24-72h typically.

"""

        bulletin += f"""---

## 4️⃣ TRANSITION ZONE COMPUTATION

**Explicit Calculation:**

```
┌────────────────────────────────────────┐
│ Elevated State Count    : {elevated_count:>3} × 1.0 = {elevated_count * 1.0:>5.1f} │
│ Peak State Multiplier   : {peak_count:>3} × 2.0 = {peak_count * 2.0:>5.1f} │
│ Interaction Bonus       : {interaction_count:>3} × 0.5 = {interaction_count * 0.5:>5.1f} │
│ Stabilizer Penalty      :   0 × 1.5 =   0.0 │
│────────────────────────────────────────│
│ TOTAL SCORE             :       {tz_score:>5.1f} │
│ THRESHOLD (HIGH)        :       ≥4.5 │
│ CLASSIFICATION          :       {tz_level.value:>5} │
└────────────────────────────────────────┘
```

**Threshold Basis:** {TZ_THRESHOLDS['basis']}

| Level | Range | Current |
|-------|-------|---------|
| LOW | 0 - 2.5 | {"✓" if tz_level.value == "LOW" else ""} |
| MEDIUM | 2.5 - 4.5 | {"✓" if tz_level.value == "MEDIUM" else ""} |
| HIGH | ≥ 4.5 | {"✓" if tz_level.value == "HIGH" else ""} |

---

## 5️⃣ WHAT THE SYSTEM IS LYING ABOUT

"""
        if not lies:
            bulletin += """*No systematic deceptions detected.*

**Note:** This is rare. Markets almost always present misleading signals during stress.

"""
        else:
            for i, lie in enumerate(lies, 1):
                bulletin += f"""### Deception #{i}

**Surface Signal:** "{lie['claim']}"

**Underlying Reality:**
> {lie['reality']}

**Consequence If Believed:**
> {lie['consequence']}

"""

        bulletin += f"""---

## 6️⃣ RESOLUTION PATHS

> ⚠️ These are **structural possibilities**, not predictions.

### PATH A — ESCALATION

| | |
|---|---|
| **Speed** | {path_a.speed} |
| **Conditions Required** | {path_a.condition_count} |

**Trigger Checklist:**
"""
        for t in path_a.triggers:
            bulletin += f"- [ ] {t}\n"

        bulletin += f"""
### PATH B — ABSORPTION

| | |
|---|---|
| **Speed** | {path_b.speed} |
| **Conditions Required** | {path_b.condition_count} |

**Trigger Checklist:**
"""
        for t in path_b.triggers:
            bulletin += f"- [ ] {t}\n"

        bulletin += f"""
---

## 7️⃣ ASYMMETRY ANALYSIS

| Factor | Path A (Escalation) | Path B (Absorption) |
|--------|---------------------|---------------------|
| Conditions Required | {path_a.condition_count} | {path_b.condition_count} |
| Speed Profile | {path_a.speed} | {path_b.speed} |
| Requires Intervention | No | Often |

"""
        if tz_level.value == "HIGH":
            bulletin += """> **BIAS: ESCALATION**
> High transition score = momentum toward instability.
> Escalation requires less "work" than absorption.
"""
        elif len(undecided) > 2:
            bulletin += """> **BIAS: INDETERMINATE**
> Too many unresolved contradictions.
> Wait for at least one to resolve.
"""
        else:
            bulletin += """> **BIAS: NEUTRAL**
> Neither path has structural advantage.
"""

        bulletin += f"""
---

## 8️⃣ WATCH CONDITIONS (48–72h)

"""
        for i, w in enumerate(watch_conditions[:5], 1):
            bulletin += f"""**#{i}: {w['trigger']}**
- Activates: `{w['state_activates']}`
- Implication: {w['implication']}

"""

        bulletin += f"""---

## 9️⃣ FINAL ADJUDICATION

"""
        if resolution_status == ResolutionStatus.SUSPENDED:
            bulletin += f"""### RULING: ADJUDICATION SUSPENDED

**What This Court States:**
- {len(dominant)} dominant state(s) active
- {len(contradictions)} contradiction(s), {len(undecided)} unresolved
- Transition Zone: {tz_score:.1f} ({tz_level.value})

**What This Court Refuses To State:**
- Which path will materialize
- When resolution will occur
- Any single regime label

**The Adjudication:**
> The system is **suspended between incompatible configurations**.
> Unresolved: {', '.join([c.id for c in undecided]) or 'None'}
>
> **The hesitation itself is the signal.**
> Default to defensive positioning until resolution.

"""
        elif resolution_status == ResolutionStatus.COMPLETED:
            bulletin += f"""### RULING: SYSTEM COHERENT

No structural contradictions. Continue standard monitoring.

"""
        else:
            bulletin += f"""### RULING: TRANSITION IN PROGRESS

Resolution actively occurring. Monitor for completion.

"""

        bulletin += f"""</details>

---

*G9 State Adjudication Engine v3.4 (DVSS)*
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S KST')}*
"""

        return bulletin


def main():
    import argparse

    parser = argparse.ArgumentParser(description="G9 State Adjudication Bulletin Generator v3.3")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output", default=None)
    parser.add_argument("--skip-validation", action="store_true", help="Skip data validation (not recommended)")
    parser.add_argument("--force", action="store_true", help="Force generation even if validation fails")
    args = parser.parse_args()

    # ==========================================
    # STEP 1: DATA VALIDATION GATE (DVSS v2.0)
    # ==========================================
    validation_report = None
    if VALIDATOR_AVAILABLE and not args.skip_validation:
        validator = DataValidator(verbose=True)
        validation_report = validator.validate(args.date)

        if not validation_report.can_publish:
            print("\n" + "="*60)
            print("⛔ PUBLICATION BLOCKED")
            print("="*60)
            print(f"\nDVSS Score: {validation_report.total_score:.0f}/100 (Grade: {validation_report.grade.value})")
            print("\nCritical failures:")
            for issue in validation_report.critical_failures:
                print(f"  ❌ {issue}")

            if args.force:
                print("\n⚠️  --force flag detected. Generating anyway (NOT RECOMMENDED)...")
            else:
                print("\nUse --skip-validation to bypass (dangerous)")
                print("Use --force to generate anyway (will include validation warnings)")
                exit(1)

    # ==========================================
    # STEP 2: BULLETIN GENERATION
    # ==========================================
    print("\n" + "="*60)
    print("STEP 2: BULLETIN GENERATION")
    print("="*60 + "\n")

    generator = BulletinGeneratorV3()

    try:
        bulletin = generator.generate(args.date)

        # Inject validation status into bulletin (v3.3)
        if validation_report:
            validation_section = _generate_validation_section(validation_report)
            # Insert after the header section
            bulletin = bulletin.replace(
                "---\n\n## 📋 SUMMARY",
                f"---\n\n{validation_section}\n---\n\n## 📋 SUMMARY"
            )

        print(bulletin)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(bulletin)
            print(f"\n✅ Saved: {args.output}")
        else:
            output_dir = os.path.join(BASE_DIR, "reports/bulletins")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"BULLETIN_{args.date}.md")
            with open(output_path, 'w') as f:
                f.write(bulletin)
            print(f"\n✅ Saved: {output_path}")

    finally:
        generator.close()


def _generate_validation_section(report) -> str:
    """Generate markdown section for DVSS validation status"""
    grade_emoji = {
        DVSSGrade.A: "✅",
        DVSSGrade.B: "✅",
        DVSSGrade.C: "⚠️",
        DVSSGrade.F: "❌",
    }
    emoji = grade_emoji.get(report.grade, "❓")

    lines = [
        f"## {emoji} DATA VALIDATION (DVSS v2.0)",
        "",
        f"**DVSS Score:** {report.total_score:.0f}/100 (Grade {report.grade.value})",
        f"**Publication:** {'✅ APPROVED' if report.can_publish else '🔴 BLOCKED (FORCED)'}",
        "",
        "| Layer | Check | Score | Status |",
        "|-------|-------|-------|--------|",
    ]

    # Layer results
    layers = [
        ("L1", "Completeness", report.l1_completeness),
        ("L2", "Range", report.l2_range),
        ("L3", "Rate of Change", report.l3_rate_of_change),
        ("L4", "Cross-Validation", report.l4_cross_validation),
    ]

    for layer_id, name, result in layers:
        status_icon = "✅" if result.status == ValidationStatus.PASSED else "⚠️" if result.status == ValidationStatus.WARNING else "❌"
        lines.append(f"| {layer_id} | {name} | {result.score:.0f}/100 | {status_icon} |")

    # Current data values
    lines.extend([
        "",
        "**Validated Data:**",
        "",
        "| Indicator | Value | Daily Δ |",
        "|-----------|-------|---------|",
    ])

    current = report.current_data
    previous = report.previous_data

    for indicator in ["VIX", "DXY", "SPX", "GOLD", "BTC", "TNX"]:
        curr = current.get(indicator)
        prev = previous.get(indicator)
        if curr is not None:
            val_str = f"{curr:.2f}"
            if prev and prev != 0:
                pct = ((curr - prev) / prev) * 100
                change_str = f"{pct:+.2f}%"
            else:
                change_str = "-"
            lines.append(f"| {indicator} | {val_str} | {change_str} |")

    # Critical failures
    if report.critical_failures:
        lines.extend([
            "",
            "**🔴 Critical Failures:**",
        ])
        for failure in report.critical_failures:
            lines.append(f"- {failure}")

    # L3 failures (the critical ones)
    if report.l3_rate_of_change.failures:
        lines.extend([
            "",
            "**⚠️ L3 Rate of Change Issues:**",
        ])
        for failure in report.l3_rate_of_change.failures:
            lines.append(f"- {failure}")

    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
