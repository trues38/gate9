from flask import Flask, jsonify, request
from neo4j import GraphDatabase
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import os
import logging
import re
import hashlib
from xml.etree import ElementTree as ET
from collections import defaultdict

app = Flask(__name__)

# ============ 중복 방지 & 인스턴스 관리 ============
seen_hashes = set()  # 최근 24시간 해시 (메모리, 재시작시 초기화)
instance_failures = defaultdict(int)  # 인스턴스별 연속 실패 횟수
instance_cooldown = {}  # 인스턴스 쿨다운 시간

# 소스 신뢰도 점수
SOURCE_CREDIBILITY = {
    'ShamsCharania': 1.0,
    'wojespn': 1.0,
    'OfficialNBARefs': 0.95,
    'FantasyLabsNBA': 0.85,
    'underaboremblba': 0.8,
    # beat writers
    'LakersReporter': 0.7,
    'WarriorsWorld': 0.7,
    # default
    '_default': 0.3
}

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Neo4j 연결
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://neo4j-nba:7687')
NEO4J_USER = os.getenv('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'nba_vultr_2025')

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# ESPN API Base URL
ESPN_BASE = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba"

# Nitter 인스턴스
NITTER_INSTANCES = [
    'https://nitter.net',
    'https://nitter.poast.org',
    'https://nitter.privacydev.net',
    'https://nitter.cz'
]

# NBA 화이트리스트 (Tier 1: 가장 신뢰)
NBA_WHITELIST = [
    'ShamsCharania', 'wojespn',  # Top-tier insiders
    'OfficialNBARefs',            # Official refs
    'FantasyLabsNBA',             # Injury aggregator
    'underaboremblba'             # Injury specialist
]

# ============ 스케줄 체크 ============

def check_today_schedule():
    """오늘 경기 있는지 확인"""
    today = datetime.now().strftime('%Y%m%d')
    url = f"{ESPN_BASE}/scoreboard"
    params = {"dates": today}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        games = data.get('events', [])
        return len(games) > 0, games
    except Exception as e:
        logger.error(f"스케줄 확인 실패: {e}")
        return False, []

# ============ 실시간 이벤트 수집 ============

def fetch_nitter_rss(account):
    """Nitter RSS 가져오기 (fallback + 쿨다운 포함)"""
    now = datetime.now()

    for instance in NITTER_INSTANCES:
        # 쿨다운 체크 (30분간 skip)
        if instance in instance_cooldown:
            if now < instance_cooldown[instance]:
                logger.debug(f"{instance} 쿨다운 중 - 스킵")
                continue
            else:
                del instance_cooldown[instance]
                instance_failures[instance] = 0

        url = f"{instance}/{account}/rss"
        try:
            response = requests.get(url, timeout=6)
            if response.status_code == 200:
                instance_failures[instance] = 0  # 성공시 리셋
                return response.text, instance
            else:
                instance_failures[instance] += 1
        except:
            instance_failures[instance] += 1

        # 3회 연속 실패 → 30분 쿨다운
        if instance_failures[instance] >= 3:
            instance_cooldown[instance] = now + timedelta(minutes=30)
            logger.warning(f"{instance} 3회 연속 실패 → 30분 쿨다운")

    return None, None


def get_text_hash(text):
    """텍스트 해시 생성"""
    normalized = re.sub(r'\s+', ' ', text.lower().strip())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def is_duplicate(text):
    """중복 체크"""
    text_hash = get_text_hash(text)
    if text_hash in seen_hashes:
        return True
    seen_hashes.add(text_hash)
    return False


def cleanup_old_hashes():
    """오래된 해시 정리 (24시간 주기로 호출)"""
    global seen_hashes
    seen_hashes = set()
    logger.info("해시 캐시 초기화 완료")

def parse_rss(rss_content):
    """RSS XML 파싱"""
    if not rss_content:
        return []

    try:
        root = ET.fromstring(rss_content)
        items = []

        for item in root.findall('.//item'):
            title = item.find('title')
            description = item.find('description')
            pubDate = item.find('pubDate')
            link = item.find('link')

            items.append({
                'title': title.text if title is not None else '',
                'description': description.text if description is not None else '',
                'pubDate': pubDate.text if pubDate is not None else '',
                'link': link.text if link is not None else ''
            })

        return items
    except Exception as e:
        logger.error(f"RSS 파싱 실패: {e}")
        return []

def filter_recent_posts(items, hours=1):
    """최근 N시간 포스트만 필터"""
    cutoff = datetime.now() - timedelta(hours=hours)
    recent = []

    for item in items:
        # RSS pubDate 파싱 (예: "Thu, 26 Dec 2024 12:30:00 GMT")
        try:
            pub_date = datetime.strptime(item['pubDate'], '%a, %d %b %Y %H:%M:%S %Z')
            if pub_date > cutoff:
                recent.append(item)
        except:
            # 파싱 실패하면 포함
            recent.append(item)

    return recent

def filter_keywords(items):
    """키워드 필터링"""
    keywords = [
        r'\b(out|gtd|questionable|doubtful|probable)\b',
        r'\b(injury|injured|sprain|strain|soreness)\b',
        r'\b(lineup|starting|will start|bench)\b',
        r'\b(referee|official|crew chief)\b',
        r'\b(trade|waive|sign|acquire)\b'
    ]

    filtered = []
    for item in items:
        text = item['title'] + ' ' + item['description']
        if any(re.search(kw, text, re.IGNORECASE) for kw in keywords):
            filtered.append(item)

    return filtered

def parse_nba_event_logic(text):
    """로직 기반 파싱 (LLM 없이)"""
    patterns = {
        'status': r'\b(OUT|GTD|QUESTIONABLE|DOUBTFUL|PROBABLE|ACTIVE|AVAILABLE)\b',
        'player': r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        'team': r'(Lakers|Warriors|Celtics|Heat|Knicks|Nets|Sixers|76ers|Bucks|Clippers|Nuggets|Suns|Mavericks|Mavs|Grizzlies|Pelicans|Thunder|Timberwolves|Wolves|Blazers|Trail Blazers|Kings|Spurs|Rockets|Jazz|Hawks|Hornets|Bulls|Cavaliers|Cavs|Pistons|Pacers|Magic|Raptors|Wizards)',
        'reason': r'\(([^)]+)\)',
        'reasonKeyword': r'(ankle|knee|back|hamstring|shoulder|wrist|elbow|hip|foot|calf|quad|illness|rest|load management|personal|concussion)'
    }

    status_match = re.search(patterns['status'], text, re.IGNORECASE)
    status = status_match.group(0).upper() if status_match else 'UNKNOWN'

    player_match = re.search(patterns['player'], text)
    player = player_match.group(0) if player_match else 'Unknown'

    team_match = re.search(patterns['team'], text, re.IGNORECASE)
    team = team_match.group(0) if team_match else 'Unknown'

    reason = 'unknown'
    paren_match = re.search(patterns['reason'], text)
    if paren_match:
        reason = paren_match.group(1).lower()
    else:
        reason_match = re.search(patterns['reasonKeyword'], text, re.IGNORECASE)
        if reason_match:
            reason = reason_match.group(0).lower()

    event_type = 'injury'
    if re.search(r'\b(crew chief|referee|official)\b', text, re.IGNORECASE):
        event_type = 'referee'
    elif re.search(r'\b(starting lineup|will start)\b', text, re.IGNORECASE):
        event_type = 'lineup'
    elif re.search(r'\b(trade|waive|sign)\b', text, re.IGNORECASE):
        event_type = 'trade'

    game_match = re.search(r'(vs|at|against)\s+([A-Z]{3}|[A-Z][a-z]+)', text, re.IGNORECASE)
    game = game_match.group(0) if game_match else ''

    return {
        'event_type': event_type,
        'player': player,
        'team': team,
        'status': status,
        'reason': reason,
        'game': game,
        'confidence': 0.9 if status != 'UNKNOWN' and player != 'Unknown' else 0.5
    }

def save_nba_event(event_data, raw_text, source_account):
    """Neo4j에 NBA 이벤트 저장 (소스 신뢰도 포함)"""
    try:
        with driver.session() as session:
            text_hash = get_text_hash(raw_text)
            event_id = f'nba_rt_{text_hash}'

            # 소스 신뢰도
            credibility = SOURCE_CREDIBILITY.get(source_account, SOURCE_CREDIBILITY['_default'])

            query = """
            MERGE (e:NBAEvent {event_id: $event_id})
            ON CREATE SET
                e.type = $type,
                e.player = $player,
                e.team = $team,
                e.status = $status,
                e.reason = $reason,
                e.game = $game,
                e.confidence = toFloat($confidence),
                e.source_account = $source_account,
                e.source_credibility = toFloat($credibility),
                e.cost_usd = 0.0,
                e.raw_text = $raw_text,
                e.text_hash = $text_hash,
                e.created_at = datetime()
            RETURN e
            """

            session.run(query, {
                'event_id': event_id,
                'type': event_data['event_type'],
                'player': event_data['player'],
                'team': event_data['team'],
                'status': event_data['status'],
                'reason': event_data['reason'],
                'game': event_data['game'],
                'confidence': event_data['confidence'],
                'source_account': source_account,
                'credibility': credibility,
                'raw_text': raw_text,
                'text_hash': text_hash
            })

            logger.info(f"[{source_account}:{credibility}] {event_data['player']} {event_data['status']}")
            return True

    except Exception as e:
        logger.error(f"Neo4j 저장 실패: {e}")
        return False

def check_realtime_events():
    """실시간 이벤트 체크 (크론으로 호출)"""
    # 1. 오늘 경기 있는지 확인
    has_games, games = check_today_schedule()
    if not has_games:
        logger.info("오늘 경기 없음 - 실시간 체크 스킵")
        return

    logger.info(f"오늘 {len(games)}개 경기 - 실시간 이벤트 체크 시작")

    total_events = 0
    duplicates_skipped = 0

    # 2. 화이트리스트 계정별로 체크
    for account in NBA_WHITELIST:
        rss_content, used_instance = fetch_nitter_rss(account)
        if not rss_content:
            logger.warning(f"{account} RSS 가져오기 실패 (모든 인스턴스)")
            continue

        items = parse_rss(rss_content)
        recent = filter_recent_posts(items, hours=1)  # 최근 1시간
        filtered = filter_keywords(recent)

        logger.info(f"{account} via {used_instance}: {len(filtered)}개 후보")

        for item in filtered:
            text = item['title'] + ' ' + item['description']

            # 중복 체크
            if is_duplicate(text):
                duplicates_skipped += 1
                continue

            event_data = parse_nba_event_logic(text)

            if save_nba_event(event_data, text, account):
                total_events += 1

    logger.info(f"실시간 체크 완료 - 저장: {total_events}, 중복스킵: {duplicates_skipped}")

# ============ 박스스코어 수집 ============

def fetch_scoreboard(date_str):
    """ESPN API에서 스코어보드 가져오기"""
    url = f"{ESPN_BASE}/scoreboard"
    params = {"dates": date_str}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"스코어보드 가져오기 실패: {e}")
        return None

