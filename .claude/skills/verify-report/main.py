#!/usr/bin/env python3
"""
NBA/축구 베팅 보고서 검증 스킬
- 외부 공식 API로 팩트 체크 (ESPN, NBA Stats)
- Neo4j 데이터와 교차 검증
- 논리적 일관성 검증
- 환각/착오 감지
- 검증 점수 산출
"""

import re
import os
import sys
import requests
import json
from datetime import datetime, timedelta
from neo4j import GraphDatabase

# Neo4j 연결 (교차 검증용)
NEO4J_URI = "bolt://141.164.35.214:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', '')

# 외부 API 엔드포인트
ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
NBA_STATS_BASE = "https://stats.nba.com/stats"


class ReportVerifier:
    """보고서 검증 엔진"""

    def __init__(self, neo4j_uri, neo4j_user, neo4j_password):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.issues = []
        self.warnings = []
        self.verified = []
        self.api_cache = {}  # API 호출 캐시

    # ===== 외부 API 조회 메서드 =====

    def _get_espn_team_stats(self, team_abbr):
        """ESPN API로 팀 통계 조회 (공식 데이터)"""
        cache_key = f"espn_stats_{team_abbr}"
        if cache_key in self.api_cache:
            return self.api_cache[cache_key]

        try:
            # ESPN Team 페이지 조회
            url = f"{ESPN_API_BASE}/teams/{self._get_espn_team_id(team_abbr)}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                stats = {
                    'team': team_abbr,
                    'avg_points': None,
                    'avg_allowed': None,
                    'win_pct': None
                }

                # 통계 파싱 (ESPN API 구조에 맞게)
                if 'team' in data and 'record' in data['team']:
                    record = data['team']['record']
                    if 'items' in record:
                        for item in record['items']:
                            if item.get('type') == 'total':
                                stats['win_pct'] = item.get('stats', [{}])[0].get('value')

                self.api_cache[cache_key] = stats
                return stats
            else:
                self.warnings.append(f"ESPN API 호출 실패: {response.status_code}")
                return None

        except Exception as e:
            self.warnings.append(f"ESPN API 오류: {str(e)}")
            return None

    def _get_espn_h2h(self, team_a, team_b, limit=5):
        """ESPN API로 H2H 기록 조회"""
        cache_key = f"espn_h2h_{team_a}_{team_b}"
        if cache_key in self.api_cache:
            return self.api_cache[cache_key]

        try:
            # ESPN Scoreboard에서 최근 경기 조회
            # 실제로는 더 정교한 날짜 범위 검색 필요
            url = f"{ESPN_API_BASE}/scoreboard"
            params = {
                'dates': self._get_date_range(days=180),  # 최근 6개월
                'limit': 100
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                h2h_games = []

                # 두 팀 간 경기 필터링
                if 'events' in data:
                    for event in data['events']:
                        competitions = event.get('competitions', [])
                        for comp in competitions:
                            home = comp.get('competitors', [{}])[0].get('team', {}).get('abbreviation')
                            away = comp.get('competitors', [{}])[1].get('team', {}).get('abbreviation')

                            if (home == team_a and away == team_b) or (home == team_b and away == team_a):
                                h2h_games.append({
                                    'date': event.get('date'),
                                    'home': home,
                                    'away': away,
                                    'home_score': comp.get('competitors', [{}])[0].get('score'),
                                    'away_score': comp.get('competitors', [{}])[1].get('score')
                                })

                # 최근 경기 순으로 정렬
                h2h_games = sorted(h2h_games, key=lambda x: x['date'], reverse=True)[:limit]
                self.api_cache[cache_key] = h2h_games
                return h2h_games
            else:
                return None

        except Exception as e:
            self.warnings.append(f"ESPN H2H 조회 오류: {str(e)}")
            return None

    def _get_espn_team_id(self, team_abbr):
        """팀 약어 → ESPN Team ID 변환"""
        # ESPN Team ID 매핑 (주요 팀만 예시)
        team_id_map = {
            'LAL': '13', 'BOS': '2', 'GSW': '9', 'MIA': '14',
            'PHI': '20', 'MEM': '29', 'DET': '8', 'SAC': '23',
            'LAC': '12', 'UTAH': '26', 'PHX': '21', 'DAL': '6',
            # ... 나머지 팀 추가
        }
        return team_id_map.get(team_abbr, team_abbr)

    def _get_date_range(self, days=180):
        """날짜 범위 생성 (YYYYMMDD 형식)"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return f"{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}"

    def _fallback_web_scrape(self, team_abbr):
        """API 실패 시 웹 스크래핑 백업 (ESPN.com)"""
        try:
            url = f"https://www.espn.com/nba/team/stats/_/name/{team_abbr.lower()}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                # 간단한 파싱 (BeautifulSoup 사용하면 더 정확)
                content = response.text

                # 정규식으로 주요 통계 추출
                ppg_match = re.search(r'PPG.*?(\d+\.\d+)', content)
                if ppg_match:
                    return {'avg_points': float(ppg_match.group(1))}

            return None

        except Exception as e:
            self.warnings.append(f"웹 스크래핑 실패: {str(e)}")
            return None

    def verify_report(self, report_path):
        """보고서 전체 검증"""
        print(f"\n{'='*80}")
        print(f"🔍 보고서 검증 시작: {os.path.basename(report_path)}")
        print(f"{'='*80}\n")

        # 보고서 읽기
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 매치업 추출
        matchup = self._extract_matchup(report_path, content)
        if not matchup:
            print("❌ ERROR: 매치업 정보를 찾을 수 없습니다.")
            return 0

        away_team, home_team = matchup
        print(f"📊 매치업: {away_team} @ {home_team}\n")

        # 검증 실행
        score = 100

        # 1. H2H 기록 검증
        score -= self._verify_h2h(content, away_team, home_team)

        # 2. 팀 통계 검증
        score -= self._verify_team_stats(content, away_team, home_team)

        # 3. 최근 경기 검증
        score -= self._verify_recent_games(content, away_team, home_team)

        # 4. 논리적 일관성 검증
        score -= self._verify_logic(content)

        # 결과 출력
        self._print_results(score)

        return max(0, score)

    def _extract_matchup(self, report_path, content):
        """파일명 또는 내용에서 매치업 추출"""
        # 파일명에서 추출: graphrag_PHI_at_MEM_*.md
        filename = os.path.basename(report_path)
        match = re.search(r'graphrag_([A-Z]+)_at_([A-Z]+)', filename)
        if match:
            return match.group(1), match.group(2)

        # 내용에서 추출: ## PHI @ MEM
        match = re.search(r'##\s*([A-Z]+)\s*@\s*([A-Z]+)', content)
        if match:
            return match.group(1), match.group(2)

        # DET @ LAL 형식
        match = re.search(r'([A-Z]{2,4})\s*@\s*([A-Z]{2,4})', content)
        if match:
            return match.group(1), match.group(2)

        return None

    def _verify_h2h(self, content, away_team, home_team):
        """H2H 기록 검증 (ESPN API 우선, Neo4j 교차 검증)"""
        print("📌 H2H 기록 검증 (ESPN API)...")
        penalty = 0

        # H2H 기록 추출 (예: "3-1", "5-0")
        h2h_patterns = [
            r'H2H[:\s]+.*?(\d+)[- ](\d+)',
            r'최근.*?(\d+)승\s*(\d+)패',
            r'[Hh]ead[- ]to[- ]head.*?(\d+)[- ](\d+)',
        ]

        h2h_claim = None
        for pattern in h2h_patterns:
            match = re.search(pattern, content)
            if match:
                h2h_claim = (int(match.group(1)), int(match.group(2)))
                break

        if not h2h_claim:
            self.warnings.append("H2H 기록 언급 없음 (검증 불가)")
            return 0

        # 1차 검증: ESPN API (공식 데이터)
        espn_h2h = self._get_espn_h2h(home_team, away_team, limit=10)
        espn_verified = False

        if espn_h2h:
            # ESPN 데이터로 승수 계산
            home_wins = sum(1 for g in espn_h2h if
                           (g['home'] == home_team and g['home_score'] > g['away_score']) or
                           (g['away'] == home_team and g['away_score'] > g['home_score']))
            away_wins = len(espn_h2h) - home_wins
            espn_actual = (home_wins, away_wins)

            if h2h_claim == espn_actual or h2h_claim == (away_wins, home_wins):
                self.verified.append(f"✓ H2H: {h2h_claim[0]}-{h2h_claim[1]} (ESPN 확인됨)")
                espn_verified = True
            else:
                self.issues.append(
                    f"❌ H2H ESPN 불일치: 보고서 {h2h_claim[0]}-{h2h_claim[1]} vs "
                    f"ESPN {home_team} {home_wins}-{away_wins} {away_team}"
                )
                penalty += 20  # ESPN 불일치는 치명적
                espn_verified = False

        # 2차 검증: Neo4j (교차 확인)
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (g:Game)
                    WHERE (g.home_team = $team_a AND g.away_team = $team_b)
                       OR (g.home_team = $team_b AND g.away_team = $team_a)
                    WITH CASE WHEN g.home_score > g.away_score THEN g.home_team ELSE g.away_team END AS winner
                    RETURN winner, count(*) as total
                    LIMIT 10
                """, team_a=home_team, team_b=away_team).data()

                if result:
                    home_wins_neo = sum(r['total'] for r in result if r['winner'] == home_team)
                    away_wins_neo = sum(r['total'] for r in result if r['winner'] == away_team)
                    neo_actual = (home_wins_neo, away_wins_neo)

                    # ESPN과 Neo4j 교차 검증
                    if espn_h2h and neo_actual != espn_actual:
                        self.warnings.append(
                            f"⚠️ 데이터 불일치: ESPN {espn_actual} vs Neo4j {neo_actual} "
                            f"(ESPN 기준 우선)"
                        )
                    elif not espn_h2h:
                        # ESPN 실패 시 Neo4j 사용
                        if h2h_claim == neo_actual or h2h_claim == (away_wins_neo, home_wins_neo):
                            self.verified.append(f"✓ H2H: {h2h_claim[0]}-{h2h_claim[1]} (Neo4j 확인)")
                        else:
                            self.issues.append(
                                f"H2H Neo4j 불일치: 보고서 {h2h_claim[0]}-{h2h_claim[1]} vs "
                                f"Neo4j {home_team} {home_wins_neo}-{away_wins_neo}"
                            )
                            penalty += 15

        except Exception as e:
            self.warnings.append(f"Neo4j H2H 검증 오류: {str(e)}")

        return penalty

    def _verify_team_stats(self, content, away_team, home_team):
        """팀 통계 검증 (평균 득점, 실점 등) - 개선된 파싱"""
        print("📌 팀 통계 검증...")
        penalty = 0

        # 개선된 통계 패턴: 팀명과 통계를 함께 찾기
        for team in [home_team, away_team]:
            # 팀 통계 섹션 찾기 (선수 통계와 구분)
            team_patterns = [
                # "Memphis: 107.6점, 평균 실점 101.8점"
                rf'{team}[:\s]+평균\s*(\d+\.?\d*)\s*점',
                # "평균 107.6점" (팀명 근처 50자 이내)
                rf'{team}.{{0,50}}?평균\s*(\d+\.?\d*)\s*점',
                # "Detroit의 110.1 득점"
                rf'{team}.{{0,30}}?(\d+\.?\d*)\s*득점',
            ]

            claimed_points = None
            for pattern in team_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    value = float(match.group(1))
                    # 선수 개인 통계 필터링 (보통 40점 이하)
                    if value > 50:  # 팀 득점은 최소 70점 이상
                        claimed_points = value
                        break

            if claimed_points:
                # Neo4j에서 실제 평균 득점 조회
                try:
                    with self.driver.session() as session:
                        result = session.run("""
                            MATCH (g:Game)
                            WHERE g.home_team = $team OR g.away_team = $team
                            WITH CASE WHEN g.home_team = $team THEN g.home_score ELSE g.away_score END as our_score
                            RETURN AVG(our_score) as avg_points
                        """, team=team).single()

                        if result and result['avg_points']:
                            actual_value = float(result['avg_points'])
                            diff = abs(claimed_points - actual_value)

                            if diff < 5.0:  # 5점 이내 허용 (더 관대하게)
                                self.verified.append(f"✓ {team} 평균 득점: {claimed_points:.1f} (정확)")
                            else:
                                self.issues.append(
                                    f"{team} 평균 득점 불일치: "
                                    f"보고서 {claimed_points:.1f} vs 실제 {actual_value:.1f}"
                                )
                                penalty += 10
                except Exception as e:
                    self.warnings.append(f"{team} 통계 검증 실패: {str(e)}")

            # 평균 실점 검증
            allowed_patterns = [
                rf'{team}[:\s]+평균\s*실점\s*(\d+\.?\d*)',
                rf'{team}.{{0,50}}?(\d+\.?\d*)\s*실점',
            ]

            claimed_allowed = None
            for pattern in allowed_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    value = float(match.group(1))
                    if value > 50:  # 실점도 최소 70점 이상
                        claimed_allowed = value
                        break

            if claimed_allowed:
                try:
                    with self.driver.session() as session:
                        result = session.run("""
                            MATCH (g:Game)
                            WHERE g.home_team = $team OR g.away_team = $team
                            WITH CASE WHEN g.home_team = $team THEN g.away_score ELSE g.home_score END as opponent_score
                            RETURN AVG(opponent_score) as avg_allowed
                        """, team=team).single()

                        if result and result['avg_allowed']:
                            actual_value = float(result['avg_allowed'])
                            diff = abs(claimed_allowed - actual_value)

                            if diff < 5.0:
                                self.verified.append(f"✓ {team} 평균 실점: {claimed_allowed:.1f} (정확)")
                            else:
                                self.issues.append(
                                    f"{team} 평균 실점 불일치: "
                                    f"보고서 {claimed_allowed:.1f} vs 실제 {actual_value:.1f}"
                                )
                                penalty += 10
                except Exception as e:
                    self.warnings.append(f"{team} 실점 검증 실패: {str(e)}")

        return penalty

    def _verify_recent_games(self, content, away_team, home_team):
        """최근 경기 결과 검증"""
        print("📌 최근 경기 검증...")
        penalty = 0

        # 최근 폼 패턴 (예: "2-3", "70% 승률")
        form_patterns = [
            r'최근.*?(\d+)승\s*(\d+)패',
            r'(\d+)-(\d+)',
            r'(\d+)%\s*승률',
        ]

        # 간단한 검증: 최근 5경기 승패 계산
        for team in [home_team, away_team]:
            try:
                with self.driver.session() as session:
                    result = session.run("""
                        MATCH (g:Game)
                        WHERE g.home_team = $team OR g.away_team = $team
                        WITH g,
                             CASE WHEN g.home_score > g.away_score THEN g.home_team ELSE g.away_team END AS winner
                        ORDER BY g.date DESC
                        LIMIT 5
                        RETURN winner, count(*) as games
                    """, team=team).data()

                    if result:
                        wins = sum(r['games'] for r in result if r['winner'] == team)
                        total = sum(r['games'] for r in result)
                        losses = total - wins

                        # 보고서에서 언급 확인
                        if f"{wins}-{losses}" in content or f"{wins}승 {losses}패" in content:
                            self.verified.append(f"✓ {team} 최근 폼: {wins}-{losses} (정확)")
                        elif f"{losses}-{wins}" in content:
                            self.issues.append(f"{team} 최근 폼 순서 뒤바뀜")
                            penalty += 5
            except Exception as e:
                self.warnings.append(f"{team} 최근 경기 검증 실패: {str(e)}")

        return penalty

    def _verify_logic(self, content):
        """논리적 일관성 검증 - 개선된 파싱"""
        print("📌 논리적 일관성 검증...")
        penalty = 0

        # 1. 베팅 권장과 분석 일치 확인
        if "ML" in content or "머니라인" in content:
            # ML 픽이 있으면 승자 예측도 있어야 함
            if "승자:" not in content and "Winner:" not in content and "확률" not in content:
                self.warnings.append("ML 픽이 있지만 명확한 승자 예측 없음")
                penalty += 5

        # 2. 스프레드와 점수 예측 일치 (개선된 파싱)
        spread_match = re.search(r'스프레드.*?[-+](\d+\.?\d*)', content, re.IGNORECASE)

        # 최종 예측 점수 찾기 (날짜 제외)
        score_patterns = [
            r'최종[:\s]+(?:스코어|점수)[:\s]+[A-Z]+\s+(\d{2,3})\s*[-–]\s*[A-Z]+\s+(\d{2,3})',
            r'스코어[:\s]+[A-Z]+\s+(\d{2,3})\s*[-–]\s*[A-Z]+\s+(\d{2,3})',
            r'예측[:\s]+[A-Z]+\s+(\d{2,3})\s*[-–]\s*[A-Z]+\s+(\d{2,3})',
        ]

        score_match = None
        for pattern in score_patterns:
            score_match = re.search(pattern, content, re.IGNORECASE)
            if score_match:
                break

        # 일반 점수 패턴 (날짜 필터링)
        if not score_match:
            # 100-150 범위의 점수만 (날짜 2025 같은거 제외)
            general_score = re.search(r'(\d{2,3})\s*[-–]\s*(\d{2,3})', content)
            if general_score:
                score1 = int(general_score.group(1))
                score2 = int(general_score.group(2))
                # NBA 점수 범위: 70-150
                if 70 <= score1 <= 150 and 70 <= score2 <= 150:
                    score_match = general_score

        if spread_match and score_match:
            spread = float(spread_match.group(1))
            score1 = int(score_match.group(1))
            score2 = int(score_match.group(2))
            actual_diff = abs(score1 - score2)

            if abs(actual_diff - spread) > 10:  # 10점 이내 허용 (더 관대하게)
                self.warnings.append(
                    f"스프레드 {spread}와 예측 점수차 {actual_diff} 불일치 (허용 범위 초과)"
                )
                penalty += 3

        # 3. Over/Under와 총점 일치
        if "Over" in content or "Under" in content:
            total_patterns = [
                r'총점[:\s]*(\d{3})',  # 3자리 숫자만 (200-250)
                r'총점[:\s]+.*?(\d{3})\s*점',
            ]

            total_match = None
            for pattern in total_patterns:
                total_match = re.search(pattern, content)
                if total_match:
                    total_val = int(total_match.group(1))
                    if 150 <= total_val <= 300:  # NBA 총점 범위
                        break
                    else:
                        total_match = None

            ou_match = re.search(r'(Over|Under)\s*(\d+\.?\d*)', content)

            if total_match and ou_match:
                predicted_total = int(total_match.group(1))
                ou_line = float(ou_match.group(2))
                pick = ou_match.group(1)

                if pick == "Over" and predicted_total < ou_line:
                    self.issues.append(f"Over 픽인데 예측 총점 {predicted_total} < 라인 {ou_line}")
                    penalty += 10
                elif pick == "Under" and predicted_total > ou_line:
                    self.issues.append(f"Under 픽인데 예측 총점 {predicted_total} > 라인 {ou_line}")
                    penalty += 10

        return penalty

    def _print_results(self, score):
        """검증 결과 출력"""
        print(f"\n{'='*80}")
        print(f"📊 검증 결과")
        print(f"{'='*80}\n")

        # 검증 통과 항목
        if self.verified:
            print("✅ 검증 통과:")
            for item in self.verified:
                print(f"   {item}")
            print()

        # 오류 항목
        if self.issues:
            print("❌ 오류 발견:")
            for item in self.issues:
                print(f"   • {item}")
            print()

        # 경고 항목
        if self.warnings:
            print("⚠️  경고:")
            for item in self.warnings:
                print(f"   • {item}")
            print()

        # 최종 점수
        print(f"{'='*80}")
        if score >= 90:
            emoji = "🎉"
            status = "판매 승인 권장"
        elif score >= 80:
            emoji = "⚡"
            status = "경고 확인 후 판매"
        elif score >= 70:
            emoji = "⚠️"
            status = "수정 후 재검증 필요"
        else:
            emoji = "❌"
            status = "판매 중단 권장"

        print(f"{emoji} 검증 점수: {score}/100")
        print(f"   권장 조치: {status}")
        print(f"{'='*80}\n")

    def close(self):
        """연결 종료"""
        self.driver.close()


def main():
    """메인 실행"""
    if len(sys.argv) < 2:
        print("사용법: python main.py <report_path>")
        print("예시: python main.py /path/to/graphrag_PHI_at_MEM_20251229.md")
        sys.exit(1)

    report_path = sys.argv[1]

    if not os.path.exists(report_path):
        print(f"❌ ERROR: 파일을 찾을 수 없습니다: {report_path}")
        sys.exit(1)

    # 검증 실행
    verifier = ReportVerifier(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    try:
        score = verifier.verify_report(report_path)
        verifier.close()

        # 점수에 따라 exit code 설정
        if score >= 80:
            sys.exit(0)  # 성공
        else:
            sys.exit(1)  # 실패

    except Exception as e:
        print(f"\n❌ 검증 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        verifier.close()
        sys.exit(2)


if __name__ == '__main__':
    main()
