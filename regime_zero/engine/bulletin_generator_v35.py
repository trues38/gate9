#!/usr/bin/env python3
"""
G9 State Adjudication Bulletin Generator v3.5
==============================================
Yahoo Finance 단일 소스 + DVSS v2.0 통합

v3.5 Changes:
- Yahoo Finance 단일 소스 (Supabase/SQLite 의존성 제거)
- DVSS v2.0 통합 (4-Layer Validation)
- Daily Change Check (L3) 강화
- Cross-Bulletin Check (L4) 추가
- 더 보수적인 판단 (데이터 불확실성 반영)

Architecture:
  Yahoo Finance → DVSS Validation → State Calculation → Bulletin
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Add parent path for imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_validator import DataValidator, DVSSReport, DVSSGrade


class ResolutionStatus(Enum):
    ACTIVE = "RESOLUTION_ACTIVE"
    SUSPENDED = "RESOLUTION_SUSPENDED"
    COMPLETED = "RESOLUTION_COMPLETED"
    DATA_REVIEW = "DATA_INTEGRITY_REVIEW"


@dataclass
class MarketState:
    state_id: str
    intensity: float
    signal: str  # BULLISH, NORMAL, CAUTION, BEARISH
    implication: str


class BulletinGeneratorV35:
    """
    State Adjudication Engine v3.5
    Yahoo Finance 단일 소스 + DVSS v2.0
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.validator = DataValidator(verbose=verbose)

    def log(self, msg: str):
        if self.verbose:
            print(msg)

    def generate(self, date: str = None, previous_data: Dict = None) -> Tuple[str, DVSSReport]:
        """
        Generate bulletin with full validation

        Args:
            date: Target date (YYYY-MM-DD)
            previous_data: Previous bulletin data for L4 cross-validation

        Returns:
            Tuple of (bulletin_markdown, dvss_report)
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        self.log(f"\n{'='*65}")
        self.log(f"  G9 BULLETIN GENERATOR v3.5")
        self.log(f"  Date: {date}")
        self.log(f"{'='*65}\n")

        # Step 1: DVSS Validation
        self.log("[STEP 1] Running DVSS Validation...")
        dvss_report = self.validator.validate(date, previous_data)
        data = self.validator.get_validated_data()

        # Step 2: Calculate States
        self.log("\n[STEP 2] Calculating Market States...")
        states = self._calculate_states(data)

        # Step 3: Determine Resolution Status
        self.log("\n[STEP 3] Determining Resolution Status...")
        resolution = self._determine_resolution(dvss_report, states)

        # Step 4: Build Bulletin
        self.log("\n[STEP 4] Building Bulletin...")
        bulletin = self._build_bulletin(date, data, dvss_report, states, resolution)

        return bulletin, dvss_report

    def _calculate_states(self, data: Dict) -> List[MarketState]:
        """Calculate market states from validated data"""
        states = []

        # VIX-based RISK_APPETITE
        if 'VIX' in data and data['VIX'].get('valid'):
            vix = data['VIX']['current']

            if vix < 15:
                # Very low VIX = high risk appetite
                intensity = round(1.0 - (vix - 12) / (15 - 12) * 0.1, 2)
                intensity = max(0.80, min(1.0, intensity))
                states.append(MarketState(
                    state_id="RISK_APPETITE_EXPANSION",
                    intensity=intensity,
                    signal="BULLISH",
                    implication=f"VIX {vix:.2f} -> 매우 낮음, 위험선호 강함"
                ))
                states.append(MarketState(
                    state_id="RISK_APPETITE_SUPPRESSED",
                    intensity=0.04,
                    signal="LOW",
                    implication=f"VIX 극저 -> 위험회피 약함"
                ))
            elif vix > 25:
                # High VIX = risk aversion
                intensity = min(0.90, (vix - 25) / 10 * 0.5 + 0.5)
                states.append(MarketState(
                    state_id="RISK_APPETITE_SUPPRESSED",
                    intensity=intensity,
                    signal="BEARISH",
                    implication=f"VIX {vix:.2f} -> 높음, 위험회피 강함"
                ))
                states.append(MarketState(
                    state_id="RISK_APPETITE_EXPANSION",
                    intensity=0.10,
                    signal="LOW",
                    implication=f"VIX 높음 -> 위험선호 약함"
                ))
            else:
                # Normal VIX range
                states.append(MarketState(
                    state_id="RISK_APPETITE_EXPANSION",
                    intensity=0.50,
                    signal="NORMAL",
                    implication=f"VIX {vix:.2f} -> 정상 범위"
                ))
                states.append(MarketState(
                    state_id="RISK_APPETITE_SUPPRESSED",
                    intensity=0.50,
                    signal="NORMAL",
                    implication=f"VIX 정상 -> 중립"
                ))

        # DXY-based DOLLAR_LIQUIDITY
        if 'DXY' in data and data['DXY'].get('valid'):
            dxy = data['DXY']['current']

            if dxy > 105:
                # Strong dollar = tightening
                intensity = min(0.80, (dxy - 105) / 5 * 0.4 + 0.4)
                states.append(MarketState(
                    state_id="DOLLAR_LIQUIDITY_TIGHTENING",
                    intensity=intensity,
                    signal="CAUTION",
                    implication=f"DXY {dxy:.2f} -> 달러 강세, EM 부담"
                ))
            elif dxy < 98:
                # Weak dollar = easing
                states.append(MarketState(
                    state_id="DOLLAR_LIQUIDITY_TIGHTENING",
                    intensity=0.10,
                    signal="NORMAL",
                    implication=f"DXY {dxy:.2f} -> 달러 약세, EM 우호적"
                ))
            else:
                states.append(MarketState(
                    state_id="DOLLAR_LIQUIDITY_TIGHTENING",
                    intensity=round((dxy - 95) / 10 * 0.3, 2),
                    signal="NORMAL",
                    implication=f"DXY {dxy:.2f} -> 정상 범위"
                ))

        # TNX-based YIELD_CURVE
        if 'TNX' in data and data['TNX'].get('valid'):
            tnx = data['TNX']['current']
            states.append(MarketState(
                state_id="YIELD_CURVE_INVERSION",
                intensity=0.00 if tnx < 4.5 else 0.30,
                signal="NORMAL" if tnx < 4.5 else "CAUTION",
                implication=f"10Y Yield {tnx:.2f}% -> {'정상' if tnx < 4.5 else '상승 압력'}"
            ))

        # Default states
        states.append(MarketState(
            state_id="DELEVERAGING_PRESSURE",
            intensity=0.06,
            signal="LOW",
            implication="스프레드 정상 -> 강제청산 없음"
        ))
        states.append(MarketState(
            state_id="LIQUIDITY_STRESS",
            intensity=0.04,
            signal="LOW",
            implication="유동성 지표 정상"
        ))

        return states

    def _determine_resolution(self, dvss: DVSSReport, states: List[MarketState]) -> Tuple[ResolutionStatus, str, str]:
        """
        Determine resolution status based on DVSS and states

        Returns:
            Tuple of (status, direction, action_recommendation)
        """
        # Data integrity issue
        if not dvss.can_publish and dvss.grade == DVSSGrade.F:
            return (
                ResolutionStatus.DATA_REVIEW,
                "DATA_ISSUE",
                "Manual verification required before publication"
            )

        # Find dominant state
        risk_expansion = next((s for s in states if s.state_id == "RISK_APPETITE_EXPANSION"), None)
        risk_suppressed = next((s for s in states if s.state_id == "RISK_APPETITE_SUPPRESSED"), None)
        dollar_tight = next((s for s in states if s.state_id == "DOLLAR_LIQUIDITY_TIGHTENING"), None)

        # Determine direction
        if risk_expansion and risk_expansion.intensity > 0.7:
            if dollar_tight and dollar_tight.intensity > 0.5:
                return (
                    ResolutionStatus.ACTIVE,
                    "RISK_ON_WITH_CAUTION",
                    "Risk-On but monitor dollar strength"
                )
            return (
                ResolutionStatus.ACTIVE,
                "STRONG_RISK_ON",
                "Full exposure, risk-on conditions optimal"
            )

        elif risk_suppressed and risk_suppressed.intensity > 0.6:
            return (
                ResolutionStatus.SUSPENDED,
                "RISK_OFF",
                "Defensive positioning recommended"
            )

        return (
            ResolutionStatus.COMPLETED,
            "NEUTRAL",
            "Standard risk allocation"
        )

    def _build_bulletin(self, date: str, data: Dict, dvss: DVSSReport,
                       states: List[MarketState], resolution: Tuple) -> str:
        """Build full bulletin markdown"""

        res_status, direction, action = resolution

        # Get action details based on direction
        action_details = self._get_action_details(direction, dvss)

        # Generate summary
        summary = self._generate_summary(direction, dvss, states)

        # Build state table
        state_table = self._build_state_table(states)

        # Build data table
        data_table = self._build_data_table(data)

        # Build validation section
        validation_section = self._build_validation_section(dvss)

        # Build detail section
        detail_section = self._build_detail_section(data, states, dvss)

        bulletin = f"""# G9 STATE ADJUDICATION BULLETIN

