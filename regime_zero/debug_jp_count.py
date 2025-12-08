import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key)

# Check JP news with score >= 6
res = supabase.table('ingest_news').select('count', count='exact').eq('country', 'JP').gte('importance_score', 6).execute()

print(f"🇯🇵 JP News with Score >= 6: {res.count}")

# Check ALL news with score >= 6
res_all = supabase.table('ingest_news').select('count', count='exact').gte('importance_score', 6).execute()
print(f"🌍 Total News with Score >= 6: {res_all.count}")
