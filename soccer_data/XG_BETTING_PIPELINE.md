# xG 베팅 분석 파이프라인 가이드

## 파이프라인 구조

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 데이터 수집 (자동 - 크론)                                │
│    매주 일요일 0:00 UTC (KST 오전 9시)                       │
│    scripts/understat_selenium_collector.py                  │
│    → xG 데이터 자동 수집 (5개 리그)                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. 데이터 검증 (수동 - 보고서 생성 전 필수)                 │
│    analysis/validate_xg_data.py                             │
│    → 데이터 품질 확인                                       │
│    → 검증 통과해야 다음 단계 진행                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. 보고서 생성 (수동 - 검증 후 실행)                        │
│    analysis/xg_betting_analyzer.py                          │
│    analysis/xg_report_generator.py                          │
│    → 베팅 인사이트 리포트 생성                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 자동화된 부분 (크론)

### 데이터 수집 - 주 1회 자동 실행

**크론 설정:**
```bash
0 0 * * 0 cd /opt/g9/domains/soccer && python3 scripts/understat_selenium_collector.py >> logs/xg_collection.log 2>&1
```

**실행 일정:** 매주 일요일 자정 (UTC)
- KST 기준: 오전 9시
- 소요 시간: 약 3분
- 수집 리그: EPL, LaLiga, Bundesliga, SerieA, Ligue1

**로그 확인:**
```bash
tail -f /opt/g9/domains/soccer/logs/xg_collection.log
```

---

## 수동 실행 부분

### Step 1: 데이터 검증 (필수)

크론이 데이터를 수집한 후, 보고서 생성 전에 **반드시 검증**을 실행하세요.

```bash
cd /opt/g9/domains/soccer
python3 analysis/validate_xg_data.py
```

**검증 항목:**
- ✅ 데이터베이스 접근 가능
- ✅ xG 데이터 존재
- ✅ 최근 업데이트 (14일 이내)
- ✅ 리그별 커버리지 (30% 이상)
- ✅ 데이터 품질 (이상치, NULL 값)
- ✅ 분석 준비 완료

**결과 예시:**
```
============================================================
xG Data Validation Report
============================================================

✅ Database Access
   Database accessible with 5,432 total matches

✅ xG Data Existence
   Found 2,996 xG records

✅ Recent Updates
   xG data is recent (2 days old)

✅ EPL Coverage
   570/380 matches with xG (150.0%), 20 teams

✅ Data Quality - Outliers
   Outlier check passed (3 matches with xG > 6.0)

============================================================
Summary
============================================================
Total Checks: 15
✅ Passed: 15
⚠️  Warnings: 0
❌ Errors: 0

🟢 VALIDATION PASSED - Safe to generate reports
============================================================
```

**검증 실패 시:**
```bash
# xG 데이터 다시 수집
python3 scripts/understat_selenium_collector.py

# 다시 검증
python3 analysis/validate_xg_data.py
```

---

### Step 2: 보고서 생성 (검증 통과 후)

#### 옵션 A: 통합 스크립트 (권장)

```bash
cd /opt/g9/domains/soccer
bash analysis/generate_betting_report.sh
```

**대화형 모드:**
- 검증 자동 실행
- 각 단계마다 확인 프롬프트
- 검증 실패 시 자동 중단

**자동 모드:**
```bash
bash analysis/generate_betting_report.sh --auto
```
- 검증 통과 시 자동으로 보고서 생성
- 프롬프트 없음

#### 옵션 B: 단계별 실행

```bash
# 1. 검증
python3 analysis/validate_xg_data.py

# 2. 분석 (검증 통과 시)
python3 analysis/xg_betting_analyzer.py

# 3. 리포트 생성
python3 analysis/xg_report_generator.py
```

---

## 생성되는 파일

### 검증 결과
```
analysis/reports/validation_YYYYMMDD_HHMMSS.json
```
- 검증 결과 JSON
- 리그별 통계
- 에러/경고 목록

### 분석 데이터
```
analysis/reports/xg_analysis_YYYYMMDD_HHMMSS.json
```
- 전체 5개 리그 분석 데이터
- xG 퍼포먼스, 최근 폼, 홈/원정 스플릿
- 벨류 벳 기회

### 베팅 리포트 (Markdown)
```
analysis/reports/xg_summary_YYYYMMDD.md         # 전체 요약
analysis/reports/xg_epl_YYYYMMDD.md             # EPL 상세
analysis/reports/xg_laliga_YYYYMMDD.md          # LaLiga 상세
analysis/reports/xg_bundesliga_YYYYMMDD.md      # Bundesliga 상세
analysis/reports/xg_seriea_YYYYMMDD.md          # SerieA 상세
analysis/reports/xg_ligue1_YYYYMMDD.md          # Ligue1 상세
```

---

## 리포트 확인

### VPS에서 직접 확인
```bash
# 요약 리포트
cat analysis/reports/xg_summary_*.md | less

# EPL 리포트
cat analysis/reports/xg_epl_*.md | less
```

