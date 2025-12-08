from utils.supabase_client import run_sql

def setup_youtube_table():
    print("🚀 Setting up YouTube Transcripts Table...")

    # Drop table if it exists to force recreation with new schema
    drop_table_sql = "DROP TABLE IF EXISTS youtube_transcripts CASCADE;"
    print(f"Executing: {drop_table_sql}")
    try:
        run_sql(drop_table_sql)
        print("✅ Existing 'youtube_transcripts' table dropped (if it existed).")
    except Exception as e:
        print(f"❌ Failed to drop table: {e}")

    create_table_sql = """
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
    print(f"Executing: CREATE TABLE youtube_transcripts...")
    try:
        res = run_sql(create_table_sql)
        print("✅ Table 'youtube_transcripts' created.")
    except Exception as e:
        print(f"❌ Failed to create table: {e}")

if __name__ == "__main__":
    setup_youtube_table()
