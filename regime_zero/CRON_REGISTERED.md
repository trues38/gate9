# ✅ Cron Job 등록 완료!

**등록 일시:** 2025-12-30 21:12
**상태:** ACTIVE

---

## 📋 등록된 Cron Job

```cron
# G9 Daily Bulletin Generation
# Runs every day at 7:00 AM KST (after US market close)
0 7 * * * /Users/js/g9/regime_zero/run_daily_bulletin.sh >> /Users/js/g9/regime_zero/logs/cron.log 2>&1
```

**의미:**
- `0 7 * * *` = 매일 오전 7시 정각
- `/Users/js/g9/regime_zero/run_daily_bulletin.sh` = 실행할 스크립트
- `>> /Users/js/g9/regime_zero/logs/cron.log 2>&1` = 모든 출력을 로그 파일에 저장

---

## ⏰ 실행 스케줄

| 항목 | 값 |
|------|-----|
| **실행 시간** | 매일 오전 7:00 (KST) |
| **실행 주기** | 1일 1회 |
| **다음 실행** | 내일 오전 7:00 |
| **미국 시장 기준** | 전날 장 마감 후 (EST 17:00 = KST 다음날 07:00) |

**왜 오전 7시?**
- 미국 동부시간 17:00 (오후 5시) = 한국시간 다음날 07:00 (오전 7시)
- 미국 시장 마감 후 → 최종 데이터 확정 → 다음날 아침 한국에서 확인

---

## 🔍 확인 방법

### 1. Crontab 확인

```bash
crontab -l
```

### 2. 로그 모니터링

```bash
# 실시간 로그 보기
tail -f /Users/js/g9/regime_zero/logs/cron.log

# 최근 로그 확인
tail -50 /Users/js/g9/regime_zero/logs/cron.log
```

### 3. 생성된 Bulletin 확인

```bash
# 오늘자 Bulletin
cat /Users/js/g9/regime_zero/reports/bulletins/BULLETIN_$(date +%Y-%m-%d).md

# 모든 Bulletin 목록
ls -lt /Users/js/g9/regime_zero/reports/bulletins/
```

### 4. 히스토리 확인

```bash
cd /Users/js/g9/regime_zero
python3 engine/history_writer.py
```

---

## 🧪 테스트

### 수동 실행 테스트

```bash
# 지금 바로 실행해보기
/Users/js/g9/regime_zero/run_daily_bulletin.sh
```

**예상 결과:**
- `reports/bulletins/BULLETIN_2025-12-30.md` 생성
- `logs/bulletin_20251230_HHMMSS.log` 생성
- Console에 실행 로그 출력

---

## ⚠️ macOS 권한 설정 (중요!)

macOS에서 cron이 파일에 접근하려면 **Full Disk Access** 권한이 필요합니다.

### 권한 부여 방법

1. **시스템 설정 열기**
   - Apple 메뉴 > 시스템 설정 (System Settings)

2. **개인 정보 보호 및 보안으로 이동**
   - Privacy & Security

3. **Full Disk Access 선택**
   - 왼쪽 메뉴에서 "Full Disk Access" 클릭

4. **cron 추가**
   - 자물쇠 클릭해서 잠금 해제
   - `+` 버튼 클릭
   - `/usr/sbin/cron` 파일 찾아서 추가
   - 또는 `/usr/bin/crontab` 추가

5. **터미널 추가 (필요시)**
   - 같은 방법으로 사용 중인 터미널 앱 추가
   - Terminal.app 또는 iTerm.app

### 권한 확인

내일 아침 7시 이후에:

```bash
# 로그 확인
ls -l /Users/js/g9/regime_zero/logs/cron.log

# 내용 확인
cat /Users/js/g9/regime_zero/logs/cron.log
```

**권한이 없으면:**
- `cron.log` 파일이 없거나 비어있음
- Bulletin이 생성 안 됨

**권한이 있으면:**
- `cron.log`에 실행 로그 기록됨
- Bulletin 정상 생성

---

## 📊 예상 동작

### 내일 오전 7:00에 자동 실행:

```
[2025-12-31 07:00:00]
├─ Yahoo Finance에서 실시간 데이터 수집
├─ DVSS 4-Layer 검증 실행
├─ State 계산
├─ Bulletin 생성: reports/bulletins/BULLETIN_2025-12-31.md
├─ SQLite 히스토리 저장: data/pipeline_history.db
└─ 로그 저장: logs/bulletin_20251231_070000.log
```

### 한 달 후:

```
reports/bulletins/
├── BULLETIN_2025-12-31.md
├── BULLETIN_2026-01-01.md
├── BULLETIN_2026-01-02.md
├── ...
└── BULLETIN_2026-01-31.md

data/
└── pipeline_history.db (31일치 스냅샷)

logs/
├── bulletin_20251231_070000.log
├── bulletin_20260101_070000.log
├── ...
└── cron.log (종합 로그)
```

