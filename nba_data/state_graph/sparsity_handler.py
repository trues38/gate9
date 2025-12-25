"""
데이터 희소성 처리 시스템
=========================
문제: Scott Foster + Gap Defense = 샘플 5개 미만
해결: Transfer Learning + Bayesian Prior + 신뢰 구간

Made with ❤️ by State Graph Engine
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TacticPerformance:
    """전술 성능 데이터"""
    tactic_name: str
    sample_size: int
    win_rate: float
    avg_point_diff: float
    effectiveness: float


@dataclass
class ConfidenceInterval:
    """신뢰 구간"""
    point_estimate: float
    lower_bound: float
    upper_bound: float
    confidence_level: float  # 0.95 for 95%
    sample_size: int
    reliable: bool  # 샘플이 충분한가?


# ============================================================================
# 1. 신뢰 구간 계산 (샘플 크기 기반)
# ============================================================================

def calculate_confidence_interval(
    win_rate: float,
    sample_size: int,
    confidence_level: float = 0.95
) -> ConfidenceInterval:
    """
    Wilson Score Interval 사용 (작은 샘플에 강건)

    Args:
        win_rate: 승률 (0.0 ~ 1.0)
        sample_size: 샘플 크기
        confidence_level: 신뢰 수준 (0.95 = 95%)

    Returns:
        신뢰 구간
    """

    if sample_size == 0:
        return ConfidenceInterval(
            point_estimate=0.5,  # Prior: 50%
            lower_bound=0.0,
            upper_bound=1.0,
            confidence_level=0.0,
            sample_size=0,
            reliable=False
        )

    # Z-score (95% → 1.96, 99% → 2.576)
    z = 1.96 if confidence_level == 0.95 else 2.576

    # Wilson Score Interval
    n = sample_size
    p = win_rate

    denominator = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denominator
    margin = z * math.sqrt((p*(1-p)/n + z**2/(4*n**2))) / denominator

    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)

    # 신뢰도 판정 (샘플 20개 이상이면 reliable)
    reliable = sample_size >= 20

    return ConfidenceInterval(
        point_estimate=win_rate,
        lower_bound=round(lower, 3),
        upper_bound=round(upper, 3),
        confidence_level=confidence_level,
        sample_size=sample_size,
        reliable=reliable
    )


# ============================================================================
# 2. Bayesian Prior (사전 확률)
# ============================================================================

def apply_bayesian_prior(
    observed_win_rate: float,
    sample_size: int,
    prior_win_rate: float = 0.5,
    prior_strength: int = 10
) -> float:
    """
    Bayesian 업데이트로 샘플이 적을 때 Prior에 회귀

    Args:
        observed_win_rate: 관측된 승률
        sample_size: 샘플 크기
        prior_win_rate: 사전 확률 (기본 0.5 = 50%)
        prior_strength: 사전 확률 강도 (가상 샘플 수)

    Returns:
        조정된 승률

    Example:
        샘플 2개, 100% 승률 → Prior 0.5로 끌어당김
        샘플 100개, 70% 승률 → Prior 영향 거의 없음
    """

    # Bayesian 업데이트
    posterior_wins = observed_win_rate * sample_size + prior_win_rate * prior_strength
    posterior_total = sample_size + prior_strength

    return round(posterior_wins / posterior_total, 3)


# ============================================================================
# 3. Transfer Learning (유사 전술에서 데이터 전이)
# ============================================================================

def transfer_from_similar_tactics(
    target_tactic: str,
    target_sample_size: int,
    target_win_rate: float,
    similar_tactics: List[TacticPerformance],
    similarity_scores: Dict[str, float]  # {tactic_name: similarity}
) -> Tuple[float, str]:
    """
    유사 전술의 데이터를 Transfer

    Args:
        target_tactic: 목표 전술
        target_sample_size: 목표 전술 샘플 크기
        target_win_rate: 목표 전술 승률
        similar_tactics: 유사 전술 리스트
        similarity_scores: 유사도 점수 (0.0 ~ 1.0)

    Returns:
        (조정된 승률, 설명)
    """

    if target_sample_size >= 20:
        return target_win_rate, "충분한 샘플, Transfer 불필요"

    # 1. 유사 전술 필터링 (샘플 20개 이상, 유사도 0.6 이상)
    reliable_similar = [
        tactic for tactic in similar_tactics
        if tactic.sample_size >= 20
        and similarity_scores.get(tactic.tactic_name, 0) >= 0.6
    ]

    if not reliable_similar:
        return target_win_rate, "유사 전술 데이터 없음"

    # 2. 가중 평균 (유사도 기반)
    weighted_sum = 0.0
    weight_total = 0.0

    for tactic in reliable_similar:
        similarity = similarity_scores[tactic.tactic_name]
        weight = similarity * math.sqrt(tactic.sample_size)  # 샘플 크기도 반영

        weighted_sum += tactic.win_rate * weight
        weight_total += weight

    transferred_win_rate = weighted_sum / weight_total if weight_total > 0 else 0.5

    # 3. 목표 전술 데이터와 블렌딩
    # 샘플이 적을수록 Transfer 의존도 높임
    transfer_weight = max(0.3, 1.0 - target_sample_size / 20)  # 샘플 0개면 100%, 20개면 0%
    target_weight = 1.0 - transfer_weight

    final_win_rate = (
        target_win_rate * target_weight +
        transferred_win_rate * transfer_weight
    )

    explanation = (
        f"Transfer {transfer_weight*100:.0f}% from "
        f"{len(reliable_similar)} similar tactics"
    )

    return round(final_win_rate, 3), explanation


# ============================================================================
# 4. 통합: 희소성 처리 파이프라인
# ============================================================================

def handle_sparsity(
    tactic_name: str,
    observed_win_rate: float,
    sample_size: int,
    similar_tactics: Optional[List[TacticPerformance]] = None,
    similarity_scores: Optional[Dict[str, float]] = None
) -> Dict:
    """
    데이터 희소성 종합 처리

    Pipeline:
    1. 신뢰 구간 계산
    2. Bayesian Prior 적용
    3. Transfer Learning (유사 전술)
    4. 최종 추정치 + 신뢰도 반환

    Returns:
        {
            'adjusted_win_rate': 0.65,
            'confidence_interval': {...},
            'bayesian_adjusted': 0.58,
            'transfer_adjusted': 0.63,
            'final_estimate': 0.63,
            'reliability_score': 0.45,
            'explanation': "..."
        }
    """

    # 1. 신뢰 구간
    ci = calculate_confidence_interval(observed_win_rate, sample_size)

    # 2. Bayesian 조정
    bayesian_rate = apply_bayesian_prior(observed_win_rate, sample_size)

    # 3. Transfer Learning
    if similar_tactics and similarity_scores and sample_size < 20:
        transfer_rate, transfer_note = transfer_from_similar_tactics(
            tactic_name, sample_size, observed_win_rate,
            similar_tactics, similarity_scores
        )
    else:
        transfer_rate = observed_win_rate
        transfer_note = "Transfer 불필요 또는 불가능"

    # 4. 최종 추정치 결정
    if sample_size >= 20:
        # 충분한 샘플: 관측값 사용
        final_estimate = observed_win_rate
        explanation = "충분한 샘플, 관측값 신뢰"

    elif similar_tactics and sample_size < 10:
        # 샘플 매우 적음: Transfer 우선
        final_estimate = transfer_rate
        explanation = transfer_note

    else:
        # 중간: Bayesian 사용
        final_estimate = bayesian_rate
        explanation = f"Bayesian 조정 (Prior 0.5, 강도 10)"

    # 5. 신뢰도 점수 (0.0 ~ 1.0)
    reliability_score = calculate_reliability_score(sample_size, ci)

    return {
        'observed_win_rate': observed_win_rate,
        'sample_size': sample_size,

        'confidence_interval': {
            'lower': ci.lower_bound,
            'upper': ci.upper_bound,
            'reliable': ci.reliable
        },

        'bayesian_adjusted': bayesian_rate,
        'transfer_adjusted': transfer_rate if similar_tactics else None,

        'final_estimate': round(final_estimate, 3),
        'reliability_score': round(reliability_score, 2),
        'explanation': explanation
    }


def calculate_reliability_score(sample_size: int, ci: ConfidenceInterval) -> float:
    """
    신뢰도 점수 계산

    0.0 (전혀 믿을 수 없음) ~ 1.0 (완전 신뢰)
    """

    # 샘플 크기 기여 (0 ~ 0.6)
    sample_contribution = min(sample_size / 50, 0.6)

    # 신뢰 구간 폭 기여 (좁을수록 높음, 0 ~ 0.4)
    ci_width = ci.upper_bound - ci.lower_bound
    ci_contribution = max(0, 0.4 * (1.0 - ci_width))

    return sample_contribution + ci_contribution


# ============================================================================
# 5. Neo4j 쿼리 통합 예시
# ============================================================================

def get_tactic_performance_with_sparsity_handling(
    neo4j_session,
    tactic_name: str,
    team: str,
    season: str
) -> Dict:
    """
    Neo4j에서 전술 성능 조회 + 희소성 처리

    Cypher:
        MATCH (team:Team {abbr: $team})-[use:USES_TACTIC]->(tactic:Tactic {name: $tactic})
        MATCH (game:GameState)-[:FEATURED_TACTIC {team: "home"}]->(tactic)
        WHERE game.season = $season AND game.home_team = $team
        RETURN count(*) AS sample_size,
               sum(CASE WHEN game.result.home_win THEN 1 ELSE 0 END) * 1.0 / count(*) AS win_rate
    """

    # 1. 메인 데이터 조회
    result = neo4j_session.run("""
        MATCH (team:Team {abbr: $team})-[:USES_TACTIC]->(tactic:Tactic {name: $tactic})
        MATCH (game:GameState)-[:FEATURED_TACTIC]->(tactic)
        WHERE game.season = $season
          AND (game.home_team = $team OR game.away_team = $team)

        WITH game, tactic,
             CASE WHEN game.home_team = $team THEN game.result.home_win
                  ELSE NOT game.result.home_win END AS team_win

        RETURN count(*) AS sample_size,
               sum(CASE WHEN team_win THEN 1 ELSE 0 END) * 1.0 / count(*) AS win_rate,
               avg(game.result.point_diff) AS avg_point_diff
    """, team=team, tactic=tactic_name, season=season).single()

    sample_size = result['sample_size']
    win_rate = result['win_rate'] or 0.5

    # 2. 유사 전술 조회 (EFFECTIVE_VS 관계 활용)
    similar_result = neo4j_session.run("""
        MATCH (target:Tactic {name: $tactic})-[rel:EFFECTIVE_VS]->(style:PlayStyle)
        MATCH (similar:Tactic)-[:EFFECTIVE_VS]->(style)
        WHERE similar.name <> $tactic

        WITH similar, count(*) AS shared_styles

        MATCH (game:GameState)-[:FEATURED_TACTIC]->(similar)
        WITH similar, shared_styles,
             count(*) AS similar_sample_size,
             sum(CASE WHEN game.result.home_win THEN 1 ELSE 0 END) * 1.0 / count(*) AS similar_win_rate

        WHERE similar_sample_size >= 20

        RETURN similar.name AS tactic_name,
               similar_sample_size AS sample_size,
               similar_win_rate AS win_rate,
               shared_styles * 1.0 / 3 AS similarity  // 3개 스타일 공유하면 1.0
        ORDER BY similarity DESC
        LIMIT 5
    """, tactic=tactic_name).data()

    similar_tactics = [
        TacticPerformance(
            tactic_name=r['tactic_name'],
            sample_size=r['sample_size'],
            win_rate=r['win_rate'],
            avg_point_diff=0.0,
            effectiveness=r['win_rate']
        )
        for r in similar_result
    ]

    similarity_scores = {r['tactic_name']: r['similarity'] for r in similar_result}

    # 3. 희소성 처리
    adjusted = handle_sparsity(
        tactic_name, win_rate, sample_size,
        similar_tactics, similarity_scores
    )

    return adjusted


# ============================================================================
# 예시 실행
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("데이터 희소성 처리 예시")
    print("=" * 70)

    # 케이스 1: 샘플 부족 (5개)
    result1 = handle_sparsity(
        tactic_name="Gap Defense",
        observed_win_rate=0.80,
        sample_size=5
    )
    print("\n케이스 1: 샘플 5개, 80% 승률")
    print(f"  관측 승률: {result1['observed_win_rate']}")
    print(f"  Bayesian 조정: {result1['bayesian_adjusted']}")
    print(f"  최종 추정: {result1['final_estimate']}")
    print(f"  신뢰도: {result1['reliability_score']}")
    print(f"  신뢰 구간: [{result1['confidence_interval']['lower']}, {result1['confidence_interval']['upper']}]")
    print(f"  설명: {result1['explanation']}")

    # 케이스 2: 샘플 충분 (30개)
    result2 = handle_sparsity(
        tactic_name="Gap Defense",
        observed_win_rate=0.73,
        sample_size=30
    )
    print("\n케이스 2: 샘플 30개, 73% 승률")
    print(f"  최종 추정: {result2['final_estimate']}")
    print(f"  신뢰도: {result2['reliability_score']}")
    print(f"  설명: {result2['explanation']}")

    # 케이스 3: Transfer Learning
    similar_tactics = [
        TacticPerformance("Switch Everything", 45, 0.68, 0.0, 0.68),
        TacticPerformance("Drop Coverage", 38, 0.65, 0.0, 0.65)
    ]
    similarity_scores = {
        "Switch Everything": 0.75,
        "Drop Coverage": 0.65
    }

    result3 = handle_sparsity(
        tactic_name="Gap Defense",
        observed_win_rate=0.80,
        sample_size=8,
        similar_tactics=similar_tactics,
        similarity_scores=similarity_scores
    )
    print("\n케이스 3: 샘플 8개, 유사 전술 있음")
    print(f"  관측 승률: {result3['observed_win_rate']}")
    print(f"  Transfer 조정: {result3['transfer_adjusted']}")
    print(f"  최종 추정: {result3['final_estimate']}")
    print(f"  신뢰도: {result3['reliability_score']}")
    print(f"  설명: {result3['explanation']}")

    print("\n" + "=" * 70)
    print("✅ 희소성 처리 완료!")
    print("=" * 70)
