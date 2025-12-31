# 📦 Data Storage Pipeline - RAW 데이터 저장

> **목표**: 6개월 후 "이 State가 돈이 되는가?"를 계산할 수 있게 데이터를 쌓는다

---

## 🎯 지금 할 일 (단순!)

❌ ML 고도화 X
❌ 위원회 평가 가중치 X
❌ 자동 최적화 X

✅ **이것만**:
1. RAW Event 저장
2. BoxScore 저장
3. State 스냅샷 저장
4. 날짜/경기 ID 고정

---

## 📊 저장할 데이터 구조

### 1. RAW Event (경기 전)

```json
{
  "event_id": "evt_20251228_401810212_injury_001",
  "game_id": "401810212",
  "game_date": "2025-12-28",
  "created_at": "2025-12-28T09:00:00Z",

  "event_type": "INJURY_IMPACT",

  "prediction": {
    "player": "RJ Barrett",
    "team": "TOR",
    "status": "OUT",
    "expected_impact": -8.5,
    "confidence": 0.75,
    "reasoning": "RJ Barrett OUT (21.5ppg, 주력 선수)"
  },

  "context": {
    "odds_at_creation": {
      "moneyline": {"GSW": -175, "TOR": 155},
      "spread": {"GSW": -4.5}
    },
    "team_state_snapshot": {
      "TOR": {
        "regime": "DECLINE",
        "regime_confidence": 0.85,
        "injury_resilience": "MEDIUM",
        "market_trust": "MEDIUM"
      }
    }
  },

  "validation": null  // 경기 후 채워짐
}
```

**보관 위치**: Neo4j + JSON 파일 (이중 백업)

---

### 2. AI Council Prediction (경기 전)

```json
{
  "prediction_id": "pred_20251228_401810212",
  "game_id": "401810212",
  "game_date": "2025-12-28",
  "created_at": "2025-12-28T09:30:00Z",

  "consensus": {
    "score": "3/5",
    "recommendation": "BET",
    "confidence": "MEDIUM"
  },

  "individual_votes": [
    {
      "analyst": "DeepSeek V3.2",
      "vote": "BET",
      "confidence": "HIGH",
      "reasoning": "Regime 우위 명확 (ROAD_DOMINANCE vs DECLINE)",
      "model_used": "deepseek/deepseek-chat"
    },
    {
      "analyst": "Qwen 72B",
      "vote": "BET",
      "confidence": "MEDIUM",
      "reasoning": "H2H 3-0, 스프레드 커버율 100%",
      "model_used": "qwen/qwen-2.5-72b-instruct"
    },
    {
      "analyst": "Grok 4.1 Fast",
      "vote": "PASS",
      "confidence": "MEDIUM",
      "reasoning": "부상자 양팀 모두 있어 변수 큼",
      "model_used": "x-ai/grok-4.1-fast"
    },
    {
      "analyst": "Gemini 2.5 Flash Lite",
      "vote": "BET",
      "confidence": "MEDIUM",
      "reasoning": "TOR injury_resilience LOW, GSW 원정 강세",
      "model_used": "google/gemini-2.5-flash-lite"
    },
    {
      "analyst": "GPT-4o-mini",
      "vote": "PASS",
      "confidence": "LOW",
      "reasoning": "라인 -4.5는 적정, 벨류 없음",
      "model_used": "openai/gpt-4o-mini"
    }
  ],

  "input_context": {
    "odds": {...},
    "team_states": {...},
    "injuries": [...]
  },

  "validation": null  // 경기 후 채워짐
}
```

---

### 3. BoxScore (경기 후 - 정답지)

```json
{
  "boxscore_id": "box_20251228_401810212",
  "game_id": "401810212",
  "game_date": "2025-12-28",
  "created_at": "2025-12-28T23:30:00Z",

  "final_score": {
    "home": 102,
    "away": 115,
    "margin": -13
  },

  "spread_result": {
    "line": -4.5,
    "covered_by": "AWAY",
    "margin_vs_spread": -8.5
  },

  "measured_impacts": {
    "home_injuries_impact": -12.3,  // 실제 측정
    "away_injuries_impact": -3.1,
    "pace": 98.5,
    "home_fg_pct": 0.42,
    "away_fg_pct": 0.51
  },

  "key_stats": {
    "home_rebounds": 41,
    "away_rebounds": 48,
    "home_turnovers": 14,
    "away_turnovers": 9
  }
}
```

