# NBA 베팅 분석 웹 서비스 아키텍처

## 시스템 구성

```
┌─────────────────────────────────────────────────────────────┐
│                    소비자 웹페이지                           │
│  - 내일 경기 리스트                                          │
│  - 경기별 상세 분석 페이지                                   │
│  - 실시간 업데이트 표시                                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    API 서버 (FastAPI)                        │
│  - GET /games/tomorrow        → 내일 경기 리스트            │
│  - GET /games/{game_id}       → 경기 상세 분석              │
│  - GET /games/{game_id}/llm   → LLM 자연어 보고서           │
│  - POST /update/yesterday     → 수동 업데이트 트리거        │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                 데이터 레이어                                │
│  - tomorrow_games.json        (내일 스케줄)                 │
│  - tomorrow_previews.json     (ESPN 프리뷰)                 │
│  - tomorrow_contexts.json     (계산된 컨텍스트)             │
│  - context_based_analysis_*.txt (패턴 분석)                 │
│  - Neo4j                      (927+ 경기 이력)              │
└─────────────────────────────────────────────────────────────┘
                 ▲
                 │
┌─────────────────────────────────────────────────────────────┐
│              자동화 스케줄러 (Cron/GitHub Actions)          │
│  - 매일 09:00: 어제 경기 업데이트                           │
│  - 매일 15:00: 내일 경기 1차 분석 (부상자/스케줄)          │
│  - 매일 18:00: 최종 분석 (심판/배당 업데이트)              │
└─────────────────────────────────────────────────────────────┘
```

---

## 핵심 기능

### 1. 실시간 경기 리스트 (내일 경기)

**엔드포인트**: `GET /api/games/tomorrow`

**응답 예시**:
```json
{
  "date": "2025-12-27",
  "games": [
    {
      "game_id": "401810001",
      "away_team": "BOS",
      "home_team": "IND",
      "time": "19:00",
      "our_prediction": {
        "home_win_prob": 41,
        "away_win_prob": 59,
        "confidence": "MEDIUM"
      },
      "espn_prediction": {
        "home_win_prob": 46,
        "away_win_prob": 54
      },
      "key_factors": [
        "BOS 휴식 우위",
        "IND 부상자 5명"
      ],
      "last_updated": "2025-12-26T15:00:00"
    }
  ]
}
```

**웹 UI**:
```
┌────────────────────────────────────────────────────┐
│  NBA 내일 경기 분석 - 2025-12-27                   │
├────────────────────────────────────────────────────┤
│                                                    │
│  BOS @ IND                           19:00        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━    │
│  우리 예측: BOS 59% ⚡ MEDIUM                      │
│  ESPN 예측: BOS 54%                                │
│  🔑 BOS 휴식 우위, IND 부상자 5명                 │
│  [상세보기 →]                                      │
│                                                    │
│  MIA @ ATL                           19:30        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━    │
│  우리 예측: 50-50 ⚠️ LOW                          │
│  ESPN 예측: ATL 52%                                │
│  [상세보기 →]                                      │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

### 2. 경기 상세 분석 페이지

**엔드포인트**: `GET /api/games/{game_id}`

**응답 예시**:
```json
{
  "game_id": "401810001",
  "basic_info": {
    "date": "2025-12-27",
    "time": "19:00",
    "away_team": "BOS",
    "home_team": "IND",
    "venue": "Gainbridge Fieldhouse"
  },
  "context": {
    "home_rest_days": 2,
    "away_rest_days": 3,
    "rest_advantage": "BOS +1일",
    "home_injuries": 5,
    "away_injuries": 2,
    "referee": "Mike Callahan",
    "referee_bias": "홈 유리 (54% 홈승률, 45경기)"
  },
  "predictions": {
    "our_model": {
      "home_win_prob": 41,
      "away_win_prob": 59,
      "confidence": "MEDIUM",
      "factors": [
        {"factor": "부상자 많음", "impact": -9},
        {"factor": "휴식 열세", "impact": -5}
      ]
    },
    "espn": {
      "home_win_prob": 46,
      "away_win_prob": 54
    }
  },
  "historical_patterns": {
    "home_team_with_context": {
      "description": "IND 2일 휴식",
      "win_pct": 33.3,
      "avg_margin": 0.0,
      "sample_size": 3
    },
    "away_team_with_context": {
      "description": "BOS 3일 휴식",
      "win_pct": 78.0,
      "avg_margin": 5.2,
      "sample_size": 12
    },
    "matchup_history": {
      "total_games": 9,
      "away_wins": 6,
      "home_wins": 3,
      "avg_away_margin": 5.2
    }
  },
  "injuries": {
    "home": [
      {"name": "Tyrese Haliburton", "status": "Questionable", "details": "Hamstring"},
      {"name": "Aaron Nesmith", "status": "Out", "details": "Ankle"}
    ],
    "away": [
      {"name": "Kristaps Porzingis", "status": "Out", "details": "Ankle"}
    ]
  },
  "betting_lines": {
    "spread": -3.5,
    "spread_team": "BOS",
    "over_under": 225.5,
    "moneyline_home": 145,
    "moneyline_away": -165
  },
  "last_updated": "2025-12-26T18:00:00"
}
```

**웹 UI**:
```
┌────────────────────────────────────────────────────────────┐
│  BOS @ IND - 2025-12-27 19:00                              │
│  Gainbridge Fieldhouse                                     │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  🎯 우리 예측                                              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  BOS 59%  [██████████████████    ] 41% IND               │
│  신뢰도: MEDIUM                                            │
│                                                            │
│  📊 근거                                                   │
│  • IND 부상자 5명 → -9%                                   │
│  • BOS 휴식 우위 (3일 vs 2일) → +5%                       │
│  • IND 2일 휴식 승률: 33.3% (3경기)                       │
│  • BOS 3일 휴식 승률: 78.0% (12경기, 평균 +5.2점)        │
│                                                            │
│  🏀 ESPN 예측                                              │
│  BOS 54% vs IND 46%                                        │
│                                                            │
│  📋 경기 컨텍스트                                          │
│  휴식일: BOS 3일 🟢 vs IND 2일 🟢                         │
│  부상자: BOS 2명 vs IND 5명 ⚠️                            │
│  심판: Mike Callahan (홈 유리 54%, 45경기)                │
│                                                            │
│  🏥 부상자 명단                                            │
│  IND: Tyrese Haliburton (Q), Aaron Nesmith (O), ...      │
│  BOS: Kristaps Porzingis (O)                              │
│                                                            │
│  💰 배당 (경기 2시간 전 업데이트)                         │
│  스프레드: BOS -3.5                                        │
│  오버언더: 225.5                                           │
│  머니라인: BOS -165 / IND +145                            │
│                                                            │
│  📖 과거 맞대결 (최근 9경기)                               │
│  BOS 6승 3패 (평균 +5.2점)                                │
│                                                            │
│  [AI 자연어 분석 보기 →]                                   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

