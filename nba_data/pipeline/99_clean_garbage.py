import json
import os
import glob
import re

# Strict Cleanup Script
# Goal: Remove any file that is NOT from a trusted DB or has garbage content.

DATA_DIR = "/Users/js/g9/nba_data/stories_raw"
TRUSTED_DOMAINS = ["espn", "yahoo", "cbssports", "nba.com", "bleacherreport", "si.com"]

def is_garbage(data):
    # 1. Check URL/Source against whitelist
    url = data.get('url', '').lower()
    source = data.get('source_domain', '').lower()
    
    is_trusted = False
    for d in TRUSTED_DOMAINS:
        if d in url or d in source:
            is_trusted = True
            break
            
    if not is_trusted:
        return True, f"Untrusted domain: {source}"

    # 2. Check for empty strings
    if not data.get('headline') or not data.get('body'):
        return True, "Empty content"

    # 3. Check for Chinese characters (Baidu/Zhihu leakage)
    if re.search(r'[\u4e00-\u9fff]', data.get('headline', '')):
        return True, "Chinese characters in headline"
        
    return False, ""

def clean():
    files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    deleted = 0
    
    print(f"Scanning {len(files)} files...")
    
    for f in files:
        try:
            with open(f, "r") as r:
                data = json.load(r)
                
            garbage, reason = is_garbage(data)
            
            if garbage:
                print(f"Deleting {os.path.basename(f)}: {reason}")
                os.remove(f)
                deleted += 1
                
        except Exception as e:
            print(f"Error reading {f}: {e}")
            
    print(f"Cleanup complete. Deleted {deleted} files.")

if __name__ == "__main__":
    clean()