def fetch_game_details(game_id):
    """특정 게임의 박스스코어 가져오기"""
    url = f"{ESPN_BASE}/summary"
    params = {"event": game_id}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"게임 {game_id} 가져오기 실패: {e}")
        return None

def save_boxscore_to_neo4j(game_data):
    """박스스코어를 Neo4j에 저장"""
    if not game_data:
        return False

    try:
        with driver.session() as session:
            game_id = game_data.get('header', {}).get('id')
            if not game_id:
                return False

            competition = game_data.get('header', {}).get('competitions', [{}])[0]
            home_team = competition.get('competitors', [{}])[0]
            away_team = competition.get('competitors', [{}])[1] if len(competition.get('competitors', [])) > 1 else {}

            query = """
            MERGE (g:Game {game_id: $game_id})
            SET g.date = $date,
                g.home_team = $home_team,
                g.away_team = $away_team,
                g.home_score = toInteger($home_score),
                g.away_score = toInteger($away_score),
                g.status = $status,
                g.updated_at = datetime()
            RETURN g
            """

            result = session.run(query, {
                'game_id': game_id,
                'date': game_data.get('header', {}).get('season', {}).get('year'),
                'home_team': home_team.get('team', {}).get('abbreviation'),
                'away_team': away_team.get('team', {}).get('abbreviation'),
                'home_score': home_team.get('score', 0),
                'away_score': away_team.get('score', 0),
                'status': competition.get('status', {}).get('type', {}).get('description', 'Unknown')
            })

            logger.info(f"게임 {game_id} Neo4j 저장 완료")
            return True

    except Exception as e:
        logger.error(f"Neo4j 저장 실패: {e}")
        return False

