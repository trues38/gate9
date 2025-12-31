"""
Layer 1: X Search Real-time Monitor
xAI Agent Tools API를 사용한 실시간 이벤트 감지
"""

import os
import re
import json
import asyncio
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import yaml


class EventType(Enum):
    """이벤트 유형"""
    INJURY = "INJURY"
    LINEUP = "LINEUP"
    TRADE = "TRADE"
    SUSPENSION = "SUSPENSION"
    BREAKING = "BREAKING"


class SourceTier(Enum):
    """소스 신뢰도 티어"""
    TIER1 = 1  # 최우선 (확실한 소스)
    TIER2 = 2  # 우선 (신뢰도 높음)
    TIER3 = 3  # 참고 (검증 필요)
    OFFICIAL = 0  # 공식


@dataclass
class RealTimeEvent:
    """실시간 이벤트 구조"""
    sport: str
    event_type: EventType
    player: Optional[str]
    team: Optional[str]
    status: Optional[str]
    details: Dict[str, Any]
    source: str
    source_tier: int
    timestamp: datetime
    raw_text: str
    tweet_id: str
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            **asdict(self),
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat()
        }

    def to_alert_message(self) -> str:
        """알림 메시지 생성"""
        emoji_map = {
            EventType.INJURY: "🏥",
            EventType.LINEUP: "📋",
            EventType.TRADE: "🔄",
            EventType.SUSPENSION: "⚠️",
            EventType.BREAKING: "🚨"
        }

        emoji = emoji_map.get(self.event_type, "📢")
        tier_indicator = "⭐" * (4 - self.source_tier) if self.source_tier > 0 else "✅"

        return f"""
{emoji} **{self.event_type.value}** {tier_indicator}

**Player**: {self.player or 'N/A'}
**Team**: {self.team or 'N/A'}
**Status**: {self.status or 'N/A'}

> {self.raw_text[:200]}{'...' if len(self.raw_text) > 200 else ''}

**Source**: @{self.source}
**Time**: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""


class XSearchMonitor:
    """
    X Search 실시간 모니터

    xAI Agent Tools API를 사용하여 X에서 실시간 이벤트 감지

    Usage:
        monitor = XSearchMonitor("nba")
        events = await monitor.search_injury_updates()
        for event in events:
            await monitor.send_alert(event)
    """

    XAI_API_URL = "https://api.x.ai/v1/chat/completions"

    def __init__(self, sport: str):
        """
        Args:
            sport: 스포츠 코드 (nba, nfl, mlb, etc.)
        """
        self.sport = sport
        self.config = self._load_config()
        self.xai_api_key = os.getenv('XAI_API_KEY')

        if not self.xai_api_key:
            raise ValueError("XAI_API_KEY environment variable not set")

        # 팀 매핑 로드
        self.teams = self.config.get('teams', {})

    def _load_config(self) -> Dict[str, Any]:
        """스포츠별 설정 로드"""
        config_path = Path(f"/Users/js/g9/g9_sports_platform/sports/{self.sport}/config.yaml")

        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _get_accounts_by_tier(self, tier: str) -> List[Dict[str, Any]]:
        """티어별 계정 목록 반환"""
        realtime_config = self.config.get('layer1_realtime', {})
        x_accounts = realtime_config.get('x_accounts', {})
        return x_accounts.get(tier, [])

    def _build_query(self, query_type: str, account: str) -> str:
        """쿼리 템플릿 빌드"""
        realtime_config = self.config.get('layer1_realtime', {})
        queries = realtime_config.get('queries', {})
        template = queries.get(query_type, '')
        return template.replace('{account}', account)

    async def _call_x_search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        xAI Agent Tools API로 X Search 실행

        Args:
            query: X 검색 쿼리
            max_results: 최대 결과 수

        Returns:
            트윗 리스트
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.XAI_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.xai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "grok-beta",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a sports news analyst. Extract tweet information accurately."
                            },
                            {
                                "role": "user",
                                "content": f"Search X (Twitter) for recent tweets matching: {query}\n\nReturn the tweets as JSON array with fields: id, text, author_username, created_at"
                            }
                        ],
                        "tools": [
                            {
                                "type": "function",
                                "function": {
                                    "name": "x_search",
                                    "description": "Search X (Twitter) for tweets",
                                    "parameters": {
                                        "type": "object",
                                        "properties": {
                                            "query": {
                                                "type": "string",
                                                "description": "Search query"
                                            },
                                            "max_results": {
                                                "type": "integer",
                                                "description": "Maximum number of results"
                                            },
                                            "search_type": {
                                                "type": "string",
                                                "enum": ["latest", "popular"],
                                                "description": "Type of search"
                                            }
                                        },
                                        "required": ["query"]
                                    }
                                }
                            }
                        ],
                        "tool_choice": "auto"
                    }
                )

                response.raise_for_status()
                data = response.json()

                # 응답에서 트윗 추출
                return self._extract_tweets_from_response(data)

            except httpx.HTTPStatusError as e:
                print(f"[X Search] HTTP error: {e}")
                return []
            except Exception as e:
                print(f"[X Search] Error: {e}")
                return []

    def _extract_tweets_from_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """xAI 응답에서 트윗 추출"""
        tweets = []

        try:
            # 메시지 내용 확인
            choices = response.get('choices', [])
            if not choices:
                return tweets

            message = choices[0].get('message', {})

            # Tool call 결과 확인
            tool_calls = message.get('tool_calls', [])
            for tool_call in tool_calls:
                if tool_call.get('function', {}).get('name') == 'x_search':
                    # 결과 파싱
                    result = tool_call.get('function', {}).get('arguments', '{}')
                    if isinstance(result, str):
                        result = json.loads(result)
                    # 실제 트윗 데이터는 여기서 추출

            # 또는 content에서 직접 추출
            content = message.get('content', '')
            if content:
                # JSON 배열 찾기
                json_match = re.search(r'\[[\s\S]*\]', content)
                if json_match:
                    tweets = json.loads(json_match.group())

        except Exception as e:
            print(f"[X Search] Parse error: {e}")

        return tweets

    def _parse_injury_event(self, tweet: Dict[str, Any], tier: int) -> Optional[RealTimeEvent]:
        """부상 이벤트 파싱"""
        text = tweet.get('text', '')

        # 부상 패턴 매칭
        patterns = self.config.get('layer1_realtime', {}).get('parsing_patterns', {})
        injury_pattern = patterns.get('injury', r"(\w+(?:\s\w+)?)['\']?s?\s+\(([^)]+)\)\s+(OUT|DOUBTFUL|QUESTIONABLE|DAY-TO-DAY|PROBABLE)")

        match = re.search(injury_pattern, text, re.IGNORECASE)

        if match:
            player = match.group(1)
            injury_type = match.group(2)
            status = match.group(3).upper()

            return RealTimeEvent(
                sport=self.sport.upper(),
                event_type=EventType.INJURY,
                player=player,
                team=self._extract_team(text),
                status=status,
                details={"injury_type": injury_type},
                source=tweet.get('author_username', 'unknown'),
                source_tier=tier,
                timestamp=self._parse_timestamp(tweet.get('created_at')),
                raw_text=text,
                tweet_id=tweet.get('id', ''),
                confidence=0.9 if tier == 1 else 0.7
            )

        return None

    def _parse_lineup_event(self, tweet: Dict[str, Any], tier: int) -> Optional[RealTimeEvent]:
        """라인업 이벤트 파싱"""
        text = tweet.get('text', '')

        patterns = self.config.get('layer1_realtime', {}).get('parsing_patterns', {})
        lineup_pattern = patterns.get('lineup_change', r"(\w+(?:\s\w+)?)\s+(will start|won't start|starting|benched|DNP)")

        match = re.search(lineup_pattern, text, re.IGNORECASE)

        if match:
            player = match.group(1)
            action = match.group(2).lower()

            status = "STARTING" if "start" in action else "BENCHED"
            if "dnp" in action.lower():
                status = "DNP"

            return RealTimeEvent(
                sport=self.sport.upper(),
                event_type=EventType.LINEUP,
                player=player,
                team=self._extract_team(text),
                status=status,
                details={"action": action},
                source=tweet.get('author_username', 'unknown'),
                source_tier=tier,
                timestamp=self._parse_timestamp(tweet.get('created_at')),
                raw_text=text,
                tweet_id=tweet.get('id', ''),
                confidence=0.85 if tier == 1 else 0.65
            )

        return None

    def _extract_team(self, text: str) -> Optional[str]:
        """텍스트에서 팀 추출"""
        for team_code, team_info in self.teams.items():
            team_name = team_info.get('name', '')
            city = team_info.get('city', '')

            # 팀 이름 또는 도시 매칭
            if team_name.lower() in text.lower() or city.lower() in text.lower():
                return team_code

            # 팀 별명 매칭 (Lakers, Warriors 등)
            nickname = team_name.split()[-1]  # "Los Angeles Lakers" -> "Lakers"
            if nickname.lower() in text.lower():
                return team_code

        return None

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """타임스탬프 파싱"""
        if not timestamp_str:
            return datetime.now()

        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except:
            return datetime.now()

    async def search_events(self, event_type: str = "injury") -> List[RealTimeEvent]:
        """
        이벤트 유형별 검색

        Args:
            event_type: injury, lineup, trade, breaking

        Returns:
            감지된 이벤트 리스트
        """
        events = []

        # 티어별로 검색
        tier_configs = [
            ('tier1', 1),
            ('tier2', 2),
            ('tier3', 3),
            ('official', 0)
        ]

        for tier_name, tier_value in tier_configs:
            accounts = self._get_accounts_by_tier(tier_name)

            for account_config in accounts:
                handle = account_config.get('handle', '')
                if not handle:
                    continue

                query = self._build_query(event_type, handle)
                print(f"[X Search] Searching @{handle} for {event_type}...")

                tweets = await self._call_x_search(query)

                for tweet in tweets:
                    event = None

                    if event_type == "injury":
                        event = self._parse_injury_event(tweet, tier_value)
                    elif event_type == "lineup":
                        event = self._parse_lineup_event(tweet, tier_value)
                    # 다른 이벤트 타입 추가 가능

                    if event:
                        events.append(event)

        # 중복 제거 (tweet_id 기준)
        seen_ids = set()
        unique_events = []
        for event in events:
            if event.tweet_id not in seen_ids:
                seen_ids.add(event.tweet_id)
                unique_events.append(event)

        return unique_events

    async def send_webhook_alert(self, event: RealTimeEvent, webhook_url: str):
        """Webhook으로 알림 전송"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    webhook_url,
                    json=event.to_dict()
                )
                response.raise_for_status()
                print(f"[Alert] Sent to webhook: {event.event_type.value} - {event.player}")
            except Exception as e:
                print(f"[Alert] Webhook error: {e}")

    async def send_telegram_alert(self, event: RealTimeEvent, bot_token: str, chat_id: str):
        """Telegram으로 알림 전송"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                message = event.to_alert_message()
                response = await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": message,
                        "parse_mode": "Markdown"
                    }
                )
                response.raise_for_status()
                print(f"[Alert] Sent to Telegram: {event.event_type.value} - {event.player}")
            except Exception as e:
                print(f"[Alert] Telegram error: {e}")


# CLI 인터페이스
async def main():
    import argparse

    parser = argparse.ArgumentParser(description="X Search Real-time Monitor")
    parser.add_argument("sport", help="Sport code (nba, nfl, mlb, etc.)")
    parser.add_argument("--event", default="injury", choices=["injury", "lineup", "trade", "breaking"])
    parser.add_argument("--webhook", type=str, help="Webhook URL for alerts")

    args = parser.parse_args()

    monitor = XSearchMonitor(args.sport)
    events = await monitor.search_events(args.event)

    print(f"\n[Result] Found {len(events)} {args.event} events:")
    for event in events:
        print(f"\n{event.to_alert_message()}")

        if args.webhook:
            await monitor.send_webhook_alert(event, args.webhook)


if __name__ == "__main__":
    asyncio.run(main())
