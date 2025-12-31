"""
BTC Regime Engine - 시장 구조 판단 엔진

❌ 트레이딩 봇 아님
❌ 시그널 봇 아님
✅ 판단 엔진 + 위험 관리자

핵심 철학:
- 패턴 위계화 (S/A/B/C/D Tier)
- 전이를 경로(Path)로 승격
- 구조적 출력 (BUY/SELL 아님)
"""
import json
import sqlite3
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from enum import Enum
from collections import defaultdict


class PatternTier(Enum):
    """패턴 위계"""
    S = "S"  # 시장을 바꾸는 패턴 (최우선)
    A = "A"  # 진입 가치 패턴
    B = "B"  # 보조 컨펌
    C = "C"  # 참고용
    D = "D"  # 회피용 (진입 금지)


class RiskLevel(Enum):
    """리스크 레벨"""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class MarketRegime(Enum):
    """시장 레짐"""
    MOMENTUM_EXPANSION = "Momentum Expansion"      # 강한 추세 확장
    MOMENTUM_CONTINUATION = "Momentum Continuation" # 추세 지속
    TREND_EXHAUSTION = "Trend Exhaustion"          # 추세 소진
    MEAN_REVERSION_SETUP = "Mean Reversion Setup"  # 평균회귀 셋업
    CONSOLIDATION = "Consolidation"                # 횡보/축적
    DISTRIBUTION = "Distribution"                  # 분배 (천장)
    CAPITULATION = "Capitulation"                  # 항복 (바닥)
    UNCERTAIN = "Uncertain"                        # 불확실


@dataclass
class TieredPattern:
    """위계화된 패턴"""
    pattern_key: str
    tier: PatternTier
    win_rate: float
    avg_return: float
    samples: int
    description: str

    # 액션 가이드
    allows_long: bool = True
    allows_short: bool = True
    allows_mean_revert: bool = True

    # 신뢰도
    confidence: float = 0.5


@dataclass
class PathResult:
    """경로 분석 결과"""
    path: List[str]  # 상태 시퀀스
    path_id: str
    occurrences: int
    success_rate: float  # 목표 도달률
    avg_return: float
    avg_duration_days: int
    typical_outcome: str  # "CONTINUATION", "REVERSAL", "SIDEWAYS"
    failure_points: List[str]  # 실패 지점들


@dataclass
class RegimeJudgment:
    """레짐 판단 결과 - 엔진의 최종 출력"""
    # 현재 상태
    timestamp: datetime
    current_state: str
    current_cluster: str

    # 레짐 판단
    market_regime: MarketRegime
    regime_confidence: float

    # 경로 분석
    dominant_path: Optional[str]
    path_position: str  # "EARLY", "MID", "LATE", "END"
    historical_similar_paths: List[PathResult]

    # 리스크
    risk_level: RiskLevel
    risk_factors: List[str]

    # 허용/금지 액션 (BUY/SELL 직접 말하지 않음)
    allowed_actions: List[str]
    invalid_actions: List[str]

    # 활성 패턴 (Tier별)
    active_s_tier: List[str]
    active_a_tier: List[str]
    active_d_tier: List[str]  # 경고

    # 컨텍스트
    context_summary: str

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "current_state": self.current_state,
            "current_cluster": self.current_cluster,
            "market_regime": self.market_regime.value,
            "regime_confidence": self.regime_confidence,
            "dominant_path": self.dominant_path,
            "path_position": self.path_position,
            "risk_level": self.risk_level.value,
            "risk_factors": self.risk_factors,
            "allowed_actions": self.allowed_actions,
            "invalid_actions": self.invalid_actions,
            "active_s_tier": self.active_s_tier,
            "active_a_tier": self.active_a_tier,
            "active_d_tier": self.active_d_tier,
            "context_summary": self.context_summary
        }


