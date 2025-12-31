# NBA 보고서 시스템 종합 감사 (2025-12-30)

## 🎯 Executive Summary

**상태**: 🟡 부분 작동 (데이터 수집 3일 정체, 크론 설정 불일치)

**핵심 문제**:
1. ❌ **Boxscore 크론이 작동하지 않음** - API 엔드포인트 불일치
2. ⚠️ **데이터가 2025-12-27에서 정체** - 3일간 업데이트 없음
3. ⚠️ **보고서 생성 파이프라인이 VPS에 없음** - 로컬에서만 수동 실행

**즉시 필요한 조치**:
1. 크론 스크립트 수정 (`/collect/boxscores` → `/collect/nba`)
2. VPS에 보고서 생성 파이프라인 배포
3. 데이터 수집 재개 및 백필

---

## 📋 시스템 구성도

### VPS 시스템 (141.164.35.214)

```
┌─────────────────────────────────────────────────────┐
│                 크론 스케줄 (UTC)                    │
├─────────────────────────────────────────────────────┤
│ 0 0 * * *    → nba_boxscore.sh                      │
│                └─ POST /collect/boxscores ❌ 404    │
│                                                       │
│ */30 * * * * → nba_realtime.sh                      │
│                └─ POST /check/realtime ✅ 작동       │
│                                                       │
│ 0 8 * * *    → Soccer 수집 ✅                        │
│ 30 23 * * *  → Economy 수집 ✅                       │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│              Docker 컨테이너 (10개)                  │
├─────────────────────────────────────────────────────┤
│ g9-neo4j-nba       (7687, 7474) ✅ Healthy          │
│  ├─ PlayerStats: 14,140개                           │
│  ├─ Game: 3,220개 (최신: 2025-12-27)                │
│  ├─ Player: 712명                                    │
│  ├─ Team: 35팀                                       │
│  └─ NBAEvent: 47개                                   │
│                                                       │
│ g9-nba-collector   (8001) ✅ Twitter 수집 (30분마다) │
│  ├─ Twitter API 사용량: 14/250 (NBA)                │
│  ├─ 새 트윗: 0개 (모두 중복)                         │
│  └─ SQLite: raw_tweets.db (2건만 있음)              │
│                                                       │
│ g9-flask-nba       (8000) ⚠️ 옛날 RSS 시스템        │
│  ├─ /health ✅                                       │
│  ├─ /collect/nba ✅                                  │
│  ├─ /check/realtime ✅ (하지만 RSS 모두 실패)       │
│  └─ /collect/boxscores ❌ 존재하지 않음!            │
│                                                       │
│ g9-neo4j-economy   (7688, 7475) ✅                   │
│ g9-neo4j-soccer    (7689, 7476) ✅                   │
│ 모니터링 스택       (Prometheus, Grafana 등) ✅      │
└─────────────────────────────────────────────────────┘
```

### 로컬 시스템 (/Users/js/g9)

```
┌─────────────────────────────────────────────────────┐
│            nba_data/odds_report_engine/              │
├─────────────────────────────────────────────────────┤
│ ✅ generate_graph_rag_reports.py                     │
│ ✅ ai_betting_council.py                             │
│ ✅ graph_odds_report_generator.py                    │
│ ✅ /verify-report 스킬 (품질 검증)                   │
│                                                       │
│ ❌ VPS 배포 안됨                                     │
│ ❌ 크론 자동화 안됨                                  │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│            nba_data/state_graph/                     │
├─────────────────────────────────────────────────────┤
│ ✅ calculate_coach_stats.py                          │
│ ✅ expand_player_attributes.py                       │
│ ✅ calculate_team_strength.py                        │
│ ✅ daily_automation.py                               │
│                                                       │
│ ❌ VPS 연동 안됨                                     │
└─────────────────────────────────────────────────────┘
```

---

## 🔍 상세 분석

### 1. 크론 → 데이터 파이프라인

#### ✅ 정상 작동
- **Realtime 수집** (30분마다)
  - 엔드포인트: `/check/realtime` ✅ 존재
  - 로그: `/var/log/g9/nba_realtime.log` ✅
  - 상태: RSS 피드 모두 실패, 저장 0건
  - **분석**: RSS는 실패하지만 크론은 작동 중

