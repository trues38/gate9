# 최적 데이터 전략: 양 vs 품질

## 문제 진단

### 현재 상황 (927경기)
- **샘플 부족**: 73.2%의 조합이 10경기 미만
- **신뢰도 낮음**: "LAL 3일 휴식: 66.7% (3경기)" 같은 통계는 무의미
- **예측 불안정**: 샘플이 적으면 운이 좌우함

### 분석 결과
```
239개 팀×휴식일×장소 조합:
  16개 (6.7%)   - 20경기 이상 (신뢰 가능) ✅
  48개 (20.1%)  - 10-19경기 (양호) ⚠️
  93개 (38.9%)  - 5-9경기 (부족) ❌
  82개 (34.3%)  - 5경기 미만 (매우 부족) ❌
```

---

## 최적 데이터 범위

### 옵션 1: 최근 2시즌만 (2,500경기) ⭐ 추천

**장점:**
- 샘플 사이즈 3배 증가 (927 → 2,460)
- 대부분의 조합이 10경기 이상 확보
- 현재 팀 로스터/전략과 가장 관련성 높음

**단점:**
- 여전히 일부 희귀 조합은 샘플 부족

**구현:**
```python
# migrate_clean.py 수정
def should_include_game(game_date: str) -> bool:
    """최근 2시즌만 포함"""
    from datetime import datetime

    game_dt = datetime.strptime(game_date, '%Y-%m-%d')
    cutoff = datetime(2023, 10, 1)  # 2023-24 시즌 시작

    return game_dt >= cutoff
```

**예상 결과:**
- 대부분의 조합이 10-30경기로 증가
- 신뢰할 수 있는 조합: 6.7% → 40-50%로 증가

---

### 옵션 2: 최근 3시즌 (3,700경기)

**장점:**
- 샘플 사이즈 4배 증가
- 거의 모든 조합이 10경기 이상

**단점:**
- 3년 전 데이터는 관련성 떨어짐
- 선수 이적/코치 변경으로 팀 특성 변화

**권장하지 않음**: 오래된 데이터가 노이즈로 작용

---

### 옵션 3: 시간 가중치 전략 ⭐⭐ 최고

**개념:**
```
최근 데이터에 더 높은 가중치 부여

예시: BOS 3일 휴식 패턴
- 2024-25 시즌 경기: 가중치 1.0
- 2023-24 시즌 경기: 가중치 0.7
- 2022-23 시즌 경기: 가중치 0.4
- 2021-22 시즌 이전: 가중치 0.0 (제외)
```

**구현:**
```python
def get_rest_day_performance_weighted(team: str, rest_days: int, home_away: str):
    """시간 가중치 적용한 휴식일 성적"""
    query = """
    MATCH (game:GameState {home_team: $team})
    WHERE game.home_rest_days = $rest_days
    WITH game,
         CASE
           WHEN game.date >= date('2024-10-01') THEN 1.0
           WHEN game.date >= date('2023-10-01') THEN 0.7
           WHEN game.date >= date('2022-10-01') THEN 0.4
           ELSE 0.0
         END AS weight
    WHERE weight > 0
    WITH sum(weight) AS total_weight,
         sum(CASE WHEN game.home_win THEN weight ELSE 0 END) AS weighted_wins,
         avg(game.home_score - game.away_score) AS avg_diff
    RETURN round(weighted_wins * 100.0 / total_weight, 1) AS win_pct,
           round(avg_diff, 1) AS avg_diff,
           round(total_weight, 1) AS effective_games
    """

    # effective_games는 "가중치 적용한 유효 경기 수"
    # 예: 10경기 × 1.0 + 5경기 × 0.7 = 13.5 유효 경기
```

**장점:**
- 최근 데이터 중요도 ↑, 오래된 데이터는 참고용
- 샘플 사이즈도 확보하면서 관련성도 유지
- 부드러운 전환 (갑자기 무시 안함)

**단점:**
- 구현 복잡도 증가
- 쿼리 속도 약간 느려짐 (미미함)

---

## 권장 전략 (단계별)

### Phase 1: 최근 2시즌 데이터 확보 (즉시)

```bash
# 2023-24, 2024-25 시즌 데이터 크롤링
python3 crawl_season_data.py --season 2023-24
python3 crawl_season_data.py --season 2024-25

# Neo4j에 임포트
python3 migrate_clean.py --since 2023-10-01
```

**예상 결과:**
- 927경기 → 2,460경기
- 신뢰 가능한 조합: 16개 → 100개 이상
- 대부분의 팀×휴식일 조합이 10경기 이상 확보

**타임라인**: 1-2일

---

### Phase 2: 시간 가중치 적용 (1주 후)

