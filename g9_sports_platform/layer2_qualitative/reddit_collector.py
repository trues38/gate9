"""
Layer 2: Reddit Post-Game Collector
경기 후 정성 데이터 수집 및 LLM 분석
"""

import os
import re
import json
import praw
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import yaml


@dataclass
class PlayerEvaluation:
    """선수 평가"""
    player: str
    sentiment: str  # positive, negative, neutral
    key_points: List[str]
    sample_quote: str
    score_avg: float = 0.0


@dataclass
class CoachAnalysis:
    """코치 분석"""
    coach: str
    rotations_sentiment: str
    rotations_points: List[str]
    schemes_sentiment: str
    schemes_points: List[str]
    decisions: List[str]


@dataclass
class TeamChemistry:
    """팀 케미스트리"""
    morale: str  # high, low, mixed
    leadership_moments: List[str]
    conflicts: List[str]
    notes: str


@dataclass
class BettingSentiment:
    """베팅 관련 센티먼트"""
    favorite_perception: str
    underdog_story: str
    betting_trends: List[str]
    sharp_money_hints: List[str]


@dataclass
class RedditAnalysis:
    """Reddit 분석 결과"""
    sport: str
    game_id: str
    thread_id: str
    thread_url: str
    thread_title: str

    player_evaluations: List[PlayerEvaluation]
    coach_analysis: Optional[CoachAnalysis]
    team_chemistry: Optional[TeamChemistry]
    betting_sentiment: Optional[BettingSentiment]

    overall_sentiment: str  # positive, negative, mixed
    controversies: List[str]
    key_insights: List[str]

    collected_at: datetime
    total_comments: int
    analyzed_comments: int

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'sport': self.sport,
            'game_id': self.game_id,
            'thread_id': self.thread_id,
            'thread_url': self.thread_url,
            'thread_title': self.thread_title,
            'player_evaluations': [asdict(pe) for pe in self.player_evaluations],
            'coach_analysis': asdict(self.coach_analysis) if self.coach_analysis else None,
            'team_chemistry': asdict(self.team_chemistry) if self.team_chemistry else None,
            'betting_sentiment': asdict(self.betting_sentiment) if self.betting_sentiment else None,
            'overall_sentiment': self.overall_sentiment,
            'controversies': self.controversies,
            'key_insights': self.key_insights,
            'collected_at': self.collected_at.isoformat(),
            'total_comments': self.total_comments,
            'analyzed_comments': self.analyzed_comments
        }


