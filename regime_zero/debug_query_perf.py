import os
import time
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key)

def test_query(name, query_builder):
    start = time.time()
    try:
        res = query_builder.execute()
        duration = time.time() - start
        print(f"✅ {name}: Success ({duration:.2f}s) - Count: {len(res.data) if res.data else 0}")
    except Exception as e:
        duration = time.time() - start
        print(f"❌ {name}: Failed ({duration:.2f}s) - Error: {e}")

print("--- Starting Query Performance Test ---")

# 1. Simple Count (US)
test_query(
    "Count US News",
    supabase.table('ingest_news').select('id', count='exact').eq('country', 'US').limit(1)
)

# 2. Filter by Score (US)
test_query(
    "Filter Score >= 6 (US)",
    supabase.table('ingest_news').select('id').eq('country', 'US').gte('importance_score', 6).limit(50)
)

# 3. Filter + Sort (US) - THE SUSPECT
test_query(
    "Filter + Sort (US)",
    supabase.table('ingest_news').select('id')
    .eq('country', 'US')
    .gte('importance_score', 6)
    .order('published_at', desc=True)
    .limit(50)
)

# 4. Full Query (US) - EXACT DASHBOARD QUERY
test_query(
    "Full Dashboard Query (US)",
    supabase.table('ingest_news')
    .select('id, title, clean_title, published_at, summary, url, source, country, category, importance_score, short_summary, title_ko, summary_ko')
    .eq('country', 'US')
    .gte('importance_score', 6)
    .order('published_at', desc=True)
    .limit(50)
)

# 5. Full Query (KR)
test_query(
    "Full Dashboard Query (KR)",
    supabase.table('ingest_news')
    .select('id, title, clean_title, published_at, summary, url, source, country, category, importance_score, short_summary, title_ko, summary_ko')
    .eq('country', 'KR')
    .gte('importance_score', 6)
    .order('published_at', desc=True)
    .limit(50)
)

# 6. Time Range Fix (US)
# Try limiting to last 7 days to force index usage or reduce scan
from datetime import datetime, timedelta
seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

test_query(
    "Time Range Fix (US)",
    supabase.table('ingest_news')
    .select('id')
    .eq('country', 'US')
    .gte('importance_score', 6)
    .gte('published_at', seven_days_ago)
    .order('published_at', desc=True)
    .limit(50)
)
