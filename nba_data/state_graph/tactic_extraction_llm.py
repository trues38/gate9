"""
전술 추출 LLM 프롬프트 시스템
================================
문제: 전술 태깅의 주관성 → 그래프 오염
해결: 체계적 프롬프트 + 통계적 검증 + 일관성 보장

Made with ❤️ by State Graph Engine
"""

import json
from typing import Dict, List, Optional
from dataclasses import dataclass

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


@dataclass
class TacticSignature:
    """전술의 통계적 시그니처 (일관성 보장)"""
    name: str
    category: str

    # 필수 통계 조건 (AND)
    required_stats: Dict[str, Dict[str, float]]  # {stat_name: {min: , max: }}

    # 선택 통계 조건 (OR, 2개 이상 만족)
    optional_stats: Dict[str, Dict[str, float]]

    # 설명
    description: str


# ============================================================================
# 전술 시그니처 정의 (일관성의 기준)
# ============================================================================

TACTIC_SIGNATURES = {
    "Gap Defense": TacticSignature(
        name="Gap Defense",
        category="defense",
        required_stats={
            "opponent_paint_points": {"max": 42},
            "opponent_fg_pct_paint": {"max": 0.50}
        },
        optional_stats={
            "steals": {"min": 9},
            "blocks": {"min": 5},
            "opponent_turnovers": {"min": 14}
        },
        description="드라이브 레인에 디펜더를 배치해 페인트 진입 차단. 속도 있는 윙이 갭 로테이션."
    ),

    "No-Pick Roll Play": TacticSignature(
        name="No-Pick Roll Play",
        category="offense",
        required_stats={
            "assists": {"min": 24},
            "points_in_paint": {"min": 46}
        },
        optional_stats={
            "turnovers": {"max": 13},
            "fast_break_points": {"min": 12},
            "second_chance_points": {"min": 10}
        },
        description="픽앤롤 없이 바로 롤맨이 다이빙. 갭 디펜스의 스크린 예상을 역이용."
    ),

    "Inside Spacing": TacticSignature(
        name="Inside Spacing",
        category="offense",
        required_stats={
            "three_point_rate": {"max": 0.32},
            "points_in_paint": {"min": 48},
            "offensive_rating": {"min": 112}
        },
        optional_stats={
            "mid_range_fg_pct": {"min": 0.46},
            "free_throw_rate": {"min": 0.25},
            "offensive_rebound_pct": {"min": 0.28}
        },
        description="빅맨이 페인트-미드레인지 장악. 3점 적지만 오펜스 효율 극대화 (휴스턴 스타일)."
    ),

    "20-30min Rotation": TacticSignature(
        name="20-30min Rotation",
        category="rotation",
        required_stats={
            "minutes_variance": {"max": 6},  # 선수별 분 차이 작음
            "bench_points": {"min": 30}
        },
        optional_stats={
            "fourth_quarter_point_diff": {"min": 2},  # 4쿼터 강함
            "fatigue_index": {"max": 0.55}
        },
        description="주요 선수들 20-30분 균등 배분. 시즌 후반 체력 우위 (샌안 스타일)."
    ),

    "Pace & Space": TacticSignature(
        name="Pace & Space",
        category="offense",
        required_stats={
            "pace": {"min": 100},
            "three_point_rate": {"min": 0.38}
        },
        optional_stats={
            "fast_break_points": {"min": 14},
            "offensive_rating": {"min": 115},
            "three_point_pct": {"min": 0.36}
        },
        description="빠른 템포 + 3점 공격 (골든스테이트 스타일)."
    )
}


# ============================================================================
# 1단계: 통계 기반 전술 감지 (자동, 일관성 100%)
# ============================================================================

