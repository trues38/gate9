# 일일 자동화 설정 가이드 (Daily Automation Setup)

## 개요 (Overview)

정량 데이터 수집을 완전히 자동화합니다. 매일 정해진 시간에 모든 데이터가 자동으로 수집되고 업데이트됩니다.

## 자동화 파이프라인 (Pipeline)

매일 실행되는 작업:

1. **BoxScores 수집** (`crawl_current_season_boxscores.py`)
   - 어제의 모든 경기 결과
   - 선수별 개별 통계

2. **PlayerRecentForm** (`generate_player_recent_form.py`)
   - 각 선수의 최근 3시즌 성적
   - 자동 롤링 계산

3. **RefereeStats** (`generate_referee_stats.py`)
   - 심판이 담당한 경기 통계
   - 자동 업데이트

4. **TeamStrength** (`calculate_team_strength.py`)
   - 팀 강도 재계산
   - 최신 데이터 기반

5. **CoachStats** (`calculate_coach_stats.py`)
   - 감독 통계 업데이트
   - 자동 반영

## 설정 방법 (Setup Instructions)

### 옵션 1: Cron Job (Linux/Mac)

```bash
# crontab 편집
crontab -e

# 매일 KST 18:00 (UTC 09:00) 실행
0 9 * * * cd /Users/js/g9/nba_data && /Users/js/g9/.venv/bin/python3 state_graph/daily_automation.py
```

### 옵션 2: N8N 워크플로우

N8N에서 Schedule 트리거로 설정:
- 매일 09:00 UTC 실행
- 모든 스크립트 순차 실행
- 실패 시 자동 재시도

### 옵션 3: systemd Timer (Linux)

```bash
# /etc/systemd/system/nba-automation.service
[Unit]
Description=NBA Data Automation Pipeline
After=network.target

[Service]
Type=oneshot
User=js
WorkingDirectory=/Users/js/g9/nba_data
ExecStart=/Users/js/g9/.venv/bin/python3 state_graph/daily_automation.py
Environment="PATH=/Users/js/g9/.venv/bin:/usr/local/bin:/usr/bin"

# /etc/systemd/system/nba-automation.timer
[Unit]
Description=NBA Data Automation Schedule

[Timer]
OnCalendar=*-*-* 09:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

## 로그 확인 (Log Monitoring)

```bash
# 자동화 로그 디렉토리
ls -la state_graph/.automation_logs/

# 오늘 로그 확인
tail -f state_graph/.automation_logs/automation_2025-12-26.log

# 결과 확인
cat state_graph/.automation_logs/result_2025-12-26.json
```

## 데이터 검증 (Data Validation)

매일 자동으로 생성되는 데이터:

```
PlayerRecentForm: 458명 × 3시즌 = 1,374개 노드
RefereeStats: 79명 = 79개 노드
TeamStrength: 30개팀 = 30개 노드
CoachStats: ~60명 = ~60개 노드
```

## 네오포4j 백업 (Neo4j Backup)

자동화 완료 후 자동 백업:

```bash
# 백업 폴더 설정
mkdir -p state_graph/backups

# 일일 백업 스크립트
# (daily_automation.py에 추가 가능)
```

## 환경 변수 (Environment Variables)

```bash
# .env 파일
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
```

## 의존성 (Dependencies)

- Python 3.8+
- neo4j library
- requests library

## 자동화 비활성화 (Disable Automation)

필요 시 cron 비활성화:

```bash
# 특정 작업만 주석 처리
crontab -e
```

## 모니터링 (Monitoring)

- 매일 09:00 UTC 자동 실행
- 로그 파일에 모든 실행 기록 저장
- 실패 시 상세 오류 메시지 기록
- JSON 결과 파일로 자동화 상태 추적

---

**마지막 업데이트:** 2025-12-26
**상태:** 자동화 파이프라인 완성
