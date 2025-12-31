# Claude Code 대화 자동 로깅 시스템

## 개요

Claude Code와의 모든 대화를 자동으로 일자별 로그 파일에 저장하는 시스템입니다.

**목적**:
- ✅ 대화 연속성 보장 (오류로 종료되어도 복구 가능)
- ✅ 일자별 대화 기록 유지
- ✅ 프로젝트 진행 상황 추적
- ✅ 컨텍스트 손실 방지

---

## 시스템 구성

### 1. Hook 스크립트

**위치**: `.claude/hooks/`

```
.claude/hooks/
├── user-prompt-submit-hook     # 사용자 메시지 로깅
└── message-response-hook        # Claude 응답 로깅
```

**동작 방식**:
- Claude Code가 메시지를 보내거나 받을 때마다 자동 실행
- JSONL 형식으로 로그 파일에 append
- 오류 발생 시에도 대화는 계속 진행 (hook 실패 허용)

### 2. 로그 파일

**위치**: `logs/`

**파일명**: `conversation_YYYY-MM-DD.jsonl`

**예시**:
```
logs/
├── conversation_2025-12-25.jsonl
├── conversation_2025-12-26.jsonl
└── conversation_2025-12-27.jsonl
```

**포맷**: JSONL (JSON Lines)
```json
{"timestamp": "2025-12-25T16:25:01.979900", "type": "user_prompt", "content": {...}}
{"timestamp": "2025-12-25T16:25:03.123456", "type": "assistant_response", "content": {...}}
```

### 3. 로그 뷰어

**파일**: `view_conversation_log.py`

대화 로그를 읽기 쉬운 형태로 표시하는 유틸리티

---

## 사용법

### 자동 로깅 (설정 필요 없음)

Hook이 설치되어 있으면 **자동으로 모든 대화가 로깅됩니다**.

Claude Code 세션 중:
```
User: NBA daily update 실행해줘
→ 자동 로깅: logs/conversation_2025-12-25.jsonl

Claude: 실행합니다...
→ 자동 로깅: logs/conversation_2025-12-25.jsonl
```

---

### 로그 보기

#### 오늘 대화 전체 보기
```bash
python3 view_conversation_log.py
```

#### 특정 날짜 로그 보기
```bash
python3 view_conversation_log.py 2025-12-25
```

#### 최근 N개 메시지만 보기
```bash
python3 view_conversation_log.py --last 10
```

#### 키워드 검색
```bash
python3 view_conversation_log.py --search "NBA"
python3 view_conversation_log.py --search "lineup"
```

#### 사용 가능한 로그 파일 목록
```bash
python3 view_conversation_log.py --list
```

**출력 예시**:
```
📂 사용 가능한 대화 로그:
============================================================
  2025-12-25   -   47개 메시지 (  12.3 KB)
  2025-12-24   -   32개 메시지 (   8.7 KB)
  2025-12-23   -   18개 메시지 (   5.2 KB)
============================================================
```

---

## 로그 파일 구조

### JSONL 포맷

한 줄에 하나의 JSON 객체:

```json
{"timestamp": "2025-12-25T16:25:01.979900", "type": "user_prompt", "content": {"message": "...", "session_id": "..."}}
{"timestamp": "2025-12-25T16:25:03.123456", "type": "assistant_response", "content": {"text": "...", "tool_uses": [...]}}
```

### 필드 설명

- **timestamp**: ISO 8601 형식 타임스탬프
- **type**: 메시지 타입
  - `user_prompt`: 사용자 메시지
  - `assistant_response`: Claude 응답
- **content**: 실제 메시지 내용 (JSON 객체)

---

## 고급 사용법

### 로그 분석 (Python)

```python
import json
from pathlib import Path

# 오늘 로그 읽기
log_file = Path("logs/conversation_2025-12-25.jsonl")

messages = []
with open(log_file, 'r') as f:
    for line in f:
        messages.append(json.loads(line))

# 사용자 메시지만 필터링
user_messages = [
    msg for msg in messages
    if msg['type'] == 'user_prompt'
]

print(f"총 {len(user_messages)}개 사용자 메시지")

# 특정 키워드 검색
nba_messages = [
    msg for msg in messages
    if 'NBA' in json.dumps(msg)
]
```

### 로그 백업

```bash
# 주간 백업
tar -czf logs_backup_$(date +%Y-%m-%d).tar.gz logs/

# 월별 아카이브
mkdir -p archives/2025-12/
mv logs/conversation_2025-12-*.jsonl archives/2025-12/
```

### 로그 검색 (grep)

