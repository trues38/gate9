import os
from supabase import create_client, ClientOptions
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()  # ← 이 한 줄이 환경변수를 로드한다

# ===============================
# 1) 환경변수 로드
# ===============================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError("❌ 환경변수 SUPABASE_URL 또는 SUPABASE_KEY(SERVICE_KEY) 누락")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY, options=ClientOptions(schema="mm"))

# ===============================
# 2) 문지기(7B) → 정제 기준 (간단 버전)
# ===============================
import re
from bs4 import BeautifulSoup

# ... (imports remain the same, but we need to add re and bs4)

# ===============================
# 2) 문지기(7B) → 정제 기준 (간단 버전)
# ===============================
def clean_text(text: str):
    """요약과 HTML 제거 등 기본 정제"""
    if not text:
        return None

    # 1. HTML 제거 (BeautifulSoup)
    try:
        soup = BeautifulSoup(text, "html.parser")
        text = soup.get_text(separator=" ")
    except Exception:
        pass  # BS4 실패 시 원본 유지 혹은 추가 처리

    # 2. 공백 정규화 (연속된 공백 -> 공백 1개)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def clean_event(row: dict):
    """단일 이벤트 정제"""
    return {
        "raw_id": row.get("id"),
        "title": row.get("title"),
        "clean_text": clean_text(row.get("raw_text") or row.get("summary")),
        "summary": clean_text(row.get("summary")),
        "category": row.get("category"),
        "tickers": [row.get("ticker")] if row.get("ticker") else [],
        "keywords": row.get("keywords"),
        "sentiment": row.get("sentiment"),
        "published_at": row.get("published_at"),
        "source": row.get("publisher"),
        "country": row.get("country"),
    }


# ===============================
# 3) Supabase에서 RAW 읽어오기
# ===============================
def fetch_raw_events(start: int, end: int):
    # range is inclusive of start, exclusive of end in Python slicing, 
    # but Supabase range is inclusive-inclusive usually. 
    # Let's check supabase-py docs or assume standard 0-indexed offset.
    # .range(0, 9) returns 10 items.
    res = supabase.table("events").select("*").range(start, end).execute()
    return res.data or []


# ===============================
# 4) 정제 후 Supabase에 저장
# ===============================
def save_cleaned(clean_rows: list):
    if not clean_rows:
        return

    res = supabase.table("events_cleaned").insert(clean_rows).execute()
    # print(f"✔ Supabase 저장 완료: {len(clean_rows)} rows")


# ===============================
# 5) 전체 실행
# ===============================
def run(total_limit=100000, batch_size=1000):
    print(f"\n� 총 {total_limit}개 이벤트 정제 시작 (Batch Size: {batch_size})...")
    
    processed_count = 0
    
    for start in range(0, total_limit, batch_size):
        end = start + batch_size - 1
        
        # 1. Fetch
        raw_events = fetch_raw_events(start, end)
        if not raw_events:
            print(f"🏁 더 이상 데이터가 없습니다. (Processed: {processed_count})")
            break
            
        # 2. Clean
        cleaned = []
        for r in raw_events:
            c = clean_event(r)
            if c:
                cleaned.append(c)
        
        # 3. Save
        if cleaned:
            save_cleaned(cleaned)
            processed_count += len(cleaned)
            print(f"✔ Batch {start}~{end}: {len(cleaned)}개 저장 완료 (누적: {processed_count})")
        else:
            print(f"⚠ Batch {start}~{end}: 저장할 데이터 없음")

    print(f"\n✨ 전체 완료! 총 {processed_count}개 정제됨.")


if __name__ == "__main__":
    # 10만개 처리
    run(total_limit=500000, batch_size=1000)