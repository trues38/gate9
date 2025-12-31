#!/usr/bin/env python3
"""
Neo4j Bolt 연결 테스트

n8n 컨테이너에서 neo4j-nba로 접근 가능한지 확인
"""

import os
import sys
from neo4j import GraphDatabase


def test_connection_from_host():
    """호스트에서 Neo4j 연결 테스트"""
    print("\n" + "="*80)
    print("1️⃣ 호스트 → Neo4j (localhost:7687)")
    print("="*80 + "\n")

    uri = "bolt://localhost:7687"
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "your-password")

    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        with driver.session() as session:
            result = session.run("RETURN 'Connected!' as message, datetime() as time")
            record = result.single()
            print(f"✅ 연결 성공!")
            print(f"   Message: {record['message']}")
            print(f"   Time: {record['time']}")

        driver.close()
        return True

    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        return False


def test_nba_data():
    """NBA 데이터 확인"""
    print("\n" + "="*80)
    print("2️⃣ NBA 데이터 확인")
    print("="*80 + "\n")

    uri = "bolt://localhost:7687"
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "your-password")

    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        with driver.session() as session:
            # 노드 타입별 개수
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(*) as count
                ORDER BY count DESC
                LIMIT 10
            """)

            print("📊 노드 통계:")
            print("-" * 60)
            for record in result:
                label = record['label'] or 'Unlabeled'
                count = record['count']
                print(f"   {label:20s} {count:>10,} nodes")

            print()

            # Team 노드 확인
            result = session.run("""
                MATCH (t:Team)
                RETURN t.name as team, t.abbreviation as abbr
                ORDER BY t.name
                LIMIT 5
            """)

            print("🏀 Team 샘플 (5개):")
            print("-" * 60)
            for record in result:
                print(f"   {record['abbr']:5s} - {record['team']}")

            print()

            # Player 노드 확인
            result = session.run("""
                MATCH (p:Player)
                RETURN p.name as player
                ORDER BY p.name
                LIMIT 5
            """)

            print("👤 Player 샘플 (5개):")
            print("-" * 60)
            for record in result:
                print(f"   {record['player']}")

        driver.close()
        print("\n✅ NBA 데이터 확인 완료")
        return True

    except Exception as e:
        print(f"❌ 데이터 확인 실패: {e}")
        return False


def test_n8n_query():
    """n8n에서 사용할 쿼리 테스트"""
    print("\n" + "="*80)
    print("3️⃣ n8n 쿼리 테스트")
    print("="*80 + "\n")

    uri = "bolt://localhost:7687"
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "your-password")

    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        with driver.session() as session:
            # Event 노드 생성 테스트 (dry-run)
            print("🧪 테스트 Event 노드 생성...")
            result = session.run("""
                // 테스트 Event 노드 생성
                CREATE (e:TestEvent {
                    tweet_id: 'test_' + toString(datetime().epochSeconds),
                    event_type: 'lineup_change',
                    player: 'Test Player',
                    team: 'TEST',
                    status: 'OUT',
                    confidence: 0.95,
                    created_at: datetime()
                })
                RETURN e.tweet_id as tweet_id, e.player as player
            """)

            record = result.single()
            print(f"✅ TestEvent 생성 성공")
            print(f"   Tweet ID: {record['tweet_id']}")
            print(f"   Player: {record['player']}")

            print()

            # 테스트 노드 정리
            print("🧹 테스트 노드 정리...")
            session.run("MATCH (e:TestEvent) DELETE e")
            print("✅ 정리 완료")

        driver.close()
        return True

    except Exception as e:
        print(f"❌ 쿼리 테스트 실패: {e}")
        return False


def test_connection_from_docker():
    """Docker 컨테이너 내부에서 연결 테스트"""
    print("\n" + "="*80)
    print("4️⃣ n8n 컨테이너 → Neo4j (neo4j-nba:7687)")
    print("="*80 + "\n")

    import subprocess

    try:
        # n8n 컨테이너가 실행 중인지 확인
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=n8n-nba", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )

        if "n8n-nba" not in result.stdout:
            print("⚠️  n8n-nba 컨테이너가 실행 중이 아닙니다.")
            print("   먼저 배포하세요: ./deploy_n8n.sh")
            return False

        # n8n 컨테이너에서 Neo4j 연결 테스트
        print("🐳 n8n 컨테이너에서 연결 테스트 중...")

        password = os.getenv("NEO4J_PASSWORD", "your-password")
        username = os.getenv("NEO4J_USERNAME", "neo4j")

        test_command = f"""
python3 -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://neo4j-nba:7687', auth=('{username}', '{password}'))
with driver.session() as session:
    result = session.run('RETURN 1 as test')
    print('✅ n8n → Neo4j 연결 성공!')
driver.close()
"
        """

        result = subprocess.run(
            ["docker", "exec", "n8n-nba", "sh", "-c", test_command],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print(f"❌ 연결 실패")
            print(f"   Error: {result.stderr}")
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Docker 명령 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False


def main():
    """모든 테스트 실행"""
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + " "*20 + "Neo4j Bolt 연결 테스트" + " "*37 + "█")
    print("█" + " "*78 + "█")
    print("█"*80)

    # 환경변수 확인
    if not os.getenv("NEO4J_PASSWORD"):
        print("\n⚠️  NEO4J_PASSWORD 환경변수를 설정하세요:")
        print("   export NEO4J_PASSWORD='your-password'")
        print("\n또는 .env.n8n 파일에 설정:")
        print("   source .env.n8n")
        sys.exit(1)

    results = []

    # 1. 호스트 연결 테스트
    results.append(("호스트 → Neo4j", test_connection_from_host()))

    # 2. NBA 데이터 확인
    results.append(("NBA 데이터 확인", test_nba_data()))

    # 3. n8n 쿼리 테스트
    results.append(("n8n 쿼리 테스트", test_n8n_query()))

    # 4. Docker 컨테이너 연결 테스트 (n8n이 실행 중이면)
    results.append(("n8n → Neo4j", test_connection_from_docker()))

    # 결과 요약
    print("\n" + "="*80)
    print("📋 테스트 결과 요약")
    print("="*80 + "\n")

    all_passed = True
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} - {name}")
        if not success:
            all_passed = False

    print()

    if all_passed:
        print("🎉 모든 테스트 통과!")
        print("\nn8n 워크플로우에서 Neo4j를 사용할 준비가 완료되었습니다.")
        print("\n다음 단계:")
        print("  1. n8n 웹 UI 접속: http://localhost:5678")
        print("  2. Credentials → Neo4j 추가")
        print("     - URI: bolt://neo4j-nba:7687")
        print("     - Username: neo4j")
        print("     - Password: (환경변수 값)")
        print("  3. 워크플로우 Import: n8n_nba_realtime_workflow.json")
        print()
    else:
        print("❌ 일부 테스트 실패")
        print("\n트러블슈팅:")
        print("  1. Neo4j 컨테이너 확인: docker ps | grep neo4j-nba")
        print("  2. Neo4j 로그 확인: docker logs neo4j-nba")
        print("  3. 비밀번호 확인: echo $NEO4J_PASSWORD")
        print("  4. 네트워크 확인: docker network inspect nba-network")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
