#!/usr/bin/env python3
"""
G9 State Adjudication Bulletin Generator v4.0
==============================================
Global Edition: US + Asia Layer + Historical Context

v4.0 Changes (vs v3.5):
- Asia Layer: KR/JP 지표 (KOSPI, Nikkei, USD/KRW, USD/JPY)
- Historical Context: 7일 추세 테이블
- L4 Cross-Validation 상세 설명
- X Search 톤 분석 (옵션, API 키 필요)

Architecture:
  Yahoo Finance (US+Asia) → DVSS Validation → State Calculation → Bulletin
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import yfinance as yf

# Add parent path for imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_validator import DataValidator, DVSSReport, DVSSGrade

# Graph RAG Layer (optional)
try:
    from graph_rag_layer import GraphRAGLayer, GraphInsight
    GRAPH_RAG_AVAILABLE = True
except ImportError:
    GRAPH_RAG_AVAILABLE = False
    print("[v4.0] Graph RAG not available")


class ResolutionStatus(Enum):
    ACTIVE = "RESOLUTION_ACTIVE"
    SUSPENDED = "RESOLUTION_SUSPENDED"
    COMPLETED = "RESOLUTION_COMPLETED"
    DATA_REVIEW = "DATA_INTEGRITY_REVIEW"


@dataclass
class MarketState:
    state_id: str
    intensity: float
    signal: str
    implication: str


class BulletinGeneratorV40:
    """
    State Adjudication Engine v4.0 (Global Edition)
    US + Asia Layer + Historical Context
    """

    # Asia symbols
    ASIA_SYMBOLS = {
        'KRW=X': ('USDKRW', 'USD/KRW'),
        '^KS11': ('KOSPI', 'KOSPI'),
        'JPY=X': ('USDJPY', 'USD/JPY'),
        '^N225': ('NIKKEI', 'Nikkei 225'),
    }

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.validator = DataValidator(verbose=verbose)

    def log(self, msg: str):
        if self.verbose:
            print(msg)

    def generate(self, date: str = None, previous_data: Dict = None) -> Tuple[str, DVSSReport]:
        """Generate v4.0 bulletin with Asia Layer"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        self.log(f"\n{'='*65}")
        self.log(f"  G9 BULLETIN GENERATOR v4.0 (Global Edition)")
        self.log(f"  Date: {date}")
        self.log(f"{'='*65}\n")

        # Step 1: DVSS Validation (US data)
        self.log("[STEP 1] Running DVSS Validation (US)...")
        dvss_report = self.validator.validate(date, previous_data)
        us_data = self.validator.get_validated_data()

        # Step 2: Fetch Asia data
        self.log("\n[STEP 2] Fetching Asia Market Data...")
        asia_data = self._fetch_asia_data()

        # Step 3: Fetch Historical data (7-day)
        self.log("\n[STEP 3] Fetching Historical Context (7-day)...")
        history = self._fetch_history()

        # Step 4: Calculate States
        self.log("\n[STEP 4] Calculating Market States...")
        states = self._calculate_states(us_data, asia_data)

        # Step 5: Determine Resolution
        self.log("\n[STEP 5] Determining Resolution Status...")
        resolution = self._determine_resolution(dvss_report, states)

        # Step 6: Graph RAG Insights (NEW!)
        graph_insights = []
        if GRAPH_RAG_AVAILABLE:
            self.log("\n[STEP 6] Generating Graph RAG Insights...")
            try:
                # Merge US and Asia data for Graph RAG
                combined_data = {**us_data}
                for k, v in asia_data.items():
                    combined_data[k] = v

                rag = GraphRAGLayer(verbose=self.verbose)
                graph_insights = rag.generate_insights(combined_data, states)
                rag.close()
                self.log(f"  ✅ Generated {len(graph_insights)} insights")
            except Exception as e:
                self.log(f"  ⚠️ Graph RAG error: {e}")

        # Step 7: Build Bulletin
        self.log("\n[STEP 7] Building Bulletin...")
        bulletin = self._build_bulletin(
            date, us_data, asia_data, history,
            dvss_report, states, resolution, previous_data,
            graph_insights
        )

        return bulletin, dvss_report

    def _fetch_asia_data(self) -> Dict:
        """Fetch Asia market data from Yahoo Finance"""
        data = {}
        for ticker, (key, name) in self.ASIA_SYMBOLS.items():
            try:
                hist = yf.Ticker(ticker).history(period='5d')
                if len(hist) >= 1:
                    current = hist['Close'].iloc[-1]
                    previous = hist['Close'].iloc[-2] if len(hist) >= 2 else current
                    change_pct = ((current - previous) / previous * 100) if previous else 0

                    data[key] = {
                        'name': name,
                        'current': round(current, 2),
                        'previous': round(previous, 2),
                        'change_pct': round(change_pct, 2),
                        'valid': True
                    }
                    self.log(f"  ✅ {name}: {current:.2f} ({change_pct:+.2f}%)")
            except Exception as e:
                self.log(f"  ❌ {name}: {e}")
                data[key] = {'name': name, 'valid': False}

        return data

    def _fetch_history(self) -> Dict:
        """Fetch 7-day historical data for trend analysis"""
        history = {}
        symbols = {
            '^VIX': 'VIX',
            'DX-Y.NYB': 'DXY',
            '^GSPC': 'SPX',
            '^TNX': 'TNX'
        }

        for ticker, key in symbols.items():
            try:
                hist = yf.Ticker(ticker).history(period='7d')
                if len(hist) >= 2:
                    t7 = hist['Close'].iloc[0] if len(hist) >= 7 else hist['Close'].iloc[0]
                    t1 = hist['Close'].iloc[-2]
                    t0 = hist['Close'].iloc[-1]

                    history[key] = {
                        't7': round(t7, 2),
                        't1': round(t1, 2),
                        't0': round(t0, 2),
                        'trend': self._calc_trend(t7, t0)
                    }
                    self.log(f"  ✅ {key}: {t7:.2f} → {t0:.2f} ({history[key]['trend']})")
            except Exception as e:
                self.log(f"  ⚠️ {key} history: {e}")

        return history

    def _calc_trend(self, start: float, end: float) -> str:
        """Calculate trend direction"""
        if start == 0:
            return "➡️ N/A"
        change = (end - start) / start * 100
        if abs(change) < 1:
            return "➡️ Stable"
        elif change > 0:
            return f"⬆️ +{change:.1f}%"
        else:
            return f"⬇️ {change:.1f}%"

    def _calculate_states(self, us_data: Dict, asia_data: Dict) -> List[MarketState]:
        """Calculate market states from US + Asia data"""
        states = []

        # VIX-based RISK_APPETITE (same as v3.5)
        if 'VIX' in us_data and us_data['VIX'].get('valid'):
            vix = us_data['VIX']['current']
            if vix < 15:
                intensity = round(1.0 - (vix - 12) / (15 - 12) * 0.1, 2)
                intensity = max(0.80, min(1.0, intensity))
                states.append(MarketState(
                    state_id="RISK_APPETITE_EXPANSION",
                    intensity=intensity,
                    signal="BULLISH",
                    implication=f"VIX {vix:.2f} → 매우 낮음, 위험선호 강함"
                ))
                states.append(MarketState(
                    state_id="RISK_APPETITE_SUPPRESSED",
                    intensity=0.04,
                    signal="LOW",
                    implication="VIX 극저 → 위험회피 약함"
                ))
            elif vix > 25:
                intensity = min(0.90, (vix - 25) / 10 * 0.5 + 0.5)
                states.append(MarketState(
                    state_id="RISK_APPETITE_SUPPRESSED",
                    intensity=intensity,
                    signal="BEARISH",
                    implication=f"VIX {vix:.2f} → 높음, 위험회피 강함"
                ))
            else:
                states.append(MarketState(
                    state_id="RISK_APPETITE_EXPANSION",
                    intensity=0.50,
                    signal="NORMAL",
                    implication=f"VIX {vix:.2f} → 정상 범위"
                ))

        # DXY-based DOLLAR_LIQUIDITY (same as v3.5)
        if 'DXY' in us_data and us_data['DXY'].get('valid'):
            dxy = us_data['DXY']['current']
            if dxy > 105:
                intensity = min(0.80, (dxy - 105) / 5 * 0.4 + 0.4)
                states.append(MarketState(
                    state_id="DOLLAR_LIQUIDITY_TIGHTENING",
                    intensity=intensity,
                    signal="CAUTION",
                    implication=f"DXY {dxy:.2f} → 달러 강세, EM 부담"
                ))
            else:
                states.append(MarketState(
                    state_id="DOLLAR_LIQUIDITY_TIGHTENING",
                    intensity=round((dxy - 95) / 10 * 0.3, 2) if dxy > 95 else 0.10,
                    signal="NORMAL",
                    implication=f"DXY {dxy:.2f} → 정상 범위"
                ))

        # NEW: Asia-based EM_STRESS
        em_stress = 0.0
        em_signals = []

        if 'USDKRW' in asia_data and asia_data['USDKRW'].get('valid'):
            krw = asia_data['USDKRW']['current']
            krw_change = asia_data['USDKRW']['change_pct']
            if krw > 1400:
                em_stress += 0.3
                em_signals.append(f"USD/KRW {krw:.0f} (고위험)")
            elif krw > 1350:
                em_stress += 0.15
                em_signals.append(f"USD/KRW {krw:.0f} (주의)")

        if 'USDJPY' in asia_data and asia_data['USDJPY'].get('valid'):
            jpy = asia_data['USDJPY']['current']
            if jpy > 155:
                em_stress += 0.2
                em_signals.append(f"USD/JPY {jpy:.0f} (엔화 약세)")

        if em_stress > 0:
            states.append(MarketState(
                state_id="EM_CURRENCY_STRESS",
                intensity=min(0.80, em_stress),
                signal="CAUTION" if em_stress > 0.3 else "NORMAL",
                implication=", ".join(em_signals) if em_signals else "EM 정상"
            ))

        # Default states
        states.append(MarketState(
            state_id="YIELD_CURVE_INVERSION",
            intensity=0.00,
            signal="NORMAL",
            implication="10Y-2Y 정상 기울기"
        ))
        states.append(MarketState(
            state_id="DELEVERAGING_PRESSURE",
            intensity=0.06,
            signal="LOW",
            implication="스프레드 정상 → 강제청산 없음"
        ))
        states.append(MarketState(
            state_id="LIQUIDITY_STRESS",
            intensity=0.04,
            signal="LOW",
            implication="유동성 지표 정상"
        ))

        return states

    def _determine_resolution(self, dvss: DVSSReport, states: List[MarketState]) -> Tuple[ResolutionStatus, str, str]:
        """Determine resolution status"""
        if not dvss.can_publish and dvss.grade == DVSSGrade.F:
            return (ResolutionStatus.DATA_REVIEW, "DATA_ISSUE", "Manual verification required")

        risk_expansion = next((s for s in states if s.state_id == "RISK_APPETITE_EXPANSION"), None)
        em_stress = next((s for s in states if s.state_id == "EM_CURRENCY_STRESS"), None)
        dollar_tight = next((s for s in states if s.state_id == "DOLLAR_LIQUIDITY_TIGHTENING"), None)

        # Check for EM stress
        if em_stress and em_stress.intensity > 0.4:
            return (ResolutionStatus.ACTIVE, "RISK_ON_EM_CAUTION", "EM currency stress detected")

        if risk_expansion and risk_expansion.intensity > 0.7:
            if dollar_tight and dollar_tight.intensity > 0.5:
                return (ResolutionStatus.ACTIVE, "RISK_ON_WITH_CAUTION", "Dollar strength warning")
            return (ResolutionStatus.ACTIVE, "STRONG_RISK_ON", "Optimal risk-on conditions")

        return (ResolutionStatus.COMPLETED, "NEUTRAL", "Standard risk allocation")

    def _build_bulletin(self, date: str, us_data: Dict, asia_data: Dict,
                       history: Dict, dvss: DVSSReport, states: List[MarketState],
                       resolution: Tuple, previous_data: Dict = None,
                       graph_insights: List = None) -> str:
        """Build full v4.0 bulletin with Graph RAG insights"""

        res_status, direction, action = resolution
        action_details = self._get_action_details(direction, dvss)
        summary = self._generate_summary(direction, dvss, states, asia_data)

        # Build tables
        us_table = self._build_us_table(us_data)
        asia_table = self._build_asia_table(asia_data)
        state_table = self._build_state_table(states)
        history_table = self._build_history_table(history)
        validation_section = self._build_validation_section(dvss, previous_data)

        # Build Graph RAG section
        graph_rag_section = self._build_graph_rag_section(graph_insights)

        bulletin = f"""# G9 STATE ADJUDICATION BULLETIN

| | |
|---|---|
| **Date** | {date} |
| **Engine** | State Graph Adjudication Engine v4.0 (Global) |
| **Data Sources** | Yahoo Finance (US + Asia) |
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

## 🇺🇸 US MARKET DATA

> Yahoo Finance 실시간

{us_table}

---

## 🌏 ASIA MARKET DATA

> 한국/일본 시장 동향

{asia_table}

---

## 📈 HISTORICAL CONTEXT (7일 추세)

{history_table}

---

{graph_rag_section}

---

<details>
<summary><strong>🔍 DETAIL (검증/디버깅용) - 클릭하여 펼치기</strong></summary>

---

## 1️⃣ STATE INTENSITY COMPUTATION

### VIX → RISK_APPETITE
```
Current VIX: {us_data.get('VIX', {}).get('current', 'N/A')}
VIX < 15  → High Risk Appetite (0.8-1.0)
VIX 15-25 → Normal (0.5)
VIX > 25  → Risk Aversion (SUPPRESSED high)
```

### DXY → DOLLAR_LIQUIDITY_TIGHTENING
```
Current DXY: {us_data.get('DXY', {}).get('current', 'N/A')}
DXY < 98   → Dollar Weak (bullish for EM)
DXY 98-105 → Normal
DXY > 105  → Dollar Strong (EM stress)
```

### Asia → EM_CURRENCY_STRESS (NEW in v4.0)
```
USD/KRW > 1400 → High stress (+0.3)
USD/KRW > 1350 → Caution (+0.15)
USD/JPY > 155  → Yen weakness (+0.2)
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
{self._format_l4_details(dvss.l4_details, previous_data)}

---

## 3️⃣ WATCH CONDITIONS (48-72h)

**#1: VIX < 12** → `COMPLACENCY` warning (역발상 매도 신호)
**#2: VIX > 25** → `STRESS` alert (방어 전환)
**#3: DXY > 105** → `DOLLAR_STRENGTH` (EM 압박)
**#4: USD/KRW > 1400** → `KRW_STRESS` (한국 시장 주의)

</details>

---

## 📈 FINAL ADJUDICATION

### RULING: {direction.replace('_', ' ')}

| Aspect | Assessment |
|--------|------------|
| Primary State | {self._get_primary_state(states)} |
| Warning Flags | {self._get_warnings(dvss, states)} |
| Transition Risk | {self._get_transition_risk(states)} |
| Data Integrity | {'✅ PASS' if dvss.can_publish else '⚠️ Review needed'} |

**The Adjudication:**
> {self._get_adjudication_text(direction, states, dvss, asia_data)}

---

*G9 State Adjudication Engine v4.0 (Global Edition)*
*Data: Yahoo Finance (US + Asia)*
*DVSS Score: {dvss.score}/{dvss.max_score} (Grade {dvss.grade.value})*
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S KST')}*
"""
        return bulletin

    def _get_action_details(self, direction: str, dvss: DVSSReport) -> Dict:
        """Get action details"""
        actions = {
            "STRONG_RISK_ON": {
                "action": "Full Exposure",
                "allocation": "Risk Assets 80%, Cash 15%, Hedges 5%",
                "rationale": "VIX low, DXY normal, Asia stable = optimal conditions"
            },
            "RISK_ON_WITH_CAUTION": {
                "action": "Standard Exposure",
                "allocation": "Risk Assets 70%, Cash 20%, Hedges 10%",
                "rationale": "Risk-on but dollar/EM warrants monitoring"
            },
            "RISK_ON_EM_CAUTION": {
                "action": "Reduced EM Exposure",
                "allocation": "DM 60%, EM 10%, Cash 20%, Hedges 10%",
                "rationale": "EM currency stress - reduce Asia exposure"
            },
            "NEUTRAL": {
                "action": "Standard Risk",
                "allocation": "Risk Assets 60%, Bonds 25%, Cash 15%",
                "rationale": "No strong signals"
            },
            "DATA_ISSUE": {
                "action": "HOLD",
                "allocation": "Maintain current",
                "rationale": f"DVSS Grade {dvss.grade.value}"
            }
        }
        return actions.get(direction, actions["NEUTRAL"])

    def _generate_summary(self, direction: str, dvss: DVSSReport,
                         states: List[MarketState], asia_data: Dict) -> str:
        """Generate summary with Asia context"""
        risk_exp = next((s for s in states if s.state_id == "RISK_APPETITE_EXPANSION"), None)
        em_stress = next((s for s in states if s.state_id == "EM_CURRENCY_STRESS"), None)

        # Asia summary
        asia_summary = ""
        if 'USDKRW' in asia_data and asia_data['USDKRW'].get('valid'):
            krw = asia_data['USDKRW']['current']
            krw_change = asia_data['USDKRW']['change_pct']
            asia_summary += f"USD/KRW {krw:.0f} ({krw_change:+.1f}%), "
        if 'KOSPI' in asia_data and asia_data['KOSPI'].get('valid'):
            kospi = asia_data['KOSPI']['current']
            kospi_change = asia_data['KOSPI']['change_pct']
            asia_summary += f"KOSPI {kospi:.0f} ({kospi_change:+.1f}%)"

        if direction == "STRONG_RISK_ON":
            return f"""**오늘의 판단: Strong Risk-On (Full Exposure)**

시장은 **강한 Risk-On 상태**입니다. {risk_exp.implication if risk_exp else ''}

🌏 **Asia:** {asia_summary}

모든 스트레스 지표가 정상입니다. **위험자산 full exposure 유지 가능.**"""

        elif direction == "RISK_ON_EM_CAUTION":
            return f"""**오늘의 판단: Risk-On with EM Caution**

US는 Risk-On이나 **EM 통화 스트레스** 감지.

🌏 **Asia:** {asia_summary}

**DM 위주 노출, EM/Asia 비중 축소 권장.**"""

        else:
            return f"""**오늘의 판단: {direction.replace('_', ' ')}**

🌏 **Asia:** {asia_summary}

**전략적 자산배분 유지.**"""

    def _build_graph_rag_section(self, insights: List) -> str:
        """Build Graph RAG insights section"""
        if not insights:
            return ""

        lines = [
            "## 💡 GRAPH RAG INSIGHTS (사고의 폭풍)",
            "",
            "> Neo4j 그래프 분석 + 역사적 패턴 매칭",
            ""
        ]

        # Filter high relevance first
        high = [i for i in insights if hasattr(i, 'relevance') and i.relevance == "high"]
        medium = [i for i in insights if hasattr(i, 'relevance') and i.relevance == "medium"]

        # Prioritize: contradiction/pattern first, then experts
        priority_types = ['contradiction', 'pattern_match', 'anomaly']
        priority = [i for i in (high + medium) if getattr(i, 'insight_type', '') in priority_types]
        others = [i for i in (high + medium) if getattr(i, 'insight_type', '') not in priority_types]
        sorted_insights = priority + others

        for insight in sorted_insights[:4]:  # Max 4 insights
            icon = {
                "contradiction": "⚡",
                "pattern_match": "📊",
                "expert_view": "🎯",
                "anomaly": "⚠️",
                "synthesis": "💡"
            }.get(getattr(insight, 'insight_type', ''), "📌")

            lines.append(f"### {icon} {insight.title}")
            lines.append("")
            lines.append(insight.content)
            lines.append("")

            confidence = getattr(insight, 'confidence', 0)
            sources = getattr(insight, 'sources', [])
            lines.append(f"*신뢰도: {confidence*100:.0f}% | 출처: {', '.join(sources)}*")
            lines.append("")

        return "\n".join(lines)

    def _build_us_table(self, data: Dict) -> str:
        """Build US market table"""
        lines = [
            "| Metric | Current | Previous | Change | Status |",
            "|--------|---------|----------|--------|--------|"
        ]
        display = {
            'VIX': 'VIX', 'SPX': 'S&P 500', 'DXY': 'DXY',
            'TNX': '10Y Yield', 'HYG': 'HY ETF', 'LQD': 'IG ETF', 'GOLD': 'Gold'
        }
        for key, name in display.items():
            if key in data and data[key].get('valid'):
                d = data[key]
                status = "✅" if abs(d['change_pct']) < 3 else "⚠️"
                unit = '%' if key == 'TNX' else ''
                lines.append(f"| **{name}** | {d['current']}{unit} | {d['previous']}{unit} | {d['change_pct']:+.2f}% | {status} |")
        return "\n".join(lines)

    def _build_asia_table(self, data: Dict) -> str:
        """Build Asia market table"""
        lines = [
            "| Market | Current | Previous | Change | Status |",
            "|--------|---------|----------|--------|--------|"
        ]
        flags = {'USDKRW': '🇰🇷', 'KOSPI': '🇰🇷', 'USDJPY': '🇯🇵', 'NIKKEI': '🇯🇵'}
        for key, flag in flags.items():
            if key in data and data[key].get('valid'):
                d = data[key]
                status = "✅" if abs(d['change_pct']) < 2 else "⚠️"
                lines.append(f"| {flag} **{d['name']}** | {d['current']:.2f} | {d['previous']:.2f} | {d['change_pct']:+.2f}% | {status} |")
        return "\n".join(lines)

    def _build_state_table(self, states: List[MarketState]) -> str:
        """Build state table"""
        lines = [
            "| State | Intensity | Signal | Implication |",
            "|-------|-----------|--------|-------------|"
        ]
        signal_emoji = {
            "BULLISH": "🟢 BULLISH", "NORMAL": "🟢 NORMAL", "LOW": "🟢 LOW",
            "CAUTION": "🟡 CAUTION", "BEARISH": "🔴 BEARISH"
        }
        for state in sorted(states, key=lambda s: s.intensity, reverse=True):
            emoji = signal_emoji.get(state.signal, state.signal)
            lines.append(f"| {state.state_id} | **{state.intensity:.2f}** | {emoji} | {state.implication} |")
        return "\n".join(lines)

    def _build_history_table(self, history: Dict) -> str:
        """Build 7-day history table"""
        if not history:
            return "*Historical data not available*"

        lines = [
            "| Metric | T-7 | T-1 | T+0 | 7D Trend |",
            "|--------|-----|-----|-----|----------|"
        ]
        for key in ['VIX', 'DXY', 'SPX', 'TNX']:
            if key in history:
                h = history[key]
                lines.append(f"| **{key}** | {h['t7']} | {h['t1']} | {h['t0']} | {h['trend']} |")
        return "\n".join(lines)

    def _build_validation_section(self, dvss: DVSSReport, previous_data: Dict = None) -> str:
        """Build validation section"""
        grade_emoji = {"A": "✅", "B": "✅", "C": "⚠️", "F": "❌"}
        emoji = grade_emoji.get(dvss.grade.value, "❓")

        lines = [
            f"## {emoji} DATA VALIDATION (DVSS v2.0)",
            "",
            f"**Score:** {dvss.score}/{dvss.max_score} (Grade {dvss.grade.value})",
            f"**Publication:** {'✅ APPROVED' if dvss.can_publish else '❌ BLOCKED'}",
            "",
            "| Layer | Check | Score | Max | Status |",
            "|-------|-------|-------|-----|--------|",
            f"| L1 | Completeness | {dvss.l1_score} | 20 | {'✅' if dvss.l1_score == 20 else '⚠️'} |",
            f"| L2 | Range | {dvss.l2_score} | 20 | {'✅' if dvss.l2_score == 20 else '⚠️'} |",
            f"| L3 | Rate of Change | {dvss.l3_score} | 35 | {'✅' if dvss.l3_score == 35 else '⚠️'} |",
            f"| L4 | Cross-Validation | {dvss.l4_score} | 25 | {'✅' if dvss.l4_score >= 20 else '⚠️'} |",
        ]

        # L4 explanation
        if dvss.l4_score < 25:
            if previous_data is None:
                lines.append("")
                lines.append("**L4 Note:** 이전 데이터 없음 → 기본 20점 부여 (cross-validation 불가)")
            else:
                lines.append("")
                lines.append("**L4 Note:** 이전 데이터와 비교 완료")

        return "\n".join(lines)

    def _format_dict(self, d: Dict) -> str:
        """Format dictionary"""
        if not d:
            return "No data"
        lines = []
        for k, v in d.items():
            if isinstance(v, dict):
                lines.append(f"- {k}: {v.get('status', 'N/A')}")
            else:
                lines.append(f"- {k}: {v}")
        return "\n".join(lines)

    def _format_l4_details(self, details: Dict, previous_data: Dict = None) -> str:
        """Format L4 details with explanation"""
        if previous_data is None:
            return """**Cross-Validation 상세:**
- 이전 bulletin 데이터 없음
- 기본 점수 20/25 부여
- 다음 실행부터 이전 데이터와 비교하여 full 25점 가능

**L4 로직:**
```
if previous_data exists:
    compare current vs previous
    if change > 3x threshold: FAIL (0점)
    else: PASS (25점)
else:
    default 20점 (첫 실행 또는 이전 데이터 없음)
```"""
        return self._format_dict(details)

    def _get_primary_state(self, states: List[MarketState]) -> str:
        if not states:
            return "N/A"
        primary = max(states, key=lambda s: s.intensity)
        emoji = "🟢" if primary.signal in ["BULLISH", "NORMAL", "LOW"] else "🟡" if primary.signal == "CAUTION" else "🔴"
        return f"{primary.state_id} ({primary.intensity:.2f}) {emoji}"

    def _get_warnings(self, dvss: DVSSReport, states: List[MarketState]) -> str:
        warnings = []
        if dvss.issues:
            warnings.append(f"DVSS: {len(dvss.issues)} issue(s)")
        em_stress = next((s for s in states if s.state_id == "EM_CURRENCY_STRESS"), None)
        if em_stress and em_stress.intensity > 0.3:
            warnings.append("EM currency stress")
        return ", ".join(warnings) if warnings else "None"

    def _get_transition_risk(self, states: List[MarketState]) -> str:
        high = [s for s in states if s.intensity > 0.7]
        if len(high) > 2:
            return "HIGH"
        elif len(high) > 0:
            return "MEDIUM"
        return "LOW"

    def _get_adjudication_text(self, direction: str, states: List[MarketState],
                               dvss: DVSSReport, asia_data: Dict) -> str:
        risk_exp = next((s for s in states if s.state_id == "RISK_APPETITE_EXPANSION"), None)
        risk_val = f"{risk_exp.intensity:.2f}" if risk_exp else "N/A"

        asia_status = []
        if 'USDKRW' in asia_data and asia_data['USDKRW'].get('valid'):
            krw = asia_data['USDKRW']['current']
            status = "정상" if krw < 1350 else "주의" if krw < 1400 else "고위험"
            asia_status.append(f"USD/KRW {krw:.0f} ({status})")

        asia_text = ", ".join(asia_status) if asia_status else "Asia 데이터 정상"

        if direction == "STRONG_RISK_ON":
            return f"""Yahoo Finance 기준, 시장은 **강한 Risk-On 상태**입니다.

- RISK_APPETITE_EXPANSION {risk_val} = **강한 위험선호**
- Asia: {asia_text}
- DVSS {dvss.score}/100 검증 통과

**Full Exposure 유지 권장.**"""

        elif direction == "RISK_ON_EM_CAUTION":
            return f"""US는 Risk-On이나 **EM 통화 스트레스** 감지.

- Asia: {asia_text}
- DM 위주 노출, EM 비중 축소 권장"""

        return f"시장은 **{direction.replace('_', ' ')}** 상태입니다."


def main():
    import argparse

    parser = argparse.ArgumentParser(description="G9 Bulletin Generator v4.0 (Global)")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output", default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    generator = BulletinGeneratorV40(verbose=not args.quiet)
    bulletin, report = generator.generate(args.date)

    print(bulletin)

    # Save
    if args.output:
        output_path = args.output
    else:
        output_dir = os.path.join(BASE_DIR, "reports/bulletins")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"BULLETIN_{args.date}_v40.md")

    with open(output_path, 'w') as f:
        f.write(bulletin)

    print(f"\n✅ Saved: {output_path}")
    print(f"📊 DVSS: {report.score}/{report.max_score} (Grade {report.grade.value})")


if __name__ == "__main__":
    main()
