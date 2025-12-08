import os
import re
import duckdb
import glob
from regime_definitions import REGIMES

# Config
DATA_DIR = "./data/txt"
DB_PATH = "./data/db/bible.duckdb"

# Ensure DB dir exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Connect to DuckDB
con = duckdb.connect(DB_PATH)

# Create Logic Scheme
# We use a primitive ARRAY for regime_tags initially
con.execute("""
CREATE TABLE IF NOT EXISTS verses (
    id VARCHAR PRIMARY KEY,
    book_name VARCHAR,
    chapter INT,
    verse INT,
    section_title VARCHAR,
    text_korean VARCHAR,
    regime_tags VARCHAR[],
    embedding FLOAT[]
);
""")

print(f"DB initialized at {DB_PATH}")

def get_regime_tags(text):
    tags = []
    for rid, rdata in REGIMES.items():
        for kw in rdata['keywords']:
            if kw in text:
                tags.append(rid)
                break # One hit per regime is enough to tag it candidate
    return tags

def parse_line(line, filename_book):
    # Regex: [BookChar][Chap]:[Verse] (<Section>)? [Text]
    # Example: 창1:1 <천지 창조> 태초에...
    # But sometimes the book char is 1 or 2 chars?
    # Actually, looking at the file `1-01...txt`, the line starts with `창1:1`.
    
    # We will be loose: match parsed "BookAndChap:Verse" then split
    pattern = r"^(\S+?):(\d+)\s*(<.*?>)?\s*(.*)"
    match = re.match(pattern, line.strip())
    
    if not match:
        return None
        
    ref_part = match.group(1) # 창1
    verse_num = int(match.group(2))
    section = match.group(3) if match.group(3) else ""
    text = match.group(4)
    
    # Separate Book / Chapter from ref_part (e.g. 창1 -> 창, 1)
    # Finding where the number starts
    split_match = re.search(r"\d", ref_part)
    if not split_match:
        return None
    
    idx = split_match.start()
    book_abbr = ref_part[:idx]
    chapter_num = int(ref_part[idx:])
    
    # Clean section title
    if section:
        section = section.strip("<> ")
        
    return {
        "id": f"{book_abbr}-{chapter_num}-{verse_num}",
        "book": book_abbr,
        "chapter": chapter_num,
        "verse": verse_num,
        "section": section,
        "text": text
    }

files = sorted(glob.glob(os.path.join(DATA_DIR, "*.txt")))
print(f"Found {len(files)} files.")

total_inserted = 0

for filepath in files:
    filename = os.path.basename(filepath)
    # print(f"Processing {filename}...")
    
    batch_data = []
    
    try:
        # EUC-KR encoding is critical here
        with open(filepath, 'r', encoding='euc-kr', errors='replace') as f:
            for line in f:
                if not line.strip(): continue
                
                parsed = parse_line(line, filename)
                if parsed:
                    tags = get_regime_tags(parsed['text'])
                    batch_data.append((
                        parsed['id'],
                        parsed['book'],
                        parsed['chapter'],
                        parsed['verse'],
                        parsed['section'],
                        parsed['text'],
                        tags,
                        None # Embedding placeholder
                    ))
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        continue
        
    if batch_data:
        # Bulk Insert
        try:
            con.executemany("""
                INSERT OR IGNORE INTO verses 
                (id, book_name, chapter, verse, section_title, text_korean, regime_tags, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, batch_data)
            total_inserted += len(batch_data)
        except Exception as e:
             print(f"Error inserting batch for {filename}: {e}")

print(f"Successfully digested {total_inserted} verses into DuckDB.")
con.close()
