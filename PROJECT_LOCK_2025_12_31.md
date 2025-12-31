# G9 Project Lock - 2025-12-31

> **Status**: LOCKED (재개 예정: 2025-01-02~03)
> **Last Updated**: 2025-12-31 12:30 KST

---

## 1. 프로젝트 개요

G9는 **Graph RAG 기반 투자 분석 시스템**으로, 3개 도메인을 운영:

```
┌─────────────────────────────────────────────────────────────┐
│                         G9 SYSTEM                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   ECONOMY   │  │     NBA     │  │   SOCCER    │         │
│  │  매크로경제  │  │  농구베팅   │  │  축구베팅   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│         │                │                │                 │
│         ▼                ▼                ▼                 │
│  ┌─────────────────────────────────────────────────┐       │
│  │              Neo4j Graph Database               │       │
│  │         (VPS: 141.164.35.214)                   │       │
│  └─────────────────────────────────────────────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 도메인별 상태

### 2.1 ECONOMY (매크로 경제)

| 항목 | 상태 | 설명 |
|------|------|------|
| Daily Collect | ✅ 활성 | Systemd Timer: 23:30 UTC |
| X Search Weekly | ✅ 활성 | Systemd Timer: 일요일 03:30 UTC |
| Neo4j | ✅ 운영중 | Port 7688 |
| Graph RAG Layer | ✅ 완료 | X tone 주간 데이터 읽기 방식 |
| Bulletin Generator | ⏸️ 수동 | 자동화 대기 |

**주요 파일**:
- `/opt/g9/domains/economy/` - VPS 경제 도메인
- `regime_zero/engine/graph_rag_layer.py` - Graph RAG 엔진
- `regime_zero/engine/state_graph/` - State Machine 엔진

**데이터 소스**:
- X Search (RapidAPI) → Neo4j ExpertWeekly/AsiaWeekly
- 시장 데이터 API → SQLite → Neo4j

---

### 2.2 NBA (농구 베팅)

| 항목 | 상태 | 설명 |
|------|------|------|
| Realtime Collection | ✅ 활성 | Systemd Timer: 30분마다 |
| Boxscore Collection | ✅ 활성 | Systemd Timer: 00:00 UTC |
| Twitter/X API | ✅ 작동 | **RapidAPI** (RSS 제거됨) |
| Neo4j | ✅ 운영중 | Port 7687 |
| Flask API | ✅ 운영중 | Port 8000 |

**주요 파일**:
- `/opt/g9/flask-nba/app.py` - **RapidAPI Only** (오늘 수정)
- `/opt/g9/nba-collector/` - 수집기 코드
- `/opt/g9/cron/nba_*.sh` - Cron 스크립트 (Systemd로 대체됨)

**데이터 소스**:
- RapidAPI Twitter API45 (월 1000콜 무료)
- ESPN API (스케줄, 박스스코어)
- The Odds API (배당률)

**최근 수정 (2025-12-31)**:
- Nitter RSS 완전 제거
- RapidAPI Twitter 전환 완료
- 20개 트윗 수집 성공 확인

---

### 2.3 SOCCER (축구 베팅)

| 항목 | 상태 | 설명 |
|------|------|------|
| Daily Collection | ✅ 활성 | Systemd Timer: 08:00 UTC |
| xG Weekly | ✅ 활성 | Systemd Timer: 일요일 00:00 UTC |
| Understat xG | ✅ 완료 | Selenium 기반 |
| Graph RAG | ✅ 완료 | 5대 리그 분석 |

**주요 파일**:
- `/opt/g9/domains/soccer/` - VPS 축구 도메인
- `soccer_data/collectors/understat_selenium_collector.py`
- `soccer_data/analysis/graph_rag_report_generator.py`

**데이터 소스**:
- Understat (xG 데이터)
- Football-Data.co.uk (역대 배당률)
- Neo4j (Graph RAG)

---

## 3. 인프라 현황

### 3.1 VPS (141.164.35.214)

```
┌─────────────────────────────────────────────┐
│  Vultr VPS - Seoul                          │
│  IP: 141.164.35.214                         │
├─────────────────────────────────────────────┤
│                                             │
│  Docker Containers:                         │
│  ├─ g9-neo4j-nba     (7474, 7687) ✅       │
│  ├─ g9-flask-nba     (8000)       ✅       │
│  ├─ g9-nba-collector (8001)       ✅       │
│  └─ g9-neo4j-econ    (7475, 7688) ✅       │
│                                             │
│  Systemd Timers (Cron 대체):                │
│  ├─ g9-nba-realtime    (30분마다)  ✅      │
│  ├─ g9-nba-boxscore    (매일 00:00) ✅     │
│  ├─ g9-soccer-daily    (매일 08:00) ✅     │
│  ├─ g9-soccer-xg       (일 00:00)   ✅     │
│  ├─ g9-economy-daily   (매일 23:30) ✅     │
│  └─ g9-xsearch-weekly  (일 03:30)   ✅     │
│                                             │
└─────────────────────────────────────────────┘
```

### 3.2 API Keys

| API | 용도 | 상태 |
|-----|------|------|
| RAPIDAPI_KEY | Twitter/X 수집 | ✅ SET |
| ODDS_API_KEY | 배당률 | ✅ SET |
| XAI_API_KEY | Grok LLM | ✅ SET |
| OPENROUTER_API_KEY | Claude/GPT | ✅ SET |

---

## 4. 디렉토리 구조

```
/Users/js/g9/
├── regime_zero/          # 경제 분석 엔진
│   ├── engine/
│   │   ├── graph_rag_layer.py    # ⭐ Graph RAG (X tone 읽기)
│   │   ├── unified_pipeline.py
│   │   └── state_graph/          # State Machine
│   └── btc_macro/                # BTC 분석 (archived)
│
├── nba_data/             # NBA 로컬 데이터
├── soccer_data/          # 축구 로컬 데이터
│   ├── collectors/
│   ├── analysis/
│   └── raw_data/understat/
│
├── vultr-g9-deploy/      # VPS 배포 코드
│   └── domains/
│       ├── economy/
│       ├── nba/
│       └── soccer/
│
├── scheduler/            # 스케줄러 (텔레그램 알림)
├── g9-landing/           # 랜딩 페이지 (Next.js)
└── reports/              # 생성된 리포트
```

---

## 5. 재개 시 체크리스트

### Day 1 체크 (5분)

```bash
# 1. VPS 연결 확인
ssh root@141.164.35.214