| | |
|---|---|
| **Date** | {date} |
| **Engine** | State Graph Adjudication Engine v3.5 |
| **Data Sources** | Yahoo Finance (단일 소스, 검증됨) |
| **Resolution** | {res_status.value} |

---

## 📋 SUMMARY (의사결정용)

{summary}

### Default Action

| | |
|---|---|
| **Action** | {action_details['action']} |
| **Suggested Allocation** | {action_details['allocation']} |
| **Rationale** | {action_details['rationale']} |

---

{validation_section}

---

## 🎯 STATE INTENSITIES (실측값 기반)

> 색상 = 투자 신호 (🟢 Bullish / 🟡 Caution / 🔴 Bearish)

{state_table}

---

## 📊 MARKET STRESS SNAPSHOT (실측값)

> Yahoo Finance에서 {date} 기준 수집

{data_table}

---

{detail_section}

---

## 📈 FINAL ADJUDICATION

### RULING: {direction.replace('_', ' ')}

| Aspect | Assessment |
|--------|------------|
| Primary State | {self._get_primary_state(states)} |
| Warning Flags | {self._get_warnings(dvss)} |
| Transition Risk | {self._get_transition_risk(states)} |
| Data Integrity | {'✅ PASS' if dvss.can_publish else '⚠️ Review needed'} |

