# 새 Claude Code - 5분 Quick Start

**이 파일만 읽으면 시작 가능**

---

## 1. 프로젝트 이해 (30초)

```
300만 헤드라인 → 2만 레짐 → 19개 클러스터 → Neo4j Graph
```

**목표**: "2018년 12월과 지금이 비슷하네!" 같은 Graph RAG 검색

---

## 2. NBA 프로젝트에서 배운 것 (1분)

### ✅ 해야 할 것

1. 작은 샘플(100개)로 먼저 검증
2. 수동 Input으로 시작 (자동화는 나중에)
3. Schema는 여러번 리팩토링 OK

### ✗ 하지 말아야 할 것

1. 자동 분류 급하게 뛰어들기
2. 300만 데이터 전부 임베딩
3. 완벽한 Schema 기대

---

## 3. 첫 세션 목표 (2분)

```python
# Step 1: 데이터 확인
regimes = pd.read_csv('regimes.csv', nrows=100)
print(regimes.head())

# Step 2: Neo4j 설정
docker run -d --name neo4j-economy -p 7474:7474 -p 7687:7687 neo4j:5.15

# Step 3: 100개 샘플 임포트
# (스크립트는 ECONOMIC_REGIME_PROJECT_BRIEF.md 참고)

# Step 4: 첫 쿼리
MATCH (r:Regime)
RETURN r.name, count(*) as cnt
ORDER BY cnt DESC
```

---

## 4. 사용자에게 물어볼 질문 (1분)

```
1. 2만 레짐 데이터 파일 경로?
2. 파일 포맷? (CSV/JSON)
3. 19개 클러스터 이름 정의되어 있나요?
4. 시장 지표 데이터도 있나요? (S&P500, VIX)
```

---

## 5. 시작 명령어

```
"경제레짐 State Graph 프로젝트를 시작합니다.

읽을 파일:
- ECONOMIC_REGIME_PROJECT_BRIEF.md (상세 지침)
- QUICK_START_FOR_NEW_CLAUDE.md (이 파일)

현재 상황:
- 2만 레짐, 19개 클러스터 데이터 보유
- Neo4j State Graph 구축 목표

첫 단계:
1. 데이터 파일 위치 확인
2. 100개 샘플 로드
3. Neo4j 설정

데이터 파일 위치를 알려주세요."
```

---

**끝! 이제 ECONOMIC_REGIME_PROJECT_BRIEF.md 읽고 시작하세요** 🚀