# 2. Systemd Timer 상태
systemctl list-timers | grep g9

# 3. Docker 컨테이너 상태
docker ps

# 4. 최근 로그 확인
journalctl -u g9-nba-realtime --since "1 hour ago"
journalctl -u g9-economy-daily --since "1 day ago"
```

### 문제 발생 시

```bash
# Timer 재시작
systemctl restart g9-nba-realtime.timer

# 컨테이너 재시작
docker restart g9-flask-nba

# 전체 로그
journalctl -u g9-* --since today
```

---

## 6. 다음 할 일 (재개 후)

### Priority 1 (필수)
- [ ] Economy Bulletin 자동화 활성화
- [ ] 텔레그램 알림 연동 완료

### Priority 2 (개선)
- [ ] Landing Page 배포
- [ ] 리포트 품질 검증

### Priority 3 (확장)
- [ ] BTC/Crypto 도메인 재활성화
- [ ] 추가 스포츠 (MLB, NFL)

---

## 7. 백업 정보

| 항목 | 위치 | 날짜 |
|------|------|------|
| Git Tag | `v1.2-lock-2025-12-31` | 2025-12-31 |
| VPS Crontab | `/root/crontab_backup_*.txt` | 2025-12-31 |
| Systemd Files | `/etc/systemd/system/g9-*.{service,timer}` | 2025-12-31 |

---

## 8. 연락처 & 참고

- **VPS**: Vultr Seoul (141.164.35.214)
- **Git**: https://github.com/trues38/gate9
- **Neo4j Browser**: http://141.164.35.214:7474 (NBA), :7475 (Economy)

---

*Last locked by Claude Code - 2025-12-31 12:30 KST*