```bash
# NBA 관련 대화 찾기
grep -i "nba" logs/conversation_2025-12-25.jsonl

# 특정 시간대 메시지
grep "16:25" logs/conversation_2025-12-25.jsonl

# 에러 메시지 찾기
grep -i "error" logs/*.jsonl
```

---

## Hook 비활성화

Hook을 일시적으로 비활성화하려면:

```bash
# Hook 실행 권한 제거
chmod -x .claude/hooks/*

# 다시 활성화
chmod +x .claude/hooks/*
```

또는 파일 이름 변경:

```bash
# 비활성화
mv .claude/hooks/user-prompt-submit-hook .claude/hooks/user-prompt-submit-hook.disabled

# 활성화
mv .claude/hooks/user-prompt-submit-hook.disabled .claude/hooks/user-prompt-submit-hook
```

---

## 로그 관리

### 자동 정리 (Cron)

오래된 로그 자동 삭제 (90일 이상):

```bash
# crontab -e
0 0 * * 0 find /Users/js/g9/nba_data/state_graph/logs -name "*.jsonl" -mtime +90 -delete
```

### 디스크 사용량 확인

```bash
# 로그 디렉토리 크기
du -sh logs/

# 파일별 크기
du -h logs/*.jsonl | sort -h
```

---

## 연속성 보장 예시

### 시나리오: 대화 중 오류 발생

**Before (로깅 없음)**:
```
User: NBA v2.0 시스템 설계해줘
Claude: [장문의 설계 문서 작성 중...]
→ 💥 오류 발생! Claude Code 종료
→ ❌ 모든 내용 손실
```

**After (로깅 활성화)**:
```
User: NBA v2.0 시스템 설계해줘
Claude: [장문의 설계 문서 작성 중...]
→ ✅ logs/conversation_2025-12-25.jsonl에 자동 저장
→ 💥 오류 발생! Claude Code 종료

# 복구
python3 view_conversation_log.py --last 5
→ ✅ 작성된 내용 모두 확인 가능
→ ✅ 컨텍스트 복구
```

---

## 트러블슈팅

### Hook이 작동하지 않을 때

**1. 실행 권한 확인**:
```bash
ls -l .claude/hooks/
# -rwxr-xr-x 여야 함 (x = 실행 가능)
```

**권한이 없으면**:
```bash
chmod +x .claude/hooks/*
```

**2. Python 경로 확인**:
```bash
which python3
# /usr/bin/python3 또는 유사 경로
```

**3. Hook 수동 테스트**:
```bash
echo '{"test": "message"}' | .claude/hooks/user-prompt-submit-hook
# [Hook] Logged user prompt to ... 출력 확인
```

### 로그 파일이 생성되지 않을 때

**logs/ 디렉토리 확인**:
```bash
ls -la logs/
# 디렉토리가 없으면
mkdir -p logs
```

**권한 확인**:
```bash
# 쓰기 권한 있는지 확인
touch logs/test.txt && rm logs/test.txt
```

---

## Git 관리

### .gitignore 설정

로그 파일은 개인 대화 기록이므로 Git에서 제외 권장:

```bash
# .gitignore에 추가
echo "logs/*.jsonl" >> .gitignore
```

**Hook 스크립트는 공유**:
```bash
git add .claude/hooks/
git commit -m "feat: Add conversation logging hooks"
```

---

## 참고

### Claude Code Hooks 문서

Hook에 대한 자세한 정보:
- Hook 종류: user-prompt-submit, message-response, tool-use, tool-result
- Hook 입력: JSON 형식 stdin
- Hook 출력: stdout (빈 출력 = 성공)

### 보안 고려사항

- ⚠️ 로그 파일에는 민감한 정보가 포함될 수 있음
- ⚠️ API 키, 비밀번호 등이 대화에 포함되지 않도록 주의
- ✅ 로그 파일을 Git에 커밋하지 말 것
- ✅ 백업 시 암호화 고려

---

## 요약

✅ **자동 설치 완료**: Hook이 이미 설치되어 있음
✅ **자동 로깅**: 모든 대화가 자동으로 `logs/` 디렉토리에 저장
✅ **일자별 파일**: `conversation_YYYY-MM-DD.jsonl` 형식
✅ **연속성 보장**: 오류 발생 시에도 복구 가능
✅ **검색/분석**: `view_conversation_log.py` 유틸리티 사용

**즉시 사용 가능**:
```bash
# 오늘 대화 보기
python3 view_conversation_log.py

# 로그 목록
python3 view_conversation_log.py --list
```
