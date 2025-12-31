# Graph RAG 구현 로드맵

## 현재 상태 (2025-12-29)

### ✅ 완료된 것
1. **VPS 자동화 수정**: 수집 윈도우 T+4h 확장 → 2 tweets → 50-200+ tweets 예상
2. **Opus 4.5 품질 증명**: 4개 경기 분석 완료 (PHI@MEM, BOS@UTAH, DET@LAL, SAC@LAC)
3. **분석 프레임워크 확립**: 5-section 구조 (구조적 우위 / 모멘텀 / 미시 레버리지 / 시나리오 / 베팅 엣지)
4. **Smart Graph RAG 전략**: GRAPH_RAG_STRATEGY.md 문서화 완료

### 📍 현재 운영 방식 (Option 1: Manual)
```
User 요청 → Claude Code 실행 → Neo4j 직접 쿼리 → Opus 4.5 스타일 분석 작성
비용: $0
품질: 100%
시간: 5-10분/day
```

---

## Phase 1: 수동 실행 (현재 ~ 1주일)

### 목표
- 매일 고품질 리포트 생성
- 분석 패턴 관찰 및 기록
- Smart Graph RAG 설계 검증

### 일일 워크플로우
```bash
# 1. 오늘 경기 확인
cd /Users/js/g9/nba_data/odds_report_engine
python3 generate_graph_rag_reports.py  # Neo4j 데이터 읽기

# 2. Claude Code 호출
"오늘 NBA 경기 Opus 4.5 스타일로 분석해줘"

# 3. 출력 확인
ls -lh /Users/js/g9/nba_data/odds_reports/graphrag_*_OPUS45_*.md
```

### 관찰할 패턴
매일 분석하면서 **어떤 쿼리를 자주 쓰는지** 기록:

**패턴 체크리스트:**
```python
# 경기마다 체크
patterns_observed = {
    'defensive_mismatch': False,  # 수비 효율 10+ 차이?
    'h2h_dominance': False,       # H2H 4승+ 우위?
    'blowout_tendency': False,    # 최근 15+ 점차 3경기+?
    'home_court_strong': False,   # 홈 승률 65%+?
    'revenge_game': False,        # 최근 H2H 패배?
    'fatigue_factor': False,      # 백투백 or 1일 휴식?
}

# 사용한 쿼리
queries_used = [
    'h2h_detailed',
    'recent_games_with_opponent_strength',
    'defensive_breakdown',  # ← 언제 썼나?
    ...
]
```

**기록 파일**: `/Users/js/g9/nba_data/odds_report_engine/pattern_log.jsonl`
```jsonl
{"date":"2025-12-29","game":"PHI@MEM","patterns":{"defensive_mismatch":true,"h2h_dominance":true},"queries_used":["h2h_detailed","defensive_breakdown"]}
```

---

## Phase 2: Rich Context 자동화 (1-2주차)

### 목표
- `build_rich_context()` 함수 구현
- Core 10 Queries 자동 실행
- Sonnet 4 API 테스트

### 구현 파일
**File**: `/Users/js/g9/nba_data/odds_report_engine/smart_graph_rag.py`

