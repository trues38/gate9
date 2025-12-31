# Soccer System Logs

**위치**: `/Users/js/g9/logs/soccer/` (로컬), `/opt/g9/logs/soccer/` (VPS)

---

## 📋 로그 목록

### 세션 로그
- **SESSION_2025_12_31.md** - 2025-12-31 세션 기록
  - Quick Win: Graph RAG 통합 완료
  - 고가치 베팅 3개 발견
  - 내일 할 일 체크리스트

- **SESSION_SUMMARY.md** - Graph RAG Phase 1 세션 요약

### 완료 문서
- **QUICK_WIN_COMPLETE.md** - Graph RAG 통합 완료 기록
  - Before/After 비교
  - 고가치 베팅 상세
  - 시스템 구조

- **GRAPH_RAG_PHASE1_COMPLETE.md** - Phase 1 기술 문서
  - 3,504 Match 노드 로드
  - 6,898 폼 시퀀스 생성
  - Liverpool 검증 완료

- **PROGRESS_UPDATE_2025_12_30.md** - 전체 진행 상황

---

## 🔍 빠른 참조

### 다음 세션 재개 시
```bash
cat /Users/js/g9/logs/soccer/SESSION_2025_12_31.md
```

### 작업 완료 내역
```bash
cat /Users/js/g9/logs/soccer/QUICK_WIN_COMPLETE.md
```

### 전체 진행 상황
```bash
ls -lth /Users/js/g9/logs/soccer/
```

---

## 📁 구조

```
/Users/js/g9/
├── logs/soccer/              (작업 로그)
│   ├── SESSION_*.md
│   ├── *_COMPLETE.md
│   └── PROGRESS_*.md
│
└── reports/soccer/           (실제 리포트)
    ├── graphrag_*.md         (Graph RAG 리포트)
    ├── xg_*.md               (xG 분석 리포트)
    ├── README.md             (시스템 가이드)
    └── *_STATUS.md           (상태 문서)
```

---

**최종 업데이트**: 2025-12-31 00:55 KST
