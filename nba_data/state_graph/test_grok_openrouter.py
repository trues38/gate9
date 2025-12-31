#!/usr/bin/env python3
"""
Grok 4.1 Fast API 테스트 (via OpenRouter)

NBA 실시간 이벤트 정규화 테스트:
- Lineup changes (OUT / RULED OUT / INACTIVE)
- Injury reports (QUESTIONABLE / DOUBTFUL / PROBABLE)
- Referee assignments

사용자 경제 레짐 분석에 사용하던 Grok 4 FAST 모델 테스트
"""

import os
import json
from typing import Dict, List, Optional
import requests
from datetime import datetime


class GrokOpenRouterTester:
    """Grok 4.1 Fast API 테스트 클래스 (OpenRouter)"""

    def __init__(self, api_key: Optional[str] = None):
        """
        OpenRouter API 초기화

        API Key는 환경변수 OPENROUTER_API_KEY에서 가져옴
        또는 직접 전달 가능
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY 환경변수를 설정하거나 api_key를 전달하세요")

        self.base_url = "https://openrouter.ai/api/v1"
        self.model_id = "x-ai/grok-4.1-fast"

        # HTTP 헤더
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/yourusername/nba_data",  # 필수
            "X-Title": "NBA Real-time Event Normalizer"  # 선택
        }

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1000,
        reasoning: bool = False
    ) -> Dict:
        """
        Grok 4.1 Fast 채팅 완료 요청

        Args:
            messages: 대화 메시지 리스트 [{"role": "user", "content": "..."}]
            temperature: 온도 (0.0 = 결정적, 1.0 = 창의적)
            max_tokens: 최대 출력 토큰
            reasoning: True = 추론 활성화

        Returns:
            API 응답 (JSON)
        """
        payload = {
            "model": self.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Reasoning 활성화 (선택)
        if reasoning:
            payload["reasoning"] = {"enabled": True}

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"❌ API 요청 실패: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"응답: {e.response.text}")
            raise

    def normalize_lineup_event(self, tweet_text: str) -> Dict:
        """
        라인업 변경 트윗 정규화

        입력 예시:
        - "Luka Doncic is OUT tonight vs Warriors"
        - "Kawhi Leonard ruled out for rest"
        - "Jimmy Butler (ankle) - INACTIVE"

        출력 예시:
        {
          "event_type": "lineup_change",
          "player": "Luka Doncic",
          "team": "DAL",
          "status": "OUT",
          "reason": null,
          "game": "DAL vs GSW",
          "confidence": 0.95
        }
        """
        system_prompt = """You are an NBA event normalizer. Parse tweet text and extract structured data.

Output JSON only, no explanation. Format:
{
  "event_type": "lineup_change" | "injury_report" | "referee_assignment" | "unknown",
  "player": "Player Name" or null,
  "team": "TEAM_ABBR" or null,
  "status": "OUT" | "QUESTIONABLE" | "DOUBTFUL" | "PROBABLE" | "ACTIVE" | null,
  "reason": "injury/rest/personal" or null,
  "game": "TEAM1 vs TEAM2" or null,
  "referee_crew": ["Ref1", "Ref2", "Ref3"] or null,
  "confidence": 0.0-1.0,
  "raw_text": "original tweet"
}

Key rules:
- Normalize all status variations to standard terms (OUT/QUESTIONABLE/DOUBTFUL/PROBABLE)
- Extract team abbreviations (3 letters)
- Identify opponent from context
- Confidence = certainty of extraction (0.0-1.0)
"""

        user_message = f"Parse this tweet:\n\n{tweet_text}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = self.chat_completion(messages, temperature=0.1)

        # 응답 파싱
        content = response['choices'][0]['message']['content']

        # JSON 추출 (코드 블록 제거)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        return json.loads(content)

    def test_multiple_events(self, tweet_samples: List[str]) -> List[Dict]:
        """여러 트윗 샘플 일괄 테스트"""
        results = []

        print("\n" + "="*80)
        print("🧪 Grok 4.1 Fast - NBA 이벤트 정규화 테스트")
        print("="*80 + "\n")

        for i, tweet in enumerate(tweet_samples, 1):
            print(f"[{i}/{len(tweet_samples)}] 원본 트윗:")
            print(f"  {tweet}")
            print()

            try:
                result = self.normalize_lineup_event(tweet)
                results.append(result)

                print("✅ 정규화 결과:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                print()

            except Exception as e:
                print(f"❌ 처리 실패: {e}")
                print()
                results.append({"error": str(e), "raw_text": tweet})

            print("-" * 80 + "\n")

        return results


def main():
    """테스트 실행"""

    # OpenRouter API Key 확인
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY 환경변수를 설정하세요")
        print("\n설정 방법:")
        print("  export OPENROUTER_API_KEY='your-api-key-here'")
        print("\nAPI Key 발급: https://openrouter.ai/keys")
        return

    # 테스터 초기화
    tester = GrokOpenRouterTester(api_key)

    # NBA 이벤트 샘플 (실제 트윗 스타일)
    tweet_samples = [
        # Lineup changes
        "Luka Doncic is OUT tonight vs Warriors due to ankle injury",
        "Kawhi Leonard ruled out for rest - DNP tonight @ Lakers",
        "Jimmy Butler (ankle) - INACTIVE for Heat vs Celtics",

        # Injury reports
        "Anthony Davis QUESTIONABLE (back) for tonight's game",
        "Stephen Curry PROBABLE vs Rockets - expected to play",
        "Giannis Antetokounmpo DOUBTFUL (knee soreness)",

        # Referee assignments
        "Crew Chief: Scott Foster. Referees: Tony Brothers, Marc Davis. Game: MIA @ LAL",

        # Multiple players
        "OUT: KD (hamstring), Booker (ankle). Suns @ Mavs tonight",

        # 애매한 표현 (정규화 테스트)
        "Ja Morant won't play tonight - personal reasons",
        "LeBron listed as day-to-day, status TBD vs Denver"
    ]

    # 테스트 실행
    results = tester.test_multiple_events(tweet_samples)

    # 결과 저장
    output_file = "grok_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "model": tester.model_id,
            "total_samples": len(tweet_samples),
            "results": results
        }, f, indent=2, ensure_ascii=False)

    print("="*80)
    print(f"✅ 테스트 완료 - 결과 저장: {output_file}")
    print("="*80)

    # 통계
    success_count = sum(1 for r in results if "error" not in r)
    avg_confidence = sum(r.get("confidence", 0) for r in results if "error" not in r) / max(success_count, 1)

    print(f"\n📊 통계:")
    print(f"  - 성공: {success_count}/{len(tweet_samples)}")
    print(f"  - 평균 신뢰도: {avg_confidence:.2f}")
    print()


if __name__ == "__main__":
    main()
