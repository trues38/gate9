import sqlite3
import webbrowser
import os
import sys
from pathlib import Path

DB_PATH = "nba_state.db"

def list_recent_reports(cur):
    print("\n📜 Recent Reports in DB:")
    print("-" * 50)
    print(f"{'GAME ID':<12} | {'MODEL':<20} | {'DATE'}")
    print("-" * 50)
    
    cur.execute("SELECT game_id, model_used, created_at FROM reports ORDER BY created_at DESC LIMIT 10")
    rows = cur.fetchall()
    
    for row in rows:
        print(f"{row[0]:<12} | {row[1]:<20} | {row[2]}")
    print("-" * 50)

def view_report(game_id):
    if not os.path.exists(DB_PATH):
        print("❌ Database not found.")
        return

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    # Check if ID exists
    cur.execute("SELECT content_html, model_used FROM reports WHERE game_id=?", (game_id,))
    result = cur.fetchone()
    
    if not result:
        print(f"❌ Report for Game ID '{game_id}' not found.")
        list_recent_reports(cur)
        con.close()
        return

    content, model = result
    con.close()
    
    # Save to Temp File
    temp_dir = Path("temp_views")
    temp_dir.mkdir(exist_ok=True)
    temp_file = temp_dir / f"view_{game_id}.html"
    
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"\n✅ Extracted Report (Model: {model})")
    print(f"🚀 Opening in Browser: {temp_file}")
    
    # Open in Browser
    webbrowser.open(f"file://{temp_file.absolute()}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 db_viewer.py <GAME_ID>")
        # If no arg, just list options
        con = sqlite3.connect(DB_PATH)
        list_recent_reports(con.cursor())
        con.close()
    else:
        view_report(sys.argv[1])
