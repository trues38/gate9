"""
Graph RAG - 경제 레짐 Graph DB 연동 모듈

Neo4j 기반 경제 레짐 분석:
- 현재 레짐 조회
- 전이 확률 예측
- BTC 성과 조합 분석
"""
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from neo4j import GraphDatabase


@dataclass
class RegimeTransition:
    """레짐 전이 정보"""
    from_regime: str
    to_regime: str
    probability: float
    count: int


@dataclass
class BTCRegimePerformance:
    """레짐별 BTC 성과"""
    regime: str
    win_rate: float
    avg_return: float
    samples: int

    @property
    def grade(self) -> str:
        if self.win_rate >= 0.6 and self.avg_return > 2:
            return "S"
        elif self.win_rate >= 0.55 and self.avg_return > 1:
            return "A"
        elif self.win_rate >= 0.5:
            return "B"
        elif self.win_rate >= 0.45:
            return "C"
        else:
            return "D"


@dataclass
class MacroContext:
    """매크로 컨텍스트 - Graph RAG 결과"""
    current_regime: str
    current_family: str
    regime_description: str

    # 전이 예측
    next_regime_predictions: List[RegimeTransition]

    # BTC 성과
    current_btc_performance: Optional[BTCRegimePerformance]
    next_btc_performance: Optional[BTCRegimePerformance]

    # 권고
    position_size_modifier: float  # 1.0 = 기본, 0.5 = 절반, 1.5 = 확대
    risk_warning: Optional[str]
    opportunity_signal: Optional[str]

    def to_dict(self) -> dict:
        return {
            "current_regime": self.current_regime,
            "current_family": self.current_family,
            "regime_description": self.regime_description[:200],
            "next_predictions": [
                {"regime": t.to_regime, "prob": f"{t.probability:.1%}"}
                for t in self.next_regime_predictions[:3]
            ],
            "btc_grade": self.current_btc_performance.grade if self.current_btc_performance else "N/A",
            "position_modifier": self.position_size_modifier,
            "risk_warning": self.risk_warning,
            "opportunity": self.opportunity_signal
        }