### 3. LLM 자연어 보고서

**엔드포인트**: `GET /api/games/{game_id}/llm`

**응답 예시**:
```json
{
  "game_id": "401810001",
  "llm_analysis": {
    "summary": "보스턴 셀틱스가 인디애나 페이서스를 원정에서 상대합니다. 우리 모델은 보스턴이 59% 확률로 승리할 것으로 예측하며, 신뢰도는 중간 수준입니다.",

    "key_insights": [
      "보스턴은 3일간의 휴식으로 충분한 컨디션 회복이 예상됩니다. 과거 데이터상 보스턴은 3일 휴식 시 78%의 높은 승률을 기록했으며, 평균 5.2점 차로 승리했습니다.",

      "인디애나는 핵심 선수 5명이 부상으로 결장하거나 출전 불확실한 상황입니다. 특히 Tyrese Haliburton의 햄스트링 부상은 팀 공격력에 큰 영향을 미칠 것으로 보입니다.",

      "인디애나는 2일 휴식 시 과거 33.3%의 저조한 승률을 보였습니다. 반면 보스턴은 최근 인디애나와의 맞대결에서 6승 3패로 우위를 점하고 있습니다.",

      "심판 Mike Callahan은 54%의 홈팀 승률을 기록하고 있어 인디애나에게 약간 유리할 수 있으나, 부상자와 휴식일 요인이 더 큰 영향을 미칠 것으로 판단됩니다."
    ],

    "betting_recommendation": {
      "recommendation": "BOS -3.5 스프레드 베팅 추천",
      "confidence": "MEDIUM",
      "reasoning": "보스턴의 휴식 우위와 인디애나의 다수 부상자를 고려할 때, 보스턴이 3.5점 이상 차이로 승리할 가능성이 높습니다. 다만 원정 경기이고 심판이 홈팀에 약간 유리한 점을 감안하여 중간 신뢰도로 평가합니다.",
      "risk_factors": [
        "인디애나 홈 경기 (심판 홈 편향)",
        "부상자 명단 경기 직전 변동 가능성",
        "보스턴 원정 피로도"
      ]
    },

    "alternative_bets": [
      {
        "type": "언더 225.5",
        "reasoning": "양 팀 모두 부상자가 많아 득점력이 제한될 가능성이 있습니다."
      }
    ],

    "generated_at": "2025-12-26T18:30:00",
    "model": "claude-sonnet-4.5"
  }
}
```

