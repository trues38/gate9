# 📘 G9 Hybrid Backtest System Manual

## 1. 개요 (Overview)
**"과거의 위기에서 미래의 수익을 배운다."**

이 시스템은 **역사적 데이터(History)**와 **통계적 이상 징후(Z-Score)**를 결합하여, AI가 과거의 결정적인 순간들을 다시 체험하고 학습하는 **시뮬레이션 훈련장**입니다.

---

## 2. 입력 데이터 (The Fuel)
AI는 다음 3가지 **실제 데이터(Real Data)**를 먹고 자랍니다.

### A. 타겟 (Targeting) - "언제(When)를 볼 것인가?"
*   **Z-Score (Data)**: 뉴스량이 평소보다 폭발적으로 급증한 날 (예: 2020-03-19).
*   **History (Human)**: 인간이 선정한 100대 경제 사건 (예: 2008-09-15 리만 브라더스 파산).
*   **Hybrid Synergy**: 두 리스트가 겹치는 날은 **가중치 2배**로 집중 학습합니다.

### B. 상황판 (Context) - "상황(State)이 어떠한가?"
*   **Macro Indicators (5대장)**:
    *   `US10Y` (금리), `DXY` (달러), `WTI` (유가), `VIX` (공포), `CPI` (물가).
    *   AI는 단순히 수치만 보는 것이 아니라, **"금리 급등 + 공포 확산"** 같은 **상태(State)**를 읽습니다.

### C. 정답지 (Verification) - "결과(Result)는 어땠는가?"
*   **Real Price**: SPY(미국장), KOSPI(한국장), 삼성전자 등 실제 주가 데이터.
*   가짜(Mock)가 아닌 **진짜 시장의 반응**으로 채점합니다.

---

## 3. 작동 프로세스 (The Pipeline)

명령어 `python3 run_backtest.py --mode hybrid`를 실행하면 다음 과정이 **자동**으로 일어납니다.

### Step 1. 타겟 선정 (Target Selection)
*   시스템이 **Z-Score DB**와 **History CSV**를 병합하여 **"검증해야 할 날짜 리스트"**를 뽑습니다.
*   (예: 2008-09-15, 2020-03-19, 2022-02-24...)

### Step 2. 전략 수립 (Strategy Generation)
*   **Orchestra (Pattern RAG)**가 가동됩니다.
*   **입력**: "2020년 3월 19일, 뉴스량 폭발, 공포지수(VIX) 80 돌파, 유가 폭락."
*   **AI 판단**:
    > *"이건 [P-049 투매] 패턴이다. 지금은 공포에 질려 팔 때가 아니라, 용기 내어 살 때다."*
    > *전략: **Aggressive Buy (공격 매수)** / 종목: **SPY, Samsung Elec***

### Step 3. 가상 매매 & 검증 (Execution & Verification)
*   AI가 수립한 전략대로 **가상 매매**를 체결합니다.
*   **3일 뒤, 7일 뒤의 실제 주가(Real Price)**를 확인합니다.
    *   *결과: 3일 뒤 +15% 수익.*

### Step 4. 기억 저장 (Intelligence Core)
*   이 모든 과정이 **하나의 패킷(Packet)**으로 묶여 **`g9_intelligence_core`** 테이블에 영구 저장됩니다.

| 컬럼 | 내용 (예시) |
| :--- | :--- |
| **Date** | 2020-03-19 |
| **Macro** | `{"VIX": 82.0, "State": "Panic"}` |
| **Pattern** | `P-049 (Capitulation)` |
| **Logic** | "공포가 극에 달했으므로 역발상 매수 진입" |
| **Result** | **Success (+15%)** |
| **Embedding** | (벡터화된 기억) |

---

## 4. 기대 효과 (Why do this?)

### 1. "경험 있는 신입사원"
*   이 훈련을 마친 AI는 2025년의 위기가 닥쳤을 때, **"어? 이거 2020년 3월이랑 비슷한 냄새가 나는데?"**라고 직감적으로 반응합니다. (Vector Similarity Search)

### 2. 살아있는 전략서
*   백테스트가 돌 때마다 `g9_intelligence_core`는 점점 더 똑똑해집니다.
*   단순한 규칙(Rule)이 아니라, **시장의 맥락(Context)을 이해하는 지능**이 쌓입니다.

---

### 🚀 결론
이 시스템은 단순한 백테스트기가 아닙니다.
**"과거의 데이터를 먹고 미래의 통찰을 뱉어내는 AI 진화 장치"**입니다.