class EconomicRegimeGraph:
    """경제 레짐 Graph DB 클라이언트"""

    def __init__(self, uri: str = "bolt://localhost:7687",
                 user: str = "neo4j", password: str = "regime2024"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

        # 날짜→Family 캐시 (파일에서 로드)
        self._date_family_cache = {}
        self._load_date_family_cache()

    def _load_date_family_cache(self):
        """날짜→Family 매핑 캐시 로드"""
        try:
            with open('/Users/js/Documents/btc-macro/data/regime_families.json', 'r') as f:
                families = json.load(f)
            for fam in families:
                for date in fam.get('member_dates', []):
                    self._date_family_cache[date] = fam['family_name']
        except Exception as e:
            print(f"캐시 로드 실패: {e}")

    def close(self):
        self.driver.close()

    def get_current_regime(self, date: str = None) -> Tuple[Optional[str], Optional[str]]:
        """현재 날짜의 레짐 조회"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        # 캐시에서 Family 조회
        family = self._date_family_cache.get(date)

        # Neo4j에서 상세 레짐 조회
        with self.driver.session() as session:
            result = session.run("""
                MATCH (r:Regime {date: $date})
                RETURN r.name as name, r.description as desc
            """, date=date)

            record = result.single()
            if record:
                return record['name'], family or "Unknown"

            # 가장 가까운 과거 날짜 찾기
            result = session.run("""
                MATCH (r:Regime)
                WHERE r.date <= $date
                RETURN r.name as name, r.date as date
                ORDER BY r.date DESC
                LIMIT 1
            """, date=date)

            record = result.single()
            if record:
                closest_family = self._date_family_cache.get(record['date'])
                return record['name'], closest_family or "Unknown"

        return None, family

    def get_transition_probabilities(self, family: str) -> List[RegimeTransition]:
        """특정 Family에서의 전이 확률"""
        transitions = []

        with self.driver.session() as session:
            result = session.run("""
                MATCH (f1:Family {name: $family})-[t:TRANSITIONS_TO]->(f2:Family)
                RETURN f2.name as to_regime, t.probability as prob, t.count as count
                ORDER BY t.probability DESC
            """, family=family)

            for record in result:
                transitions.append(RegimeTransition(
                    from_regime=family,
                    to_regime=record['to_regime'],
                    probability=record['prob'],
                    count=record['count']
                ))

        return transitions

    def get_btc_performance(self, family: str) -> Optional[BTCRegimePerformance]:
        """특정 Family의 BTC 성과"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (f:Family {name: $family})-[p:BTC_PERFORMANCE]->(a:Asset {name: 'BTC'})
                RETURN p.win_rate as win_rate, p.avg_return as avg_return, p.samples as samples
            """, family=family)

            record = result.single()
            if record:
                return BTCRegimePerformance(
                    regime=family,
                    win_rate=record['win_rate'],
                    avg_return=record['avg_return'],
                    samples=record['samples']
                )

        return None

    def get_path_analysis(self, from_family: str, depth: int = 2) -> List[dict]:
        """N-hop 경로 분석"""
        paths = []

        with self.driver.session() as session:
            # 2-hop 경로
            result = session.run("""
                MATCH path = (f1:Family {name: $family})-[t1:TRANSITIONS_TO]->(f2:Family)-[t2:TRANSITIONS_TO]->(f3:Family)
                WHERE t1.probability > 0.1 AND t2.probability > 0.1
                RETURN f2.name as mid, f3.name as end,
                       t1.probability as p1, t2.probability as p2,
                       t1.probability * t2.probability as combined_prob
                ORDER BY combined_prob DESC
                LIMIT 5
            """, family=from_family)

            for record in result:
                paths.append({
                    'path': f"{from_family} → {record['mid']} → {record['end']}",
                    'combined_probability': record['combined_prob'],
                    'steps': [
                        {'to': record['mid'], 'prob': record['p1']},
                        {'to': record['end'], 'prob': record['p2']}
                    ]
                })

        return paths

    def get_regime_context(self, date: str = None) -> MacroContext:
        """현재 날짜 기준 전체 매크로 컨텍스트"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        # 1. 현재 레짐
        regime_name, family = self.get_current_regime(date)

        # 2. 레짐 설명
        description = ""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (r:Regime {date: $date})
                RETURN r.description as desc
            """, date=date)
            record = result.single()
            if record:
                description = record['desc'] or ""

        # 3. 전이 예측
        transitions = self.get_transition_probabilities(family) if family else []

        # 4. BTC 성과
        current_btc = self.get_btc_performance(family) if family else None
        next_btc = None
        if transitions:
            next_btc = self.get_btc_performance(transitions[0].to_regime)

        # 5. 권고 생성
        position_modifier = 1.0
        risk_warning = None
        opportunity = None

        if current_btc:
            if current_btc.grade == "D":
                position_modifier = 0.0
                risk_warning = f"{family}: BTC 롱 불리 (승률 {current_btc.win_rate:.0%}, {current_btc.avg_return:+.1f}%)"
            elif current_btc.grade == "C":
                position_modifier = 0.5
                risk_warning = f"{family}: 신중한 접근 필요"
            elif current_btc.grade in ["S", "A"]:
                position_modifier = 1.2
                opportunity = f"{family}: BTC 롱 유리 (승률 {current_btc.win_rate:.0%}, {current_btc.avg_return:+.1f}%)"

        # 전이 예측 기반 추가 조정
        if transitions and len(transitions) > 0:
            top_next = transitions[0]
            if top_next.to_regime == "Hawkish Tightening Grind" and top_next.probability > 0.2:
                risk_warning = f"주의: Hawkish Tightening 전이 가능성 {top_next.probability:.0%}"
                position_modifier *= 0.7
            elif top_next.to_regime in ["Weak Dollar Risk-On Boom", "Reflation Rally"] and top_next.probability > 0.3:
                opportunity = f"기회: {top_next.to_regime} 전이 가능성 {top_next.probability:.0%}"
                position_modifier *= 1.1

        return MacroContext(
            current_regime=regime_name or "Unknown",
            current_family=family or "Unknown",
            regime_description=description,
            next_regime_predictions=transitions,
            current_btc_performance=current_btc,
            next_btc_performance=next_btc,
            position_size_modifier=min(1.5, max(0.0, position_modifier)),
            risk_warning=risk_warning,
            opportunity_signal=opportunity
        )


class IntegratedRegimeEngine:
    """BTC 엔진 + Graph RAG 통합 엔진"""

    def __init__(self):
        from btc_engine.core.regime_engine import RegimeEngine

        self.btc_engine = RegimeEngine(db_path="data/btc_patterns.db")
        self.graph = EconomicRegimeGraph()

    def close(self):
        self.graph.close()

    def analyze(self, btc_state: str, date: str = None) -> dict:
        """
        통합 분석 실행

        Args:
            btc_state: BTC 상태 문자열 (e.g., "weak|extreme_fear|lower|flat|neutral|high")
            date: 분석 날짜 (기본: 오늘)

        Returns:
            통합 분석 결과
        """
        # 1. BTC 엔진 판단
        btc_judgment = self.btc_engine.judge(btc_state)

        # 2. 매크로 컨텍스트
        macro_context = self.graph.get_regime_context(date)

        # 3. 통합 판단
        final_allowed = list(btc_judgment.allowed_actions)
        final_invalid = list(btc_judgment.invalid_actions)

        # 매크로 리스크 반영
        if macro_context.position_size_modifier == 0:
            final_allowed = ["WAIT", "EXIT_ALL"]
            final_invalid = ["LONG", "ADD_LONG", "NEW_POSITION"]
        elif macro_context.position_size_modifier < 0.7:
            if "AGGRESSIVE_LONG" not in final_invalid:
                final_invalid.append("AGGRESSIVE_LONG")
            if "REDUCE_SIZE" not in final_allowed:
                final_allowed.insert(0, "REDUCE_SIZE")

        # 4. 결과 조합
        return {
            "timestamp": datetime.now().isoformat(),
            "btc_state": btc_state,

            # BTC 엔진 결과
            "btc_regime": btc_judgment.market_regime.value,
            "btc_risk": btc_judgment.risk_level.value,
            "btc_confidence": btc_judgment.regime_confidence,

            # 매크로 결과
            "macro_regime": macro_context.current_regime,
            "macro_family": macro_context.current_family,
            "macro_btc_grade": macro_context.current_btc_performance.grade if macro_context.current_btc_performance else "N/A",

            # 전이 예측
            "next_regime_prediction": [
                {"regime": t.to_regime, "probability": f"{t.probability:.1%}"}
                for t in macro_context.next_regime_predictions[:3]
            ],

            # 통합 판단
            "position_size_modifier": macro_context.position_size_modifier,
            "allowed_actions": final_allowed,
            "invalid_actions": final_invalid,

            # 경고/기회
            "risk_warning": macro_context.risk_warning,
            "opportunity": macro_context.opportunity_signal,

            # 종합 요약
            "summary": self._generate_summary(btc_judgment, macro_context)
        }

    def _generate_summary(self, btc_judgment, macro_context) -> str:
        """종합 요약 생성"""
        parts = []

        # BTC 상태
        parts.append(f"BTC: {btc_judgment.market_regime.value}")

        # 매크로 상태
        parts.append(f"매크로: {macro_context.current_family}")

        # 리스크
        if macro_context.risk_warning:
            parts.append(f"⚠️ {macro_context.risk_warning}")

        # 기회
        if macro_context.opportunity_signal:
            parts.append(f"✅ {macro_context.opportunity_signal}")

        # 포지션
        mod = macro_context.position_size_modifier
        if mod == 0:
            parts.append("→ 진입 금지")
        elif mod < 1:
            parts.append(f"→ 포지션 {mod:.0%}로 축소")
        elif mod > 1:
            parts.append(f"→ 포지션 확대 가능 ({mod:.0%})")

        return " | ".join(parts)


def create_integrated_engine() -> IntegratedRegimeEngine:
    """통합 엔진 팩토리"""
    return IntegratedRegimeEngine()