def collect_yesterday_games():
    """어제 경기들의 박스스코어 수집"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    logger.info(f"어제({yesterday}) 경기 수집 시작")

    scoreboard = fetch_scoreboard(yesterday)
    if not scoreboard:
        logger.warning("스코어보드 가져오기 실패")
        return

    games = scoreboard.get('events', [])
    logger.info(f"{len(games)}개 경기 발견")

    for game in games:
        game_id = game.get('id')
        status = game.get('status', {}).get('type', {}).get('state')

        if status == 'post':
            logger.info(f"게임 {game_id} 상세 정보 수집 중...")
            game_details = fetch_game_details(game_id)
            if game_details:
                save_boxscore_to_neo4j(game_details)

    logger.info("어제 경기 수집 완료")

# ============ API 엔드포인트 ============

@app.route('/health', methods=['GET'])
def health():
    """헬스 체크"""
    return jsonify({"status": "healthy", "service": "NBA API (Boxscore + Realtime)"})

@app.route('/check/realtime', methods=['POST'])
def check_realtime():
    """실시간 이벤트 수동 체크"""
    try:
        check_realtime_events()
        return jsonify({"status": "success", "message": "실시간 이벤트 체크 완료"})
    except Exception as e:
        logger.error(f"실시간 체크 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/collect/yesterday', methods=['POST'])
def collect_yesterday():
    """어제 경기 수동 수집"""
    try:
        collect_yesterday_games()
        return jsonify({"status": "success", "message": "어제 경기 수집 완료"})
    except Exception as e:
        logger.error(f"수집 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/collect/date', methods=['POST'])
def collect_by_date():
    """특정 날짜 경기 수집"""
    date_str = request.json.get('date')
    if not date_str:
        return jsonify({"status": "error", "message": "date 파라미터 필요"}), 400

    try:
        scoreboard = fetch_scoreboard(date_str)
        if not scoreboard:
            return jsonify({"status": "error", "message": "스코어보드 가져오기 실패"}), 500

        games = scoreboard.get('events', [])
        collected = 0

        for game in games:
            game_id = game.get('id')
            status = game.get('status', {}).get('type', {}).get('state')

            if status == 'post':
                game_details = fetch_game_details(game_id)
                if game_details and save_boxscore_to_neo4j(game_details):
                    collected += 1

        return jsonify({
            "status": "success",
            "date": date_str,
            "total_games": len(games),
            "collected": collected
        })

    except Exception as e:
        logger.error(f"수집 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ============ 스케줄러 설정 ============

scheduler = BackgroundScheduler()

# 매일 오전 9시: 어제 박스스코어 수집
scheduler.add_job(func=collect_yesterday_games, trigger="cron", hour=9, minute=0)

# 경기 시간대 (한국시간 오전 7시 ~ 오후 3시): 5분마다 실시간 이벤트 체크
scheduler.add_job(func=check_realtime_events, trigger="cron", hour='7-15', minute='*/5')

# 매일 자정: 해시 캐시 초기화
scheduler.add_job(func=cleanup_old_hashes, trigger="cron", hour=0, minute=0)

scheduler.start()

if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("NBA API 시작 (Boxscore + Realtime)")
    logger.info("=" * 50)
    logger.info(f"Neo4j 연결: {NEO4J_URI}")
    logger.info("스케줄러:")
    logger.info("  - 매일 오전 9시: 어제 박스스코어 수집")
    logger.info("  - 오전 7시~오후 3시: 5분마다 실시간 이벤트 체크")
    logger.info("  - 매일 자정: 해시 캐시 초기화")
    logger.info("=" * 50)

    app.run(host='0.0.0.0', port=8000, debug=False)