class PatternHierarchy:
    """패턴 위계 시스템"""

    def __init__(self):
        self.patterns: Dict[str, TieredPattern] = {}
        self._initialize_tiers()

    def _initialize_tiers(self):
        """백테스트 결과 기반 패턴 위계 설정"""

        # ========== S-Tier: 시장을 바꾸는 패턴 ==========
        # 높은 승률 + 높은 수익 + 충분한 샘플

        self.add_pattern(
            "RSI:overbought|Trend:down",
            PatternTier.S,
            win_rate=0.95, avg_return=2.28, samples=20,
            description="과매수 후 조정 = 강한 반등 신호",
            allows_short=False, allows_mean_revert=True
        )

        self.add_pattern(
            "overbought|greed|upper_touch|strong_up|neutral|normal",
            PatternTier.S,
            win_rate=0.76, avg_return=4.46, samples=17,
            description="모멘텀 최강 - 추가 상승",
            allows_short=False, allows_mean_revert=False
        )

        # 경로 기반 S-Tier
        self.add_pattern(
            "PATH:strong→overbought→strong_up",
            PatternTier.S,
            win_rate=0.72, avg_return=5.19, samples=12,
            description="모멘텀 확장 경로",
            allows_short=False
        )

        # ========== A-Tier: 진입 가치 패턴 ==========

        self.add_pattern(
            "RSI:oversold|FNG:fear",
            PatternTier.A,
            win_rate=0.79, avg_return=2.40, samples=33,
            description="공포 + 과매도 = 반등 가능",
            allows_short=False
        )

        self.add_pattern(
            "strong|greed|upper_touch|up|neutral|normal",
            PatternTier.A,
            win_rate=0.64, avg_return=2.67, samples=11,
            description="추세 지속 구간",
            allows_short=False
        )

        self.add_pattern(
            "RSI:overbought|FNG:greed|Trend:strong_up",
            PatternTier.A,
            win_rate=0.65, avg_return=3.00, samples=26,
            description="FOMO 모멘텀",
            allows_short=False, allows_mean_revert=False
        )

        # 클러스터 전이 기반
        self.add_pattern(
            "TRANSITION:C0→C1",  # strong→overbought
            PatternTier.A,
            win_rate=0.65, avg_return=1.59, samples=11,
            description="모멘텀 가속 전이"
        )

        # ========== B-Tier: 보조 컨펌 ==========

        self.add_pattern(
            "RSI:oversold|BB:lower",
            PatternTier.B,
            win_rate=0.67, avg_return=1.75, samples=33,
            description="기술적 과매도"
        )

        self.add_pattern(
            "weak|neutral|middle|flat|neutral|normal",
            PatternTier.B,
            win_rate=0.70, avg_return=1.83, samples=10,
            description="조용한 축적 구간"
        )

        self.add_pattern(
            "FNG:fear|Trend:down",
            PatternTier.B,
            win_rate=0.66, avg_return=0.50, samples=32,
            description="공포 하락 - 관망 또는 분할매수"
        )

        # ========== C-Tier: 참고용 ==========

        self.add_pattern(
            "RSI:neutral|BB:lower",
            PatternTier.C,
            win_rate=0.70, avg_return=0.28, samples=30,
            description="약한 신호 - 다른 컨펌 필요"
        )

        self.add_pattern(
            "FNG:greed|Trend:down",
            PatternTier.C,
            win_rate=0.60, avg_return=0.57, samples=82,
            description="조정 구간 - 방향 불확실"
        )

        # ========== D-Tier: 회피용 (진입 금지) ==========

        self.add_pattern(
            "neutral|greed|middle|flat|neutral|normal",
            PatternTier.D,
            win_rate=0.43, avg_return=0.01, samples=150,
            description="데드존 - 진입 금지",
            allows_long=False, allows_short=False
        )

        self.add_pattern(
            "TRANSITION:overbought|extreme_greed→lower",
            PatternTier.D,
            win_rate=0.25, avg_return=-3.77, samples=10,
            description="급락 위험 - 롱 금지",
            allows_long=False
        )

        self.add_pattern(
            "weak|fear|lower|flat",
            PatternTier.D,
            win_rate=0.35, avg_return=-0.87, samples=20,
            description="약세 지속 - 관망",
            allows_long=False, allows_mean_revert=False
        )

    def add_pattern(self, key: str, tier: PatternTier,
                   win_rate: float, avg_return: float, samples: int,
                   description: str, **kwargs):
        """패턴 추가"""
        confidence = min(0.95, win_rate * (samples / 100))

        self.patterns[key] = TieredPattern(
            pattern_key=key,
            tier=tier,
            win_rate=win_rate,
            avg_return=avg_return,
            samples=samples,
            description=description,
            confidence=confidence,
            **kwargs
        )

    def get_tier(self, pattern_key: str) -> Optional[PatternTier]:
        """패턴의 Tier 조회"""
        if pattern_key in self.patterns:
            return self.patterns[pattern_key].tier
        return None

    def get_patterns_by_tier(self, tier: PatternTier) -> List[TieredPattern]:
        """특정 Tier의 모든 패턴"""
        return [p for p in self.patterns.values() if p.tier == tier]

    def match_state(self, state_key: str) -> List[TieredPattern]:
        """상태에 매칭되는 패턴들 반환"""
        matches = []
        state_parts = set(state_key.split('|'))

        for key, pattern in self.patterns.items():
            if key.startswith("PATH:") or key.startswith("TRANSITION:"):
                continue  # 경로/전이 패턴은 별도 처리

            pattern_parts = key.replace("RSI:", "").replace("FNG:", "").replace("Trend:", "").replace("BB:", "").split('|')

            # 부분 매칭
            match_count = sum(1 for p in pattern_parts if p in state_parts or p in state_key)
            if match_count >= len(pattern_parts) * 0.7:
                matches.append(pattern)

        # Tier 순서로 정렬
        tier_order = {PatternTier.S: 0, PatternTier.A: 1, PatternTier.B: 2,
                     PatternTier.C: 3, PatternTier.D: 4}
        matches.sort(key=lambda p: (tier_order[p.tier], -p.win_rate))

        return matches


