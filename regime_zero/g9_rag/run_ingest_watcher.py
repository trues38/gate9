import os
import json
import time
import shutil
from antigravity_ingest import ingest

DROPZONE_DIR = os.path.join(os.path.dirname(__file__), "dropzone")
ARCHIVE_DIR = os.path.join(os.path.dirname(__file__), "archive")

def process_files():
    print(f"👀 Watching {DROPZONE_DIR} for new JSON reports...")
    
    # Ensure directories exist
    os.makedirs(DROPZONE_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    files = [f for f in os.listdir(DROPZONE_DIR) if f.endswith('.json')]
    
    if not files:
        print("   (No files found. Waiting...)")
        return

    for filename in files:
        file_path = os.path.join(DROPZONE_DIR, filename)
        print(f"\n📄 Found: {filename}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Ingest
            result = ingest(data)
            
            # Check result
            # ingest returns a list if input is list, or dict if input is dict
            success = False
            if isinstance(result, list):
                success = all(r.get('stored', False) for r in result)
                error_msg = [r.get('error') for r in result if not r.get('stored')]
            else:
                success = result.get('stored', False)
                error_msg = result.get('error')

            if success:
                print(f"   ✅ Ingestion Successful.")
                # Move to archive
                shutil.move(file_path, os.path.join(ARCHIVE_DIR, f"{int(time.time())}_{filename}"))
                print(f"   📦 Archived to {ARCHIVE_DIR}")
            else:
                print(f"   ❌ Ingestion Failed: {error_msg}")
                # Don't move, let user fix
                
        except json.JSONDecodeError:
            print(f"   ❌ Invalid JSON format.")
        except Exception as e:
            print(f"   ❌ Error processing file: {e}")

if __name__ == "__main__":
    # Single run or loop? User asked "Where do I upload", implying a process.
    # Let's run once. If they want a daemon, they can loop it.
    process_files()
