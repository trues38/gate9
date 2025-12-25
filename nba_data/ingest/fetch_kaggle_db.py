# 1. 라이브러리 설치 (터미널에서 실행된다고 가정)
import os
try:
    import kagglehub
except ImportError:
    print("Installing kagglehub...")
    os.system('pip install kagglehub')
    import kagglehub

import sqlite3
import pandas as pd

print("🚀 [G9 Engine] 데이터 다운로드 시작...")

# ---------------------------------------------------------
# 수정된 부분: load_dataset 대신 dataset_download 사용
# 이유: SQLite DB 파일 전체를 경로(Path)로만 받아오기 위함
# ---------------------------------------------------------
path = kagglehub.dataset_download("wyattowalsh/basketball")

print(f"📂 다운로드 완료 경로: {path}")

# 폴더 내의 .sqlite 파일 찾기
db_file = os.path.join(path, "basketball.sqlite")

# DB 연결 및 데이터 로드 (Game 테이블)
if os.path.exists(db_file):
    conn = sqlite3.connect(db_file)
    
    # 최근 5경기만 샘플로 가져오기
    query = "SELECT * FROM game ORDER BY game_date DESC LIMIT 5"
    df = pd.read_sql(query, conn)
    
    print("\n✅ 최신 데이터 로드 성공!")
    print(df[['game_date', 'matchup_home', 'wl_home', 'pts_home', 'pts_away']])
    
    conn.close()
else:
    print("🚨 에러: sqlite 파일을 찾을 수 없습니다.")
