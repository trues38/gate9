import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
# Sometimes it's DIRECT_URL or POSTGRES_URL
if not DATABASE_URL:
    DATABASE_URL = os.environ.get("DIRECT_URL")
if not DATABASE_URL:
    DATABASE_URL = os.environ.get("POSTGRES_URL")

if not DATABASE_URL:
    print("❌ Error: DATABASE_URL not found in environment variables.")
    exit(1)

SQL_FILE = "regime_zero/infra/create_news_raw.sql"

try:
    print(f"🔌 Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    with open(SQL_FILE, 'r') as f:
        sql = f.read()
        
    print(f"🚀 Executing {SQL_FILE}...")
    cur.execute(sql)
    conn.commit()
    
    print("✅ Migration successful!")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Migration failed: {e}")
    exit(1)