- **Economy 수집** (매일 23:30 UTC)
  - 크론 ✅ 설정됨
  - 파이프라인 ✅ 작동 중

- **Soccer 수집** (매일 08:00 UTC)
  - 크론 ✅ 설정됨
  - 파이프라인 ✅ 작동 중

#### ❌ 문제 발견
- **Boxscore 수집** (매일 00:00 UTC = 09:00 KST)
  - 크론: `0 0 * * * /opt/g9/cron/nba_boxscore.sh`
  - 스크립트 내용: `curl -X POST http://localhost:8000/collect/boxscores`
  - **문제**: `/collect/boxscores` 엔드포인트가 존재하지 않음 (404 오류)
  - **로그**: `/var/log/g9/nba_boxscore.log` 파일 자체가 없음
  - **결과**: Boxscore 수집이 전혀 이루어지지 않음

---

### 2. 데이터 수집 파이프라인

#### VPS에 두 개의 수집 시스템 공존

**시스템 A: g9-nba-collector (신규, Twitter API 기반)**
- 포트: 8001
- 상태: ✅ 작동 중 (30분마다)
- 수집 방식: Twitter API (twitter-api45)
- 엔드포인트:
  - `/collect/nba` ✅
  - `/collect/odds` ✅
  - `/process/llm` ✅
- API 사용량: NBA=14/250, Economy=1/200
- **수집 결과**: 트윗은 가져오지만 모두 중복 (저장 0건)
- **로그 예시**:
  ```
  2025-12-30 09:00:03 - ✅ Fetched 1 tweets from 12 accounts (1 API call)
  2025-12-30 09:00:03 - Batch save: 0/1 new tweets
  2025-12-30 09:00:03 - Saved 0 new tweets to raw storage
  ```

**시스템 B: g9-flask-nba (옛날, RSS 기반)**
- 포트: 8000
- 상태: ⚠️ 부분 작동
- 수집 방식: RSS 피드
- 엔드포인트:
  - `/health` ✅
  - `/check/realtime` ✅ (하지만 RSS 모두 실패)
  - `/collect/boxscores` ❌ 존재하지 않음
- **수집 결과**: RSS 피드 모두 실패
- **로그 예시**:
  ```
  WARNING: ShamsCharania RSS 가져오기 실패 (모든 인스턴스)
  WARNING: wojespn RSS 가져오기 실패 (모든 인스턴스)
  WARNING: OfficialNBARefs RSS 가져오기 실패 (모든 인스턴스)
  INFO: 실시간 체크 완료 - 저장: 0, 중복스킵: 0
  ```

#### 결론: 크론-API 불일치
- **크론이 호출**: `http://localhost:8000/collect/boxscores`
- **실제 존재**: `http://localhost:8001/collect/nba` (g9-nba-collector)
- **결과**: Boxscore 수집 실패, 데이터 3일 정체

---

### 3. Neo4J 데이터베이스 상태

#### 연결 정보
- **URI**: bolt://localhost:7687 (VPS 내부)
- **Username**: neo4j
- **Password**: nba_vultr_2025
- **Health**: ✅ Healthy

#### 노드 통계
| 노드 타입 | 개수 | 상태 | 비고 |
|-----------|------|------|------|
| PlayerStats | 14,140 | ✅ | 박스스코어 데이터 |
| Game | 3,220 | ⚠️ | 최신: 2025-12-27 (3일 전) |
| Player | 712 | ✅ | 선수 정보 |
| Team | 35 | ✅ | 팀 정보 (30팀 + 5개 옛날 팀?) |
| NBAEvent | 47 | ⚠️ | 실시간 이벤트 (매우 적음) |
| Odds | 20 | ⚠️ | 오즈 정보 (매우 적음) |

#### 스키마 구조
```cypher
(:Player)-[:PLAYS_FOR]->(:Team)
(:Player)-[:PLAYED_IN]->(:Game)
(:Player)-[:RECORDED]->(:PlayerStats)
(:Game)-[:IN_GAME]->(:PlayerStats)
```