class PathAnalyzer:
    """경로(Path) 분석기"""

    def __init__(self, db_path: str = "data/btc_patterns.db"):
        self.db_path = db_path
        self.paths: Dict[str, PathResult] = {}
        self._load_paths()

    def _load_paths(self):
        """DB에서 경로 학습"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 상태 히스토리에서 경로 추출
            cursor.execute("""
                SELECT state_key, price, timestamp
                FROM state_history
                ORDER BY timestamp
            """)

            rows = cursor.fetchall()
            conn.close()

            if len(rows) < 10:
                return

            # 3-상태 경로 분석
            path_outcomes = defaultdict(list)

            for i in range(len(rows) - 10):
                # 3일 경로
                path = [rows[i+j][0] for j in range(3)]
                path_key = " → ".join(self._simplify_state(s) for s in path)

                # 7일 후 결과
                entry_price = rows[i+2][1]
                exit_price = rows[i+9][1]
                outcome = (exit_price - entry_price) / entry_price * 100

                path_outcomes[path_key].append({
                    'outcome': outcome,
                    'entry_price': entry_price,
                    'exit_price': exit_price
                })

            # 경로별 통계
            for path_key, outcomes in path_outcomes.items():
                if len(outcomes) < 3:
                    continue

                returns = [o['outcome'] for o in outcomes]
                wins = sum(1 for r in returns if r > 0)

                self.paths[path_key] = PathResult(
                    path=path_key.split(" → "),
                    path_id=f"PATH_{hash(path_key) % 10000:04d}",
                    occurrences=len(outcomes),
                    success_rate=wins / len(outcomes),
                    avg_return=sum(returns) / len(returns),
                    avg_duration_days=7,
                    typical_outcome="CONTINUATION" if sum(returns) > 0 else "REVERSAL",
                    failure_points=[]
                )

        except Exception as e:
            print(f"Path loading error: {e}")

    def _simplify_state(self, state: str) -> str:
        """상태 간략화"""
        parts = state.split('|')
        if len(parts) >= 4:
            return f"{parts[0][:4]}|{parts[1][:4]}|{parts[3][:4]}"
        return state[:15]

    def analyze_current_path(self, recent_states: List[str]) -> Optional[PathResult]:
        """현재 경로 분석"""
        if len(recent_states) < 3:
            return None

        current_path = " → ".join(self._simplify_state(s) for s in recent_states[-3:])

        # 정확히 일치하는 경로
        if current_path in self.paths:
            return self.paths[current_path]

        # 유사 경로 찾기
        best_match = None
        best_score = 0

        for path_key, path_result in self.paths.items():
            path_parts = path_key.split(" → ")
            current_parts = current_path.split(" → ")

            match_score = sum(1 for a, b in zip(path_parts, current_parts)
                            if a == b or a[:8] == b[:8])

            if match_score > best_score and match_score >= 2:
                best_score = match_score
                best_match = path_result

        return best_match

    def get_similar_historical_paths(self, current_path: str, limit: int = 5) -> List[PathResult]:
        """유사한 과거 경로들"""
        results = []
        current_parts = current_path.split(" → ") if " → " in current_path else [current_path]

        for path_key, path_result in self.paths.items():
            path_parts = path_key.split(" → ")

            # 시작점이 유사한 경로
            if path_parts[0][:8] == current_parts[0][:8] if current_parts else False:
                results.append(path_result)

        # 성공률 순 정렬
        results.sort(key=lambda x: x.success_rate, reverse=True)
        return results[:limit]


class RegimeEngine:
    """레짐 판단 엔진 - 핵심 클래스"""

    def __init__(self, db_path: str = "data/btc_patterns.db"):
        self.hierarchy = PatternHierarchy()
        self.path_analyzer = PathAnalyzer(db_path)
        self.state_history: List[str] = []
        self.max_history = 30

        # 클러스터 매핑 (이전 분석 결과)
        self.cluster_map = {
            'strong|greed': 'C0',
            'overbought|greed': 'C1',
            'neutral|greed': 'C2',
            'weak|neutral': 'C3',
            'weak|fear': 'C4'
        }

    def _get_cluster(self, state_key: str) -> str:
        """상태의 클러스터 판단"""
        parts = state_key.split('|')
        if len(parts) >= 2:
            prefix = f"{parts[0]}|{parts[1]}"
            for key, cluster in self.cluster_map.items():
                if key in prefix or prefix in key:
                    return cluster
        return "C_UNKNOWN"

    def _determine_regime(self, state_key: str, matched_patterns: List[TieredPattern],
                         path_result: Optional[PathResult]) -> Tuple[MarketRegime, float]:
        """시장 레짐 판단"""
        parts = state_key.split('|')

        # 기본 분류
        rsi = parts[0] if len(parts) > 0 else ""
        fng = parts[1] if len(parts) > 1 else ""
        trend = parts[3] if len(parts) > 3 else ""

        confidence = 0.5

        # S-Tier 패턴 있으면 높은 신뢰도
        s_tier = [p for p in matched_patterns if p.tier == PatternTier.S]
        if s_tier:
            confidence = max(confidence, s_tier[0].confidence)

        # 레짐 결정
        if 'overbought' in rsi and 'strong_up' in trend:
            return MarketRegime.MOMENTUM_EXPANSION, min(0.9, confidence + 0.2)

        if 'overbought' in rsi and ('up' in trend or 'flat' in trend):
            return MarketRegime.MOMENTUM_CONTINUATION, confidence

        if 'overbought' in rsi and 'down' in trend:
            return MarketRegime.TREND_EXHAUSTION, confidence

        if 'oversold' in rsi and 'fear' in fng:
            return MarketRegime.CAPITULATION, confidence

        if 'oversold' in rsi or ('weak' in rsi and 'down' in trend):
            return MarketRegime.MEAN_REVERSION_SETUP, confidence

        if 'extreme_greed' in fng and 'overbought' in rsi:
            return MarketRegime.DISTRIBUTION, confidence

        if 'neutral' in rsi and 'flat' in trend:
            return MarketRegime.CONSOLIDATION, confidence - 0.1

        return MarketRegime.UNCERTAIN, 0.3

    def _determine_risk(self, state_key: str, matched_patterns: List[TieredPattern],
                       regime: MarketRegime) -> Tuple[RiskLevel, List[str]]:
        """리스크 레벨 판단"""
        risk_factors = []
        risk_score = 0

        # D-Tier 패턴 체크
        d_tier = [p for p in matched_patterns if p.tier == PatternTier.D]
        if d_tier:
            risk_score += 3
            risk_factors.append(f"D-Tier 패턴 활성: {d_tier[0].description}")

        # 레짐 기반 리스크
        if regime == MarketRegime.DISTRIBUTION:
            risk_score += 2
            risk_factors.append("분배 레짐 - 천장 가능성")

        if regime == MarketRegime.TREND_EXHAUSTION:
            risk_score += 1
            risk_factors.append("추세 소진 - 조정 가능성")

        # 상태 기반 리스크
        if 'extreme_greed' in state_key:
            risk_score += 1
            risk_factors.append("극단적 탐욕")

        if 'extreme_fear' in state_key and 'strong_down' in state_key:
            risk_score += 1
            risk_factors.append("패닉 셀링 진행 중")

        # 리스크 레벨 매핑
        if risk_score >= 4:
            return RiskLevel.EXTREME, risk_factors
        elif risk_score >= 3:
            return RiskLevel.HIGH, risk_factors
        elif risk_score >= 2:
            return RiskLevel.MODERATE, risk_factors
        elif risk_score >= 1:
            return RiskLevel.LOW, risk_factors
        else:
            return RiskLevel.VERY_LOW, risk_factors

    def _determine_actions(self, matched_patterns: List[TieredPattern],
                          regime: MarketRegime,
                          risk_level: RiskLevel) -> Tuple[List[str], List[str]]:
        """허용/금지 액션 결정"""
        allowed = []
        invalid = []

        # 기본 설정
        can_long = True
        can_short = True
        can_mean_revert = True

        # 패턴 기반 제한
        for pattern in matched_patterns:
            if not pattern.allows_long:
                can_long = False
            if not pattern.allows_short:
                can_short = False
            if not pattern.allows_mean_revert:
                can_mean_revert = False

        # 리스크 기반 제한
        if risk_level in [RiskLevel.EXTREME, RiskLevel.HIGH]:
            can_long = False
            invalid.append("HIGH_RISK_LONG")

        # 레짐 기반 액션
        if regime == MarketRegime.MOMENTUM_EXPANSION:
            allowed.extend(["ALLOW_LONG_ONLY", "TREND_FOLLOW", "ADD_ON_DIP"])
            invalid.extend(["SHORT", "MEAN_REVERT", "FADE"])

        elif regime == MarketRegime.MOMENTUM_CONTINUATION:
            allowed.extend(["HOLD_LONG", "TRAIL_STOP"])
            invalid.extend(["SHORT", "AGGRESSIVE_ADD"])

        elif regime == MarketRegime.TREND_EXHAUSTION:
            allowed.extend(["REDUCE_POSITION", "TIGHTEN_STOP", "TAKE_PARTIAL_PROFIT"])
            invalid.extend(["ADD_LONG", "NEW_LONG"])

        elif regime == MarketRegime.MEAN_REVERSION_SETUP:
            if can_long:
                allowed.extend(["SCALE_IN_LONG", "DCA_BUY"])
            invalid.extend(["SHORT", "AGGRESSIVE_LONG"])

        elif regime == MarketRegime.CAPITULATION:
            allowed.extend(["WATCH", "SMALL_SCALE_IN"])
            invalid.extend(["LARGE_POSITION", "LEVERAGE"])

        elif regime == MarketRegime.DISTRIBUTION:
            allowed.extend(["EXIT_LONG", "REDUCE", "HEDGE"])
            invalid.extend(["NEW_LONG", "ADD_LONG"])

        elif regime == MarketRegime.CONSOLIDATION:
            allowed.extend(["RANGE_TRADE", "WAIT"])
            invalid.extend(["TREND_FOLLOW", "BREAKOUT_ANTICIPATE"])

        else:  # UNCERTAIN
            allowed.extend(["WAIT", "REDUCE_SIZE"])
            invalid.extend(["AGGRESSIVE_POSITION"])

        return allowed, invalid

    def _generate_context(self, regime: MarketRegime,
                         matched_patterns: List[TieredPattern],
                         path_result: Optional[PathResult]) -> str:
        """맥락 요약 생성"""
        parts = []

        parts.append(f"현재 시장은 '{regime.value}' 레짐입니다.")

        # S/A Tier 패턴
        high_tier = [p for p in matched_patterns if p.tier in [PatternTier.S, PatternTier.A]]
        if high_tier:
            parts.append(f"주요 패턴: {high_tier[0].description}")

        # 경로 정보
        if path_result:
            parts.append(f"유사 과거 경로 성공률: {path_result.success_rate*100:.0f}%")

        # D-Tier 경고
        d_tier = [p for p in matched_patterns if p.tier == PatternTier.D]
        if d_tier:
            parts.append(f"⚠️ 경고: {d_tier[0].description}")

        return " ".join(parts)

    def judge(self, current_state: str) -> RegimeJudgment:
        """
        레짐 판단 실행 - 핵심 메서드

        Returns:
            RegimeJudgment: 구조화된 판단 결과
        """
        # 히스토리 업데이트
        self.state_history.append(current_state)
        if len(self.state_history) > self.max_history:
            self.state_history = self.state_history[-self.max_history:]

        # 1. 패턴 매칭
        matched_patterns = self.hierarchy.match_state(current_state)

        # 2. 클러스터 판단
        current_cluster = self._get_cluster(current_state)

        # 3. 경로 분석
        path_result = self.path_analyzer.analyze_current_path(self.state_history)
        similar_paths = self.path_analyzer.get_similar_historical_paths(current_state)

        # 4. 레짐 결정
        regime, regime_confidence = self._determine_regime(
            current_state, matched_patterns, path_result
        )

        # 5. 리스크 평가
        risk_level, risk_factors = self._determine_risk(
            current_state, matched_patterns, regime
        )

        # 6. 액션 결정
        allowed_actions, invalid_actions = self._determine_actions(
            matched_patterns, regime, risk_level
        )

        # 7. 컨텍스트 생성
        context = self._generate_context(regime, matched_patterns, path_result)

        # 8. Tier별 활성 패턴
        s_tier = [p.pattern_key for p in matched_patterns if p.tier == PatternTier.S]
        a_tier = [p.pattern_key for p in matched_patterns if p.tier == PatternTier.A]
        d_tier = [p.pattern_key for p in matched_patterns if p.tier == PatternTier.D]

        # 경로 위치 판단
        path_position = "UNKNOWN"
        if path_result:
            if path_result.avg_return > 2:
                path_position = "EARLY"
            elif path_result.avg_return > 0:
                path_position = "MID"
            else:
                path_position = "LATE"

        return RegimeJudgment(
            timestamp=datetime.now(),
            current_state=current_state,
            current_cluster=current_cluster,
            market_regime=regime,
            regime_confidence=regime_confidence,
            dominant_path=path_result.path_id if path_result else None,
            path_position=path_position,
            historical_similar_paths=similar_paths,
            risk_level=risk_level,
            risk_factors=risk_factors,
            allowed_actions=allowed_actions,
            invalid_actions=invalid_actions,
            active_s_tier=s_tier,
            active_a_tier=a_tier,
            active_d_tier=d_tier,
            context_summary=context
        )


def create_regime_engine(db_path: str = "data/btc_patterns.db") -> RegimeEngine:
    """레짐 엔진 팩토리"""
    return RegimeEngine(db_path)
