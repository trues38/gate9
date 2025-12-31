# 대화 로깅 시스템 설치 완료 ✅

## 즉시 사용 가능!

모든 Claude Code 대화가 **자동으로 로그에 저장됩니다**.

---

## 시스템 구성

### 1. 자동 Hook (설치 완료)

```
.claude/hooks/
├── user-prompt-submit-hook      ✅ 사용자 메시지 자동 로깅
└── message-response-hook         ✅ Claude 응답 자동 로깅
```

**동작 방식**:
- 메시지를 보내거나 받을 때마다 **자동 실행**
- 오류 발생 시에도 대화는 계속 진행

---

### 2. 로그 파일 (자동 생성)

```
logs/
└── conversation_YYYY-MM-DD.jsonl  # 일자별 자동 생성
```

**예시**:
```
logs/conversation_2025-12-25.jsonl
logs/conversation_2025-12-26.jsonl
logs/conversation_2025-12-27.jsonl
```

---

### 3. 로그 뷰어 (설치 완료)

**파일**: `view_conversation_log.py`

---

## 사용법 (간단!)

### 오늘 대화 보기
```bash
python3 view_conversation_log.py
```

### 특정 날짜 보기
```bash
python3 view_conversation_log.py 2025-12-25
```

### 최근 10개 메시지만
```bash
python3 view_conversation_log.py --last 10
```

### 검색
```bash
python3 view_conversation_log.py --search "NBA"
```

### 로그 목록
```bash
python3 view_conversation_log.py --list
```

---

## 연속성 보장 예시

### 시나리오: 오류로 대화 종료

**Before (로깅 없음)**:
```
User: v2.0 시스템 설계해줘
Claude: [작성 중...]
💥 오류! 모든 내용 손실 ❌
```

**After (로깅 있음)**:
```
User: v2.0 시스템 설계해줘
Claude: [작성 중...]
✅ logs/conversation_2025-12-25.jsonl에 저장
💥 오류 발생!

# 복구
python3 view_conversation_log.py --last 5
→ ✅ 모든 내용 확인 가능!
→ ✅ 컨텍스트 복구 완료
```

---

## 실제 테스트

### Hook 작동 확인
```bash
echo '{"test": "hello"}' | .claude/hooks/user-prompt-submit-hook
# [Hook] Logged user prompt to ... ← 성공 메시지
```

### 로그 파일 확인
```bash
cat logs/conversation_2025-12-25.jsonl
# JSON 형식 로그 출력
```

### 로그 뷰어 테스트
```bash
python3 view_conversation_log.py --list
```

**출력**:
```
📂 사용 가능한 대화 로그:
============================================================
  2025-12-25   -    1개 메시지 (   0.1 KB)
============================================================
```

---

## 자동으로 저장되는 내용

✅ **사용자 메시지**: 모든 질문과 명령
✅ **Claude 응답**: 모든 답변과 설명
✅ **타임스탬프**: 정확한 시간 기록
✅ **메시지 순서**: 대화 흐름 완벽 재현

---

## Git 관리

### Hook은 공유 (팀원도 사용)
```bash
git add .claude/hooks/
git commit -m "feat: Add conversation logging"
```

### 로그는 개인 보관 (Git 제외)
```bash
# .gitignore에 이미 추가됨
logs/*.jsonl
```

---

## 장점

### 1️⃣ 연속성 보장
- ✅ 대화 중 오류 발생해도 복구 가능
- ✅ 컨텍스트 손실 방지
- ✅ 진행 상황 추적

### 2️⃣ 프로젝트 기록
- ✅ 일자별 작업 내용 확인
- ✅ 의사결정 과정 추적
- ✅ 지식 누적

### 3️⃣ 디버깅
- ✅ 오류 발생 시점 파악
- ✅ 문제 재현 가능
- ✅ 원인 분석 용이

### 4️⃣ 검색/분석
- ✅ 키워드 검색
- ✅ JSON 형식으로 프로그래밍 분석 가능
- ✅ 통계 생성

---

## 디스크 사용량

**예상 크기**:
- 1개 메시지: ~0.1-0.5 KB
- 하루 50개 메시지: ~10-20 KB
- 1개월: ~300-600 KB
- 1년: ~4-7 MB

→ **무시할 수준의 용량**

---

## 보안

### ✅ 안전한 점
- 로컬에만 저장 (외부 전송 없음)
- Git에 커밋되지 않음 (.gitignore)
- 파일 권한으로 보호

### ⚠️ 주의사항
- API 키나 비밀번호를 대화에 포함하지 말 것
- 민감한 정보는 로그에 남음
- 필요 시 로그 파일 암호화 고려

---

## 추가 기능 (선택)

### 자동 백업 (Cron)

```bash
# 매주 일요일 백업
crontab -e

# 추가:
0 0 * * 0 tar -czf ~/backups/nba_logs_$(date +\%Y-\%m-\%d).tar.gz /Users/js/g9/nba_data/state_graph/logs/
```

### 오래된 로그 자동 삭제

```bash
# 90일 이상 된 로그 삭제 (매주)
0 0 * * 0 find /Users/js/g9/nba_data/state_graph/logs -name "*.jsonl" -mtime +90 -delete
```

---

## 문제 해결

### Hook이 작동하지 않을 때

**1. 실행 권한 확인**:
```bash
ls -l .claude/hooks/
# -rwxr-xr-x 여야 함

# 권한 없으면:
chmod +x .claude/hooks/*
```

**2. 수동 테스트**:
```bash
echo '{"test": "message"}' | .claude/hooks/user-prompt-submit-hook
# 성공 메시지 확인
```

**3. logs/ 디렉토리 확인**:
```bash
ls -la logs/
# 없으면 생성
mkdir -p logs
```

---

## 요약

✅ **설치 완료**: Hook이 자동으로 작동
✅ **자동 로깅**: 모든 대화 자동 저장
✅ **일자별 파일**: `logs/conversation_YYYY-MM-DD.jsonl`
✅ **즉시 사용 가능**: 추가 설정 불필요

**지금부터 모든 대화가 자동으로 로그에 저장됩니다!**

---

## 빠른 참조

```bash
# 오늘 대화 보기
python3 view_conversation_log.py

# 로그 목록
python3 view_conversation_log.py --list

# 최근 10개
python3 view_conversation_log.py --last 10

# 검색
python3 view_conversation_log.py --search "NBA"

# 특정 날짜
python3 view_conversation_log.py 2025-12-25
```

---

**상세 문서**: `CONVERSATION_LOGGING.md`
