# Shot Quality Metrics - xG Alternative System

## Summary

무료 xG 데이터 수집이 불가능하므로, 기존 슛 통계를 활용한 대체 메트릭 시스템을 구축했습니다.

## 시스템 개요

### 사용 가능한 메트릭

| 메트릭 | 계산식 | 의미 | 범위 |
|--------|--------|------|------|
| `shot_quality` | SoT / Shots | 슛 정확도 (타겟 비율) | 0-1 |
| `conversion_rate` | Goals / SoT | 마무리 능력 (득점 효율) | 0-1 |
| `shot_efficiency` | Goals / Shots | 전체 공격 효율성 | 0-1 |
| `shot_volume_index` | Shots / League Avg | 슛 볼륨 (리그 평균 대비) | 0-2+ |

### xG와의 비교

| 항목 | xG | Shot Quality Metrics |
|------|-----|---------------------|
| 정교함 | 매우 높음 (위치, 각도 고려) | 중간 (결과 기반) |
| 비용 | $10-15/월 | 무료 |
| 데이터 소스 | Understat, API-Football | football-data.co.uk |
| 안정성 | API 의존 | CSV 기반 (안정) |
| 해석 | xG = 예상 골 | 실제 슛 품질 |

## 사용 방법

### 1. 메트릭 계산

```bash
# 로컬
cd /Users/js/g9/soccer_data
python3 collectors/shot_quality_metrics.py

# VPS
ssh root@141.164.35.214
cd /opt/g9/domains/soccer
python3 scripts/shot_quality_metrics.py
```

결과:
```
✅ Calculated metrics for 7004 match records
✅ Updated 4 new columns in match_stats table
```

### 2. SQL 쿼리 예시

#### 최근 EPL 경기 슛 품질 조회
```sql
SELECT
    m.date,
    m.home_team_id,
    m.away_team_id,
    ms_h.shots as h_shots,
    ms_h.shots_on_target as h_sot,
    m.home_score,
    ms_h.shot_quality as h_quality,
    ms_h.conversion_rate as h_conversion,
    ms_a.shots as a_shots,
    ms_a.shots_on_target as a_sot,
    m.away_score,
    ms_a.shot_quality as a_quality,
    ms_a.conversion_rate as a_conversion
FROM matches m
JOIN match_stats ms_h ON m.match_id = ms_h.match_id AND ms_h.is_home = 1
JOIN match_stats ms_a ON m.match_id = ms_a.match_id AND ms_a.is_home = 0
WHERE m.league = 'EPL'
ORDER BY m.date DESC
LIMIT 10;
```

#### 팀별 평균 슛 품질 (시즌 전체)
```sql
SELECT
    CASE WHEN ms.is_home = 1 THEN m.home_team_id ELSE m.away_team_id END as team,
    COUNT(*) as matches,
    ROUND(AVG(ms.shot_quality), 3) as avg_quality,
    ROUND(AVG(ms.conversion_rate), 3) as avg_conversion,
    ROUND(AVG(ms.shot_efficiency), 3) as avg_efficiency,
    ROUND(AVG(ms.shots), 1) as avg_shots
FROM match_stats ms
JOIN matches m ON ms.match_id = m.match_id
WHERE m.league = 'EPL' AND m.season = '2024-25'
GROUP BY team
ORDER BY avg_quality DESC;
```

#### 고품질 공격 vs 저품질 공격
```sql
-- Shot Quality >= 0.5 (고품질)
SELECT
    m.date,
    CASE WHEN ms.is_home = 1 THEN m.home_team_id ELSE m.away_team_id END as team,
    ms.shots,
    ms.shots_on_target,
    CASE WHEN ms.is_home = 1 THEN m.home_score ELSE m.away_score END as goals,
    ms.shot_quality,
    ms.conversion_rate
FROM match_stats ms
JOIN matches m ON ms.match_id = m.match_id
WHERE m.league = 'EPL'
AND ms.shot_quality >= 0.5
AND ms.shots >= 10
ORDER BY ms.shot_quality DESC
LIMIT 20;
```

### 3. LLM 분석 예시

```python
# 경기 분석에 사용
def analyze_match(match_id):
    # SQL에서 데이터 가져오기
    query = """
    SELECT
        m.home_team_id, m.away_team_id,
        ms_h.shots, ms_h.shot_quality, ms_h.conversion_rate,
        ms_a.shots, ms_a.shot_quality, ms_a.conversion_rate,
        m.home_score, m.away_score
    FROM matches m
    JOIN match_stats ms_h ON m.match_id = ms_h.match_id AND ms_h.is_home = 1
    JOIN match_stats ms_a ON m.match_id = ms_a.match_id AND ms_a.is_home = 0
    WHERE m.match_id = ?
    """

    # LLM 프롬프트 생성
    prompt = f"""
    경기 분석:

    홈팀 ({home_team}):
    - 총 슛: {h_shots}개
    - 슛 품질: {h_quality:.1%} (타겟 비율)
    - 마무리: {h_conversion:.1%} (득점/타겟슛)
    - 실제 득점: {home_score}골

    어웨이 ({away_team}):
    - 총 슛: {a_shots}개
    - 슛 품질: {a_quality:.1%}
    - 마무리: {a_conversion:.1%}
    - 실제 득점: {away_score}골

    판단:
    {home_team}의 슛 품질이 {h_quality:.1%}로 우수하며,
    마무리 능력도 {h_conversion:.1%}로 양호합니다.
    반면 {away_team}는 슛 품질 {a_quality:.1%}로 상대적으로 부족합니다.
    """

    return prompt
```

