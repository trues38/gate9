import sqlite3
import os

def check_db():
    db_path = "nba_state.db"
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return

    print(f"📂 Validating Database: {db_path} ...\n")
    
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        
        # 1. Count Reports
        cur.execute("SELECT COUNT(*) FROM reports")
        count = cur.fetchone()[0]
        print(f"📊 Total Reports Stored: {count}")
        print("-" * 60)
        
        # 2. List Reports
        print(f"{'GAME ID':<15} | {'MODEL USED':<25} | {'SIZE (Bytes)':<12} | {'CREATED AT':<20}")
        print("-" * 60)
        
        cur.execute("SELECT game_id, model_used, length(content_html), created_at FROM reports ORDER BY created_at DESC")
        rows = cur.fetchall()
        
        for row in rows:
            # GameID, Model, Size, Time
            g_id = row[0]
            model = row[1][:25] # truncate for display
            size = row[2]
            time = row[3]
            print(f"{g_id:<15} | {model:<25} | {size:<12} | {time:<20}")
            
        print("-" * 60)
        
        # 3. Check Schedule Table
        cur.execute("SELECT COUNT(*) FROM game_schedule")
        sched_count = cur.fetchone()[0]
        print(f"\n📅 Schedule Cache: {sched_count} games found.")
        
        con.close()
        
    except Exception as e:
        print(f"❌ Error reading DB: {e}")

if __name__ == "__main__":
    check_db()
