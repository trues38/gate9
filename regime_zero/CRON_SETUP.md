# G9 Daily Bulletin - Cron Job 설정 가이드

**자동화된 일일 보고서 생성**

---

## 📋 개요

매일 정해진 시간에 자동으로:
1. Yahoo Finance에서 실시간 데이터 수집
2. DVSS 4-Layer 검증 실행
3. State 계산
4. Bulletin 생성
5. SQLite 히스토리 저장

---

## ⏰ 권장 실행 시간

### 미국 시장 기준

| 시간대 | 시간 | 이유 |
|--------|------|------|
| **미국 동부 (EST)** | 17:00 | 시장 마감 후 |
| **한국 (KST)** | 오전 7:00 | 다음 날 아침 |
| **UTC** | 22:00 | 표준시 |

**권장:** 미국 동부시간 17:00 (장 마감 후 데이터 확정)

---

## 🛠️ Cron 설정 방법

### 1. Crontab 편집

```bash
crontab -e
```

### 2. Cron 표현식 추가

**한국시간 오전 7시 (미국 동부 17:00) - 매일 실행:**

```cron
# G9 Daily Bulletin Generation
# 매일 오전 7시 (KST) = 미국 동부 17:00 (전날)
0 7 * * * /Users/js/g9/regime_zero/run_daily_bulletin.sh >> /Users/js/g9/regime_zero/logs/cron.log 2>&1
```

**미국 동부시간 17:00 직접 설정:**

```cron
# G9 Daily Bulletin Generation (EST 17:00)
# Timezone: America/New_York
TZ=America/New_York
0 17 * * * /Users/js/g9/regime_zero/run_daily_bulletin.sh >> /Users/js/g9/regime_zero/logs/cron.log 2>&1
```

**주중만 실행 (월-금):**

```cron
# G9 Daily Bulletin Generation (Weekdays only)
0 7 * * 1-5 /Users/js/g9/regime_zero/run_daily_bulletin.sh >> /Users/js/g9/regime_zero/logs/cron.log 2>&1
```

### 3. Cron 시간대 설명

```
분 시 일 월 요일 명령어
│  │  │  │  │
│  │  │  │  └─── 요일 (0-7, 0=일요일, 7=일요일)
│  │  │  └────── 월 (1-12)
│  │  └───────── 일 (1-31)
│  └──────────── 시 (0-23)
└─────────────── 분 (0-59)
```

**예제:**
- `0 7 * * *` = 매일 오전 7시
- `0 17 * * 1-5` = 주중 오후 5시
- `30 9,18 * * *` = 매일 오전 9:30, 오후 6:30

---

## 🧪 테스트

### 수동 실행 테스트

```bash
cd /Users/js/g9/regime_zero
./run_daily_bulletin.sh
```

**예상 출력:**
```
================================================
G9 Daily Bulletin Generation
Date: 2025-12-30
Time: Mon Dec 30 21:00:00 KST 2025
================================================

✅ Environment loaded

Running pipeline...

=================================================================
  UNIFIED PIPELINE v1.0
  Date: 2025-12-30
=================================================================

[STEP 1] Running DVSS Validation...
...

================================================
✅ SUCCESS - Bulletin generated
   File: /Users/js/g9/regime_zero/reports/bulletins/BULLETIN_2025-12-30.md
   Size: 1.4K

History status:
📊 SQLite History Database Stats
==================================================
Total snapshots: 2
Latest: 2025-12-30 at 2025-12-30 21:00:00
  DVSS: 83/100 (Grade B)
Date range: 2025-12-30 → 2025-12-30
================================================
```

### Cron 설정 확인

```bash
# 현재 crontab 확인
crontab -l

# Cron 서비스 상태 확인 (macOS)
sudo launchctl list | grep cron
```

---

## 📁 생성되는 파일

### 1. Bulletin 파일

**위치:** `reports/bulletins/BULLETIN_YYYY-MM-DD.md`

**예시:**
```
reports/bulletins/
├── BULLETIN_2025-12-30.md
├── BULLETIN_2025-12-31.md
└── BULLETIN_2026-01-01.md
```

### 2. 로그 파일

**위치:** `logs/bulletin_YYYYMMDD_HHMMSS.log`

**예시:**
```
logs/
├── bulletin_20251230_070001.log
├── bulletin_20251231_070001.log
└── cron.log
```

**자동 정리:** 30일 이상 된 로그는 자동 삭제

### 3. 히스토리 데이터베이스

**위치:** `data/pipeline_history.db`

**내용:**
- 일일 DVSS 점수
- 시장 데이터 스냅샷
- State 계산 결과

---

## 🔍 모니터링

### 최근 실행 확인

```bash
# 최근 로그 보기
tail -100 /Users/js/g9/regime_zero/logs/cron.log

# 오늘 생성된 Bulletin 확인
cat /Users/js/g9/regime_zero/reports/bulletins/BULLETIN_$(date +%Y-%m-%d).md

# 히스토리 확인
cd /Users/js/g9/regime_zero
python3 engine/history_writer.py
```

### 에러 확인

```bash
# Cron 로그에서 에러 찾기
grep -i "error\|failed\|❌" /Users/js/g9/regime_zero/logs/cron.log

# 최근 실행 로그 확인
ls -lt /Users/js/g9/regime_zero/logs/bulletin_*.log | head -5
```

