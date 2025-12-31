# Graph RAG + Odds Report - 로컬 실행 가이드

로컬에서 VPS Neo4j를 사용해 완전한 Graph RAG + Odds 리포트 생성하기

---

## 🎯 필요한 것

1. **VPS Neo4j 접근** (bolt://141.164.35.214:7687)
2. **Neo4j 비밀번호**
3. **Anthropic API 키** (Claude LLM)
4. **Odds API 키** (이미 있음: b01049f1f29d61c53189799c40d66f69)

---

## 📋 사전 준비

### 1. Neo4j 비밀번호 확인

VPS에 SSH로 접속해서 비밀번호 확인:

```bash
ssh root@141.164.35.214

# Neo4j 설정 파일 확인
cat /etc/neo4j/neo4j.conf | grep password

# 또는 환경 변수 확인
cat ~/.bashrc | grep NEO4J

# 또는 Docker 설정 확인 (Neo4j가 Docker로 실행 중이면)
docker inspect neo4j | grep NEO4J_AUTH
```

비밀번호 찾으면 메모해두기: `______________________`

---

### 2. Anthropic API 키 확인

https://console.anthropic.com/settings/keys

API 키 생성 후 메모: `sk-ant-______________________`

---

## 🚀 방법 1: SSH 터널 사용 (추천)

### Step 1: 터미널 1 - SSH 터널 시작

```bash
cd /Users/js/g9/nba_data/odds_report_engine

# SSH 터널 실행 (VPS Neo4j를 localhost:7687로 포워딩)
./connect_vps_neo4j.sh
```

**출력**:
```
==========================================
Creating SSH Tunnel to VPS Neo4j
==========================================

Local:  localhost:7687
Remote: root@141.164.35.214:7687

Press Ctrl+C to close tunnel
==========================================

```

**터널이 열린 상태로 유지** (이 터미널은 계속 켜놓기)

---

### Step 2: 터미널 2 - 환경 변수 설정

새 터미널 열고:

```bash
cd /Users/js/g9/nba_data/odds_report_engine

# API 키 설정
export ODDS_API_KEY='b01049f1f29d61c53189799c40d66f69'
export ANTHROPIC_API_KEY='sk-ant-YOUR_KEY_HERE'
export NEO4J_PASSWORD='YOUR_NEO4J_PASSWORD_HERE'
```

---

### Step 3: 연결 테스트

```bash
# Neo4j 연결 테스트
python3 << 'EOF'
from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver(
    'bolt://localhost:7687',
    auth=('neo4j', os.environ.get('NEO4J_PASSWORD'))
)

with driver.session() as session:
    result = session.run("MATCH (n) RETURN count(n) as count")
    count = result.single()['count']
    print(f"✓ Neo4j connected! Total nodes: {count}")

driver.close()
EOF
```

**성공하면**:
```
✓ Neo4j connected! Total nodes: 12847
```

---

### Step 4: Graph RAG 리포트 생성

#### 단일 경기 (Warriors @ Raptors)

```bash
./generate_full_graph_rag_report.sh TOR GSW
```

#### 오늘 전체 경기

```bash
./generate_full_graph_rag_report.sh daily
```

---

## 🌐 방법 2: 직접 연결 (Neo4j 포트 오픈 필요)

### Step 1: VPS 방화벽 설정

VPS에서 Neo4j 포트 7687 열기:

```bash
ssh root@141.164.35.214

# UFW 방화벽 (Ubuntu/Debian)
sudo ufw allow 7687/tcp

# 또는 firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-port=7687/tcp
sudo firewall-cmd --reload

# Neo4j가 외부 접속 허용하는지 확인
cat /etc/neo4j/neo4j.conf | grep listen_address

# 아래처럼 설정되어 있어야 함:
# dbms.default_listen_address=0.0.0.0

# Neo4j 재시작
sudo systemctl restart neo4j
```

---

### Step 2: 로컬에서 직접 연결

```bash
cd /Users/js/g9/nba_data/odds_report_engine

export ODDS_API_KEY='b01049f1f29d61c53189799c40d66f69'
export ANTHROPIC_API_KEY='sk-ant-YOUR_KEY_HERE'
export NEO4J_PASSWORD='YOUR_NEO4J_PASSWORD_HERE'

# 직접 연결 테스트
python3 << 'EOF'
from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver(
    'bolt://141.164.35.214:7687',  # VPS 직접 연결
    auth=('neo4j', os.environ.get('NEO4J_PASSWORD'))
)

with driver.session() as session:
    result = session.run("MATCH (n:Team) RETURN n.name as name LIMIT 5")
    for record in result:
        print(f"Team: {record['name']}")

driver.close()
EOF
```

---

### Step 3: 리포트 생성

```bash
# generate_full_graph_rag_report.sh 실행 시
# "Use SSH tunnel?" 질문에 'n' 입력

./generate_full_graph_rag_report.sh TOR GSW
```

---

## 📊 생성되는 리포트 예시

완전한 Graph RAG + Odds 리포트 구조:

```markdown
# 🏀 NBA Betting Analysis Report
## Golden State Warriors @ Toronto Raptors

## 📊 EXECUTIVE SUMMARY
Based on historical regime analysis and current odds, Warriors show
strong road performance with 4-1 record in similar contexts...

## 🎯 REGIME ANALYSIS
**Warriors**: Currently in "ROAD_DOMINANCE" regime (12 games, 89% confidence)
- Historical pattern: 8-2 record when facing home underdogs
- Regime started: 2025-12-15
- Key indicators: ORtg > 118, DRtg < 108

**Raptors**: In "HOME_STRUGGLE" regime (8 games, 76% confidence)
- Recent home record: 2-6
- Avg margin: -4.2 points
- Defensive rating: 114.8 (bottom 25%)

## 📈 RECENT FORM
**Warriors (Last 10)**:
- W-W-L-W-W-W-W-L-W-W (8-2)
- Avg margin: +6.8
- Road record: 4-1
- Steph Curry: 28.4 PPG, 5.2 3PM/G

**Raptors (Last 10)**:
- L-L-W-L-L-L-W-L-W-L (3-7)
- Avg margin: -5.1
- Home record: 2-4
- Scottie Barnes: 22.1 PPG (only bright spot)

## 🔥 KEY MATCHUP FACTORS
**Graph Insights**:
- Warriors have won 7 of last 10 H2H matchups
- Steph Curry shoots 42% from 3PT vs Raptors (career)
- Raptors struggle vs pick-and-roll (bottom 10 in league)

**Player Matchups**:
- Curry vs VanVleet: Historical advantage Warriors
- Draymond vs Barnes: Defensive chess match
- Warriors bench +8.4 vs Raptors bench

## 💰 ODDS EVALUATION
**Moneyline**: GSW -170, TOR +154
**Spread**: GSW -4.5 @ -101, TOR +4.5 @ -110

**Market Analysis**:
- Line opened at GSW -3.5, moved to -4.5 (sharp money on Warriors)
- 68% of public bets on Warriors (fade-the-public angle weak)
- Juice slightly favors Warriors spread (-101 vs -110)

**Value Assessment**:
Warriors -4.5 shows good value given:
- Regime analysis suggests 6+ point win
- Historical H2H: Warriors win by avg 7.2 pts
- Current form disparity (+6.8 vs -5.1)

## 🎲 BETTING RECOMMENDATION

**PRIMARY PICK**: Warriors -4.5 @ -101 ✅
- **Confidence**: HIGH (85%)
- **Edge vs Market**: 2.5 points (expected: -7, line: -4.5)
- **Bet Size**: 2 units

**SECONDARY PICK**: Warriors 1H -2.5 @ -105
- **Confidence**: MEDIUM (70%)
- **Rationale**: Warriors average +4.1 in 1H on road

**AVOID**: Raptors +4.5
- Regime data shows high blowout risk
- Recent home struggles compound

**SUGGESTED STAKE**:
- Bankroll: Assume 100 units
- Risk: 2 units (2% of bankroll)
- Expected Value: +0.85 units (42.5% ROI)

## ⚠️ RISK FACTORS

**Invalidating Scenarios**:
1. Steph Curry injury/rest (check 30min before tip)
2. Line moves to -6.5+ (too much juice)
3. Raptors announce lineup change (new players)

**Monitor**:
- Warriors played yesterday? (B2B fatigue)
- Toronto weather affecting travel
- Public betting % shifts above 75%

## 📈 GRAPH RAG INSIGHTS

**From Neo4j Analysis**:
- Warriors in 89% confidence "ROAD_DOMINANCE" regime
- Raptors in 76% confidence "HOME_STRUGGLE" regime
- H2H historical pattern: Warriors 7-3 (70%)
- Similar context games (regime match): Warriors 11-2 ATS

**Player Network Analysis**:
- Curry + Green on court: +12.4 NetRtg
- Barnes + Siakam on court: +2.1 NetRtg (vulnerable)

---

*Report Generated: 2025-12-28 19:45*
*Data Sources: Neo4j Graph DB, The Odds API, Claude Analysis*
```

---

## 🔧 트러블슈팅

### "Connection refused" - Neo4j 연결 안됨

**원인**: SSH 터널이 안 열렸거나, Neo4j 꺼짐

**해결**:
1. SSH 터널 재시작: `./connect_vps_neo4j.sh`
2. VPS에서 Neo4j 상태 확인: `systemctl status neo4j`
3. Neo4j 시작: `systemctl start neo4j`

---

### "Authentication failed" - 비밀번호 틀림

**원인**: NEO4J_PASSWORD 잘못됨

**해결**:
```bash
# VPS에서 비밀번호 재설정
ssh root@141.164.35.214
cypher-shell -u neo4j -p old_password
ALTER USER neo4j SET PASSWORD 'new_password';
```

---

### "Module not found: anthropic"

**해결**:
```bash
pip3 install anthropic
```

---

### LLM 리포트가 fallback mode로 생성됨

**원인**: ANTHROPIC_API_KEY 없거나 잘못됨

**해결**:
```bash
export ANTHROPIC_API_KEY='sk-ant-...'
echo $ANTHROPIC_API_KEY  # 확인
```

---

## 📝 완성된 워크플로우

```bash
# Terminal 1: SSH Tunnel
./connect_vps_neo4j.sh

# Terminal 2: Report Generation
export ODDS_API_KEY='b01049f1f29d61c53189799c40d66f69'
export ANTHROPIC_API_KEY='sk-ant-...'
export NEO4J_PASSWORD='...'

./generate_full_graph_rag_report.sh daily
```

**결과**:
- 7개 경기 모두 Graph RAG + Odds 통합 리포트
- 1 API call (오즈 스냅샷)
- Neo4j에서 팀 레짐, H2H, 선수 데이터
- Claude LLM으로 종합 분석

---

**Built with**: Neo4j + The Odds API + Anthropic Claude
**Optimized for**: Snapshot caching (88% API reduction)
**Local + Remote**: SSH tunnel for secure access