def detect_tactic_by_stats(team_stats: Dict, signatures: Dict[str, TacticSignature]) -> List[Dict]:
    """
    통계만으로 전술 감지 (완전 자동, 주관 배제)

    Returns:
        [{'name': 'Gap Defense', 'confidence': 0.85, 'matched_stats': [...]}]
    """
    detected = []

    for tactic_name, signature in signatures.items():
        # 1. 필수 조건 체크 (AND)
        required_match = all(
            check_stat_condition(team_stats, stat, condition)
            for stat, condition in signature.required_stats.items()
        )

        if not required_match:
            continue

        # 2. 선택 조건 체크 (OR, 2개 이상)
        optional_matches = sum(
            1 for stat, condition in signature.optional_stats.items()
            if check_stat_condition(team_stats, stat, condition)
        )

        if optional_matches < 2:
            continue

        # 3. Confidence 계산
        total_optional = len(signature.optional_stats)
        confidence = 0.5 + (optional_matches / total_optional) * 0.5

        detected.append({
            'name': tactic_name,
            'category': signature.category,
            'confidence': round(confidence, 2),
            'source': 'statistical',
            'matched_required': list(signature.required_stats.keys()),
            'matched_optional': [
                stat for stat, condition in signature.optional_stats.items()
                if check_stat_condition(team_stats, stat, condition)
            ]
        })

    return detected


def check_stat_condition(stats: Dict, stat_name: str, condition: Dict[str, float]) -> bool:
    """통계 조건 체크"""
    value = stats.get(stat_name)
    if value is None:
        return False

    if 'min' in condition and value < condition['min']:
        return False
    if 'max' in condition and value > condition['max']:
        return False

    return True


# ============================================================================
# 2단계: LLM 검증 (일관성 있는 프롬프트)
# ============================================================================

def verify_tactic_with_llm(
    game_id: str,
    team: str,
    detected_tactics: List[Dict],
    game_data: Dict,
    client = None
) -> Dict:
    """
    LLM으로 전술 검증 (일관성 보장 프롬프트)

    핵심: 예/아니오 체크리스트 방식으로 주관 최소화
    """

    # 프롬프트 구조화
    prompt = f"""
당신은 NBA 전술 분석 전문가입니다. **객관적 검증**만 수행하세요.

경기: {game_data['matchup']}
팀: {team}
결과: {game_data['result']}

통계:
{format_stats(game_data['team_stats'])}

자동 감지된 전술:
{json.dumps(detected_tactics, indent=2)}

---

**검증 체크리스트 (예/아니오로만 답변):**

각 전술별로 아래 질문에 답하세요.

전술: {detected_tactics[0]['name']}
설명: {TACTIC_SIGNATURES[detected_tactics[0]['name']].description}

1. 통계적 시그니처가 명확한가? (예: 페인트 득점 42점 이하)
   → 예 / 아니오

2. 주요 플레이에서 이 전술의 특징이 관찰되는가?
   예: Gap Defense → "드라이브 시도 시 갭에서 디펜더가 막음"
   → 예 / 아니오 / 불확실

3. 상대 팀이 이 전술에 반응했는가?
   예: 갭 디펜스 → 상대가 외곽 슈팅 시도 증가
   → 예 / 아니오 / 불확실

4. 이 전술이 승패에 영향을 미쳤는가?
   → 예 / 아니오 / 불확실

---

**JSON 응답 형식:**

{{
  "verified_tactics": [
    {{
      "name": "Gap Defense",
      "verified": true,  // 1~4번 중 3개 이상 "예"면 true
      "checklist": {{
        "statistical_match": true,
        "observable_in_plays": true,
        "opponent_reaction": true,
        "impact_on_result": false
      }},
      "confidence": 0.75,  // 체크리스트 통과율
      "notes": "페인트 수비 강했으나 상대 3점이 터져서 승패 영향 제한적"
    }}
  ]
}}

**중요:**
- "불확실"이 2개 이상이면 verified: false
- 주관적 해석 금지, 체크리스트만 따를 것
"""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    result = json.loads(response.content[0].text)
    return result


# ============================================================================
# 3단계: 최종 전술 태그 생성 (통계 + LLM 통합)
# ============================================================================

