# 🚀 NBA/축구 보고서 생성 치트시트

**1분 안에 시작하기**

---

## ⚡ 빠른 시작

### 1. 터미널 열고
```bash
cd /Users/js/g9
claude
```

### 2. 보고서 생성
```bash
> "오늘 NBA 주요 5경기 Graph RAG 분석해줘, Opus 4.5 스타일로"
```

### 3. 검증
```bash
> /verify-report nba_data/odds_reports/graphrag_*_20251229.md
```

### 4. 점수 확인
- 90+ ✅ 판매
- 80-89 ⚡ 확인 후 판매
- 70-79 ⚠️ 수정
- <70 ❌ 폐기

**끝!**

---

## 📋 프롬프트 모음

### NBA (오전 00:00)
```
오늘 NBA 주요 5경기 Graph RAG 분석해줘, Opus 4.5 스타일로
```

### 축구 (오후 12:00)
```
오늘 EPL + 라리가 주요 10경기 Graph RAG 분석해줘, Opus 4.5 스타일로
```

### 수정
```
[팀A] @ [팀B] 보고서에서 H2H를 [수정 내용]으로 변경해줘
```

### 재작성
```
[팀A] @ [팀B] 다시 작성해줘, H2H는 이번 시즌만 기준으로
```

---

## 🎯 점수 기준

| 점수 | 상태 | 조치 |
|------|------|------|
| 90-100 | 🎉 | 즉시 판매 |
| 80-89 | ⚡ | 경고 확인 → 판매 |
| 70-79 | ⚠️ | 수정 필요 |
| < 70 | ❌ | 폐기 또는 재작성 |

---

## 🔧 자주 쓰는 명령어

```bash
# 검증 (하나)
> /verify-report nba_data/odds_reports/graphrag_LAL_at_BOS_20251229.md

# 검증 (전체)
> /verify-report nba_data/odds_reports/graphrag_*_20251229.md

# 보고서 위치
ls nba_data/odds_reports/

# 최신 보고서 확인
ls -lt nba_data/odds_reports/ | head -10
```

---

## 💡 수정 패턴

### H2H 불일치
```
❌ H2H: 보고서 5-0 vs ESPN 0-1

수정:
> "H2H를 이번 시즌 0-1로 수정해줘"
```

### 팀 통계 오류
```
❌ 평균 득점: 보고서 110.1 vs 실제 113.4

수정:
> "LAL 평균 득점을 113.4로 수정해줘"
```

### 논리 불일치
```
❌ Under 픽인데 예측 총점 215 > 라인 210

수정:
> "총점 예측을 205로 수정해줘"
```

---

## ⏰ 타임라인

**00:00 NBA (30분)**
- 00:00-00:25: 생성 (5개)
- 00:25-00:28: 검증
- 00:28-00:30: 승인

**12:00 축구 (30분)**
- 12:00-12:25: 생성 (10개)
- 12:25-12:28: 검증
- 12:28-12:30: 승인

**총: 1시간/일**

---

## 🚨 긴급 문제 해결

### 검증 안될 때
```bash
export NEO4J_PASSWORD="nba_vultr_2025"
cd /Users/js/g9/.claude/skills/verify-report
python3 main.py /path/to/report.md
```

### 느릴 때
```
5개 → 3개로 줄이기
```

### 전부 낮은 점수
```
내일 다시 시도
(Neo4j 업데이트 대기)
```

---

## 📞 연락처

문제 발생 시:
1. DAILY_WORKFLOW.md 참조
2. README.md 확인
3. Github Issues

---

**© 2025 G9 Regime Zero**
