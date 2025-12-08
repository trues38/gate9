import os
import shutil

def create_youtube_kit():
    kit_dir = "youtube_deploy"
    if os.path.exists(kit_dir):
        shutil.rmtree(kit_dir)
    os.makedirs(kit_dir)
    
    # Define files to copy (Source -> Dest)
    files = [
        ("src/ingest/youtube/youtube_pipeline.py", "youtube_pipeline.py"), # Flatten structure for ease
        ("utils/openrouter_client.py", "utils/openrouter_client.py"),
        ("utils/__init__.py", "utils/__init__.py"),
        (".env", ".env")
    ]
    
    print(f"📦 Creating YouTube Deployment Kit in '{kit_dir}'...")
    
    for src, dest in files:
        # Create subdirs if needed
        dest_path = os.path.join(kit_dir, dest)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        if os.path.exists(src):
            shutil.copy2(src, dest_path)
            print(f"   ✅ Copied: {src} -> {dest}")
        else:
            if "utils/__init__.py" in src:
                with open(dest_path, 'w') as f: pass
                print(f"   ✅ Created: {dest} (Empty)")
            else:
                print(f"   ❌ Missing: {src}")

    # Create requirements.txt
    reqs = """supabase
python-dotenv
youtube-transcript-api
"""
    with open(os.path.join(kit_dir, "requirements.txt"), "w") as f:
        f.write(reqs)
    print(f"   ✅ Created: requirements.txt")
    
    # Create a helper script to run it easily since we flattened the path
    run_script = """
import sys
import os
# Add current dir to path so utils can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import youtube_pipeline

if __name__ == "__main__":
    # Pass arguments to the pipeline
    youtube_pipeline.main() 
"""
    # Wait, youtube_pipeline.py has its own __main__ block. 
    # But since we moved it to root of deploy folder, imports inside it might break if they expect 'utils' to be at ../../utils
    # Let's check youtube_pipeline.py imports.
    # It does: sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    # This tries to go up 4 levels to find root.
    # In deploy kit:
    # youtube_deploy/
    #   youtube_pipeline.py
    #   utils/
    #     openrouter_client.py
    #
    # So youtube_pipeline.py needs to find 'utils'. 'utils' is in the SAME directory.
    # We need to patch youtube_pipeline.py in the kit to look in current dir.
    
    print(f"\n🔧 Patching youtube_pipeline.py for deployment structure...")
    
    target_pipeline = os.path.join(kit_dir, "youtube_pipeline.py")
    with open(target_pipeline, 'r') as f:
        content = f.read()
        
    # Replace the deep path appending with simple current dir appending
    new_content = content.replace(
        "sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))",
        "sys.path.append(os.path.dirname(os.path.abspath(__file__)))"
    )
    
    with open(target_pipeline, 'w') as f:
        f.write(new_content)
        
    print(f"   ✅ Patched import path in youtube_pipeline.py")

    print(f"\n🎉 YouTube Kit Ready!")
    print(f"   1. Copy 'youtube_deploy' folder.")
    print(f"   2. Run: pip install -r requirements.txt")
    print(f"   3. Run: python3 youtube_pipeline.py --video_id <ID> (or --file list.txt)")

if __name__ == "__main__":
    create_youtube_kit()
