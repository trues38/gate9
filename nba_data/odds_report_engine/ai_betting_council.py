"""
5인 AI 베팅 분석 위원회 (Updated 2025-12-28)
- DeepSeek V3.2: 정량 분석
- Qwen 72B: 스토리텔링 & 레짐 패턴
- Grok 4.1 Fast: 리스크 분석 & 반대 의견
- Gemini 2.5 Flash Lite: 뉴스/부상자 분석
- GPT-4o-mini: 정리/구조화

백업 모델 (Fallback):
- Xiaomi MiMo-V2-Flash (free)
- TNG DeepSeek R1T2 Chimera (free)
- Z.AI GLM 4.5 Air (free)

Consensus Scoring: 5/5, 4/5, 3/5
"""
import os
import json
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Load environment variables
load_dotenv('/Users/js/g9/regime_zero/.env')

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"


class AIBettingCouncil:
    """
    5인 AI 베팅 분석 위원회
    """

    COUNCIL_MEMBERS = {
        "DeepSeek_V3": {
            "name": "DeepSeek V3.2",
            "role": "정량 분석가 (Quantitative Analyst)",
            "model": "deepseek/deepseek-chat",
            "backup_models": [
                "xiaomi/mimo-v2-flash:free",
                "tng/deepseek-r1t2-chimera:free",
                "zai/glm-4.5-air:free"
            ],
            "focus": "Win Rate, 스프레드 분석, 통계적 유의성",
            "persona": """당신은 DeepSeek V3, 정량 분석 전문가입니다.

**역할**: 배당률과 통계 데이터를 냉철하게 분석
**강점**: 수학, 확률, 데이터 기반 의사결정
**약점**: 감정적 요소, 뉴스 영향 무시 가능성

**분석 포인트**:
- Win Rate 계산 및 기댓값
- 스프레드 커버율 분석
- 배당률 vs 실제 승률 비교 (Value 찾기)
- 통계적 유의성 검증

**출력 형식** (JSON):
{
  "recommendation": "BET/PASS",
  "confidence": "HIGH/MEDIUM/LOW",
  "edge": "Expected value in %",
  "analysis": "상세 분석 (Markdown)",
  "self_critique": "본인 분석의 약점"
}"""
        },

        "Qwen_72B": {
            "name": "Qwen 72B",
            "role": "레짐 패턴 분석가 (Regime Analyst)",
            "model": "qwen/qwen-2.5-72b-instruct",
            "backup_models": [
                "xiaomi/mimo-v2-flash:free",
                "tng/deepseek-r1t2-chimera:free",
                "zai/glm-4.5-air:free"
            ],
            "focus": "레짐 패턴, 역사적 유사성, 스토리텔링",
            "persona": """당신은 Qwen 72B, 레짐 분석 및 스토리텔링 전문가입니다.

**역할**: Graph RAG 데이터를 스토리로 연결
**강점**: 맥락 이해, 패턴 인식, 서사 구성
**약점**: 감정에 치우쳐 하드 데이터 경시 가능

**분석 포인트**:
- 현재 팀 레짐 (상승/하락/안정)
- 역사적 H2H 패턴
- "이 경기는 과거 ____와 비슷하다"
- 승부 흐름 예측

**출력 형식** (JSON):
{
  "recommendation": "BET/PASS",
  "confidence": "HIGH/MEDIUM/LOW",
  "pattern": "감지된 레짐 패턴",
  "analysis": "상세 분석 (Markdown)",
  "self_critique": "본인 분석의 약점"
}"""
        },

        "Grok_Fast": {
            "name": "Grok 4.1 Fast",
            "role": "리스크 분석가 (Risk Manager)",
            "model": "x-ai/grok-4.1-fast",
            "backup_models": [
                "xiaomi/mimo-v2-flash:free",
                "tng/deepseek-r1t2-chimera:free",
                "zai/glm-4.5-air:free"
            ],
            "focus": "반대 의견, 블랙스완, 군중심리 반대",
            "persona": """당신은 Grok Fast, 리스크 관리 및 반대 의견 전문가입니다.

**역할**: 모두가 낙관할 때 경고하라
**강점**: 회의론, 리스크 탐지, 비주류 관점
**약점**: 지나친 비관론으로 기회 놓칠 수 있음

**분석 포인트**:
- "모두가 A팀에 베팅하면 → B팀이 value"
- 숨겨진 리스크 (부상자, 컨디션)
- 군중심리 역행 (Fade the public)
- 최악의 시나리오

**출력 형식** (JSON):
{
  "recommendation": "BET/PASS/CONTRARIAN",
  "confidence": "HIGH/MEDIUM/LOW",
  "risk_score": "1-10 (10=최고위험)",
  "analysis": "상세 분석 (Markdown)",
  "self_critique": "본인 분석의 약점"
}"""
        },

        "Gemini_Flash": {
            "name": "Gemini 2.5 Flash Lite",
            "role": "뉴스 분석가 (News Analyst)",
            "model": "google/gemini-2.5-flash-lite",
            "backup_models": [
                "xiaomi/mimo-v2-flash:free",
                "tng/deepseek-r1t2-chimera:free",
                "zai/glm-4.5-air:free"
            ],
            "focus": "최신 뉴스, 부상자 리포트, 실시간 컨텍스트",
            "persona": """당신은 Gemini 2.0 Flash, 뉴스 및 실시간 컨텍스트 전문가입니다.

**역할**: 경기 당일 변수 확인
**강점**: 실시간 정보, 부상자 리포트, 헤드라인 분석
**약점**: 최근 편향 (Recency Bias)

**분석 포인트**:
- 부상자 명단 (30분 전 확인)
- 최근 팀 뉴스 (감독 교체, 내부 갈등 등)
- 휴식 일수 (Back-to-back 여부)
- 날씨/여행 영향 (있다면)

**출력 형식** (JSON):
{
  "recommendation": "BET/PASS/WAIT",
  "confidence": "HIGH/MEDIUM/LOW",
  "news_impact": "긍정/부정/중립",
  "analysis": "상세 분석 (Markdown)",
  "self_critique": "본인 분석의 약점"
}"""
        },

        "GPT4o_mini": {
            "name": "GPT-4o-mini",
            "role": "종합 정리 (Synthesizer)",
            "model": "openai/gpt-4o-mini",
            "backup_models": [
                "xiaomi/mimo-v2-flash:free",
                "tng/deepseek-r1t2-chimera:free",
                "zai/glm-4.5-air:free"
            ],
            "focus": "구조화, 명확성, Executive Summary",
            "persona": """당신은 GPT-4o-mini, 종합 정리 및 구조화 전문가입니다.

**역할**: 복잡한 정보를 명료하게 정리
**강점**: 구조화, 가독성, 핵심 추출
**약점**: 지나친 단순화로 뉘앙스 손실 가능

**분석 포인트**:
- Executive Summary (3줄 요약)
- 핵심 포인트 Bullet Points
- 추천 액션 명확화
- 리스크/리워드 균형

**출력 형식** (JSON):
{
  "recommendation": "BET/PASS",
  "confidence": "HIGH/MEDIUM/LOW",
  "summary": "3줄 요약",
  "analysis": "상세 분석 (Markdown)",
  "self_critique": "본인 분석의 약점"
}"""
        }
    }

    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")

    def call_analyst(self, analyst_id: str, user_prompt: str) -> Dict:
        """
        개별 AI 분석가 호출 (Fallback 지원)

        메인 모델 실패 시 백업 모델 순차 시도:
        1. 메인 모델
        2. Xiaomi MiMo-V2-Flash (free)
        3. TNG DeepSeek R1T2 Chimera (free)
        4. Z.AI GLM 4.5 Air (free)
        """
        analyst = self.COUNCIL_MEMBERS[analyst_id]

        print(f"\n🤖 {analyst['name']} ({analyst['role']}) 분석 중...")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://g9-regime-zero.com",
            "X-Title": "G9 NBA Betting Analysis"
        }

        # 시도할 모델 리스트 (메인 + 백업)
        models_to_try = [analyst['model']]
        backup_models = analyst.get('backup_models', [])
        models_to_try.extend(backup_models)

        last_error = None

        for idx, model in enumerate(models_to_try):
            is_backup = idx > 0
            if is_backup:
                print(f"  ↳ 백업 모델 시도 ({idx}/{len(backup_models)}): {model}")

            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": analyst['persona']},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }

            try:
                response = requests.post(
                    OPENROUTER_BASE_URL,
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                response.raise_for_status()

                result = response.json()
                content = result['choices'][0]['message']['content']

                # JSON 파싱 시도
                try:
                    clean_content = content.replace("```json", "").replace("```", "").strip()
                    parsed = json.loads(clean_content)

                    if is_backup:
                        print(f"  ✅ 백업 모델 성공: {model}")

                    return {
                        "analyst": analyst['name'],
                        "role": analyst['role'],
                        "success": True,
                        "model_used": model,
                        "is_backup": is_backup,
                        "output": parsed
                    }
                except:
                    # JSON 파싱 실패 시 텍스트로 반환
                    if is_backup:
                        print(f"  ✅ 백업 모델 성공 (JSON 파싱 실패): {model}")

                    return {
                        "analyst": analyst['name'],
                        "role": analyst['role'],
                        "success": True,
                        "model_used": model,
                        "is_backup": is_backup,
                        "output": {
                            "recommendation": "PASS",
                            "confidence": "LOW",
                            "analysis": content,
                            "self_critique": "JSON 형식 파싱 실패"
                        }
                    }

            except Exception as e:
                last_error = str(e)
                if is_backup:
                    print(f"  ❌ 백업 모델 실패: {model} - {e}")
                else:
                    print(f"  ⚠️ 메인 모델 실패, 백업 시도 중... ({e})")
                continue  # 다음 모델 시도

        # 모든 모델 실패
        print(f"❌ {analyst['name']} 전체 실패 (메인 + 백업 {len(backup_models)}개 모두 실패)")
        return {
            "analyst": analyst['name'],
            "role": analyst['role'],
            "success": False,
            "error": f"All models failed. Last error: {last_error}"
        }

    def load_context_from_file(self, json_filepath: str) -> Dict:
        """
        Stage 1에서 생성한 JSON 컨텍스트 파일 로드 (RAW DATA만)

        🚀 OPTIMIZED: 메인 리포트 텍스트는 로드하지 않음 (토큰 절약)
        """
        with open(json_filepath, 'r') as f:
            context = json.load(f)

        # AI Council용 포맷으로 변환 (RAW DATA만)
        return {
            "home_team": context['game_info']['home_team'],
            "away_team": context['game_info']['away_team'],
            "game_time": context['game_info']['game_time'],
            "odds_formatted": context['odds']['formatted_text'],
            "odds_moneyline": context['odds']['moneyline'],
            "odds_spreads": context['odds']['spreads'],
            "team_stats": context.get('team_stats', {}),
            "head_to_head": context.get('head_to_head', []),
            "graph_data_available": context.get('graph_data_available', False)
        }

    def run_council_analysis(self, betting_context: Dict) -> Dict:
        """
        5인 위원회 병렬 실행 및 Consensus 도출
        """
        print("\n" + "="*60)
        print("🏛️  5인 AI 베팅 분석 위원회 소집")
        print("="*60)

        # 프롬프트 구성
        user_prompt = self._build_prompt(betting_context)

        # 병렬 실행
        results = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.call_analyst, analyst_id, user_prompt): analyst_id
                for analyst_id in self.COUNCIL_MEMBERS.keys()
            }

            for future in as_completed(futures):
                analyst_id = futures[future]
                try:
                    result = future.result()
                    results[analyst_id] = result
                except Exception as e:
                    print(f"❌ {analyst_id} 예외 발생: {e}")

        # Consensus 도출
        consensus = self._calculate_consensus(results)

        return {
            "individual_analyses": results,
            "consensus": consensus,
            "metadata": {
                "home_team": betting_context.get('home_team'),
                "away_team": betting_context.get('away_team'),
                "total_analysts": len(results),
                "successful_analysts": sum(1 for r in results.values() if r.get('success'))
            }
        }

    def _build_prompt(self, context: Dict) -> str:
        """
        베팅 컨텍스트를 AI 프롬프트로 변환 (RAW DATA만 사용)

        🚀 OPTIMIZED: 메인 리포트 텍스트 제외, Raw Data만 전달
        """
        home = context.get('home_team', 'Unknown')
        away = context.get('away_team', 'Unknown')

        prompt = f"""# NBA 베팅 분석 요청

## 경기 정보
- **매치업**: {away} @ {home}
- **경기 시간**: {context.get('game_time', 'TBD')}

## 배당률 정보 (The Odds API)

{context.get('odds_formatted', '배당률 정보 없음')}

**Moneyline**:
- {home}: {context.get('odds_moneyline', {}).get('home', {}).get('odds', 'N/A')} ({context.get('odds_moneyline', {}).get('home', {}).get('bookmaker', 'N/A')})
- {away}: {context.get('odds_moneyline', {}).get('away', {}).get('odds', 'N/A')} ({context.get('odds_moneyline', {}).get('away', {}).get('bookmaker', 'N/A')})

**Spreads**:
- {home}: {context.get('odds_spreads', {}).get('home', {}).get('point', 'N/A')} @ {context.get('odds_spreads', {}).get('home', {}).get('odds', 'N/A')}
- {away}: {context.get('odds_spreads', {}).get('away', {}).get('point', 'N/A')} @ {context.get('odds_spreads', {}).get('away', {}).get('odds', 'N/A')}

"""

        # Graph 데이터 추가 (있으면)
        if context.get('graph_data_available') and context.get('team_stats'):
            prompt += f"""
## Graph RAG 분석 데이터 (Neo4j)

### {home} (홈팀)
{json.dumps(context['team_stats'].get('home', {}), indent=2, ensure_ascii=False)}

### {away} (원정팀)
{json.dumps(context['team_stats'].get('away', {}), indent=2, ensure_ascii=False)}

"""

        # H2H 데이터
        if context.get('head_to_head'):
            prompt += f"""
### 최근 H2H 기록
{json.dumps(context['head_to_head'], indent=2, ensure_ascii=False)}

"""

        prompt += """
## 분석 요청

위 **RAW DATA**를 기반으로 당신의 역할에 맞게 이 경기를 분석하세요.

**출력 형식** (JSON):
```json
{
  "recommendation": "BET/PASS/WAIT",
  "confidence": "HIGH/MEDIUM/LOW",
  "analysis": "상세 분석 내용 (Markdown 형식, 300자 이내)",
  "self_critique": "본인 분석의 한계점 (100자 이내)"
}
```

**중요**:
- 당신의 페르소나(역할)에 충실하세요
- 다른 분석가의 관점은 무시하세요
- RAW DATA만 보고 독립적으로 판단하세요
- 간결하게 작성하세요 (토큰 절약)
"""

        return prompt

    def _calculate_consensus(self, results: Dict) -> Dict:
        """
        Consensus Scoring: 5/5, 4/5, 3/5 등
        """
        recommendations = []
        confidences = []

        for analyst_id, result in results.items():
            if not result.get('success'):
                continue

            output = result.get('output', {})
            rec = output.get('recommendation', 'PASS').upper()
            conf = output.get('confidence', 'LOW').upper()

            recommendations.append(rec)
            confidences.append(conf)

        # BET 투표 수
        bet_votes = recommendations.count('BET')
        total_votes = len(recommendations)

        # Consensus 점수
        if total_votes == 0:
            consensus_score = "0/0"
            final_recommendation = "PASS"
        else:
            consensus_score = f"{bet_votes}/{total_votes}"

            # 과반수 이상이면 BET
            if bet_votes >= (total_votes / 2):
                final_recommendation = "BET"
            else:
                final_recommendation = "PASS"

        # 신뢰도 종합 (HIGH가 많으면 전체 신뢰도 높음)
        high_conf_count = confidences.count('HIGH')
        if high_conf_count >= (len(confidences) / 2):
            overall_confidence = "HIGH"
        elif confidences.count('MEDIUM') >= (len(confidences) / 2):
            overall_confidence = "MEDIUM"
        else:
            overall_confidence = "LOW"

        return {
            "score": consensus_score,
            "recommendation": final_recommendation,
            "confidence": overall_confidence,
            "bet_votes": bet_votes,
            "total_votes": total_votes,
            "details": {
                "recommendations": recommendations,
                "confidences": confidences
            }
        }

    def format_premium_report(self, council_result: Dict) -> str:
        """
        프리미엄 리포트 포맷 (유료 판매용)
        """
        consensus = council_result['consensus']
        analyses = council_result['individual_analyses']
        meta = council_result['metadata']

        report = f"""# 🏀 G9 Premium NBA Betting Report
## {meta['away_team']} @ {meta['home_team']}

---

## 🎯 AI 위원회 합의 (Consensus)

**최종 추천**: {consensus['recommendation']}
**합의 점수**: {consensus['score']} ({consensus['bet_votes']}명이 BET 추천)
**전체 신뢰도**: {consensus['confidence']}

---

## 👥 5인 AI 분석가 개별 의견

"""

        # 각 분석가 의견
        for analyst_id, result in analyses.items():
            if not result.get('success'):
                report += f"\n### ❌ {result['analyst']} ({result['role']})\n"
                report += f"*분석 실패: {result.get('error', 'Unknown error')}*\n\n"
                continue

            output = result['output']

            # 백업 모델 사용 여부 표시
            backup_badge = ""
            if result.get('is_backup'):
                backup_badge = " 🔄 *백업 모델 사용*"

            report += f"""
### {result['analyst']} ({result['role']}){backup_badge}

**추천**: {output.get('recommendation', 'N/A')}
**신뢰도**: {output.get('confidence', 'N/A')}

{output.get('analysis', '*분석 내용 없음*')}

<details>
<summary>자기 비판 (Self-Critique)</summary>

{output.get('self_critique', '*없음*')}

</details>

---
"""

        # 투자 가이드
        report += f"""
## 💰 투자 가이드

**위원회 합의**: {consensus['score']}

- **5/5 또는 4/5**: 강력 추천 (2-3 units)
- **3/5**: 중립/소극적 (0.5-1 unit)
- **2/5 이하**: 패스 (0 units)

**현재 점수**: {consensus['score']} → {'**강력 추천**' if consensus['bet_votes'] >= 4 else '**소극적**' if consensus['bet_votes'] == 3 else '**패스**'}

---

## ⚠️ 리스크 고지

이 리포트는 AI 분석 기반이며, **투자 권유가 아닙니다**.
모든 베팅은 본인 책임하에 진행하세요.

---

*Report Generated by G9 Regime Zero AI Council*
*Premium Tier - 5 AI Analysts*
"""

        return report


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='5인 AI 베팅 분석 위원회')
    parser.add_argument('--context-file', type=str, help='Stage 1에서 생성한 JSON 컨텍스트 파일')
    parser.add_argument('--output', type=str, help='프리미엄 리포트 저장 경로')
    args = parser.parse_args()

    council = AIBettingCouncil()

    if args.context_file:
        # JSON 파일에서 컨텍스트 로드
        print(f"📂 Loading context from: {args.context_file}")
        betting_context = council.load_context_from_file(args.context_file)
    else:
        # 샘플 컨텍스트 (테스트용)
        print("⚠️  No context file provided. Using sample data.")
        betting_context = {
            "home_team": "Toronto Raptors",
            "away_team": "Golden State Warriors",
            "game_time": "2025-12-28T20:40:00Z",
            "odds_formatted": """
MONEYLINE: GSW -170, TOR +154
SPREADS: GSW -4.5 @ -101, TOR +4.5 @ -110
"""
        }

    # 위원회 분석 실행
    result = council.run_council_analysis(betting_context)

    print("\n" + "="*60)
    print("📊 CONSENSUS RESULT")
    print("="*60)
    print(json.dumps(result['consensus'], indent=2))

    # 프리미엄 리포트 생성
    premium_report = council.format_premium_report(result)

    # 저장
    if args.output:
        output_path = args.output
    else:
        # 기본 경로
        away = betting_context['away_team'].replace(' ', '_')
        home = betting_context['home_team'].replace(' ', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f'/Users/js/g9/nba_data/odds_reports/premium_{away}_at_{home}_{timestamp}.md'

    with open(output_path, 'w') as f:
        f.write(premium_report)

    print(f"\n✅ Premium report saved to: {output_path}")

    # JSON 결과도 저장
    json_output = output_path.replace('.md', '.json')
    with open(json_output, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"✅ Council JSON saved to: {json_output}")