```python
#!/usr/bin/env python3
"""
Smart Graph RAG - 지능형 쿼리 선택 엔진
"""

from neo4j import GraphDatabase
import os

class SmartGraphRAG:
    def __init__(self, neo4j_uri, neo4j_user, neo4j_password):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    def analyze_matchup(self, home_team: str, away_team: str, game_date: str):
        """스마트하게 쿼리 선택해서 분석"""

        # Step 1: Core Queries (항상 실행)
        core_data = self._execute_core_queries(home_team, away_team, game_date)

        # Step 2: Pattern Detection
        patterns = self._detect_patterns(core_data)

        # Step 3: Conditional Queries (패턴 기반)
        additional_data = {}

        if patterns['defensive_mismatch']:
            additional_data['defense'] = self._query_defensive_breakdown(home_team, away_team)

        if patterns['h2h_dominance']:
            additional_data['h2h_deep'] = self._query_h2h_quarter_breakdown(home_team, away_team)

        if patterns['blowout_tendency']:
            additional_data['blowout'] = self._query_blowout_pattern(home_team, away_team)

        # Step 4: Build Rich Context
        context = self._build_rich_context(core_data, additional_data, patterns)

        return context, patterns

    def _execute_core_queries(self, home_team: str, away_team: str, game_date: str):
        """10개 Core Queries 실행"""
        with self.driver.session() as session:
            data = {}

            # Query 1: H2H History (상세)
            data['h2h'] = session.run("""
                MATCH (g:Game)
                WHERE (g.home_team = $team_a AND g.away_team = $team_b)
                   OR (g.home_team = $team_b AND g.away_team = $team_a)
                RETURN g.date AS date,
                       g.home_team AS home_team,
                       g.away_team AS away_team,
                       g.home_score AS home_score,
                       g.away_score AS away_score,
                       CASE WHEN g.home_score > g.away_score THEN g.home_team ELSE g.away_team END AS winner
                ORDER BY g.date DESC
                LIMIT 5
            """, team_a=home_team, team_b=away_team).data()

            # Query 2: 최근 5경기 (홈팀)
            data['home_recent'] = session.run("""
                MATCH (g:Game)
                WHERE g.home_team = $team OR g.away_team = $team
                WITH g,
                     CASE WHEN g.home_team = $team THEN g.away_team ELSE g.home_team END AS opponent,
                     CASE WHEN g.home_score > g.away_score THEN g.home_team ELSE g.away_team END AS winner
                RETURN g.date AS date,
                       opponent,
                       CASE WHEN winner = $team THEN 'W' ELSE 'L' END AS result,
                       g.home_score AS home_score,
                       g.away_score AS away_score
                ORDER BY g.date DESC
                LIMIT 5
            """, team=home_team).data()

            # Query 3: 최근 5경기 (원정팀)
            data['away_recent'] = session.run("""
                MATCH (g:Game)
                WHERE g.home_team = $team OR g.away_team = $team
                WITH g,
                     CASE WHEN g.home_team = $team THEN g.away_team ELSE g.home_team END AS opponent,
                     CASE WHEN g.home_score > g.away_score THEN g.home_team ELSE g.away_team END AS winner
                RETURN g.date AS date,
                       opponent,
                       CASE WHEN winner = $team THEN 'W' ELSE 'L' END AS result,
                       g.home_score AS home_score,
                       g.away_score AS away_score
                ORDER BY g.date DESC
                LIMIT 5
            """, team=away_team).data()

            # Query 4-10: 나머지 쿼리들 (홈/원정 분리, 페이스, 수비 vs 공격, 클러치, 점수차, 리바운드, 3점)
            # ... (GRAPH_RAG_STRATEGY.md 참조)

            return data

    def _detect_patterns(self, core_data):
        """Core Query 결과에서 패턴 감지"""
        patterns = {}

        # 예시: H2H 지배력
        h2h = core_data.get('h2h', [])
        if len(h2h) >= 4:
            # 홈팀 승수 계산
            home_wins = sum(1 for g in h2h if g['winner'] == core_data.get('home_team'))
            patterns['h2h_dominance'] = home_wins >= 3 or (len(h2h) - home_wins) >= 3

        # 예시: 수비 미스매치
        # (실제로는 Core Query 4에서 가져온 수비 효율 데이터 사용)
        patterns['defensive_mismatch'] = False  # TODO: 계산

        # 예시: 블로우아웃 경향
        home_recent = core_data.get('home_recent', [])
        blowouts = sum(1 for g in home_recent if abs(g['home_score'] - g['away_score']) > 15)
        patterns['blowout_tendency'] = blowouts >= 2

        return patterns

    def _build_rich_context(self, core_data, additional_data, patterns):
        """LLM이 이해할 수 있는 풍부한 컨텍스트 생성"""

        context = f"# Matchup Analysis\n\n"

        # H2H 상세
        context += "## H2H History\n"
        for i, game in enumerate(core_data.get('h2h', [])[:5], 1):
            diff = abs(game['home_score'] - game['away_score'])
            blowout = " (블로우아웃!)" if diff > 15 else ""
            context += f"{i}. {game['date']}: {game['away_team']} {game['away_score']} @ {game['home_team']} {game['home_score']}"
            context += f" ({game['winner']} 승, {diff}점차{blowout})\n"

        # 최근 경기 상세
        context += "\n## Recent Games\n"
        # ... (상세 데이터 추가)

        # Conditional 데이터
        if 'defense' in additional_data:
            context += "\n## Defensive Breakdown\n"
            context += str(additional_data['defense'])

        return context

# 사용 예시
if __name__ == '__main__':
    rag = SmartGraphRAG(
        neo4j_uri="bolt://141.164.35.214:7687",
        neo4j_user="neo4j",
        neo4j_password=os.environ.get('NEO4J_PASSWORD')
    )

    context, patterns = rag.analyze_matchup('LAL', 'BOS', '2025-12-30')
    print(f"Detected patterns: {patterns}")
    print(f"\nRich Context ({len(context)} chars):\n{context}")
```

