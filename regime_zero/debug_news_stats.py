import os
from supabase import create_client
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key)

# Fetch all news
res = supabase.table('ingest_news').select('country').execute()

# Count by Country
stats = Counter([x.get('country', 'UNKNOWN') for x in res.data])

print("\n📊 Raw News Distribution by Country:")
for country, count in stats.most_common():
    print(f"   - {country}: {count}")