**웹 UI (AI 분석 섹션)**:
```
┌────────────────────────────────────────────────────────────┐
│  🤖 AI 자연어 분석 보고서                                  │
│  생성 시각: 2025-12-26 18:30 (경기 2시간 전)              │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  📝 요약                                                   │
│  보스턴 셀틱스가 인디애나 페이서스를 원정에서 상대합니다.  │
│  우리 모델은 보스턴이 59% 확률로 승리할 것으로 예측하며,  │
│  신뢰도는 중간 수준입니다.                                 │
│                                                            │
│  🔍 핵심 인사이트                                          │
│                                                            │
│  1️⃣ 보스턴 컨디션 우위                                    │
│     보스턴은 3일간의 휴식으로 충분한 컨디션 회복이         │
│     예상됩니다. 과거 데이터상 보스턴은 3일 휴식 시         │
│     78%의 높은 승률을 기록했으며, 평균 5.2점 차로         │
│     승리했습니다.                                          │
│                                                            │
│  2️⃣ 인디애나 부상자 악재                                  │
│     인디애나는 핵심 선수 5명이 부상으로 결장하거나         │
│     출전 불확실한 상황입니다. 특히 Tyrese Haliburton의    │
│     햄스트링 부상은 팀 공격력에 큰 영향을 미칠            │
│     것으로 보입니다.                                       │
│                                                            │
│  3️⃣ 과거 패턴 분석                                        │
│     인디애나는 2일 휴식 시 과거 33.3%의 저조한 승률을     │
│     보였습니다. 반면 보스턴은 최근 인디애나와의           │
│     맞대결에서 6승 3패로 우위를 점하고 있습니다.          │
│                                                            │
│  💡 베팅 추천                                              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  추천: BOS -3.5 스프레드                                   │
│  신뢰도: MEDIUM                                            │
│                                                            │
│  근거:                                                     │
│  보스턴의 휴식 우위와 인디애나의 다수 부상자를 고려할 때,  │
│  보스턴이 3.5점 이상 차이로 승리할 가능성이 높습니다.     │
│  다만 원정 경기이고 심판이 홈팀에 약간 유리한 점을        │
│  감안하여 중간 신뢰도로 평가합니다.                        │
│                                                            │
│  ⚠️  리스크 요인:                                          │
│  • 인디애나 홈 경기 (심판 홈 편향)                        │
│  • 부상자 명단 경기 직전 변동 가능성                      │
│  • 보스턴 원정 피로도                                     │
│                                                            │
│  🎲 대안 베팅:                                             │
│  • 언더 225.5 - 양 팀 모두 부상자가 많아 득점력이        │
│    제한될 가능성                                           │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 기술 스택

### 백엔드
- **FastAPI**: API 서버 (빠른 성능, 자동 문서화)
- **Neo4j Python Driver**: 그래프 DB 쿼리
- **Anthropic Claude API**: LLM 자연어 생성
- **APScheduler**: 자동 업데이트 스케줄링

### 프론트엔드 (옵션 1 - 간단)
- **HTML + Vanilla JS**: 빠른 프로토타입
- **Tailwind CSS**: 스타일링

### 프론트엔드 (옵션 2 - 프로덕션)
- **Next.js 14**: React 프레임워크
- **TypeScript**: 타입 안정성
- **Shadcn/UI**: UI 컴포넌트
- **React Query**: 데이터 페칭

### 배포
- **Vercel/Netlify**: 프론트엔드 (무료)
- **Railway/Fly.io**: 백엔드 + Neo4j (저렴)
- **GitHub Actions**: 자동 업데이트 Cron

---

## 데이터 업데이트 플로우

### 매일 자동 실행

```bash
# Cron 또는 GitHub Actions에서 실행

# 09:00 - 어제 경기 결과 업데이트
python3 update_yesterday_games.py

# 15:00 - 내일 경기 1차 분석
./daily_betting_report.sh
# → tomorrow_games.json, tomorrow_previews.json 생성

# 18:00 - 최종 분석 (심판/배당 업데이트)
./daily_betting_report.sh
# → context_based_analysis.txt 재생성
```

### API 서버는 파일 읽기만

```python
# FastAPI에서 최신 파일 읽기
@app.get("/api/games/tomorrow")
async def get_tomorrow_games():
    with open('tomorrow_games.json') as f:
        games = json.load(f)

    with open('tomorrow_contexts.json') as f:
        contexts = json.load(f)

    # 병합해서 응답
    return merge_data(games, contexts)
```

**장점**:
- API 서버는 가볍게 파일만 읽음
- 무거운 Neo4j 쿼리는 백그라운드에서 미리 실행
- 응답 속도 빠름 (< 50ms)

---

## LLM 통합 (Claude API)

### 자연어 보고서 생성

```python
import anthropic

