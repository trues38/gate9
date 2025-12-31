"""
Layer 2: Reddit → Neo4j 로더
Tier 1 (Core Intelligence) + Tier 2 (Sentiment Summary) 저장
"""

import os
import json
from neo4j import GraphDatabase
from datetime import datetime
from pathlib import Path


class RedditNeo4jLoader:
    def __init__(self):
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'password')

        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def load_tier1_posts(self, posts_file: str):
        """Tier 1: Core Intelligence 포스트 로드"""
        with open(posts_file, 'r', encoding='utf-8') as f:
            posts = json.load(f)

        with self.driver.session() as session:
            for post in posts:
                session.run("""
                    MERGE (p:RedditPost {post_id: $post_id})
                    SET p.title = $title,
                        p.selftext = $selftext,
                        p.author = $author,
                        p.score = $score,
                        p.num_comments = $num_comments,
                        p.flair = $flair,
                        p.subreddit = $subreddit,
                        p.tier1_reason = $tier1_reason,
                        p.created_utc = $created_utc,
                        p.collected_at = datetime()
                """,
                    post_id=post['id'],
                    title=post['title'],
                    selftext=post.get('selftext', ''),
                    author=post.get('author', ''),
                    score=post['score'],
                    num_comments=post['num_comments'],
                    flair=post.get('flair', ''),
                    subreddit=post.get('subreddit', 'nba'),
                    tier1_reason=post.get('tier1_reason', ''),
                    created_utc=post.get('created_utc', 0)
                )

                # 댓글 중 고득표만 저장 (100+ upvotes)
                for comment in post.get('comments', []):
                    if comment.get('score', 0) >= 100:
                        session.run("""
                            MATCH (p:RedditPost {post_id: $post_id})
                            MERGE (c:RedditComment {
                                comment_id: $post_id + '_' + $author + '_' + $body_hash
                            })
                            SET c.author = $author,
                                c.body = $body,
                                c.score = $score
                            MERGE (p)-[:HAS_COMMENT]->(c)
                        """,
                            post_id=post['id'],
                            author=comment.get('author', '[deleted]'),
                            body=comment['body'][:1000],  # 1000자 제한
                            body_hash=str(hash(comment['body'][:100])),
                            score=comment['score']
                        )

        print(f"✅ Tier 1: {len(posts)}개 포스트 로드 완료")

    def load_tier2_sentiment(self, sentiment_file: str):
        """Tier 2: Sentiment Summary 로드"""
        with open(sentiment_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        period = data['period']

        with self.driver.session() as session:
            # 선수별 여론
            for player, stats in data['players'].items():
                session.run("""
                    MERGE (p:Player {name: $player})
                    MERGE (s:SentimentSummary {
                        player: $player,
                        period: $period
                    })
                    SET s.mentions = $mentions,
                        s.avg_score = $avg_score,
                        s.sentiment_keywords = $sentiment_keywords,
                        s.updated_at = datetime()
                    MERGE (p)-[:HAS_SENTIMENT]->(s)
                """,
                    player=player,
                    period=period,
                    mentions=stats['mentions'],
                    avg_score=stats['avg_score'],
                    sentiment_keywords=json.dumps(stats['sentiment_keywords'])
                )

            # 팀별 여론
            for team, stats in data['teams'].items():
                session.run("""
                    MERGE (t:Team {name: $team})
                    MERGE (s:TeamSentiment {
                        team: $team,
                        period: $period
                    })
                    SET s.mentions = $mentions,
                        s.keywords = $keywords,
                        s.updated_at = datetime()
                    MERGE (t)-[:HAS_SENTIMENT]->(s)
                """,
                    team=team,
                    period=period,
                    mentions=stats['mentions'],
                    keywords=json.dumps(stats['keywords'])
                )

            # 이슈 트렌드
            session.run("""
                MERGE (it:IssueTrend {period: $period})
                SET it.keywords = $keywords,
                    it.updated_at = datetime()
            """,
                period=period,
                keywords=json.dumps(data['issues'])
            )

        print(f"✅ Tier 2: 선수 {len(data['players'])}명, 팀 {len(data['teams'])}개 여론 로드")

    def link_posts_to_entities(self):
        """포스트와 선수/팀 연결"""
        with self.driver.session() as session:
            # 포스트 제목에서 선수 언급 연결
            session.run("""
                MATCH (p:RedditPost)
                MATCH (player:Player)
                WHERE toLower(p.title) CONTAINS toLower(player.name)
                MERGE (p)-[:MENTIONS]->(player)
            """)

            # 포스트 제목에서 팀 언급 연결
            session.run("""
                MATCH (p:RedditPost)
                MATCH (team:Team)
                WHERE toLower(p.title) CONTAINS toLower(team.name)
                MERGE (p)-[:ABOUT]->(team)
            """)

        print("✅ 포스트 ↔ 선수/팀 연결 완료")

    def create_indexes(self):
        """인덱스 생성"""
        with self.driver.session() as session:
            session.run("CREATE INDEX reddit_post_id IF NOT EXISTS FOR (p:RedditPost) ON (p.post_id)")
            session.run("CREATE INDEX reddit_post_score IF NOT EXISTS FOR (p:RedditPost) ON (p.score)")
            session.run("CREATE INDEX sentiment_period IF NOT EXISTS FOR (s:SentimentSummary) ON (s.period)")

        print("✅ 인덱스 생성 완료")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Load Reddit data to Neo4j")
    parser.add_argument("--tier1", required=True, help="Tier 1 JSON file path")
    parser.add_argument("--tier2", required=True, help="Tier 2 JSON file path")

    args = parser.parse_args()

    loader = RedditNeo4jLoader()

    try:
        print("=" * 70)
        print("Reddit → Neo4j 로딩 시작")
        print("=" * 70)
        print()

        # 인덱스 생성
        loader.create_indexes()

        # Tier 1 로드
        loader.load_tier1_posts(args.tier1)

        # Tier 2 로드
        loader.load_tier2_sentiment(args.tier2)

        # 연결
        loader.link_posts_to_entities()

        print()
        print("=" * 70)
        print("✅ 완료!")
        print("=" * 70)

    finally:
        loader.close()


if __name__ == "__main__":
    main()
