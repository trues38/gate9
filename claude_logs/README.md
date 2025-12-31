# Claude Code 대화 로그 시스템

Claude Code 세션을 자동으로 로그에 저장하여 연속성을 보장합니다.

---

## 📁 파일 구조

```
/Users/js/g9/claude_logs/
├── README.md                          (이 파일)
├── save_conversation.py               (로그 저장 스크립트)
├── view_logs.py                       (로그 뷰어)
├── conversation_2025-12-25.jsonl      (일자별 이벤트 로그)
└── session_summary_2025-12-25.md      (일자별 세션 요약)
```

---

## 🚀 사용 방법

### 1. Claude Skill로 사용 (권장)

대화 중에 자동으로 로그 저장:

```
"이 작업을 로그에 저장해줘"
"지금까지 작업 내용을 기록해줘"
"세션 요약 저장해줘"
```

또는 명시적으로:

```
/conversation-logger
```

### 2. 로그 확인

**오늘의 로그 보기:**
```bash
python3 /Users/js/g9/claude_logs/view_logs.py
```

**세션 복원 정보:**
```bash
python3 /Users/js/g9/claude_logs/view_logs.py resume
```

**세션 요약 보기:**
```bash
python3 /Users/js/g9/claude_logs/view_logs.py summary
```

**로그 목록:**
```bash
python3 /Users/js/g9/claude_logs/view_logs.py list
```

### 3. 세션이 끊겼을 때

새 Claude Code 세션에서:

```
"오늘 로그를 읽고 이어서 작업해줘"
```

또는 수동으로:

```bash
# 최근 로그 확인
tail -20 /Users/js/g9/claude_logs/conversation_$(date +%Y-%m-%d).jsonl

# 요약 확인
cat /Users/js/g9/claude_logs/session_summary_$(date +%Y-%m-%d).md
```

---

## 📊 로그 형식

### JSONL 이벤트 로그

각 라인이 하나의 이벤트:

```jsonl
{"timestamp": "2025-12-25T16:00:00", "type": "milestone", "content": "...", "details": {...}}
{"timestamp": "2025-12-25T16:30:00", "type": "decision", "content": "...", "details": {...}}
{"timestamp": "2025-12-25T17:00:00", "type": "summary", "content": "...", "details": {...}}
```

**이벤트 타입:**
- `milestone`: 주요 작업 완료
- `decision`: 중요 결정 사항
- `error`: 오류 및 해결
- `summary`: 세션 요약

### Markdown 세션 요약

읽기 쉬운 형식:

```markdown
# 세션 요약: 2025-12-25

## 완료 작업
- [x] 작업 1
- [x] 작업 2

## 주요 결정
- 결정 1
- 결정 2

## 다음 단계
- [ ] 작업 3
- [ ] 작업 4
```

---

## 💡 활용 예시

### 예시 1: 장시간 작업 후

```bash
# 오늘 무엇을 했는지 확인
python3 view_logs.py

# 출력:
# 1. [12:00] 🎯 MILESTONE
#    Neo4j Graph DB 구축 완료
# 2. [14:30] 🤔 DECISION
#    섹터 상성 자동 계산 방식 채택
# ...
```

### 예시 2: 세션이 끊긴 후

```bash
# 이어서 작업하기
python3 view_logs.py resume

# 출력:
# 세션 복원: 최근 작업
# ========================
# [16:30] MILESTONE
#   섹터 상성 31개 자동 생성 완료
#
# 다음 작업 단계:
# 1. Unclassified 레짐 재분류
# 2. 실시간 API 개발
```

### 예시 3: 과거 작업 회고

```bash
# 모든 로그 확인
python3 view_logs.py list

# 출력:
# 사용 가능한 로그 파일:
# 2025-12-25  📄  9개 이벤트  conversation_2025-12-25.jsonl
# 2025-12-24  📄  5개 이벤트  conversation_2025-12-24.jsonl
```

---

## 🔧 고급 사용법

### Python에서 직접 사용

```python
import json
from datetime import datetime
from pathlib import Path

# 로그 읽기
log_file = Path(f"/Users/js/g9/claude_logs/conversation_{datetime.now().strftime('%Y-%m-%d')}.jsonl")

with open(log_file, "r") as f:
    entries = [json.loads(line) for line in f]

# 특정 타입만 필터
milestones = [e for e in entries if e['type'] == 'milestone']
decisions = [e for e in entries if e['type'] == 'decision']

print(f"오늘의 마일스톤: {len(milestones)}개")
print(f"오늘의 결정: {len(decisions)}개")
```

### 로그 검색

```bash
# 특정 키워드 검색
grep -i "neo4j" /Users/js/g9/claude_logs/conversation_*.jsonl

# 최근 7일 로그에서 "milestone" 검색
find /Users/js/g9/claude_logs -name "conversation_*.jsonl" -mtime -7 -exec grep -l "milestone" {} \;
```

---

## 📝 자동화 팁

### Cron으로 일일 요약 생성

```bash
# crontab -e
0 23 * * * python3 /Users/js/g9/claude_logs/generate_daily_summary.py
```

### Git으로 버전 관리

```bash
cd /Users/js/g9/claude_logs
git init
git add *.jsonl *.md
git commit -m "Daily log backup"
```

---

## 🛡️ 주의사항

**저장되지 않는 것:**
- 비밀번호, API 키
- 민감한 개인정보
- 전체 대화 (주요 이벤트만)

**저장되는 것:**
- 주요 작업 완료 내역
- 중요 결정 사항
- 생성된 파일 경로
- 시스템 통계

---

## 🆘 문제 해결

### Q: 로그 파일이 생성되지 않아요

**A:** Claude Skill이 호출되었는지 확인:
```
"로그 저장해줘"  (명시적 요청 필요)
```

### Q: 오래된 로그를 삭제하고 싶어요

**A:**
```bash
# 30일 이전 로그 삭제
find /Users/js/g9/claude_logs -name "conversation_*.jsonl" -mtime +30 -delete
find /Users/js/g9/claude_logs -name "session_summary_*.md" -mtime +30 -delete
```

### Q: 로그가 너무 커져요

**A:** JSONL은 압축 효율이 좋습니다:
```bash
# 압축
gzip /Users/js/g9/claude_logs/conversation_2025-12-*.jsonl

# 읽기
zcat /Users/js/g9/claude_logs/conversation_2025-12-25.jsonl.gz | tail -20
```

---

## 📚 관련 문서

- **Claude Skill:** `~/.claude/skills/conversation-logger/SKILL.md`
- **경제 레짐 스킬:** `~/.claude/skills/economic-regime-analyst/SKILL.md`

---

**최종 업데이트:** 2025-12-25
**작성자:** Claude Code Session Logger
