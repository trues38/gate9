from utils.supabase_client import run_sql

def force_create_table():
    print("🔨 Force Creating 'youtube_transcripts' table...")
    
    # 1. Drop if exists (to be sure)
    try:
        run_sql("DROP TABLE IF EXISTS youtube_transcripts CASCADE;")
        print("   - Dropped existing table (if any).")
    except Exception as e:
        print(f"   - Drop failed (might not exist): {e}")

    # 2. Create
    sql = """
    CREATE TABLE youtube_transcripts (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        video_id TEXT UNIQUE NOT NULL,
        channel_id TEXT,
        title TEXT,
        published_at TIMESTAMP WITH TIME ZONE,
        transcript_text TEXT,
        summary TEXT,
        summary_status TEXT DEFAULT 'PENDING',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    try:
        run_sql(sql)
        print("   - CREATE TABLE command executed.")
    except Exception as e:
        print(f"   ❌ Create failed: {e}")
        return

    # 3. Verify
    try:
        res = run_sql("SELECT table_name FROM information_schema.tables WHERE table_name = 'youtube_transcripts'")
        if res:
            print(f"   ✅ Verification Success: Found table '{res[0]['table_name']}'")
        else:
            print("   ❌ Verification Failed: Table not found after creation.")
    except Exception as e:
        print(f"   ❌ Verification Error: {e}")

if __name__ == "__main__":
    force_create_table()
