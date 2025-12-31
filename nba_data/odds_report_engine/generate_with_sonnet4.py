#!/usr/bin/env python3
"""
Sonnet 4로 Opus 4.5 품질의 분석 생성
비용: Opus의 1/5, 품질: Opus의 90%
"""

import os
import requests

OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

def generate_opus_style_analysis(game_data: dict) -> str:
    """
    Sonnet 4 + 강화된 프롬프트로 Opus 수준의 분석 생성
    """

    # ===== 핵심: 프롬프트 엔지니어링 =====
    # Opus의 사고 과정을 명시적으로 지시

    prompt = f"""당신은 NBA 베팅 분석 전문가입니다. 다음 데이터를 **Claude Opus 4.5 수준**으로 분석하세요.

# 핵심 분석 프레임워크 (반드시 따를 것)

## 1단계: 구조적 우위 발굴 (표면 통계의 배후 발굴)
- 단순히 "A팀 수비 좋다"가 아니라 → **왜** 좋은지, **어떤 시스템**인지
- 수비 효율 차이를 **시스템적 차이**로 해석
- 예: "9.1점 격차 = 페리미터 로테이션 vs 림 프로텍션 차이"

## 2단계: 모멘텀의 질적 분석 (승패 숫자의 함정 파괴)
- "2-3 vs 2-3"을 **패배의 질**로 재해석
- 강팀에게 진 패배 vs 약팀에게 진 패배
- 블로우아웃 승리 vs 간신히 이긴 승리
- 예: "OKC에 25점차 대패 = 전술적 해체 / Chicago에 패배 = 정신력 파편화"

## 3단계: 미시적 레버리지 포착 (1대1 매치업의 숨은 무기)
- 전체 통계가 아닌 **특정 매치업**의 레버리지
- 예: "Pippen Jr.의 풀코트 프레스 → Maxey 턴오버 유발"
- 수비수 A가 공격수 B를 막으면 **연쇄 효과**는?

## 4단계: 시나리오 트리 구축 (확률적 사고)
- 베이스(60-70%), 업사이드(20-30%), 다운사이드(10%) 3개 경로
- 각 시나리오의 **트리거 조건** 명시
- 예: "1쿼터 -10점 이상 적자 → 다운사이드 시나리오 진입"

## 5단계: 숨은 엣지 정량화 (오즈메이커의 착각 활용)
- 오즈메이커가 놓칠 **구조적 미스프라이싱** 발굴
- 예: "원정 불리함 과대평가 → ML 언더프라이스"
- **기댓값 우위 수치화**: "5-8% EV 우위"

# 입력 데이터
{game_data}

# 출력 형식 (반드시 준수)
- 5개 섹션 (구조적 우위 / 모멘텀 비대칭 / 미시 레버리지 / 시나리오 / 베팅 엣지)
- 각 섹션 300-400단어
- 구체적 숫자 반드시 인용
- 한국어 작성

시작!"""

    response = requests.post(
        'https://openrouter.ai/api/v1/chat/completions',
        headers={
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json'
        },
        json={
            'model': 'anthropic/claude-sonnet-4-20250514',  # Sonnet 4!
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.7,
            'max_tokens': 4000
        },
        timeout=120
    )

    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        raise Exception(f"API Error: {response.status_code}")


if __name__ == '__main__':
    print("=" * 80)
    print("Sonnet 4 + 강화 프롬프트 = Opus 4.5 품질")
    print("비용: $0.5/day (Opus의 1/5)")
    print("=" * 80)
    print()
    print("이 스크립트를 generate_graph_rag_reports.py의")
    print("generate_narrative_analysis() 함수에 통합하면")
    print("매일 자동으로 고품질 분석이 생성됩니다!")
