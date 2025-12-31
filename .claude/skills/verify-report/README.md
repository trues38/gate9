# verify-report 스킬

NBA/축구 베팅 보고서 검증 스킬 - **외부 공식 API로 팩트 체크**

## 🎯 핵심 기능

### 다층 검증 시스템

```
1차: ESPN API (공식 데이터) ← 최우선 기준
   ↓ 실패 시
2차: Neo4j 내부 데이터
   ↓ 실패 시
3차: 웹 스크래핑 (ESPN.com)
```

**왜 외부 API 우선?**
- ✅ 내부 크롤링 오류로부터 독립적
- ✅ 공식 데이터 소스
- ✅ 실시간 업데이트
- ✅ 교차 검증으로 내부 데이터 품질 모니터링

---

## 📋 검증 항목

### 1. H2H 기록 (20점)
```python
보고서: "MEM 3-1 PHI"
↓
ESPN API 조회 → 실제 3-1 확인 ✓
Neo4j 교차 검증 → 3-1 일치 ✓
→ 검증 통과

만약 불일치:
ESPN: 2-2
Neo4j: 3-1
→ ESPN 기준 우선, -20점 감점
→ 경고: "내부 데이터 오염 가능성"
```

### 2. 팀 통계 (20점)
```python
보고서: "MEM 평균 107.6점"
↓
ESPN API → 실제 107.3점
차이: 0.3점 (< 2.0 허용) ✓
→ 검증 통과

허용 오차: ±2.0점
초과 시: -10점
```

### 3. 최근 경기 (10점)
```python
보고서: "최근 2-3"
↓
ESPN Scoreboard → 실제 2-3 확인 ✓
```

### 4. 논리적 일관성 (15점)
```python
예측: LAL 108 - BOS 99 (9점차)
스프레드 픽: -4.5
→ 9 > 4.5 ✓ 일치

예측: Under 210
총점 예측: 207
→ 207 < 210 ✓ 일치
```

---

## 🚀 사용법

### Claude Code에서
```bash
# 보고서 검증
/verify-report nba_data/odds_reports/graphrag_PHI_at_MEM_20251229.md

# 여러 보고서 한번에
/verify-report nba_data/odds_reports/graphrag_*.md
```

### 터미널에서
```bash
export NEO4J_PASSWORD="your_password"

cd /Users/js/g9/.claude/skills/verify-report
python3 main.py /Users/js/g9/nba_data/odds_reports/graphrag_PHI_at_MEM_20251229.md
```

---

## 📊 출력 예시

```
================================================================================
🔍 보고서 검증 시작: graphrag_PHI_at_MEM_20251229.md
================================================================================

📊 매치업: PHI @ MEM

📌 H2H 기록 검증 (ESPN API)...
📌 팀 통계 검증 (ESPN API)...
📌 최근 경기 검증...
📌 논리적 일관성 검증...

================================================================================
📊 검증 결과
================================================================================

✅ 검증 통과:
   ✓ H2H: 3-1 (ESPN 확인됨)
   ✓ MEM 평균 득점: 107.6 (ESPN API 정확)
   ✓ PHI 최근 폼: 2-3 (정확)
   ✓ Under 픽과 총점 예측 일치

⚠️  경고:
   ⚠️ 데이터 불일치: ESPN (3-1) vs Neo4j (3-2) (ESPN 기준 우선)
      → 내부 크롤링 확인 필요!

================================================================================
🎉 검증 점수: 92/100
   권장 조치: 판매 승인 권장
================================================================================
```

---

## 🔧 설치

### 필수 패키지
```bash
pip install neo4j requests
```

### 선택 (웹 스크래핑용)
```bash
pip install beautifulsoup4
```

---

## 🌐 외부 API 정보

### ESPN API (무료)
- **엔드포인트**: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba`
- **제한**: 없음 (공식 무료 API)
- **데이터**: Scoreboard, Team Stats, H2H

### NBA Stats API (무료)
- **엔드포인트**: `https://stats.nba.com/stats`
- **제한**: Rate limit 있음
- **데이터**: 고급 통계, 선수 데이터

### 백업: 웹 스크래핑
- **대상**: ESPN.com, NBA.com
- **사용 시점**: API 실패 시 자동
- **주의**: Rate limit 고려

---

## 📈 검증 점수 기준

| 점수 | 상태 | 조치 |
|------|------|------|
| **90-100** | 🎉 완벽 | 즉시 판매 승인 |
| **80-89** | ⚡ 양호 | 경고 확인 후 판매 |
| **70-79** | ⚠️ 주의 | 수정 후 재검증 |
| **< 70** | ❌ 불합격 | 판매 중단 |

---

## 💰 API 비용

모두 **무료**!

- ESPN API: 무료, 무제한
- NBA Stats: 무료 (rate limit)
- 웹 스크래핑: 무료

---

## 🔄 검증 우선순위

```python
def verify_data(claim):
    # 1순위: ESPN API
    espn_data = fetch_espn_api()
    if espn_data:
        if espn_data == claim:
            return "✓ ESPN 확인"
        else:
            return "❌ ESPN 불일치 (치명적)"

    # 2순위: Neo4j
    neo_data = fetch_neo4j()
    if neo_data:
        if neo_data == claim:
            return "✓ Neo4j 확인"
        else:
            return "⚠️ Neo4j 불일치"

    # 3순위: 웹 스크래핑
    web_data = scrape_espn_com()
    if web_data:
        return check(web_data, claim)

    return "❓ 검증 불가"
```

---

## 🛡️ 내부 데이터 품질 모니터링

**부수 효과: 크롤링 오류 감지**

```
검증 중 발견:
⚠️ ESPN (3-1) vs Neo4j (3-2)
→ Neo4j 데이터에 1경기 누락 또는 중복

⚠️ ESPN (107.3점) vs Neo4j (110.5점)
→ 크롤링 로직 점수 계산 오류 가능성
```

→ 이 경고들을 모아서 **크롤링 파이프라인 디버깅**에 활용!

---

## 🔮 확장 계획

### 축구 지원
```python
# 추가 API
FOOTBALL_API = "https://api-football-v1.p.rapidapi.com"

# 팀 ID 매핑
football_teams = {
    'MCI': 'Manchester City',
    'LIV': 'Liverpool',
    ...
}
```

### 더 많은 통계
- 선수 개인 통계 (득점, 어시스트)
- 쿼터별 데이터
- 부상자 명단

---

## 📞 트러블슈팅

### ESPN API 실패
```python
# 원인: 네트워크 오류, API 다운타임
# 해결: 자동으로 Neo4j → 웹 스크래핑으로 fallback
```

### Neo4j 연결 실패
```bash
# Neo4j 비밀번호 확인
echo $NEO4J_PASSWORD

# VPS 연결 확인
nc -zv 141.164.35.214 7687
```

### 웹 스크래핑 차단
```python
# User-Agent 변경
# Proxy 사용 (필요 시)
```

---

## ✅ 체크리스트

### 보고서 생성 후
- [ ] `/verify-report` 실행
- [ ] 검증 점수 확인
- [ ] 경고 항목 검토
- [ ] ESPN vs Neo4j 불일치 기록
- [ ] 90점 이상 → 판매 승인
- [ ] 80점 미만 → 수정 또는 폐기

---

**© 2025 G9 Regime Zero - Multi-Layer Verification System**
**Truth Source: ESPN API → Neo4j → Web Scraping**