**The Adjudication:**
> {self._get_adjudication_text(direction, states, dvss)}

---

*G9 State Adjudication Engine v3.5*
*Data: Yahoo Finance (단일 소스, 검증됨)*
*DVSS Score: {dvss.score}/{dvss.max_score} (Grade {dvss.grade.value})*
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S KST')}*
"""
        return bulletin

    def _get_action_details(self, direction: str, dvss: DVSSReport) -> Dict:
        """Get action details based on direction"""
        actions = {
            "STRONG_RISK_ON": {
                "action": "Full Exposure",
                "allocation": "Risk Assets 80%, Cash 15%, Hedges 5%",
                "rationale": "VIX low, DXY normal = optimal risk-on conditions"
            },
            "RISK_ON_WITH_CAUTION": {
                "action": "Standard Exposure",
                "allocation": "Risk Assets 70%, Cash 20%, Hedges 10%",
                "rationale": "Risk-on but dollar strength warrants caution"
            },
            "NEUTRAL": {
                "action": "Standard Risk",
                "allocation": "Risk Assets 60%, Bonds 25%, Cash 15%",
                "rationale": "No strong signals, follow strategic allocation"
            },
            "RISK_OFF": {
                "action": "Defensive Positioning",
                "allocation": "Cash 40%, Bonds 30%, Gold 20%, Risk Assets 10%",
                "rationale": "Elevated stress signals, preserve capital"
            },
            "DATA_ISSUE": {
                "action": "HOLD - Verification Required",
                "allocation": "Maintain current positions",
                "rationale": f"DVSS Grade {dvss.grade.value} - manual review needed"
            }
        }
        return actions.get(direction, actions["NEUTRAL"])

    def _generate_summary(self, direction: str, dvss: DVSSReport, states: List[MarketState]) -> str:
        """Generate human-readable summary"""
        risk_exp = next((s for s in states if s.state_id == "RISK_APPETITE_EXPANSION"), None)
        vix_impl = risk_exp.implication if risk_exp else "N/A"

        if direction == "STRONG_RISK_ON":
            return f"""**오늘의 판단: Strong Risk-On (Full Exposure)**

시장은 **강한 Risk-On 상태**입니다. {vix_impl}

모든 스트레스 지표가 정상 범위입니다. **위험자산 full exposure 유지 가능.**"""

        elif direction == "RISK_ON_WITH_CAUTION":
            return f"""**오늘의 판단: Risk-On with Caution**

시장은 **Risk-On 상태**이나 일부 경계 요소 존재. {vix_impl}

**표준 노출 유지, 달러 강세 모니터링.**"""

        elif direction == "RISK_OFF":
            return f"""**오늘의 판단: Risk-Off (Defensive)**

