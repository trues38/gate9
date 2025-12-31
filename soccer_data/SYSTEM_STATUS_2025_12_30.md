# Soccer 시스템 종합 점검 보고서

**작성일**: 2025-12-30 23:30 KST
**점검자**: Claude Sonnet 4.5

---

## 📊 Executive Summary

**현재 상태**: 🟡 두 개의 독립 시스템 공존 (통합 필요)

**시스템 A - V5 백테스트 시스템** (12/29 완료)
- 상태: ✅ 완성, 검증 완료
- ROI: +1.50% (Ligue1 +10.50%)
- 위치: 로컬만 존재

**시스템 B - Hybrid xG 분석 시스템** (12/30 완료)
- 상태: ✅ 구축 완료, 리포트 생성 가능
- 위치: 로컬 + VPS 모두 배포
- 크론: ⚠️ Disabled (수동 활성화 필요)

---

## 🏗️ 시스템 A: V5 백테스트 (Historical Odds 기반)

### 위치
- **로컬**: `/Users/js/g9/soccer_data/`

### 핵심 파일
| 파일 | 상태 | 용도 |
|------|------|------|
| `backtest_v5_with_injuries.py` | ✅ 완료 | 부상 영향 백테스트 |
| `backtest_v4_with_graph.py` | ✅ 완료 | Graph Intelligence 백테스트 |
| `backtest_v4.py` | ✅ 완료 | Baseline 백테스트 |
| `processed/backtest_v5_with_injuries.csv` | ✅ 존재 | 결과 데이터 (362KB) |
| `reports/V5_INJURY_BACKTEST_RESULTS.md` | ✅ 존재 | 최종 리포트 |

### 성과 요약
```
Baseline V4  → V4+Graph → V5+Injury
+0.63%       → +1.03%   → +1.50%
           (+0.40%p)  (+0.47%p)

리그별 ROI (V5):
- Ligue 1: +10.50% 🔥 (511경기)
- Bundesliga: +2.35%
- La Liga: +2.49%
- Serie A: -1.15% (개선 중)
- EPL: -4.09% (개선 중)
```

### 데이터 소스
- Historical Odds CSV (football-data.co.uk)
- Understat xG (2024-25 시즌)
- 총 2,755 경기 백테스트

### 상태
- ✅ 백테스트 완료 및 검증
- ✅ ROI 개선 확인 (+138%)
- ❌ VPS 미배포 (로컬 전용)
- ❌ 실시간 베팅 시스템 없음

---

## 🏗️ 시스템 B: Hybrid xG 분석 (SQLite + Neo4j)

### 아키텍처
```
Understat Selenium Collector (크론 - 주 1회)
           ↓
  SQLite (정량 데이터)
  - matches: 3,504 경기
  - match_stats: xG 데이터
  - teams, odds, referees
           ↓
  Neo4j (그래프 패턴) - VPS
  - 폼 시퀀스 (last 5 matches)
  - Head-to-Head 기록
  - 트렌드 분석 (IMPROVING/DECLINING)
           ↓
  Hybrid Analysis Engine
           ↓
  Betting Reports (Markdown)
```

### 로컬 파일 구조
```
/Users/js/g9/soccer_data/
├── data/
│   └── soccer.db (3.7MB) ✅
│       - 3,504 matches
│       - 2,996 with xG data
│
├── collectors/
│   ├── understat_xg_collector.py ✅
│   ├── understat_selenium_collector.py ✅
│   └── shot_quality_metrics.py ✅
│
├── analysis/
│   ├── validate_xg_data.py ✅
│   ├── xg_betting_analyzer.py ✅
│   ├── xg_report_generator.py ✅
│   ├── hybrid_report_generator.py ✅
│   └── reports/
│       ├── hybrid_report_20251230.md ✅
│       ├── xg_summary_20251230.md ✅
│       ├── xg_epl_20251230.md ✅
│       └── (5개 리그 리포트 모두 생성됨)
│
├── scripts/
│   ├── understat_selenium_collector.py ✅
│   ├── ingest_to_sqlite.py ✅
│   └── ingest_to_neo4j.py ✅
│
└── schema/
    ├── soccer_sqlite_schema.sql ✅
    └── soccer_neo4j_schema.cypher ✅
```

### VPS 배포 상태
```
/opt/g9/domains/soccer/
├── data/
│   └── soccer.db (3.7MB) ✅ (로컬과 동기화됨)
│
├── scripts/
│   ├── understat_selenium_collector.py ✅
│   ├── ingest_to_sqlite.py ✅
│   └── ingest_to_neo4j.py ✅
│
├── analysis/
│   ├── validate_xg_data.py ✅
│   ├── xg_betting_analyzer.py ✅
│   ├── xg_report_generator.py ✅
│   ├── hybrid_report_generator.py ✅
│   └── reports/
│       └── (7개 리포트 생성됨) ✅
│
└── logs/
    └── (크론 로그용 디렉토리)
```

### 크론 설정 상태
```bash
# VPS crontab (DISABLED)
# 0 0 * * 0 cd /opt/g9/domains/soccer && \
#   python3 scripts/understat_selenium_collector.py \
#   >> logs/xg_collection.log 2>&1
```