#### 제약조건 및 인덱스
- ✅ Player: `person_id`, `player_id` UNIQUE
- ✅ Team: `team_id`, `team_abbr` UNIQUE
- ✅ PlayerStats: `stat_id` UNIQUE
- ✅ Game: `game_id` INDEX

#### 샘플 데이터 확인
```cypher
// 최근 경기 (2025-12-27)
(:Game {
  date: "20251227",
  game_id: "401810287",
  home_team: "SAC",
  away_team: "DAL",
  home_score: 113,
  away_score: 107,
  status: "post"
})
```

**문제**: `date` 필드는 있지만 `game_date` 필드는 없음 (제가 초기 조회 시 실수)

---

### 4. SQLite 데이터베이스

#### 위치
- `/opt/g9/nba-collector/data/raw_tweets.db`

#### 스키마
```sql
CREATE TABLE raw_tweets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tweet_id TEXT NOT NULL,
  username TEXT NOT NULL,
  text TEXT NOT NULL,
  created_at TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  domain TEXT NOT NULL,
  text_hash TEXT NOT NULL UNIQUE,
  url TEXT,
  retweet_count INTEGER DEFAULT 0,
  like_count INTEGER DEFAULT 0,
  reply_count INTEGER DEFAULT 0,
  raw_json TEXT,
  processed BOOLEAN DEFAULT 0,
  llm_processed_at TEXT
);
```

#### 데이터 확인
```sql
SELECT COUNT(*), domain, DATE(created_at) as date
FROM raw_tweets
GROUP BY domain, date;
-- 결과: 2 | nba | 2025-12-28
```

**문제**: 단 2건의 NBA 트윗만 저장됨 (매우 적음)

---

### 5. 검증 로직 및 데이터 품질

#### 로컬 검증 시스템 (/Users/js/g9/.claude/skills/verify-report/)
- ✅ `main.py` - Neo4J 데이터와 보고서 교차 검증
- ✅ ESPN API 연동 - 실시간 데이터 비교
- ✅ 품질 점수 산출 (0-100점)
- ✅ 경고/오류 분류

#### VPS 검증 시스템
- ❌ **존재하지 않음**
- VPS에는 보고서 생성 파이프라인 자체가 없음

---

### 6. 보고서 생성 파이프라인

#### 로컬 시스템 (수동 실행)
**위치**: `/Users/js/g9/nba_data/odds_report_engine/`

**스크립트**:
1. `generate_graph_rag_reports.py` - 기본 리포트 생성
2. `ai_betting_council.py` - AI 위원회 평가
3. `graph_odds_report_generator.py` - 오즈 통합 리포트

**워크플로우** (DAILY_WORKFLOW.md):
```
1. Claude Code 실행
2. "오늘 NBA 주요 5경기 분석해줘" (Graph RAG)
3. /verify-report로 검증
4. 점수 확인 → 판매
```

**출력**:
- `/Users/js/g9/nba_data/odds_reports/graphrag_*.md`
- 예시: `graphrag_BOS_at_UTAH_20251229_090132.md`

#### VPS 시스템
**위치**: `/opt/g9/nba_graph_rag_report.py` (스크립트만 존재)

**상태**:
- ❌ 실행 환경 없음 (Flask API에 통합 안됨)
- ❌ 크론 자동화 안됨
- ❌ 보고서 출력 디렉토리 없음

---

### 7. 타임라인 설계 분석

#### 현재 크론 타임라인 (UTC 기준)

| 시간 (UTC) | 작업 | 상태 | 비고 |
|-----------|------|------|------|
| 00:00 | NBA Boxscore 수집 | ❌ | API 404 오류 |
| 매 30분 | NBA Realtime 수집 | ⚠️ | RSS 실패, 저장 0건 |
| 08:00 | Soccer 수집 | ✅ | 정상 작동 |
| 23:30 | Economy 수집 | ✅ | 정상 작동 |

#### 이상적인 NBA 타임라인 (KST 기준)

**일일 기준** (DAILY_WORKFLOW.md 참고):
```
09:00 KST (00:00 UTC) - Boxscore 수집
  ↓
09:30 KST - 데이터 검증
  ↓
10:00 KST - Neo4J 업데이트
  ↓
00:00 KST (다음날) - NBA 보고서 생성 (5개, 30분)
  ↓
00:30 KST - 검증 및 품질 체크
  ↓
01:00 KST - 판매 승인
```