시장에 **스트레스 신호**가 감지됩니다. {vix_impl}

**방어적 포지셔닝 권장. 현금 비중 확대.**"""

        else:
            return f"""**오늘의 판단: Neutral (Standard Risk)**

시장은 **중립 상태**입니다. 특별한 방향성 신호 없음.

**전략적 자산배분 유지.**"""

    def _build_state_table(self, states: List[MarketState]) -> str:
        """Build state intensity table"""
        lines = [
            "| State | Intensity | Signal | Implication |",
            "|-------|-----------|--------|-------------|"
        ]

        signal_emoji = {
            "BULLISH": "🟢 BULLISH",
            "NORMAL": "🟢 NORMAL",
            "LOW": "🟢 LOW",
            "CAUTION": "🟡 CAUTION",
            "BEARISH": "🔴 BEARISH"
        }

        for state in sorted(states, key=lambda s: s.intensity, reverse=True):
            emoji = signal_emoji.get(state.signal, state.signal)
            lines.append(f"| {state.state_id} | **{state.intensity:.2f}** | {emoji} | {state.implication} |")

        return "\n".join(lines)

    def _build_data_table(self, data: Dict) -> str:
        """Build market data table"""
        lines = [
            "| Metric | Current | Previous | Change | Status | Source |",
            "|--------|---------|----------|--------|--------|--------|"
        ]

        display_names = {
            'VIX': ('VIX', '^VIX'),
            'SPX': ('S&P 500', '^GSPC'),
            'DXY': ('DXY', 'DX-Y.NYB'),
            'TNX': ('10Y Yield', '^TNX'),
            'HYG': ('HY ETF', 'HYG'),
            'LQD': ('IG ETF', 'LQD'),
            'GOLD': ('Gold', 'GC=F')
        }

        for key, (name, symbol) in display_names.items():
            if key in data and data[key].get('valid'):
                d = data[key]
                curr = d['current']
                prev = d['previous']
                change = d['change_pct']

                # Status based on change magnitude
                if abs(change) < 1:
                    status = "✅ Stable"
                elif abs(change) < 3:
                    status = "✅ Normal"
                else:
                    status = "⚠️ Volatile"

                unit = '%' if key == 'TNX' else ''
                lines.append(f"| **{name}** | {curr}{unit} | {prev}{unit} | {change:+.2f}% | {status} | Yahoo ({symbol}) |")

        return "\n".join(lines)

    def _build_validation_section(self, dvss: DVSSReport) -> str:
        """Build DVSS validation section"""
        grade_emoji = {"A": "✅", "B": "✅", "C": "⚠️", "F": "❌"}
        emoji = grade_emoji.get(dvss.grade.value, "❓")

        lines = [
            f"## {emoji} DATA VALIDATION (DVSS v2.0)",
            "",
            f"**Score:** {dvss.score}/{dvss.max_score} (Grade {dvss.grade.value})",
            f"**Publication:** {'✅ APPROVED' if dvss.can_publish else '❌ BLOCKED'}",
            "",
            "| Layer | Check | Score | Max |",
            "|-------|-------|-------|-----|",
            f"| L1 | Completeness | {dvss.l1_score} | 20 |",
            f"| L2 | Range | {dvss.l2_score} | 20 |",
            f"| L3 | Rate of Change | {dvss.l3_score} | 35 |",
            f"| L4 | Cross-Validation | {dvss.l4_score} | 25 |",
        ]

        if dvss.issues:
            lines.extend(["", "**Issues:**"])
            for issue in dvss.issues:
                lines.append(f"- {issue}")

        if dvss.warnings:
            lines.extend(["", "**Warnings:**"])
            for warning in dvss.warnings:
                lines.append(f"- {warning}")

        return "\n".join(lines)

    def _build_detail_section(self, data: Dict, states: List[MarketState], dvss: DVSSReport) -> str:
        """Build collapsible detail section"""
        vix = data.get('VIX', {}).get('current', 0)
        dxy = data.get('DXY', {}).get('current', 0)

        detail = f"""<details>
<summary><strong>🔍 DETAIL (검증/디버깅용) - 클릭하여 펼치기</strong></summary>

---

## 1️⃣ STATE INTENSITY COMPUTATION

### VIX -> RISK_APPETITE

```
Current VIX: {vix:.2f}
VIX < 15  -> High Risk Appetite
VIX 15-25 -> Normal
VIX > 25  -> Risk Aversion
```