### 로컬로 다운로드
```bash
# VPS → 로컬
scp root@141.164.35.214:/opt/g9/domains/soccer/analysis/reports/xg_summary_*.md .
scp root@141.164.35.214:/opt/g9/domains/soccer/analysis/reports/xg_epl_*.md .
```

---

## 베팅 인사이트 해석

### 🟢 Value Bets (저조한 득점)

**의미:** xG보다 훨씬 적게 득점하는 팀
- 좋은 찬스를 만들지만 골로 연결 못함
- **회귀 효과 기대** → 곧 더 많이 득점할 가능성

**예시:**
```
Crystal Palace: 실제 42골 vs xG 73.15 (-31.15골)
→ 최근 5경기 평균 xG: 2.34 (여전히 찬스 많이 만듦)
→ 추천: BACK TO SCORE
```

**베팅 전략:**
- 득점 마켓: O0.5, O1.5 팀 득점
- BTTS (Both Teams To Score)

---

### 🔴 Overperforming (과도한 득점)

**의미:** xG보다 훨씬 많이 득점하는 팀
- 적은 찬스로 많이 득점 중
- **회귀 효과 기대** → 곧 덜 득점할 가능성

**예시:**
```
Fulham: 실제 32골 vs xG 21.65 (+10.35골, +47.8%)
→ 추천: 득점 언더 베팅 고려
```

**베팅 전략:**
- 팀 득점 언더
- 상대팀 무승부/승리

---

### ⚡ 최강 공격 (Recent Form)

**의미:** 최근 5경기 높은 xG
- 공격력이 좋음
- 상대 약한 수비 만나면 폭발 가능

**베팅 전략:**
- Over 2.5 goals
- 팀 승리
- 핸디캡 베팅

---

### 🚨 최약 수비 (High xGA)

**의미:** 최근 5경기 많은 xG 허용
- 수비가 약함
- 상대팀 득점 기대

**베팅 전략:**
- 상대팀 득점 마켓
- Over 2.5 goals
- BTTS

---

### 🏠 홈 강세 / ✈️ 원정 강세

**의미:** 홈/원정 xG 차이가 큼
- 특정 환경에서 훨씬 강함

**베팅 전략:**
- 홈 강세팀: 홈경기에만 베팅
- 원정 강세팀: 원정에서도 베팅 가능

---

## 주간 워크플로우 예시

### 일요일 (크론 실행 후)

```bash
# 1. VPS 접속
ssh root@141.164.35.214
cd /opt/g9/domains/soccer

# 2. 크론 로그 확인 (데이터 수집 확인)
tail -50 logs/xg_collection.log
# 확인: "✅ Total: 757 matches updated"

# 3. 데이터 검증
python3 analysis/validate_xg_data.py
# 확인: "🟢 VALIDATION PASSED"

# 4. 보고서 생성
bash analysis/generate_betting_report.sh
# 또는
python3 analysis/xg_betting_analyzer.py
python3 analysis/xg_report_generator.py

# 5. 리포트 확인
cat analysis/reports/xg_summary_$(date +%Y%m%d).md
```

### 평일 (추가 분석 필요 시)

```bash
# 검증 없이 바로 리포트 재생성
python3 analysis/xg_betting_analyzer.py
python3 analysis/xg_report_generator.py
```

---

## 트러블슈팅

### 문제 1: 검증 실패 - "데이터가 오래됨"

```
⚠️ Recent Updates
   xG data is 15 days old (last update: 15/12/2024)
```

**해결:**
```bash
# xG 데이터 수동 수집
python3 scripts/understat_selenium_collector.py

# 다시 검증
python3 analysis/validate_xg_data.py
```

---

### 문제 2: 검증 실패 - "리그 커버리지 부족"

```
❌ EPL Coverage
   Insufficient xG data: 50/380 matches (13.2%)
```

**원인:** 데이터베이스에 매치 데이터가 없거나 적음

**해결:**
```bash
# 1. CSV 수집기 실행 (매치 데이터 수집)
python3 collectors/csv_collector.py

# 2. xG 수집
python3 scripts/understat_selenium_collector.py

# 3. 검증
python3 analysis/validate_xg_data.py
```

---

### 문제 3: 크론이 실행 안 됨

**확인:**
```bash
# 크론탭 확인
crontab -l | grep understat

# 로그 확인
ls -lah logs/xg_collection.log
tail -100 logs/xg_collection.log
```

**수동 실행:**
```bash
cd /opt/g9/domains/soccer
python3 scripts/understat_selenium_collector.py
```

---

## 요약

**자동화 (크론):**
- ✅ xG 데이터 수집 (주 1회)

**수동 실행 (사용자):**
- 🔍 데이터 검증 (보고서 생성 전 필수)
- 📊 보고서 생성 (검증 통과 후)

**파일 위치:**
- 검증: `analysis/validate_xg_data.py`
- 분석: `analysis/xg_betting_analyzer.py`
- 리포트: `analysis/xg_report_generator.py`
- 통합: `analysis/generate_betting_report.sh`

**다음 실행:**
```bash
ssh root@141.164.35.214
cd /opt/g9/domains/soccer
bash analysis/generate_betting_report.sh
```
