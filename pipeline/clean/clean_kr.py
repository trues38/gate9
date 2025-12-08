import os
import re
import time
from dotenv import load_dotenv
from supabase import create_client
from bs4 import BeautifulSoup

# =============================
# 0) Load ENV
# =============================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError("❌ 환경변수 SUPABASE_URL 또는 SUPABASE_SERVICE_KEY 누락")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =============================
# 1) Clean Helper Functions
# =============================

def strip_html(text):
    """본문 HTML 태그 제거"""
    if not text:
        return ""
    try:
        return BeautifulSoup(text, "html.parser").get_text(separator=" ").strip()
    except:
        return text

def normalize(text):
    """여분의 공백, 개행 제거"""
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\t", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def clean_event(row):
    """이벤트 1개 정제"""
    title = normalize(row.get("title", ""))

    # raw 텍스트 → HTML 제거 → Normalize
    raw_text = row.get("raw_text") or row.get("summary") or ""
    clean_text = normalize(strip_html(raw_text))

    return {
        "raw_id": row["id"],
        "title": title,
        "clean_text": clean_text,
        "published_at": row.get("published_at"),
        "country": row.get("country"),
        "source": row.get("publisher") or row.get("platform"),
        "summary": None,
        "category": None,
        "tickers": None,
        "keywords": None,
        "sentiment": None,
    }

# =============================
# 2) Load RAW (KR Only + Dedup)
# =============================

def load_raw_kr(limit=100):
    """
    한국(KR) 데이터만 + title 중복 제거
    """
    print(f"📥 RAW 이벤트(KR only) 가져오기 (limit={limit})...")

    res = (
        supabase.schema("mm").table("events") \
        .select("*") \
        .eq("country", "KR") \
        .limit(limit * 3) \
        .execute()
    )

    rows = res.data
    print(f"📌 가져온 개수(중복 포함): {len(rows)}")

    # ======== 🔥 제목 기준 중복 제거 ========
    seen = set()
    unique = []
    for r in rows:
        title = r.get("title", "").strip()
        if title and title not in seen:
            seen.add(title)
            unique.append(r)
        if len(unique) >= limit:
            break

    print(f"✨ 중복 제거 후 사용: {len(unique)}개")
    return unique

# =============================
# 3) Save cleaned data
# =============================

def save_clean(rows_cleaned):
    print(f"🧹 정제 완료: {len(rows_cleaned)}개 → 저장 시작")
    for c in rows_cleaned:
        try:
            supabase.schema("mm").table("events_cleaned").insert(c).execute()
        except Exception as e:
            print("⚠ 저장 오류:", e)


# =============================
# 4) Main
# =============================

def run(limit=100):
    rows = load_raw_kr(limit)
    cleaned = [clean_event(r) for r in rows]
    save_clean(cleaned)
    print("\n🎉 TEST CLEAN 100건 완료!")


if __name__ == "__main__":
    run(100)