def generate_llm_analysis(game_data: dict) -> str:
    """경기 분석 데이터를 자연어로 변환"""

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    prompt = f"""
당신은 NBA 베팅 분석 전문가입니다. 다음 데이터를 바탕으로
일반 사용자가 이해하기 쉬운 자연어 보고서를 작성하세요.

경기 정보:
- {game_data['away_team']} @ {game_data['home_team']}
- 날짜: {game_data['date']}

우리 예측:
- {game_data['away_team']} {game_data['our_prediction']['away_win_prob']}%
- {game_data['home_team']} {game_data['our_prediction']['home_win_prob']}%
- 신뢰도: {game_data['our_prediction']['confidence']}

컨텍스트:
- 휴식일: {game_data['away_team']} {game_data['context']['away_rest_days']}일,
           {game_data['home_team']} {game_data['context']['home_rest_days']}일
- 부상자: {game_data['away_team']} {game_data['context']['away_injuries']}명,
          {game_data['home_team']} {game_data['context']['home_injuries']}명
- 심판: {game_data['context']['referee']} ({game_data['context']['referee_bias']})

과거 패턴:
- {game_data['historical_patterns']['away_team_with_context']['description']}:
  {game_data['historical_patterns']['away_team_with_context']['win_pct']}% 승률
- {game_data['historical_patterns']['home_team_with_context']['description']}:
  {game_data['historical_patterns']['home_team_with_context']['win_pct']}% 승률

배당:
- 스프레드: {game_data['betting_lines']['spread_team']} {game_data['betting_lines']['spread']}
- 오버언더: {game_data['betting_lines']['over_under']}

다음 형식으로 작성하세요:
1. 요약 (2-3문장)
2. 핵심 인사이트 (3-4개 항목, 각각 구체적인 수치 포함)
3. 베팅 추천 (스프레드/오버언더 중 1개, 신뢰도, 근거, 리스크 요인)
4. 대안 베팅 (1-2개)

전문적이지만 친근한 어조로 작성하세요.
"""

    message = client.messages.create(
        model="claude-sonnet-4.5-20250929",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text
```

### 비용 계산

- Claude Sonnet 4.5: $3 / 1M input tokens, $15 / 1M output tokens
- 경기당 입력: ~1,000 tokens, 출력: ~1,500 tokens
- 경기당 비용: $0.003 + $0.0225 = **$0.026** (~35원)
- 하루 10경기: **$0.26** (~350원)
- 월간: **$7.8** (~10,000원)

**매우 저렴합니다.**

---

## MVP 구현 순서

### Phase 1: API 백엔드 (1-2일)
1. FastAPI 서버 기본 구조
2. 엔드포인트 3개:
   - `/api/games/tomorrow`
   - `/api/games/{game_id}`
   - `/api/games/{game_id}/llm`
3. JSON 파일 읽어서 응답

### Phase 2: LLM 통합 (1일)
1. Claude API 연동
2. 프롬프트 엔지니어링
3. 캐싱 (같은 경기 중복 생성 방지)

### Phase 3: 간단한 웹 UI (2-3일)
1. HTML + Vanilla JS로 프로토타입
2. 경기 리스트 페이지
3. 경기 상세 페이지
4. LLM 분석 표시

### Phase 4: 자동화 (1일)
1. GitHub Actions Cron 설정
2. 매일 09:00, 15:00, 18:00 실행
3. 에러 알림 (Slack/Discord)

### Phase 5: 프로덕션 배포 (1일)
1. Vercel에 프론트엔드 배포
2. Railway에 백엔드 + Neo4j 배포
3. 도메인 연결

**총 소요시간: 6-8일**

---

## 예상 비용

### 개발 단계 (무료)
- Neo4j: Docker로 로컬 실행
- FastAPI: 로컬 실행
- Claude API: 테스트용 크레딧

### 프로덕션 (월 ~$20)
- **Neo4j Cloud**: $5/월 (Aura Free Tier 가능)
- **Railway (백엔드)**: $5/월
- **Vercel (프론트엔드)**: 무료
- **Claude API**: $10/월 (하루 10경기 × 30일)
- **도메인**: $12/년 (~$1/월)

**총: $21/월** (~28,000원)

---

## 수익화 전략 (선택)

### 무료 티어
- 내일 경기 리스트 + 기본 예측
- 컨텍스트 정보 (휴식일, 부상자)

### 프리미엄 티어 ($9.99/월)
- LLM 자연어 분석 전체 공개
- 베팅 추천 + 리스크 분석
- 배당 변화 알림
- 과거 적중률 통계

### 광고
- Google AdSense (스포츠 베팅 관련 광고)

**손익분기점**: 3명 유료 사용자 또는 월 $30 광고 수익

---

## 다음 단계

1. **FastAPI 서버 구현**부터 시작할까요?
2. **간단한 HTML 프로토타입**으로 빠르게 시각화할까요?
3. **LLM 프롬프트 엔지니어링**부터 테스트할까요?

어떤 순서로 진행하시겠습니까?