---

## 🚨 문제 해결

### Cron이 실행 안 될 때

1. **권한 확인:**
   ```bash
   chmod +x /Users/js/g9/regime_zero/run_daily_bulletin.sh
   ls -l /Users/js/g9/regime_zero/run_daily_bulletin.sh
   ```

2. **경로 확인:**
   ```bash
   # 절대 경로 사용
   which python3
   # /usr/local/bin/python3 또는 /opt/homebrew/bin/python3
   ```

3. **로그 확인:**
   ```bash
   tail -50 /Users/js/g9/regime_zero/logs/cron.log
   ```

### Bulletin이 이상할 때

1. **DVSS 점수 확인:**
   - Total Score < 70 → 데이터 품질 문제
   - L1 < 80 → 핵심 데이터 누락

2. **수동 실행 테스트:**
   ```bash
   cd /Users/js/g9/regime_zero
   python3 engine/generate_bulletin.py --date $(date +%Y-%m-%d)
   ```

3. **Yahoo Finance 접근 확인:**
   ```python
   import yfinance as yf
   vix = yf.Ticker("^VIX")
   print(vix.history(period="1d"))
   ```

### 주말/휴일 처리

- 시장이 닫혀있으면 데이터가 없을 수 있음
- DVSS L1 Completeness가 낮게 나옴
- 정상 동작: 최근 거래일 데이터 사용

---

## 📊 알림 설정 (Optional)

### 슬랙 알림 추가

```bash
# run_daily_bulletin.sh 끝에 추가
if [ ${EXIT_CODE} -eq 0 ]; then
    curl -X POST -H 'Content-type: application/json' \
    --data "{\"text\":\"✅ G9 Bulletin Generated: ${TODAY}\"}" \
    YOUR_SLACK_WEBHOOK_URL
else
    curl -X POST -H 'Content-type: application/json' \
    --data "{\"text\":\"❌ G9 Bulletin FAILED: ${TODAY}\"}" \
    YOUR_SLACK_WEBHOOK_URL
fi
```

### 이메일 알림 (macOS)

```bash
# run_daily_bulletin.sh 끝에 추가
if [ ${EXIT_CODE} -ne 0 ]; then
    echo "G9 Bulletin generation failed on ${TODAY}" | \
    mail -s "G9 Alert: Bulletin Failed" your-email@example.com
fi
```

---

## 🔄 업그레이드 전략

### Phase 1: 기본 자동화 ✅ (현재)
- [x] Cron으로 일일 실행
- [x] 로그 저장
- [x] 히스토리 누적

### Phase 2: 모니터링 (다음)
- [ ] Slack/이메일 알림
- [ ] 대시보드 연동
- [ ] 품질 트렌드 분석

### Phase 3: 고도화 (향후)
- [ ] 실시간 업데이트 (WebSocket)
- [ ] Multi-timezone 지원
- [ ] 자동 배포 (Vercel, etc.)

---

## 📋 체크리스트

### 초기 설정

- [ ] `run_daily_bulletin.sh` 실행 권한 부여
- [ ] 수동 실행 테스트 성공
- [ ] Crontab에 작업 추가
- [ ] 로그 디렉토리 확인
- [ ] 첫 자동 실행 모니터링

### 일일 점검

- [ ] Bulletin 생성 확인
- [ ] DVSS 점수 확인 (≥70)
- [ ] 히스토리 저장 확인
- [ ] 로그 에러 확인

### 주간 점검

- [ ] 로그 파일 크기 확인
- [ ] 히스토리 DB 크기 확인
- [ ] Bulletin 품질 검토
- [ ] 데이터 트렌드 분석

---

## 🎯 예상 결과

### 정상 실행 시

```
매일 오전 7시:
1. ✅ Yahoo Finance 데이터 수집
2. ✅ DVSS 검증 (Score: 70-100)
3. ✅ State 계산 완료
4. ✅ Bulletin 생성: reports/bulletins/BULLETIN_YYYY-MM-DD.md
5. ✅ SQLite 히스토리 저장
6. ✅ 로그 저장: logs/bulletin_YYYYMMDD_070000.log
```

### 한 달 후

```
reports/bulletins/
├── BULLETIN_2025-12-01.md
├── BULLETIN_2025-12-02.md
├── ...
└── BULLETIN_2025-12-31.md  (31개 파일)

data/
└── pipeline_history.db  (31일치 스냅샷)

logs/
├── bulletin_20251201_070001.log
├── bulletin_20251202_070001.log
├── ...
└── bulletin_20251231_070001.log
```

---

## 📞 지원

### 로그 확인

```bash
# 실시간 로그 모니터링
tail -f /Users/js/g9/regime_zero/logs/cron.log

# 최근 실행 결과
ls -lt /Users/js/g9/regime_zero/reports/bulletins/ | head -10
```

### 긴급 중단

```bash
# Cron 비활성화
crontab -e
# 해당 라인 주석 처리: #0 7 * * * ...

# 또는 완전 삭제
crontab -r
```

---

**설정 완료 후 24시간 이내 첫 Bulletin이 자동 생성됩니다!**

*문서 버전: v1.0 (2025-12-30)*