---

## 🔧 관리 명령어

### Cron 관리

```bash
# Crontab 보기
crontab -l

# Crontab 편집
crontab -e

# Crontab 삭제 (주의!)
crontab -r

# 특정 entry만 비활성화 (앞에 # 추가)
crontab -e
# 0 7 * * * /Users/js/g9/regime_zero/run_daily_bulletin.sh ...
```

### 로그 관리

```bash
# 로그 크기 확인
du -sh /Users/js/g9/regime_zero/logs/

# 오래된 로그 삭제 (30일 이상)
find /Users/js/g9/regime_zero/logs -name "bulletin_*.log" -mtime +30 -delete

# 로그 압축
gzip /Users/js/g9/regime_zero/logs/bulletin_*.log
```

---

## 🚨 문제 해결

### Cron이 실행 안 될 때

1. **권한 확인**
   ```bash
   ls -l /Users/js/g9/regime_zero/run_daily_bulletin.sh
   # -rwxr-xr-x (실행 권한 있어야 함)
   ```

2. **경로 확인**
   ```bash
   # 스크립트가 존재하는지
   ls /Users/js/g9/regime_zero/run_daily_bulletin.sh

   # Python 경로 확인
   head -15 /Users/js/g9/regime_zero/run_daily_bulletin.sh | grep PYTHON
   ```

3. **수동 실행 테스트**
   ```bash
   /Users/js/g9/regime_zero/run_daily_bulletin.sh
   # 에러 메시지 확인
   ```

4. **macOS Full Disk Access 확인**
   - 시스템 설정 > 개인 정보 보호 및 보안 > Full Disk Access
   - `/usr/sbin/cron` 추가되어 있는지 확인

### 로그가 비어있을 때

```bash
# Cron이 실행되고 있는지 확인
ps aux | grep cron

# 시스템 로그 확인
log show --predicate 'eventMessage contains "cron"' --last 1h
```

### Bulletin이 생성 안 될 때

1. **DVSS 점수 확인**
   - Total Score < 70 이면 publication 거부됨
   - 로그에서 DVSS 점수 확인

2. **Yahoo Finance 접근 확인**
   ```bash
   python3 -c "import yfinance as yf; print(yf.Ticker('^VIX').history(period='1d'))"
   ```

3. **인터넷 연결 확인**

4. **시장 휴일 확인** (주말, 공휴일)

---

## 📅 스케줄 변경 (Optional)

다른 시간에 실행하고 싶다면:

```bash
# Crontab 편집
crontab -e

# 예시:
# 매일 오후 6시
0 18 * * * /Users/js/g9/regime_zero/run_daily_bulletin.sh >> /Users/js/g9/regime_zero/logs/cron.log 2>&1

# 주중만 오전 7시
0 7 * * 1-5 /Users/js/g9/regime_zero/run_daily_bulletin.sh >> /Users/js/g9/regime_zero/logs/cron.log 2>&1

# 하루 2번 (오전 9시, 오후 6시)
0 9,18 * * * /Users/js/g9/regime_zero/run_daily_bulletin.sh >> /Users/js/g9/regime_zero/logs/cron.log 2>&1
```

---

## 📊 모니터링 체크리스트

### 매일 체크

- [ ] Bulletin 생성 확인: `ls reports/bulletins/BULLETIN_$(date +%Y-%m-%d).md`
- [ ] DVSS 점수 확인: `grep "DVSS Score" logs/cron.log | tail -1`

### 주간 체크

- [ ] 로그 크기 확인: `du -sh logs/`
- [ ] 히스토리 DB 확인: `python3 engine/history_writer.py`
- [ ] Bulletin 품질 검토

### 월간 체크

- [ ] 로그 정리 (30일 이상 삭제)
- [ ] Bulletin 아카이브
- [ ] DVSS 점수 트렌드 분석

---

## 🎯 성공 지표

✅ **정상 작동 시:**

```
매일 오전 7:00:
1. Cron 자동 실행
2. Yahoo Finance 데이터 수집
3. DVSS 검증 통과 (Score ≥ 70)
4. Bulletin 생성
5. 히스토리 저장
6. 로그 기록

→ 사용자는 매일 아침 새 Bulletin을 확인하면 됨!
```

---

## 📞 지원

### 빠른 확인

```bash
# Crontab 상태
crontab -l

# 마지막 실행 로그
tail -100 /Users/js/g9/regime_zero/logs/cron.log

# 최근 Bulletin
ls -lt /Users/js/g9/regime_zero/reports/bulletins/ | head -5
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

**🎉 Cron Job 등록 완료!**

**다음 실행:** 내일 오전 7:00

**현재 시각:** 2025-12-30 21:12

**카운트다운:** 약 10시간 후 첫 자동 실행!

---

*문서 버전: v1.0 (2025-12-30)*
*상태: ACTIVE & READY*
