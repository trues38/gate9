# 🏀 NBA/축구 베팅 보고서 자동 생성 시스템

**Graph RAG + Claude Code + 품질 검증 = 1시간에 15개 보고서**

---

## 🎯 시작하기 (3단계)

### 1️⃣ 빠른 시작 (1분)
**→ [CHEATSHEET.md](CHEATSHEET.md)** ← 지금 바로 시작!

### 2️⃣ 일일 워크플로우 (필수)
**→ [DAILY_WORKFLOW.md](DAILY_WORKFLOW.md)** ← 오늘 밤 00:00 실전 투입

### 3️⃣ 검증 스킬
**→ [verify-report 스킬](../../.claude/skills/verify-report/README.md)** ← 품질 보증

---

## 📊 시스템 개요

### 워크플로우
```
Neo4j (3,209 경기)
    ↓
Claude Code (Graph RAG)
    ↓
보고서 생성 (Opus 4.5 스타일)
    ↓
검증 스킬 (ESPN API)
    ↓
당신의 최종 승인
    ↓
판매!
```

### 일일 산출물
- **NBA**: 5개 보고서 (30분)
- **축구**: 10개 보고서 (30분)  
- **품질**: 평균 90점/100
- **비용**: $0 (Claude Code 사용)

---

## ⚡ 바로 시작

```bash
# 1. 터미널 열기
cd /Users/js/g9
claude

# 2. 보고서 생성
> "오늘 NBA 주요 5경기 Graph RAG 분석해줘, Opus 4.5 스타일로"

# 3. 검증
> /verify-report nba_data/odds_reports/graphrag_*.md

# 4. 점수 확인 → 판매
90+ ✅ 즉시 판매
80-89 ⚡ 확인 후 판매
```

---

## 📁 주요 파일

### 🚀 사용자 가이드
- **[CHEATSHEET.md](CHEATSHEET.md)** - 1분 빠른 시작
- **[DAILY_WORKFLOW.md](DAILY_WORKFLOW.md)** - 일일 루틴 상세 가이드
- **[verify-report 스킬](../../.claude/skills/verify-report/README.md)** - 검증 사용법

### 🧠 기술 문서
- **[GRAPH_RAG_STRATEGY.md](GRAPH_RAG_STRATEGY.md)** - Graph RAG 전략
- **[SOLUTION_RICH_CONTEXT.md](SOLUTION_RICH_CONTEXT.md)** - Rich Context 구현
- **[IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md)** - 자동화 로드맵

### 🛠️ 스크립트
- `generate_graph_rag_reports.py` - 기본 리포트 생성기
- `generate_with_sonnet4.py` - Sonnet 4 API 버전
- `.claude/skills/verify-report/` - 검증 스킬

---

## 🎯 일일 루틴 (1시간)

### 오전 00:00 - NBA (30분)
```bash
1. claude 실행
2. "오늘 NBA 주요 5경기 분석해줘"
3. /verify-report (5개)
4. 점수 확인 → 판매
```

### 오후 12:00 - 축구 (30분)
```bash
1. "오늘 EPL+라리가 주요 10경기 분석해줘"
2. /verify-report (10개)
3. 점수 확인 → 판매
```

**→ 상세 가이드: [DAILY_WORKFLOW.md](DAILY_WORKFLOW.md)**

---

## 💰 비용 & 효율

### 현재 (반자동)
- **비용**: $0/월 (Claude Code)
- **시간**: 1시간/일 (15개 보고서)
- **품질**: 90점/100 (검증 완료)

### 수동 (기존)
- **비용**: $0/월
- **시간**: 3-4시간/일 (15개 보고서)
- **품질**: 변동적

### 자동화 (Phase 4)
- **비용**: $20/월 (Sonnet 4 API)
- **시간**: 0분/일 (자동)
- **품질**: 85-90점/100

---

## 📈 실제 검증 결과

### 보고서 품질
- DET @ LAL: **90/100** ✅ 판매 승인
- SAC @ LAC: **80/100** ⚡ 경고 확인 후 판매
- PHI @ MEM: **95/100** ✅ 판매 승인
- BOS @ UTAH: **88/100** ✅ 판매 승인

**평균: 88.3/100**

### 발견된 오류 예시
```
❌ DET 평균 실점: 보고서 101.0 vs 실제 114.9
→ 스킬이 자동 감지!
→ 판매 전 수정 가능
```

---

## 🛠️ 파일 구조

```
/Users/js/g9/
├── nba_data/
│   ├── odds_report_engine/
│   │   ├── README.md              ← 이 파일
│   │   ├── CHEATSHEET.md          ← 빠른 시작
│   │   ├── DAILY_WORKFLOW.md      ← 일일 가이드
│   │   ├── GRAPH_RAG_STRATEGY.md  ← Graph RAG 전략
│   │   └── generate_*.py          ← 생성 스크립트
│   └── odds_reports/
│       └── graphrag_*.md          ← 생성된 보고서
└── .claude/
    └── skills/
        └── verify-report/         ← 검증 스킬
            ├── main.py
            ├── README.md
            └── test.sh
```

---

## 🔧 환경 설정 (1회만)

### Neo4j 비밀번호 확인
```bash
grep NEO4J_PASSWORD /Users/js/g9/vultr-g9-deploy/.env
```

### Claude Code 설치 확인
```bash
which claude
claude --version
```

### 검증 스킬 테스트
```bash
export NEO4J_PASSWORD="nba_vultr_2025"
/Users/js/g9/.claude/skills/verify-report/test.sh
```

---

## 📚 확장 계획

### Phase 1: 현재 (완료 ✅)
- Manual Graph RAG
- Claude Code 분석
- 검증 스킬
- 반자동 워크플로우

### Phase 2-4: 선택적 자동화
자세한 내용: **[IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md)**

---

## 🚨 문제 해결

### 검증 스킬이 안 되면?
```bash
export NEO4J_PASSWORD="nba_vultr_2025"
cd /Users/js/g9/.claude/skills/verify-report
python3 main.py /path/to/report.md
```

### 모든 보고서가 낮은 점수면?
- Neo4j 데이터 확인
- ESPN API 상태 확인
- 다음날 재시도

### 보고서 생성이 느리면?
- 5개 → 3개로 줄이기
- 주요 경기만 선택

---

## ✅ 시작 체크리스트

- [ ] [CHEATSHEET.md](CHEATSHEET.md) 읽기
- [ ] [DAILY_WORKFLOW.md](DAILY_WORKFLOW.md) 숙지
- [ ] Neo4j 연결 확인
- [ ] 검증 스킬 테스트
- [ ] 첫 보고서 생성 & 검증

---

## 🎉 준비 완료!

**오늘 밤 00:00부터 시작:**

```bash
cd /Users/js/g9
claude
> "오늘 NBA 주요 5경기 분석해줘"
> /verify-report nba_data/odds_reports/graphrag_*.md
```

**1시간으로 15개 고품질 보고서!**

---

**© 2025 G9 Regime Zero - NBA/Soccer Betting Report System**
**Powered by Graph RAG + Claude Code + Quality Assurance**
