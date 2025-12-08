import os
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key)

# Time filter: Last 24 hours
one_day_ago = (datetime.utcnow() - timedelta(days=1)).isoformat()

print(f"--- News Stats Since {one_day_ago} ---")

# 1. Total News
res = supabase.table('ingest_news').select('id', count='exact').gte('published_at', one_day_ago).execute()
total = res.count
print(f"Total News: {total}")

# 2. Refined vs Unrefined
res_refined = supabase.table('ingest_news').select('id', count='exact').gte('published_at', one_day_ago).eq('is_refined', True).execute()
print(f"Refined: {res_refined.count}")

res_unrefined = supabase.table('ingest_news').select('id', count='exact').gte('published_at', one_day_ago).eq('is_refined', False).execute()
print(f"Unrefined: {res_unrefined.count}")

# 3. Score Distribution (Refined only)
res_score_0 = supabase.table('ingest_news').select('id', count='exact').gte('published_at', one_day_ago).eq('is_refined', True).eq('importance_score', 0).execute()
print(f"Refined but Score 0: {res_score_0.count}")

res_score_high = supabase.table('ingest_news').select('id', count='exact').gte('published_at', one_day_ago).gte('importance_score', 6).execute()
print(f"High Score (>=6): {res_score_high.count}")

# 4. KR Specifics
print("\n--- KR News Stats ---")
res_kr = supabase.table('ingest_news').select('id', count='exact').gte('published_at', one_day_ago).eq('country', 'KR').execute()
print(f"Total KR News: {res_kr.count}")

res_kr_refined = supabase.table('ingest_news').select('id', count='exact').gte('published_at', one_day_ago).eq('country', 'KR').eq('is_refined', True).execute()
print(f"Refined KR News: {res_kr_refined.count}")

res_kr_score_0 = supabase.table('ingest_news').select('id', count='exact').gte('published_at', one_day_ago).eq('country', 'KR').eq('is_refined', True).eq('importance_score', 0).execute()
print(f"Refined KR News with Score 0: {res_kr_score_0.count}")