## 실전 활용

### 배팅 판단 시나리오

#### 시나리오 1: 과소평가된 팀 찾기
```sql
-- 슛 품질은 좋지만 득점이 적은 팀 (언더퍼폼)
SELECT
    team,
    AVG(shot_quality) as avg_quality,
    AVG(conversion_rate) as avg_conversion,
    SUM(CASE WHEN is_home = 1 THEN m.home_score ELSE m.away_score END) as total_goals
FROM match_stats ms
JOIN matches m ON ms.match_id = m.match_id
WHERE m.league = 'EPL' AND m.season = '2024-25'
GROUP BY team
HAVING avg_quality > 0.4 AND avg_conversion < 0.25
ORDER BY avg_quality DESC;
```

해석: 슛 품질은 좋은데 마무리가 약한 팀 → 다음 경기 득점 가능성 높음

#### 시나리오 2: 오버퍼폼 팀 찾기
```sql
-- 슛 품질은 낮지만 득점이 많은 팀 (오버퍼폼)
SELECT
    team,
    AVG(shot_quality) as avg_quality,
    AVG(conversion_rate) as avg_conversion,
    SUM(CASE WHEN is_home = 1 THEN m.home_score ELSE m.away_score END) as total_goals
FROM match_stats ms
JOIN matches m ON ms.match_id = m.match_id
WHERE m.league = 'EPL' AND m.season = '2024-25'
GROUP BY team
HAVING avg_quality < 0.35 AND avg_conversion > 0.35
ORDER BY avg_conversion DESC;
```

해석: 운이 좋았던 팀 → 회귀 가능성 (regression to mean)

#### 시나리오 3: 매치업 분석
```python
# 다가오는 경기 분석
home_team = 'arsenal'
away_team = 'man_city'

# 최근 5경기 평균
query = """
SELECT
    ROUND(AVG(ms.shot_quality), 3) as avg_quality,
    ROUND(AVG(ms.conversion_rate), 3) as avg_conversion,
    ROUND(AVG(ms.shots), 1) as avg_shots
FROM match_stats ms
JOIN matches m ON ms.match_id = m.match_id
WHERE (m.home_team_id = ? AND ms.is_home = 1)
   OR (m.away_team_id = ? AND ms.is_home = 0)
ORDER BY m.date DESC
LIMIT 5
"""

# 홈팀 form: 0.45 quality, 0.30 conversion, 14 shots
# 어웨이 form: 0.52 quality, 0.35 conversion, 16 shots
# 판단: Man City가 슛 품질에서 우위 → 어웨이 승 또는 무승부 고려
```

## 실제 결과 (테스트)

### Top 5 Shot Quality (EPL)
```
1. brighton (16/09/2023)     - 80.0% quality, 10 shots → 3 goals
2. newcastle (12/08/2023)    - 76.5% quality, 17 shots → 5 goals
3. luton (03/02/2024)        - 72.7% quality, 11 shots → 4 goals
```

### Worst 5 Shot Quality (EPL)
```
1. everton (30/12/2023)      - 0.0% quality, 10 shots → 0 goals
2. man_united (30/12/2024)   - 0.0% quality, 10 shots → 0 goals
3. everton (27/04/2024)      - 5.6% quality, 18 shots → 1 goal
```

## 자동화

### Cron 설정 (선택)

```bash
# VPS에 추가 (주 1회 재계산)
ssh root@141.164.35.214
crontab -e

# 일요일 자정 실행
0 0 * * 0 cd /opt/g9/domains/soccer && python3 scripts/shot_quality_metrics.py >> logs/shot_quality.log 2>&1
```

현재는 필요 없음:
- 새 경기 데이터 수집 시 자동 계산됨
- 필요시 수동 실행

## 결론

### 장점
- ✅ **완전 무료**: football-data.co.uk CSV 사용
- ✅ **안정적**: API 의존성 없음
- ✅ **해석 용이**: 실제 슛 결과 기반
- ✅ **충분한 정보**: xG 없이도 공격 품질 판단 가능

### 제한사항
- ⚠️ **위치 정보 없음**: 슛이 어디서 발생했는지 모름
- ⚠️ **각도 정보 없음**: 슛의 난이도 반영 안 됨
- ⚠️ **선수별 분석 불가**: 팀 단위만 가능

### 권장 사용
1. **메인 분석**: Shot Quality + Conversion Rate
2. **보조 지표**: Possession, Corners, Fouls
3. **최종 판단**: LLM이 모든 지표 통합 분석

## 다음 단계

필요시 업그레이드 옵션:
1. **FBref 스크래핑** (4-6시간 구현) - xG 데이터 추가
2. **API-Football 유료** ($15/월) - xG + 선수별 통계
3. **수동 CSV** (주 1회 5분) - Understat xG 다운로드

현재는 Shot Quality로 충분합니다.