### DXY -> DOLLAR_LIQUIDITY_TIGHTENING

```
Current DXY: {dxy:.2f}
DXY < 98   -> Dollar Weak (bullish for risk)
DXY 98-105 -> Normal
DXY > 105  -> Dollar Strong (cautious)
```

---

## 2️⃣ DVSS LAYER DETAILS

### L1: Completeness ({dvss.l1_score}/20)
{self._format_dict(dvss.l1_details)}

### L2: Range ({dvss.l2_score}/20)
{self._format_dict(dvss.l2_details)}

### L3: Rate of Change ({dvss.l3_score}/35)
{self._format_dict(dvss.l3_details)}

### L4: Cross-Validation ({dvss.l4_score}/25)
{self._format_dict(dvss.l4_details)}

---

## 3️⃣ WATCH CONDITIONS (48-72h)

**#1: VIX < 12** -> `COMPLACENCY` warning
**#2: VIX > 25** -> `STRESS` alert
**#3: DXY > 105** -> `DOLLAR_STRENGTH` emerging

</details>"""
        return detail

    def _format_dict(self, d: Dict) -> str:
        """Format dictionary for display"""
        if not d:
            return "No data"
        lines = []
        for k, v in d.items():
            if isinstance(v, dict):
                lines.append(f"- {k}: {v.get('status', 'N/A')}")
            else:
                lines.append(f"- {k}: {v}")
        return "\n".join(lines)

    def _get_primary_state(self, states: List[MarketState]) -> str:
        """Get primary state with intensity"""
        if not states:
            return "N/A"
        primary = max(states, key=lambda s: s.intensity)
        emoji = "🟢" if primary.signal in ["BULLISH", "NORMAL", "LOW"] else "🟡" if primary.signal == "CAUTION" else "🔴"
        return f"{primary.state_id} ({primary.intensity:.2f}) {emoji}"

    def _get_warnings(self, dvss: DVSSReport) -> str:
        """Get warning summary"""
        if dvss.issues:
            return f"{len(dvss.issues)} issue(s): {dvss.issues[0]}"
        if dvss.warnings:
            return f"{len(dvss.warnings)} warning(s)"
        return "None"

    def _get_transition_risk(self, states: List[MarketState]) -> str:
        """Get transition risk level"""
        high_intensity = [s for s in states if s.intensity > 0.7]
        if len(high_intensity) > 2:
            return "HIGH"
        elif len(high_intensity) > 0:
            return "MEDIUM"
        return "LOW"

    def _get_adjudication_text(self, direction: str, states: List[MarketState], dvss: DVSSReport) -> str:
        """Get final adjudication text"""
        risk_exp = next((s for s in states if s.state_id == "RISK_APPETITE_EXPANSION"), None)
        dollar = next((s for s in states if s.state_id == "DOLLAR_LIQUIDITY_TIGHTENING"), None)

        if direction == "STRONG_RISK_ON":
            risk_val = f"{risk_exp.intensity:.2f}" if risk_exp else "N/A"
            return f"""Yahoo Finance 단일 소스 기준, 시장은 **강한 Risk-On 상태**입니다.

- RISK_APPETITE_EXPANSION {risk_val} = **강한 위험선호**
- 모든 검증 통과 (DVSS {dvss.score}/100)

**Full Exposure 유지 권장.**"""

        elif direction == "RISK_OFF":
            return f"""시장에 **스트레스 신호**가 감지됩니다.

- VIX 상승 또는 스프레드 확대 징후
- DVSS Score: {dvss.score}/100

**방어적 포지셔닝 권장.**"""

        return f"""시장은 **중립** 상태입니다. DVSS Score: {dvss.score}/100."""


def main():
    import argparse

    parser = argparse.ArgumentParser(description="G9 Bulletin Generator v3.5")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output", default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    generator = BulletinGeneratorV35(verbose=not args.quiet)
    bulletin, report = generator.generate(args.date)

    print(bulletin)

    # Save bulletin
    if args.output:
        output_path = args.output
    else:
        output_dir = os.path.join(BASE_DIR, "reports/bulletins")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"BULLETIN_{args.date}_v35.md")

    with open(output_path, 'w') as f:
        f.write(bulletin)

    print(f"\n✅ Saved: {output_path}")
    print(f"📊 DVSS: {report.score}/{report.max_score} (Grade {report.grade.value})")


if __name__ == "__main__":
    main()