**경기일 기준**:
```
경기 3시간 전 - Lineup + 부상자 체크
  ↓
경기 1시간 전 - Realtime 이벤트 모니터링
  ↓
경기 종료 후 - Boxscore 수집
  ↓
다음날 00:00 - 보고서 생성
```

#### 문제점
1. ❌ **Boxscore 수집 실패** → 데이터 업데이트 없음
2. ❌ **보고서 생성이 VPS에 없음** → 수동 로컬 실행만 가능
3. ⚠️ **Realtime 수집이 작동하지 않음** → RSS 실패, 저장 0건

---

## 🚨 주요 문제점 요약

### Critical (즉시 수정 필요)

1. **크론 스크립트 API 엔드포인트 불일치**
   - 파일: `/opt/g9/cron/nba_boxscore.sh`
   - 현재: `POST http://localhost:8000/collect/boxscores` (404)
   - 수정: `POST http://localhost:8001/collect/nba` 또는 Flask API에 `/collect/boxscores` 엔드포인트 추가
   - **영향**: Boxscore 수집 완전 중단, 데이터 3일 정체

2. **데이터 업데이트 중단**
   - Neo4J 최신 데이터: 2025-12-27 (3일 전)
   - 원인: 위의 크론 실패
   - **영향**: 보고서 품질 저하, 부상자/라인업 정보 누락

3. **보고서 생성 파이프라인 VPS 미배포**
   - 로컬에만 존재: `odds_report_engine/`
   - VPS 상태: 스크립트만 있음 (`nba_graph_rag_report.py`)
   - **영향**: 자동화 불가, 수동 로컬 실행만 가능

### Warning (개선 권장)

4. **Realtime 수집 실패**
   - g9-flask-nba의 RSS 피드 모두 실패
   - 저장: 0건, 중복스킵: 0건
   - **원인**: RSS 방식이 더 이상 작동하지 않음 (Twitter/X API 변경)
   - **대안**: g9-nba-collector의 Twitter API 사용 (이미 작동 중)

5. **두 개의 수집 시스템 공존**
   - g9-flask-nba (옛날 RSS) vs g9-nba-collector (신규 Twitter API)
   - 크론이 옛날 시스템을 호출
   - **영향**: 혼란, 유지보수 어려움

6. **SQLite 데이터 부족**
   - raw_tweets 테이블: 단 2건
   - Twitter 수집은 작동하지만 모두 중복
   - **원인**: 새로운 트윗이 없거나 중복 체크 로직 문제

---

## ✅ 해결 방안

### 즉시 조치 (1시간)

#### 1. 크론 스크립트 수정
```bash
# VPS 접속
ssh root@141.164.35.214

# 백업
cp /opt/g9/cron/nba_boxscore.sh /opt/g9/cron/nba_boxscore.sh.backup

# 수정
cat > /opt/g9/cron/nba_boxscore.sh << 'EOF'
#!/bin/bash
# NBA Boxscore Collection - Daily 9AM KST (0:00 UTC)

LOG=/var/log/g9/nba_boxscore.log
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting boxscore collection..." >> $LOG

# Call new Twitter API collector
curl -s -X POST http://localhost:8001/collect/nba >> $LOG 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Boxscore collection complete" >> $LOG
EOF

# 권한 설정
chmod +x /opt/g9/cron/nba_boxscore.sh

# 수동 테스트
/opt/g9/cron/nba_boxscore.sh
tail -20 /var/log/g9/nba_boxscore.log
```

#### 2. 데이터 백필 (3일치)
```bash
# VPS에서 수동으로 3일치 수집
ssh root@141.164.35.214

# 12-28, 12-29, 12-30 데이터 수집
for i in {28..30}; do
  curl -X POST http://localhost:8001/collect/nba
  sleep 5
done

# Neo4J 데이터 확인
docker exec g9-neo4j-nba cypher-shell -u neo4j -p nba_vultr_2025 \
  "MATCH (g:Game) RETURN g.date as date, count(*) as games ORDER BY date DESC LIMIT 10;"
```

