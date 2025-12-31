"""
HUMAN-IN-THE-LOOP Decision Gate

"이 신호에 내 인생 자금을 태울 가치가 있는가?"

자동화가 아니라 '결심을 대신해주는 시스템'
모든 조건 YES → 고민 없이 투입
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

from datetime import datetime
from dataclasses import dataclass
from typing import List, Tuple
from btc_engine.meta.law_health_monitor import (
    LawHealthMonitor,
    RegimeDriftDetector,
    CapitalDeploymentEngine
)


@dataclass
class DecisionCheck:
    """개별 체크 항목"""
    name: str
    passed: bool
    value: str
    threshold: str


@dataclass
class DecisionGate:
    """최종 결정 게이트"""
    timestamp: str
    law_active: bool

    checks: List[DecisionCheck]
    all_passed: bool

    verdict: str  # 'DEPLOY', 'HOLD', 'REJECT'
    confidence: str  # 'HIGH', 'MEDIUM', 'LOW'

    action_text: str


class HumanDecisionGate:
    """인간 결정 지원 시스템"""

    # 투입 기준
    HEALTH_THRESHOLD = 85
    VOL_ASYMMETRY_MIN = 0.0  # 하락일 거래량 >= 상승일

    def __init__(self):
        self.health_monitor = LawHealthMonitor()
        self.drift_detector = RegimeDriftDetector()

    def evaluate(self, law_active: bool = None) -> DecisionGate:
        """신호 발생 시 투입 여부 평가"""

        # 데이터 수집
        health = self.health_monitor.calculate_health()
        drift = self.drift_detector.detect_drift()

        checks = []

        # 1. META Health ≥ 85?
        health_pass = health.health_score >= self.HEALTH_THRESHOLD
        checks.append(DecisionCheck(
            name="META Health",
            passed=health_pass,
            value=f"{health.health_score:.0f}",
            threshold=f"≥ {self.HEALTH_THRESHOLD}"
        ))

        # 2. Drift = NONE?
        drift_pass = not drift.drift_detected
        checks.append(DecisionCheck(
            name="Regime Drift",
            passed=drift_pass,
            value="NONE" if drift_pass else "DETECTED",
            threshold="NONE"
        ))

        # 3. Vol Asymmetry 유지? (하락일 거래량 > 상승일)
        asym_pass = drift.vol_asymmetry >= self.VOL_ASYMMETRY_MIN
        checks.append(DecisionCheck(
            name="Vol Asymmetry",
            passed=asym_pass,
            value=f"{drift.vol_asymmetry:+.2f}",
            threshold=f"≥ {self.VOL_ASYMMETRY_MIN}"
        ))

        # 4. ETF 구조 이슈 없음?
        etf_issues = []
        if drift.ibit_vol_trend == 'declining':
            etf_issues.append("Vol declining")
        if drift.btc_ibit_corr_30d < 0.7:
            etf_issues.append("Low correlation")

        etf_pass = len(etf_issues) == 0
        checks.append(DecisionCheck(
            name="ETF Structure",
            passed=etf_pass,
            value="OK" if etf_pass else ", ".join(etf_issues),
            threshold="No issues"
        ))

        # 최종 판정
        all_passed = all(c.passed for c in checks)
        passed_count = sum(1 for c in checks if c.passed)

        # Law 활성 여부 (자동 감지 또는 수동 입력)
        if law_active is None:
            # 실제 시장 데이터로 Law 체크
            from btc_engine.alerts.etf_law_monitor import ETFLawMonitor
            monitor = ETFLawMonitor(channels=[])
            state = monitor.fetch_market_data()
            law_active = state.law_active if state else False

        # Verdict 결정
        if not law_active:
            verdict = 'HOLD'
            confidence = 'HIGH'
            action_text = "Law 신호 없음. 현금/단기채 유지."
        elif all_passed:
            verdict = 'DEPLOY'
            confidence = 'HIGH'
            action_text = "✅ 모든 조건 충족. 50% 투입 가능."
        elif passed_count >= 3:
            verdict = 'DEPLOY'
            confidence = 'MEDIUM'
            action_text = f"⚠️ {4-passed_count}개 조건 미충족. 30% 보수적 투입."
        elif passed_count >= 2:
            verdict = 'HOLD'
            confidence = 'MEDIUM'
            action_text = "⏸️ 조건 부족. 신호 대기."
        else:
            verdict = 'REJECT'
            confidence = 'HIGH'
            action_text = "❌ 다수 조건 실패. 투입 금지."

        return DecisionGate(
            timestamp=datetime.now().isoformat(),
            law_active=law_active,
            checks=checks,
            all_passed=all_passed,
            verdict=verdict,
            confidence=confidence,
            action_text=action_text
        )


def print_decision_gate(law_active: bool = None):
    """결정 게이트 출력"""

    gate = HumanDecisionGate()
    decision = gate.evaluate(law_active)

    # 헤더
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 12 + "HUMAN-IN-THE-LOOP DECISION GATE" + " " * 13 + "║")
    print("║" + " " * 10 + '"내 인생 자금을 태울 가치가 있는가?"' + " " * 10 + "║")
    print("╠" + "═" * 58 + "╣")

    # Law Status
    law_icon = "🟢" if decision.law_active else "⚪"
    law_text = "ACTIVE" if decision.law_active else "INACTIVE"
    print(f"║  LAW STATUS: {law_icon} {law_text:<40} ║")
    print("╠" + "═" * 58 + "╣")

    # Checklist
    print("║  CHECKLIST:                                              ║")
    print("║" + "─" * 58 + "║")

    for check in decision.checks:
        icon = "✅" if check.passed else "❌"
        name = f"{check.name}:"
        value = f"{check.value}"
        threshold = f"({check.threshold})"
        print(f"║  {icon} {name:<18} {value:<12} {threshold:<18} ║")

    print("╠" + "═" * 58 + "╣")

    # Verdict
    verdict_icons = {'DEPLOY': '🚀', 'HOLD': '⏸️', 'REJECT': '🚫'}
    verdict_icon = verdict_icons.get(decision.verdict, '❓')

    print(f"║  VERDICT: {verdict_icon} {decision.verdict:<10} (Confidence: {decision.confidence})" + " " * 14 + "║")
    print("╠" + "═" * 58 + "╣")

    # Action
    action_lines = [decision.action_text[i:i+52] for i in range(0, len(decision.action_text), 52)]
    for line in action_lines:
        print(f"║  {line:<56} ║")

    print("╚" + "═" * 58 + "╝")
    print()

    # 투입 가능 시 추가 정보
    if decision.verdict == 'DEPLOY' and decision.all_passed:
        print("  📋 ACTION PLAN:")
        print("  ─────────────────────────────────────")
        print("  • Direction: LONG BTC")
        print("  • Size: 50% of deployment capital")
        print("  • TP: +7%")
        print("  • SL: -5%")
        print("  • Max Hold: 10 days")
        print("  ─────────────────────────────────────")
        print("  → 고민 없이 실행")
        print()


def main():
    """메인 실행"""
    import argparse

    parser = argparse.ArgumentParser(description="Human Decision Gate")
    parser.add_argument("--law-active", action="store_true", help="Assume law is active")
    parser.add_argument("--law-inactive", action="store_true", help="Assume law is inactive")
    args = parser.parse_args()

    if args.law_active:
        print_decision_gate(law_active=True)
    elif args.law_inactive:
        print_decision_gate(law_active=False)
    else:
        # 자동 감지
        print_decision_gate(law_active=None)


if __name__ == "__main__":
    main()
