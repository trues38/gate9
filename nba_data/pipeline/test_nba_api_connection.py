import pandas as pd
from nba_api.stats.endpoints import leaguegamelog
from datetime import datetime, timedelta

# ==========================================
# 1. 봇 차단 방지용 '신분증' (Headers)
# ==========================================
custom_headers = {
    'Host': 'stats.nba.com',
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://stats.nba.com/',
    'Origin': 'https://stats.nba.com',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9',
}

print(f"🚀 [G9 Engine] {datetime.now().strftime('%Y-%m-%d')} 데이터 동기화 중...")

try:
    # ==========================================
    # 2. 이번 시즌 최신 데이터 요청
    # ==========================================
    # timeout=15 : 15초 동안은 기다려줌 (서버 느릴 때 대비)
    print("Requesting LeagueGameLog...", flush=True)
    log = leaguegamelog.LeagueGameLog(
        season='2024-25', 
        player_or_team_abbreviation='T',
        headers=custom_headers, # 핵심: 헤더 장착
        timeout=15 
    )
    
    # 데이터프레임으로 변환
    print("Parsing DataFrame...", flush=True)
    df = log.get_data_frames()[0]
    print(f"Total rows fetched: {len(df)}")
    
    # ==========================================
    # 3. '최신' 경기만 필터링 (최근 3일치)
    # ==========================================
    # 날짜 형식 변환 (문자열 -> 날짜)
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    
    # 오늘 기준 3일 전 날짜 계산
    three_days_ago = datetime.now() - timedelta(days=3)
    
    # 최근 3일간의 경기만 추출
    recent_games = df[df['GAME_DATE'] >= three_days_ago]
    
    if not recent_games.empty:
        print(f"✅ 동기화 성공! 최근 {len(recent_games)}경기 데이터를 가져왔습니다.")
        print("-" * 30)
        # 보기 좋게 출력 (날짜, 매치업, 승패, 점수)
        print(recent_games[['GAME_DATE', 'MATCHUP', 'WL', 'PTS', 'PLUS_MINUS']].to_string(index=False))
        
        # (선택) 파일로 저장하거나 DB에 넣기
        # recent_games.to_csv("daily_update.csv", index=False)
    else:
        print("💤 최근 3일간 경기가 없거나, 아직 업데이트되지 않았습니다.")

except Exception as e:
    print(f"🚨 NBA 서버 접속 실패: {e}")
    # print("👉 팁: 1분 뒤에 다시 시도하거나, VPN을 확인하세요.")
    import traceback
    traceback.print_exc()