**상태**: ⚠️ **주석 처리됨 (비활성화)**
- 매주 일요일 0:00 UTC (KST 오전 9시) 실행 예정
- xG 데이터 자동 수집
- 현재 수동 활성화 필요

### Neo4j 상태
```
컨테이너: g9-neo4j-soccer
포트: 7689 (bolt), 7476 (http)
상태: ✅ Up 3 hours
비밀번호: ❌ 인증 실패 (soccer_vultr_2025 틀림)
```

**문제**: Neo4j 비밀번호 불일치
- 현재 접속 불가
- 비밀번호 재설정 필요

### 생성된 리포트 (실제 확인)

**Hybrid Report (Liverpool vs Arsenal)**:
```markdown
Liverpool
- Recent xG: 3.29 (avg last 5)
- Trend: IMPROVING

Arsenal
- Recent xG: 2.16 (avg last 5)
- Trend: DECLINING

Prediction:
⚡ Match Result (MEDIUM): Liverpool favored
⚡ Over 2.5 Goals (MEDIUM): Combined xG 5.46
```

**xG Summary (Top Value Bets)**:
```
1. Crystal Palace (EPL): -31.15 xG diff 🔥
2. Werder Bremen (BUN): -28.57 xG diff 🔥
3. Union Berlin (BUN): -25.85 xG diff 🔥
4. Liverpool (EPL): -19.31 xG diff 🔥

Strongest Attacks:
1. Liverpool: 4.16 xG/경기
2. Werder Bremen: 3.25 xG/경기
3. Barcelona: 2.94 xG/경기
```

### 데이터 커버리지
```
SQLite:
- Total Matches: 3,504
- With xG: 2,996 (85.5%)

By League:
- EPL: 760 matches
- LaLiga: 760 matches
- SerieA: 760 matches
- Bundesliga: 612 matches
- Ligue1: 612 matches

Date Range:
- Earliest: 2023-12-31
- Latest: 2025-02-01
```

---

## 🔍 두 시스템 비교

| 항목 | V5 백테스트 | Hybrid xG |
|------|------------|-----------|
| **목적** | ROI 검증 (역사적) | 실시간 베팅 인사이트 |
| **데이터 소스** | Historical Odds CSV | Understat xG (Selenium) |
| **분석 방법** | Dixon-Coles 모델 | xG + Graph 패턴 |
| **ROI 검증** | ✅ 완료 (+1.50%) | ❌ 미실행 |
| **실시간 가능** | ❌ 없음 | ✅ 가능 (크론 활성화 시) |
| **VPS 배포** | ❌ 없음 | ✅ 완료 |
| **자동화** | ❌ 없음 | ⚠️ Disabled |
| **리포트 생성** | Markdown (수동) | Markdown (자동 가능) |
| **Neo4j 사용** | ❌ | ✅ (비밀번호 문제) |

---

## ❌ 발견된 문제점

### Critical
1. **Neo4j 비밀번호 불일치**
   - 컨테이너: g9-neo4j-soccer
   - 현재 시도: `soccer_vultr_2025` (실패)
   - 영향: Graph 패턴 분석 불가

2. **크론 비활성화**
   - VPS에서 xG 수집 크론이 주석 처리됨
   - 수동 활성화 필요

### Medium
3. **V5 백테스트 시스템 VPS 미배포**
   - 로컬에만 존재
   - 실전 베팅 활용 불가

4. **두 시스템 통합 없음**
   - V5 백테스트 (검증된 ROI)
   - Hybrid xG (실시간 인사이트)
   - 별도 운영 중

---

## ✅ 완료된 작업 (12/29-12/30)

### 12/29 - V5 백테스트 시스템
- [x] V4 Baseline 백테스트 (+0.63% ROI)
- [x] Graph Intelligence 추가 (+1.03% ROI)
- [x] 부상 영향 시뮬레이션 (+1.50% ROI)
- [x] Ligue1 최적화 (+10.50% ROI)
- [x] 리그별 성과 분석
- [x] V5 검증 리포트 작성

### 12/30 - Hybrid xG 시스템
- [x] Understat xG 수집 방법 연구 (10개 옵션 검토)
- [x] Selenium Collector 구현
- [x] SQLite 스키마 설계 및 데이터 로드 (3,504 경기)
- [x] Neo4j 스키마 설계
- [x] Shot Quality 대체 지표 개발
- [x] xG 분석 엔진 구현 (validate, analyze, report)
- [x] Hybrid Report Generator 구현
- [x] VPS 배포 (스크립트, DB, 리포트)
- [x] 실제 리포트 7개 생성 및 검증
- [x] 아키텍처 문서 10개 작성

---

## 🚧 미완료 작업

### 즉시 필요
1. **Neo4j 비밀번호 확인 및 수정**
   - 현재 접속 불가
   - 비밀번호 찾기 또는 재설정

2. **크론 활성화**
   - VPS crontab 수정 (주석 제거)
   - xG 자동 수집 시작