### 테스트
```bash
export NEO4J_PASSWORD="your_password"
python3 smart_graph_rag.py
```

---

## Phase 3: LLM API 통합 (2-3주차)

### 목표
- Sonnet 4 API로 Rich Context 기반 분석 생성
- 품질 vs 비용 검증 (Opus 90% 품질, 20% 비용)

### 구현
**File**: `/Users/js/g9/nba_data/odds_report_engine/generate_with_smart_rag.py`

```python
#!/usr/bin/env python3
"""
Smart Graph RAG + Sonnet 4 = 자동 고품질 분석
"""

from smart_graph_rag import SmartGraphRAG
import requests
import os

OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

def generate_analysis(home_team: str, away_team: str, game_date: str):
    """Smart RAG + Sonnet 4로 분석 생성"""

    # Step 1: Smart Graph RAG로 Rich Context 생성
    rag = SmartGraphRAG(
        neo4j_uri="bolt://141.164.35.214:7687",
        neo4j_user="neo4j",
        neo4j_password=os.environ.get('NEO4J_PASSWORD')
    )

    rich_context, patterns = rag.analyze_matchup(home_team, away_team, game_date)

    print(f"Rich Context: {len(rich_context)} chars")
    print(f"Patterns: {patterns}")

    # Step 2: Sonnet 4 API로 분석 생성
    prompt = f"""당신은 NBA 베팅 분석 전문가입니다. 다음 데이터를 **Claude Opus 4.5 수준**으로 분석하세요.

# 핵심 분석 프레임워크 (반드시 따를 것)

## 1단계: 구조적 우위 발굴
- 단순 통계 뒤의 **시스템적 차이** 발굴
- 예: "9.1점 격차 = 페리미터 로테이션 vs 림 프로텍션 차이"

## 2단계: 모멘텀의 질적 분석
- 승패 숫자의 **질적 내용** 재해석
- 강팀에게 진 패배 vs 약팀에게 진 패배

## 3단계: 미시적 레버리지 포착
- 특정 매치업의 **연쇄 효과** 분석
- 예: "Pippen Jr. 압박 → Maxey 턴오버 → MEM 전환 득점"

## 4단계: 시나리오 트리 구축
- 베이스(60-70%), 업사이드(20-30%), 다운사이드(10%)
- 각 시나리오의 **트리거 조건** 명시

## 5단계: 숨은 엣지 정량화
- 오즈메이커의 **구조적 미스프라이싱** 발굴
- 기댓값 우위 수치화: "5-8% EV"

# 입력 데이터
{rich_context}

# 감지된 패턴
{patterns}

# 출력 형식
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
            'model': 'anthropic/claude-sonnet-4-20250514',
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.7,
            'max_tokens': 4000
        },
        timeout=120
    )

    if response.status_code == 200:
        analysis = response.json()['choices'][0]['message']['content']

        # 파일 저장
        filename = f"/Users/js/g9/nba_data/odds_reports/graphrag_{away_team}_at_{home_team}_SMART_RAG.md"
        with open(filename, 'w') as f:
            f.write(f"# {away_team} @ {home_team}\n\n")
            f.write(f"Generated: {game_date} (Smart Graph RAG + Sonnet 4)\n\n")
            f.write(analysis)

        print(f"✅ Saved: {filename}")
        return analysis
    else:
        raise Exception(f"API Error: {response.status_code}")

if __name__ == '__main__':
    # 테스트
    analysis = generate_analysis('LAL', 'BOS', '2025-12-30')
    print(analysis)
```