class RedditCollector:
    """
    Reddit Post-Game Thread 수집기

    Requirements:
        - Reddit API 앱 생성: https://www.reddit.com/prefs/apps
        - 환경변수: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET

    Usage:
        collector = RedditCollector("nba")
        analysis = await collector.collect_and_analyze("0022400123", ["LAL", "GSW"])
    """

    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, sport: str):
        """
        Args:
            sport: 스포츠 코드 (nba, nfl, mlb, etc.)
        """
        self.sport = sport
        self.config = self._load_config()

        # Reddit 초기화
        self.reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=f"G9-Sports-Intelligence-{sport}/1.0"
        )

        # OpenRouter API Key
        self.openrouter_key = os.getenv('OPENROUTER_API_KEY')

    def _load_config(self) -> Dict[str, Any]:
        """스포츠별 설정 로드"""
        config_path = Path(f"/Users/js/g9/g9_sports_platform/sports/{self.sport}/config.yaml")

        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _get_subreddit_config(self) -> Dict[str, Any]:
        """서브레딧 설정 반환"""
        return self.config.get('layer2_qualitative', {}).get('subreddits', {})

    def find_post_game_thread(self, game_id: str, teams: List[str]) -> Optional[praw.models.Submission]:
        """
        Post-Game Thread 찾기

        Args:
            game_id: 경기 ID
            teams: 팀 코드 리스트 [HOME, AWAY]

        Returns:
            Reddit Submission 객체 또는 None
        """
        subreddit_config = self._get_subreddit_config()
        main_subreddit = subreddit_config.get('main', {}).get('name', 'nba')
        pattern = subreddit_config.get('main', {}).get('post_game_pattern', 'Post Game Thread')

        subreddit = self.reddit.subreddit(main_subreddit)

        # 팀 이름으로 검색 쿼리 생성
        team_names = []
        for team_code in teams:
            team_info = self.config.get('teams', {}).get(team_code, {})
            if team_info:
                # "Lakers" 또는 "Los Angeles Lakers"
                team_names.append(team_info.get('name', '').split()[-1])

        search_query = f"Post Game Thread {' '.join(team_names)}"

        print(f"[Reddit] Searching: {search_query} in r/{main_subreddit}")

        try:
            for submission in subreddit.search(search_query, time_filter='day', limit=10):
                # 패턴 매칭
                if re.search(pattern, submission.title, re.IGNORECASE):
                    print(f"[Reddit] Found: {submission.title}")
                    return submission

        except Exception as e:
            print(f"[Reddit] Search error: {e}")

        return None

    def collect_top_comments(self, submission: praw.models.Submission) -> List[Dict[str, Any]]:
        """
        Top Comments 수집

        Args:
            submission: Reddit Submission 객체

        Returns:
            댓글 리스트
        """
        subreddit_config = self._get_subreddit_config()
        min_upvotes = subreddit_config.get('main', {}).get('min_upvotes', 500)

        # 댓글 정렬: top
        submission.comment_sort = 'top'
        submission.comments.replace_more(limit=0)  # "load more" 무시

        comments = []
        for comment in submission.comments.list():
            if hasattr(comment, 'score') and comment.score >= min_upvotes:
                comments.append({
                    'author': comment.author.name if comment.author else '[deleted]',
                    'body': comment.body,
                    'score': comment.score,
                    'created_utc': comment.created_utc,
                    'permalink': f"https://reddit.com{comment.permalink}"
                })

        print(f"[Reddit] Collected {len(comments)} top comments (>= {min_upvotes} upvotes)")
        return comments

    async def analyze_with_llm(self, comments: List[Dict[str, Any]], game_id: str, teams: List[str]) -> Dict[str, Any]:
        """
        LLM으로 댓글 분석

        Args:
            comments: 댓글 리스트
            game_id: 경기 ID
            teams: 팀 코드 리스트

        Returns:
            분석 결과 딕셔너리
        """
        # 댓글 텍스트 결합 (상위 50개)
        combined_text = "\n\n---\n\n".join([
            f"[Score: {c['score']}] {c['body'][:500]}"  # 각 댓글 500자 제한
            for c in comments[:50]
        ])

        # LLM 설정
        llm_config = self.config.get('layer2_qualitative', {}).get('llm', {})
        model = llm_config.get('model', 'qwen/qwen2.5-vl-72b-instruct')
        temperature = llm_config.get('temperature', 0.3)
        max_tokens = llm_config.get('max_tokens', 2000)

        prompt = self._build_analysis_prompt(combined_text, game_id, teams)

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    self.OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {self.openrouter_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://g9-sports-intelligence.local",
                        "X-Title": "G9 Sports Intelligence"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a sports analyst. Analyze Reddit comments and extract insights. Always respond in valid JSON format."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                )

                response.raise_for_status()
                data = response.json()

                content = data['choices'][0]['message']['content']

                # JSON 추출
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    return json.loads(json_match.group())

                return {}

            except Exception as e:
                print(f"[LLM] Analysis error: {e}")
                return {}

    def _build_analysis_prompt(self, comments_text: str, game_id: str, teams: List[str]) -> str:
        """분석 프롬프트 생성"""
        team_names = []
        for team_code in teams:
            team_info = self.config.get('teams', {}).get(team_code, {})
            if team_info:
                team_names.append(team_info.get('name', team_code))

        return f"""Analyze these {self.sport.upper()} Post-Game Thread comments.

**Game**: {team_names[0] if team_names else teams[0]} vs {team_names[1] if len(team_names) > 1 else teams[1]}
**Game ID**: {game_id}

---

**Reddit Comments (sorted by upvotes)**:

{comments_text}

---

**Extract the following (respond in JSON)**:

```json
{{
  "player_evaluations": [
    {{
      "player": "Player Name",
      "sentiment": "positive|negative|neutral",
      "key_points": ["point 1", "point 2"],
      "sample_quote": "Best quote from comments"
    }}
  ],
  "coach_analysis": {{
    "coach": "Coach Name",
    "rotations_sentiment": "positive|negative|neutral",
    "rotations_points": ["rotation decision 1", "rotation decision 2"],
    "schemes_sentiment": "positive|negative|neutral",
    "schemes_points": ["scheme observation 1"],
    "decisions": ["key decision 1"]
  }},
  "team_chemistry": {{
    "morale": "high|low|mixed",
    "leadership_moments": ["moment 1"],
    "conflicts": ["conflict if any"],
    "notes": "Overall chemistry observation"
  }},
  "betting_sentiment": {{
    "favorite_perception": "How fans view the favorite",
    "underdog_story": "Underdog narrative if any",
    "betting_trends": ["trend 1"],
    "sharp_money_hints": ["hint if any"]
  }},
  "overall_sentiment": "positive|negative|mixed",
  "controversies": ["controversy 1", "controversy 2"],
  "key_insights": ["insight 1", "insight 2", "insight 3"]
}}
```

Focus on:
1. **Player Performance**: Who was praised? Who was criticized? Hidden injury concerns?
2. **Coaching**: Rotations, timeout usage, defensive/offensive schemes
3. **Team Chemistry**: Leadership, conflicts, locker room vibes
4. **Betting Angles**: Trends, sharp money hints, line movements
5. **Controversies**: What are fans arguing about?

Be specific and use actual quotes from comments when possible.
"""

    async def collect_and_analyze(self, game_id: str, teams: List[str]) -> Optional[RedditAnalysis]:
        """
        Post-Game Thread 수집 및 분석 통합

        Args:
            game_id: 경기 ID
            teams: 팀 코드 리스트 [HOME, AWAY]

        Returns:
            RedditAnalysis 객체 또는 None
        """
        # 1. Post-Game Thread 찾기
        submission = self.find_post_game_thread(game_id, teams)
        if not submission:
            print(f"[Reddit] No Post-Game Thread found for {game_id}")
            return None

        # 2. Top Comments 수집
        comments = self.collect_top_comments(submission)
        if not comments:
            print(f"[Reddit] No qualifying comments for {game_id}")
            return None

        # 3. LLM 분석
        analysis = await self.analyze_with_llm(comments, game_id, teams)
        if not analysis:
            print(f"[Reddit] LLM analysis failed for {game_id}")
            return None

        # 4. RedditAnalysis 객체 생성
        player_evals = [
            PlayerEvaluation(
                player=pe.get('player', ''),
                sentiment=pe.get('sentiment', 'neutral'),
                key_points=pe.get('key_points', []),
                sample_quote=pe.get('sample_quote', '')
            )
            for pe in analysis.get('player_evaluations', [])
        ]

        coach_data = analysis.get('coach_analysis')
        coach_analysis = None
        if coach_data:
            coach_analysis = CoachAnalysis(
                coach=coach_data.get('coach', ''),
                rotations_sentiment=coach_data.get('rotations_sentiment', 'neutral'),
                rotations_points=coach_data.get('rotations_points', []),
                schemes_sentiment=coach_data.get('schemes_sentiment', 'neutral'),
                schemes_points=coach_data.get('schemes_points', []),
                decisions=coach_data.get('decisions', [])
            )

        chemistry_data = analysis.get('team_chemistry')
        team_chemistry = None
        if chemistry_data:
            team_chemistry = TeamChemistry(
                morale=chemistry_data.get('morale', 'mixed'),
                leadership_moments=chemistry_data.get('leadership_moments', []),
                conflicts=chemistry_data.get('conflicts', []),
                notes=chemistry_data.get('notes', '')
            )

        betting_data = analysis.get('betting_sentiment')
        betting_sentiment = None
        if betting_data:
            betting_sentiment = BettingSentiment(
                favorite_perception=betting_data.get('favorite_perception', ''),
                underdog_story=betting_data.get('underdog_story', ''),
                betting_trends=betting_data.get('betting_trends', []),
                sharp_money_hints=betting_data.get('sharp_money_hints', [])
            )

        return RedditAnalysis(
            sport=self.sport.upper(),
            game_id=game_id,
            thread_id=submission.id,
            thread_url=f"https://reddit.com{submission.permalink}",
            thread_title=submission.title,
            player_evaluations=player_evals,
            coach_analysis=coach_analysis,
            team_chemistry=team_chemistry,
            betting_sentiment=betting_sentiment,
            overall_sentiment=analysis.get('overall_sentiment', 'mixed'),
            controversies=analysis.get('controversies', []),
            key_insights=analysis.get('key_insights', []),
            collected_at=datetime.now(),
            total_comments=submission.num_comments,
            analyzed_comments=len(comments)
        )


# CLI 인터페이스
async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Reddit Post-Game Collector")
    parser.add_argument("sport", help="Sport code (nba, nfl, mlb, etc.)")
    parser.add_argument("--game-id", required=True, help="Game ID")
    parser.add_argument("--teams", required=True, help="Team codes (e.g., LAL,GSW)")
    parser.add_argument("--output", type=str, help="Output JSON file path")

    args = parser.parse_args()

    teams = args.teams.split(',')

    collector = RedditCollector(args.sport)
    analysis = await collector.collect_and_analyze(args.game_id, teams)

    if analysis:
        print(f"\n[Result] Analysis complete for {args.game_id}")
        print(f"Overall Sentiment: {analysis.overall_sentiment}")
        print(f"Players Evaluated: {len(analysis.player_evaluations)}")
        print(f"Key Insights: {analysis.key_insights}")

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(analysis.to_dict(), f, indent=2, ensure_ascii=False)
            print(f"\n[Output] Saved to {args.output}")
    else:
        print(f"\n[Result] No analysis available for {args.game_id}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