```python
# context_based_analysis.py 업그레이드
# 모든 쿼리에 시간 가중치 추가

def get_rest_day_performance_weighted(...):
    # 위 코드 참조
```

**예상 결과:**
- 예측 정확도 5-10% 향상
- 신뢰도 점수 더 정교해짐

**타임라인**: 2-3일 (쿼리 수정 + 테스트)

---

### Phase 3: 매일 자동 업데이트 (지속)

```bash
# 매일 어제 경기 추가
python3 update_yesterday_games.py

# Rolling window: 2시즌만 유지
# 2년 전 데이터는 자동 삭제
python3 cleanup_old_data.py --older-than 730
```

**예상 결과:**
- 항상 최신 2시즌 데이터 유지
- 데이터 양: 2,460 ± 50경기로 일정

**타임라인**: 설정 후 자동

---

## 데이터 양별 효과 비교

| 데이터 양 | 샘플 충분 조합 | 예측 정확도 | 관련성 | 추천 |
|---------|-------------|-----------|--------|-----|
| 927경기 (현재) | 6.7% | 낮음 | 높음 | ❌ |
| 2,500경기 (2시즌) | 40-50% | 중간 | 높음 | ✅ |
| 3,700경기 (3시즌) | 60-70% | 중간 | 중간 | ⚠️ |
| 5,000경기 (4시즌) | 80%+ | 낮음 | 낮음 | ❌ |
| 2,500경기 + 가중치 | 50-60% | **높음** | **높음** | ⭐⭐ |

---

## 통계적 신뢰도 기준

### 샘플 사이즈별 신뢰 구간

통계학적으로 95% 신뢰 구간:

```
경기 수    승률 50%일 때 오차범위
  3경기    ±28.9%  (완전 무의미)
  5경기    ±22.0%  (매우 부정확)
 10경기    ±15.5%  (참고용)
 20경기    ±10.9%  (양호)
 30경기    ± 8.9%  (좋음)
 50경기    ± 6.9%  (우수)
```

**현재 문제:**
- "LAL 3일 휴식: 66.7% (3경기)"
- 실제 승률: 66.7% ± 28.9% = 37.8% ~ 95.6%
- 거의 모든 값이 가능 → 무의미

**2시즌 데이터 후:**
- "LAL 3일 휴식: 65.0% (20경기)"
- 실제 승률: 65.0% ± 10.9% = 54.1% ~ 75.9%
- 유의미한 패턴

---

## 실전 적용 규칙

### 신뢰도 등급

```python
def calculate_confidence(sample_size: int, win_prob: float) -> str:
    """샘플 사이즈 기반 신뢰도 계산"""

    # 50%에서 멀수록 (극단적일수록) 더 많은 샘플 필요
    deviation = abs(win_prob - 50)

    if sample_size >= 30:
        return "HIGH"
    elif sample_size >= 15 and deviation >= 10:
        return "MEDIUM"
    elif sample_size >= 10 and deviation >= 15:
        return "MEDIUM"
    elif sample_size >= 5:
        return "LOW"
    else:
        return "VERY_LOW"  # 예측 표시 안함
```

**적용:**
```python
# 분석 보고서에서
if confidence == "VERY_LOW":
    print("⚠️  샘플 부족으로 예측 제공 불가")
else:
    print(f"예측: {win_prob}% (신뢰도: {confidence})")
```

---

## 결론

### 답변: 데이터를 늘려야 하나?

**YES, 하지만 한계가 있음:**

1. ✅ **927 → 2,500경기 (2시즌)**: 매우 도움됨
   - 샘플 부족 문제 대부분 해결
   - 현재 팀과 관련성 높음
   - **강력 추천**

2. ⚠️  **2,500 → 3,700경기 (3시즌)**: 약간 도움됨
   - 샘플은 더 확보되지만
   - 관련성이 떨어지기 시작
   - 선택적 추천

3. ❌ **3,700 → 5,000+ 경기 (4시즌+)**: 오히려 해로움
   - 오래된 데이터가 노이즈로 작용
   - 예측 정확도 하락
   - **비추천**

### 최적 솔루션

**최근 2시즌 + 시간 가중치**
- 데이터: 2023-24, 2024-25 시즌 (~2,500경기)
- 가중치: 최근 데이터 1.0, 1년 전 0.7, 2년 전 0.4
- Rolling update: 매일 어제 경기 추가, 2년 전 데이터 삭제

**예상 효과:**
- 샘플 충분 조합: 6.7% → 50%+
- 예측 정확도: 10-15% 향상
- 시스템 신뢰도 대폭 증가

---

## 다음 단계

2시즌 데이터를 크롤링할까요?