### 비용 계산
```
Sonnet 4 가격:
- Input: $3 / 1M tokens
- Output: $15 / 1M tokens

1경기당:
- Input: 3,000 tokens (Rich Context) = $0.009
- Output: 2,000 tokens (분석) = $0.03
- 총: $0.039 ≈ $0.04

1일 4경기: $0.16
1달 (30일): $4.80

→ Opus ($60-90) 대비 **94% 절감**!
```

---

## Phase 4: VPS 자동화 (3-4주차)

### 목표
- VPS에서 매일 자동 실행
- Cron job 설정
- Grafana 모니터링

### VPS 배포
```bash
# 1. 코드 업로드
scp smart_graph_rag.py root@141.164.35.214:/opt/g9/odds-engine/
scp generate_with_smart_rag.py root@141.164.35.214:/opt/g9/odds-engine/

# 2. 환경 변수 설정
ssh root@141.164.35.214
cat >> /opt/g9/odds-engine/.env << EOF
OPENROUTER_API_KEY=sk-or-v1-...
NEO4J_PASSWORD=...
EOF

# 3. Cron job 설정
crontab -e
# 매일 오전 9시 (한국 시간 18시)
0 9 * * * cd /opt/g9/odds-engine && /usr/bin/python3 generate_with_smart_rag.py >> /var/log/g9-odds.log 2>&1
```

---

## 비용 & 품질 비교 (최종)

| 방식 | 비용/월 | 품질 | 자동화 | 시간 |
|-----|--------|------|--------|------|
| **Option 1: Manual (현재)** | $0 | 100% | ❌ | 5-10분/day |
| **Option 2: Smart RAG + Sonnet 4** | $5 | 90% | ✅ | 0분 |
| **Option 3: Opus 4.5 API** | $60-90 | 100% | ✅ | 0분 |

→ **Phase 3 목표: Option 2 완성**

---

## 체크리스트

### Week 1 (수동 실행)
- [ ] Day 1: 첫 수동 분석 (오늘 완료!)
- [ ] Day 2-7: 매일 분석 + 패턴 기록
- [ ] Pattern log 5개+ 수집

### Week 2 (Rich Context 구현)
- [ ] `smart_graph_rag.py` 작성
- [ ] 10 Core Queries 구현
- [ ] Pattern Detection 로직 구현
- [ ] 로컬 테스트 성공

### Week 3 (LLM API 통합)
- [ ] `generate_with_smart_rag.py` 작성
- [ ] Sonnet 4 API 테스트
- [ ] 품질 비교 (vs 수동 분석)
- [ ] 비용 검증

### Week 4 (VPS 배포)
- [ ] VPS 코드 업로드
- [ ] Cron job 설정
- [ ] 첫 자동 실행 성공
- [ ] Grafana 대시보드 업데이트

---

## 최종 목표

**1개월 후:**
```
VPS에서 매일 자동으로
4-8개 경기 분석 생성
품질: Opus 90%
비용: $5/month
완전 자동화
```

**지금:**
```
Claude Code로 수동 분석
품질: Opus 100%
비용: $0
시간: 5-10분/day
```

→ **점진적 전환, 품질 유지!**