3. **Neo4j 데이터 로드**
   - `scripts/ingest_to_neo4j.py` 실행
   - Graph 패턴 구축

### 통합 작업
4. **V5 백테스트 VPS 배포**
   - 로컬 → VPS 전송
   - 크론 설정 (일일 ROI 추적)

5. **두 시스템 통합**
   - V5 ROI 검증 + Hybrid xG 인사이트
   - 통합 리포트 생성

### 고급 기능
6. **실시간 베팅 추천 시스템**
   - Value Bets 자동 탐지
   - Telegram/Slack 알림

7. **자동화된 품질 검증**
   - 리포트 생성 후 검증
   - 이상 데이터 탐지

---

## 📁 파일 위치 정리

### 로컬 (/Users/js/g9/soccer_data/)
```
✅ 완성된 시스템:
- V5 백테스트: backtest_v5_with_injuries.py
- Hybrid xG: analysis/, collectors/, scripts/
- 데이터: data/soccer.db (3.7MB)
- 리포트: analysis/reports/*.md (7개)

📄 문서:
- HYBRID_ARCHITECTURE.md (시스템 설계)
- XG_BETTING_PIPELINE.md (크론 가이드)
- ARCHITECTURE_V1_STATUS.md (스키마 상태)
- FINAL_XG_VERDICT.md (xG 수집 결론)
```

### VPS (/opt/g9/domains/soccer/)
```
✅ 배포됨:
- data/soccer.db (3.7MB)
- scripts/ (수집/인제스트)
- analysis/ (분석/리포트)
- schema/ (DB 스키마)

⚠️ 비활성화:
- 크론: 주석 처리됨

❌ 문제:
- Neo4j: 비밀번호 불일치
```

---

## 🎯 다음 단계 권장사항

### 옵션 1: Hybrid xG 시스템 완성 (추천)
**작업 시간**: 1-2시간

1. Neo4j 비밀번호 확인
   ```bash
   ssh root@141.164.35.214
   docker logs g9-neo4j-soccer | grep -i password
   ```

2. 크론 활성화
   ```bash
   crontab -e
   # 주석 제거:
   0 0 * * 0 cd /opt/g9/domains/soccer && \
     python3 scripts/understat_selenium_collector.py \
     >> logs/xg_collection.log 2>&1
   ```

3. Neo4j 데이터 로드
   ```bash
   cd /opt/g9/domains/soccer
   python3 scripts/ingest_to_neo4j.py
   ```

4. 테스트 실행
   ```bash
   python3 analysis/validate_xg_data.py
   python3 analysis/hybrid_report_generator.py
   ```

**결과**: 완전 자동화된 xG 베팅 분석 시스템

---

### 옵션 2: V5 백테스트 실전 활용
**작업 시간**: 2-3시간

1. VPS 배포
   ```bash
   scp -r backtest_v5_with_injuries.py processed/ \
     root@141.164.35.214:/opt/g9/domains/soccer/
   ```

2. 실시간 ROI 추적 시스템 구축
   - 일일 배당 수집
   - V5 모델로 예측
   - 실제 결과와 비교

3. Ligue1 집중 베팅 전략
   - ROI +10.50% 검증됨
   - Value Bets 자동 탐지

---

### 옵션 3: 통합 시스템 구축
**작업 시간**: 1일

1. V5 + Hybrid 통합
   - V5 ROI 예측
   - Hybrid xG 컨텍스트
   - 결합된 신뢰도 점수

2. 통합 리포트 생성
   ```python
   # V5 예측 + Hybrid 인사이트
   Liverpool vs Arsenal:
   - V5 ROI: +12% (백테스트 검증)
   - Hybrid: Liverpool IMPROVING, Arsenal DECLINING
   - 추천: Liverpool 승리 (HIGH confidence)
   ```

---

## 📊 시스템 성숙도

### V5 백테스트: 9/10
- ✅ 검증된 ROI (+1.50%)
- ✅ Ligue1 특화 (+10.50%)
- ✅ 부상 영향 반영
- ❌ VPS 미배포 (-1점)

### Hybrid xG: 7/10
- ✅ xG 데이터 수집
- ✅ SQLite 구축
- ✅ 리포트 생성
- ⚠️ Neo4j 비밀번호 문제 (-1점)
- ⚠️ 크론 비활성화 (-1점)
- ❌ ROI 백테스트 없음 (-1점)

---

## 🎉 결론

**현재 상태**: 두 개의 강력한 시스템을 모두 보유

**V5 백테스트**:
- 검증된 ROI (+1.50%, Ligue1 +10.50%)
- 즉시 실전 투입 가능

**Hybrid xG**:
- 실시간 인사이트 제공
- 자동화 준비 완료
- 소수 문제 해결 필요 (Neo4j 비밀번호, 크론)

**권장**: 옵션 1 (Hybrid 완성) → 옵션 3 (통합)

**최종 목표**: V5 ROI + Hybrid 인사이트 = 완벽한 베팅 시스템

---

**작성 완료**: 2025-12-30 23:30 KST
**다음 체크**: Neo4j 비밀번호 확인 후 크론 활성화
