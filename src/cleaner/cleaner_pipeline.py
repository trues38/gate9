from supabase import create_client, ClientOptions
from core.config import settings
from cleaner.final_cleaner import clean_text

opts = ClientOptions(schema="mm")
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY, options=opts)

def run_cleaning_job(limit: int = 500):
    """
    - events에서 아직 clean되지 않은 항목 불러오기
    - clean 후 events_cleaned에 저장
    """

    raw_rows = (
        supabase.table("events")
        .select("*")
        .order("published_at", desc=False)
        .limit(limit)
        .execute()
        .data
    )

    print(f"🔍 Loaded {len(raw_rows)} raw events")

    for row in raw_rows:
        cleaned = clean_text(row.get("raw_text", ""))

        payload = {
            "raw_id": row["id"],
            "title": row["title"],
            "clean_text": cleaned,
            "summary": row.get("summary"),
            "category": row.get("category"),
            "tickers": [row.get("ticker")] if row.get("ticker") else None,
            "keywords": row.get("keywords"),
            "sentiment": row.get("sentiment"),
            "published_at": row.get("published_at"),
            "source": row.get("publisher"),
            "country": row.get("country"),
        }

        supabase.table("events_cleaned").insert(payload).execute()

    print("🎉 Clean job finished!")