#### 3. 크론 로그 모니터링
```bash
# 내일 00:00 UTC 이후 확인
ssh root@141.164.35.214 'tail -50 /var/log/g9/nba_boxscore.log'

# Neo4J 최신 데이터 확인
ssh root@141.164.35.214 'docker exec g9-neo4j-nba cypher-shell -u neo4j -p nba_vultr_2025 "MATCH (g:Game) RETURN MAX(g.date) as latest_date;"'
```

### 단기 조치 (1-2일)

#### 4. VPS에 보고서 생성 파이프라인 배포
```bash
# 로컬에서 VPS로 전송
cd /Users/js/g9
scp -r nba_data/odds_report_engine root@141.164.35.214:/opt/g9/

# VPS에서 설치
ssh root@141.164.35.214
cd /opt/g9/odds_report_engine
pip3 install -r requirements.txt  # requirements.txt 생성 필요

# 테스트 실행
python3 generate_graph_rag_reports.py
```

#### 5. 보고서 생성 크론 추가
```bash
# VPS 크론 편집
ssh root@141.164.35.214 'crontab -e'

# 추가할 내용 (매일 00:00 UTC = 09:00 KST)
# 0 0 * * * cd /opt/g9/odds_report_engine && python3 generate_graph_rag_reports.py >> /var/log/g9/nba_reports.log 2>&1
```

#### 6. 옛날 시스템 정리
```bash
# g9-flask-nba 컨테이너 중단 (또는 엔드포인트 통합)
ssh root@141.164.35.214
docker stop g9-flask-nba
# 또는
# g9-flask-nba에 /collect/boxscores 엔드포인트 추가하여 g9-nba-collector로 프록시
```

### 중기 조치 (1주일)

#### 7. 통합 모니터링 대시보드
- Grafana에 NBA 데이터 수집 메트릭 추가
- 알림 설정: 데이터 업데이트 중단 시 알림

#### 8. 자동화된 품질 검증
- VPS에 `/verify-report` 스킬 배포
- 보고서 생성 후 자동 검증 및 슬랙 알림

#### 9. 백업 및 복구 시스템
- Neo4J 일일 백업
- SQLite 백업
- 크론 로그 아카이빙

---

## 📊 시스템 건강 체크리스트

### 매일 확인 (자동화 권장)
- [ ] Neo4J 최신 데이터 날짜 = 어제
- [ ] SQLite raw_tweets 증가
- [ ] 크론 로그에 오류 없음
- [ ] 보고서 생성 성공

### 매주 확인
- [ ] API 사용량 (250/250 이하)
- [ ] Neo4J 디스크 사용량
- [ ] 컨테이너 헬스 체크
- [ ] 보고서 품질 점수 평균

### 매월 확인
- [ ] 데이터 무결성 감사
- [ ] 스키마 최적화
- [ ] 인덱스 성능 확인
- [ ] 비용 분석

---

## 🎯 결론 및 권장사항

### 현재 상태
- **데이터 인프라**: ✅ 양호 (Neo4J, SQLite 정상)
- **수집 파이프라인**: 🟡 부분 작동 (Realtime ✅, Boxscore ❌)
- **보고서 생성**: 🟡 로컬만 가능 (VPS 미배포)
- **자동화**: 🔴 미흡 (크론 설정 오류, VPS 미연동)

### 우선순위
1. **High**: 크론 스크립트 수정 (1시간)
2. **High**: 데이터 백필 (30분)
3. **Medium**: VPS 보고서 파이프라인 배포 (2시간)
4. **Medium**: 옛날 시스템 정리 (1시간)
5. **Low**: 모니터링 대시보드 (4시간)

### 최종 목표 아키텍처
```
크론 (00:00 UTC)
    ↓
g9-nba-collector (/collect/nba)
    ↓
Neo4J 업데이트 (PlayerStats, Game)
    ↓
보고서 생성 (VPS에서 자동)
    ↓
품질 검증 (/verify-report)
    ↓
슬랙 알림 → 사용자 승인 → 판매
```

---

**작성일**: 2025-12-30
**작성자**: Claude Sonnet 4.5
**검토 필요**: 크론 수정 후 24시간 모니터링
