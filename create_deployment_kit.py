import os
import shutil

def create_kit():
    kit_dir = "g9_deploy"
    if os.path.exists(kit_dir):
        shutil.rmtree(kit_dir)
    os.makedirs(kit_dir)
    
    # Define files to copy (Source -> Dest)
    files = [
        ("ticker_global/news_summary_pipeline.py", "ticker_global/news_summary_pipeline.py"),
        ("utils/openrouter_client.py", "utils/openrouter_client.py"),
        ("utils/__init__.py", "utils/__init__.py"), # Just in case
        (".env", ".env")
    ]
    
    print(f"📦 Creating Deployment Kit in '{kit_dir}'...")
    
    for src, dest in files:
        # Create subdirs if needed
        dest_path = os.path.join(kit_dir, dest)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        if os.path.exists(src):
            shutil.copy2(src, dest_path)
            print(f"   ✅ Copied: {src}")
        else:
            if "utils/__init__.py" in src:
                # Create empty __init__.py if missing
                with open(dest_path, 'w') as f: pass
                print(f"   ✅ Created: {dest} (Empty)")
            else:
                print(f"   ❌ Missing: {src}")

    # Create requirements.txt
    reqs = """supabase
python-dotenv
"""
    with open(os.path.join(kit_dir, "requirements.txt"), "w") as f:
        f.write(reqs)
    print(f"   ✅ Created: requirements.txt")
    
    print(f"\n🎉 Kit Ready! Size is minimal.")
    print(f"   1. Copy 'g9_deploy' folder to other computers.")
    print(f"   2. Run: pip install -r requirements.txt")
    print(f"   3. Run the pipeline commands.")

if __name__ == "__main__":
    create_kit()