def extract_tactics(game_id: str, team: str, game_data: Dict) -> Dict:
    """
    전술 추출 파이프라인

    1. 통계 자동 감지 (Confidence 0.5~0.8)
    2. LLM 검증 (Confidence 0.5~0.9)
    3. 최종 Confidence = (통계 + LLM) / 2
    """

    # 1. 통계 감지
    detected = detect_tactic_by_stats(game_data['team_stats'], TACTIC_SIGNATURES)

    if not detected:
        return {
            'game_id': game_id,
            'team': team,
            'tactics': [],
            'confidence': 0.0,
            'source': 'none'
        }

    # 2. LLM 검증
    if HAS_ANTHROPIC:
        import anthropic
        client = anthropic.Anthropic()
        verified = verify_tactic_with_llm(game_id, team, detected, game_data, client)
    else:
        # Anthropic 없으면 통계만 사용
        verified = {'verified_tactics': [
            {'name': t['name'], 'verified': True, 'checklist': {}, 'confidence': 0.7, 'notes': 'Statistical only'}
            for t in detected
        ]}

    # 3. 통합
    final_tactics = []
    for tactic in verified['verified_tactics']:
        if not tactic['verified']:
            continue

        # 통계 confidence 찾기
        stat_conf = next(
            (t['confidence'] for t in detected if t['name'] == tactic['name']),
            0.5
        )

        # 최종 confidence = (통계 + LLM) / 2
        final_conf = (stat_conf + tactic['confidence']) / 2

        # 샘플 크기 반영 (처음엔 1게임이므로 페널티)
        sample_penalty = min(1 / 20, 1.0)  # 20경기 이상이면 페널티 없음
        final_conf *= (0.5 + 0.5 * sample_penalty)  # 최소 50% 적용

        final_tactics.append({
            'name': tactic['name'],
            'category': TACTIC_SIGNATURES[tactic['name']].category,
            'confidence': round(final_conf, 2),
            'statistical_confidence': stat_conf,
            'llm_confidence': tactic['confidence'],
            'checklist': tactic['checklist'],
            'notes': tactic['notes'],
            'sample_size': 1  # 초기값, 누적되면 증가
        })

    return {
        'game_id': game_id,
        'team': team,
        'tactics': final_tactics,
        'overall_confidence': max([t['confidence'] for t in final_tactics], default=0.0)
    }


# ============================================================================
# 유틸리티 함수
# ============================================================================

def format_stats(stats: Dict) -> str:
    """통계를 읽기 좋게 포맷"""
    return "\n".join([f"  {k}: {v}" for k, v in stats.items()])


# ============================================================================
# 예시 실행
# ============================================================================

if __name__ == "__main__":
    # 예시 데이터
    game_data = {
        'game_id': '401810220',
        'matchup': 'OKC vs MIA',
        'result': 'MIA wins 108-100',
        'team_stats': {
            'opponent_paint_points': 38,
            'opponent_fg_pct_paint': 0.47,
            'steals': 11,
            'blocks': 6,
            'opponent_turnovers': 15,
            'assists': 26,
            'points_in_paint': 52,
            'turnovers': 11,
            'three_point_rate': 0.28,
            'offensive_rating': 118,
            'pace': 98
        }
    }

    # 통계 자동 감지
    detected = detect_tactic_by_stats(game_data['team_stats'], TACTIC_SIGNATURES)
    print("=" * 70)
    print("통계 기반 전술 감지:")
    print("=" * 70)
    for tactic in detected:
        print(f"\n{tactic['name']} (Confidence: {tactic['confidence']})")
        print(f"  Category: {tactic['category']}")
        print(f"  Matched Required: {', '.join(tactic['matched_required'])}")
        print(f"  Matched Optional: {', '.join(tactic['matched_optional'])}")

    # 실제 사용 시:
    # result = extract_tactics('401810220', 'OKC', game_data)
    # print(json.dumps(result, indent=2))
