# 🏀 NBA/축구 베팅 보고서 자동 생성 시스템

**Graph RAG + Claude Code + 품질 검증 = 1시간에 15개 보고서**

Neo4j 그래프 분석 + ESPN API 검증 + Claude Code 통합

## 🎯 기능

### 1. 그래프 분석 (Neo4j)
- 팀별 최근 전적 (10경기)
- 레짐 패턴 감지 (상승/하락/안정 구간)
- 핵심 선수 통계
- 상대전적 (Head-to-Head) 분석

### 2. 실시간 배당률 (The Odds API)
- Moneyline (승부 배당)
- Spreads (핸디캡)
- 여러 북메이커의 최적 배당률 추출
- 500 credits/월 예산 관리

### 3. LLM 리포트 생성 (Claude)
- 그래프 데이터 + 배당률 융합 분석
- 7개 섹션 구조화 리포트:
  1. Executive Summary
  2. Regime Analysis
  3. Recent Form
  4. Key Matchup Factors
  5. Odds Evaluation
  6. Betting Recommendation
  7. Risk Factors

---

## 📦 파일 구조

```
odds_report_engine/
├── odds_api_adapter.py              # The Odds API 클라이언트
├── graph_odds_report_generator.py   # 메인 리포트 생성기
├── test_local.py                    # 로컬 테스트 스크립트
├── deploy_to_vps.sh                 # VPS 배포 스크립트
└── README.md                        # 이 파일
```

---

## 🚀 로컬 테스트

### 1. 환경 변수 설정

```bash
export ODDS_API_KEY='b01049f1f29d61c53189799c40d66f69'
export ANTHROPIC_API_KEY='your_anthropic_key'
export NEO4J_PASSWORD='your_neo4j_password'
```

### 2. Odds API만 테스트

```bash
cd /Users/js/g9/nba_data/odds_report_engine
python3 test_local.py odds
```

**결과**: 오늘 경기 목록 + 배당률 출력

### 3. 단일 경기 리포트 생성

```bash
python3 test_local.py single
```

**결과**: Lakers vs Warriors 샘플 리포트 생성 (Markdown)

### 4. 오늘 전체 경기 리포트 생성

```bash
python3 test_local.py daily
```

**결과**: 오늘 모든 경기에 대한 리포트 배치 생성

---

## 🌐 VPS 배포

### 1. 배포 실행

```bash
cd /Users/js/g9/nba_data/odds_report_engine
chmod +x deploy_to_vps.sh
./deploy_to_vps.sh
```

### 2. VPS에서 환경 설정

```bash
ssh root@141.164.35.214

# 환경 변수 설정
export ODDS_API_KEY='b01049f1f29d61c53189799c40d66f69'
export ANTHROPIC_API_KEY='your_key'
export NEO4J_PASSWORD='your_password'

# ~/.bashrc에 추가 (영구 저장)
echo "export ODDS_API_KEY='b01049f1f29d61c53189799c40d66f69'" >> ~/.bashrc
echo "export ANTHROPIC_API_KEY='your_key'" >> ~/.bashrc
echo "export NEO4J_PASSWORD='your_password'" >> ~/.bashrc
source ~/.bashrc
```

### 3. VPS에서 리포트 생성

#### 단일 경기 리포트

```bash
cd /opt/g9/nba-collector

python3 graph_odds_report_generator.py \
  --home LAL \
  --away GSW \
  --neo4j-password $NEO4J_PASSWORD
```

#### 오늘 전체 경기 리포트

```bash
python3 graph_odds_report_generator.py \
  --daily \
  --neo4j-password $NEO4J_PASSWORD
```

#### 생성된 리포트 확인

```bash
ls -lh /opt/g9/nba-collector/odds_reports/
cat /opt/g9/nba-collector/odds_reports/report_*.md
```

---

## 📊 리포트 예시

생성되는 Markdown 리포트 구조:

```markdown
# Betting Report: GSW @ LAL
*Generated: 2025-12-28 18:30*

## EXECUTIVE SUMMARY
Lakers are riding a 5-game winning streak with strong home court advantage.
Warriors struggling on the road (2-8 L10). **Recommended: LAL -5.5**

## REGIME ANALYSIS
- Lakers: In "DOMINANT_HOME" regime (12 games, 85% confidence)
- Warriors: "ROAD_STRUGGLE" regime detected (recent pattern)

## RECENT FORM
**Lakers (Home)**: W-W-W-W-W
- Avg margin: +8.2
- PPG: 118.4
- Defensive rating: 108.2

**Warriors (Away)**: L-L-W-L-L
- Avg margin: -6.1
- PPG: 109.8
- Turnovers: 15.2/game (high)

## KEY MATCHUP FACTORS
- LeBron James (28.5 PPG) vs Draymond Green
- Anthony Davis (27.8 PPG) dominating paint
- Warriors missing Klay Thompson (injury)

## ODDS EVALUATION
**Moneyline**: LAL -250, GSW +210
**Spread**: LAL -5.5 (-110), GSW +5.5 (-110)

Market shows strong Lakers favoritism. Line movement from -4.5 to -5.5
indicates sharp money on Lakers.

## BETTING RECOMMENDATION
**PRIMARY PICK**: Lakers -5.5 @ -110 (MEDIUM confidence)
**ALTERNATE**: Lakers 1H -3.0 @ -105 (HIGH confidence)
**AVOID**: Warriors +5.5 (regime data suggests blowout risk)

Suggested bet sizing: 1.5 units

## RISK FACTORS
- Warriors have "bounce-back" history after bad stretches
- LeBron load management (check lineup confirmations)
- Public heavily on Lakers (fade-the-public contrarian angle)
```

---

## 📈 예산 관리 (500 credits/월)

### API 호출 비용
- 1회 odds 호출 = 1 credit
- Markets=['h2h', 'spreads'] = 동일 1 credit

### 전략
**Tier 1 (Critical)**: 주요 경기 8개/일 × 10일 = 80 calls
**Tier 2 (Standard)**: 일반 경기 12개/일 × 10일 = 120 calls
**Reserve**: 재확인용 100 credits

**일일 제한**: 최대 20경기 (200 credits 남김)

### 예산 확인

```python
from odds_api_adapter import OddsAPIAdapter

adapter = OddsAPIAdapter(api_key='your_key')
budget = adapter.get_budget_status()
print(f"Used: {budget['total_used']}/{budget['monthly_limit']}")
```

---

## 🔧 트러블슈팅

### 1. "Module not found: neo4j"

```bash
pip3 install neo4j
```

### 2. "Module not found: anthropic"

```bash
pip3 install anthropic
```

### 3. Neo4j 연결 실패

```bash
# Neo4j 상태 확인
systemctl status neo4j

# 비밀번호 확인
echo $NEO4J_PASSWORD
```

### 4. Odds API 403 Forbidden

- API 키 확인: `echo $ODDS_API_KEY`
- 예산 소진 확인: https://the-odds-api.com/account/

### 5. LLM 리포트가 생성 안됨

- Anthropic API 키 확인
- Fallback 리포트가 대신 생성됨 (기본 데이터만)

---

## 🎯 실전 사용 예시

### 시나리오 1: 오늘 경기 중 베팅할 경기 찾기

```bash
# 1. 오늘 전체 경기 리포트 생성
python3 graph_odds_report_generator.py --daily

# 2. 생성된 리포트 검토
cd odds_reports
grep -r "HIGH confidence" *.md

# 3. 추천 경기에 배팅
```

### 시나리오 2: 특정 팀 심층 분석

```bash
# Lakers 홈 경기만 분석
python3 graph_odds_report_generator.py --home LAL --away <opponent>

# 리포트에서 레짐 패턴 확인
grep -A 10 "REGIME ANALYSIS" report_*.md
```

### 시나리오 3: 오즈 변동 추적

```bash
# 1시간마다 오즈 스냅샷 저장
python3 << EOF
from odds_api_adapter import OddsAPIAdapter
adapter = OddsAPIAdapter()
adapter.save_odds_snapshot('odds_snapshot_$(date +%H%M).json')
EOF

# 스냅샷 비교로 라인 무브먼트 분석
diff odds_snapshot_1400.json odds_snapshot_1500.json
```

---

## 📝 TODO / 향후 개선

- [ ] N8N 워크플로우 통합 (자동화)
- [ ] Telegram 봇 알림
- [ ] 베팅 결과 추적 (ROI 계산)
- [ ] 더 많은 markets 지원 (totals, player props)
- [ ] 배당률 히스토리 그래프 저장
- [ ] Streamlit 대시보드

---

## 🔑 API 키 관리

### 안전한 저장 (.env 파일)

```bash
# /opt/g9/nba-collector/.env
ODDS_API_KEY=b01049f1f29d61c53189799c40d66f69
ANTHROPIC_API_KEY=sk-ant-...
NEO4J_PASSWORD=your_password
```

### 로드 방법

```python
from dotenv import load_dotenv
load_dotenv()

# 또는
import os
os.environ.get('ODDS_API_KEY')
```

---

## 📞 지원

**프로젝트**: Regime Zero - NBA Graph RAG System
**위치**: `/Users/js/g9/nba_data/odds_report_engine`
**VPS**: root@141.164.35.214:/opt/g9/nba-collector

**Built with**:
- Neo4j (Graph Database)
- The Odds API (Betting Data)
- Anthropic Claude (LLM Analysis)
- Python 3.10+