---

### 4. Event Validation (경기 후 - 채점 결과)

```json
{
  "validation_id": "val_20251228_401810212_evt_001",
  "event_id": "evt_20251228_401810212_injury_001",
  "game_id": "401810212",
  "validated_at": "2025-12-28T23:45:00Z",

  "result": {
    "success": true,
    "impact_score": 0.82,

    "comparison": {
      "expected": -8.5,
      "actual": -12.3,
      "error": 3.8,
      "error_pct": 44.7
    },

    "verdict": "SUCCESS",
    "reason": "오차 5점 이내, 방향 일치"
  }
}
```

---

### 5. State Snapshot (경기 후 - 업데이트된 상태)

```json
{
  "snapshot_id": "state_20251228_TOR_after_401810212",
  "team_id": "TOR",
  "snapshot_date": "2025-12-28",
  "triggered_by_game": "401810212",
  "created_at": "2025-12-28T23:50:00Z",

  "state": {
    "regime": {
      "type": "DECLINE",
      "confidence": 0.87,  // 0.85 → 0.87 (예측 성공)
      "success_rate": 0.73,
      "games_in_regime": 13
    },

    "injury_resilience": {
      "level": "LOW",  // MEDIUM → LOW (큰 손실)
      "impact_history": [0.82, 0.9, 0.7],  // 최근 3경기
      "avg_recovery": 0.81
    },

    "market_trust": {
      "level": "MEDIUM",
      "accuracy": 0.62,
      "last_30_games": 0.65
    },

    "performance": {
      "recent_form": "3-8",  // 3-7 → 3-8
      "avg_margin": -5.3,    // -5.1 → -5.3
      "home_record": "8-13"  // 8-12 → 8-13
    },

    "learning_metadata": {
      "total_events_validated": 46,  // +1
      "successful_predictions": 29,   // +1
      "overall_accuracy": 0.630
    }
  },

  "changes_from_previous": {
    "regime_confidence": +0.02,
    "injury_resilience": "MEDIUM → LOW",
    "recent_form": "3-7 → 3-8"
  }
}
```

---

## 🗂️ 파일 저장 구조

```
/Users/js/g9/nba_data/raw_events/
├── 2025-12/
│   ├── 2025-12-28/
│   │   ├── events/
│   │   │   ├── evt_20251228_401810212_injury_001.json
│   │   │   ├── evt_20251228_401810212_market_001.json
│   │   │   └── evt_20251228_401810212_lineup_001.json
│   │   │
│   │   ├── predictions/
│   │   │   └── pred_20251228_401810212.json
│   │   │
│   │   ├── boxscores/
│   │   │   └── box_20251228_401810212.json
│   │   │
│   │   ├── validations/
│   │   │   ├── val_20251228_401810212_evt_001.json
│   │   │   ├── val_20251228_401810212_evt_002.json
│   │   │   └── val_20251228_401810212_pred.json
│   │   │
│   │   └── states/
│   │       ├── state_20251228_TOR_after_401810212.json
│   │       └── state_20251228_GSW_after_401810212.json
│   │
│   └── 2025-12-29/
│       └── ...
│
└── 2026-01/
    └── ...
```

---

## 💾 이중 저장 (Neo4j + JSON)

### Neo4j (쿼리용)

```cypher
// 빠른 조회, 관계 분석
MATCH (ts:TeamState {team_id: 'TOR'})-[:UPDATED_BY]->(b:BoxScore)
RETURN ts, b
ORDER BY b.created_at DESC
LIMIT 10
```

### JSON 파일 (백업 + 분석용)

```python
# 6개월 후 분석
import json
import glob

# 모든 State 스냅샷 로드
states = []
for file in glob.glob('/Users/js/g9/nba_data/raw_events/**/**/states/*.json'):
    with open(file) as f:
        states.append(json.load(f))

# "이 State가 돈이 되는가?" 계산
for state in states:
    accuracy = state['state']['learning_metadata']['overall_accuracy']
    if accuracy > 0.70:
        print(f"✅ {state['team_id']}: {accuracy:.1%} (돈이 된다!)")
```

---

## 🔄 자동 저장 파이프라인

### Python 코드

```python
#!/usr/bin/env python3
"""자동 RAW 데이터 저장 파이프라인"""

import json
from pathlib import Path
from datetime import datetime

class RawDataPipeline:
    """RAW 데이터 저장 파이프라인"""

    def __init__(self, base_dir="/Users/js/g9/nba_data/raw_events"):
        self.base_dir = Path(base_dir)

    def save_event(self, event_data: dict):
        """Event 저장"""
        game_date = event_data['game_date']
        year_month = game_date[:7]  # 2025-12

        save_dir = self.base_dir / year_month / game_date / "events"
        save_dir.mkdir(parents=True, exist_ok=True)

        file_path = save_dir / f"{event_data['event_id']}.json"
        with open(file_path, 'w') as f:
            json.dump(event_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Event 저장: {file_path}")

    def save_prediction(self, prediction_data: dict):
        """AI Council Prediction 저장"""
        game_date = prediction_data['game_date']
        year_month = game_date[:7]

        save_dir = self.base_dir / year_month / game_date / "predictions"
        save_dir.mkdir(parents=True, exist_ok=True)

        file_path = save_dir / f"{prediction_data['prediction_id']}.json"
        with open(file_path, 'w') as f:
            json.dump(prediction_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Prediction 저장: {file_path}")

    def save_boxscore(self, boxscore_data: dict):
        """BoxScore 저장"""
        game_date = boxscore_data['game_date']
        year_month = game_date[:7]

        save_dir = self.base_dir / year_month / game_date / "boxscores"
        save_dir.mkdir(parents=True, exist_ok=True)

        file_path = save_dir / f"{boxscore_data['boxscore_id']}.json"
        with open(file_path, 'w') as f:
            json.dump(boxscore_data, f, indent=2, ensure_ascii=False)

        print(f"✅ BoxScore 저장: {file_path}")

    def save_validation(self, validation_data: dict):
        """Event Validation 저장"""
        # game_date는 BoxScore에서 가져와야 함
        game_id = validation_data['game_id']
        # 간단히 오늘 날짜 사용
        game_date = datetime.now().strftime('%Y-%m-%d')
        year_month = game_date[:7]

        save_dir = self.base_dir / year_month / game_date / "validations"
        save_dir.mkdir(parents=True, exist_ok=True)

        file_path = save_dir / f"{validation_data['validation_id']}.json"
        with open(file_path, 'w') as f:
            json.dump(validation_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Validation 저장: {file_path}")

    def save_state_snapshot(self, state_data: dict):
        """State Snapshot 저장"""
        snapshot_date = state_data['snapshot_date']
        year_month = snapshot_date[:7]

        save_dir = self.base_dir / year_month / snapshot_date / "states"
        save_dir.mkdir(parents=True, exist_ok=True)

        file_path = save_dir / f"{state_data['snapshot_id']}.json"
        with open(file_path, 'w') as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)

        print(f"✅ State Snapshot 저장: {file_path}")


# 사용 예시
if __name__ == "__main__":
    pipeline = RawDataPipeline()

    # Event 저장
    event = {
        "event_id": "evt_20251228_401810212_injury_001",
        "game_id": "401810212",
        "game_date": "2025-12-28",
        "event_type": "INJURY_IMPACT",
        "prediction": {"expected_impact": -8.5}
    }
    pipeline.save_event(event)

    # State Snapshot 저장
    state = {
        "snapshot_id": "state_20251228_TOR_after_401810212",
        "team_id": "TOR",
        "snapshot_date": "2025-12-28",
        "state": {"regime": {"confidence": 0.87}}
    }
    pipeline.save_state_snapshot(state)
```

---

## 🎯 핵심 원칙

1. **모든 데이터 저장** - 나중에 뭐가 돈이 될지 모른다
2. **날짜/경기 ID 고정** - 추적 가능하게
3. **JSON + Neo4j 이중 백업** - 안전하게
4. **스냅샷 방식** - State 변화 추적

---

## 💰 6개월 후 분석 예시

```python
# 어떤 State가 돈이 되는가?
states = load_all_states()

profitable_patterns = []
for state in states:
    if state['learning_metadata']['overall_accuracy'] > 0.70:
        profitable_patterns.append({
            "team": state['team_id'],
            "regime": state['regime']['type'],
            "confidence": state['regime']['confidence'],
            "accuracy": state['learning_metadata']['overall_accuracy']
        })

# 결과: "ROAD_DOMINANCE + confidence > 0.85 = 75% 정확도"
```

---

**이게 지식 생성 시스템입니다.** 🔥
**예측이 틀린 이유를 학습합니다.** 🎯
**6개월 후 돈이 되는 패턴을 발견합니다.** 💰
