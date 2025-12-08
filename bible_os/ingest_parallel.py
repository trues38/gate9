import os
import json
import duckdb
import glob
from collections import defaultdict

# Config
KJV_PATH = "./data/json_raw/kjv.json"
WEB_DIR = "./data/json_raw/web_repo/json"
DB_PATH = "./data/db/bible.duckdb"

# Standard Protestant Bible Order (66 Books)
BOOK_ORDER = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", 
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", 
    "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", 
    "Nehemiah", "Esther", "Job", "Psalms", "Proverbs", 
    "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations", 
    "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", 
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", 
    "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts", 
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians", 
    "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians", "1 Timothy", 
    "2 Timothy", "Titus", "Philemon", "Hebrews", "James", 
    "1 Peter", "2 Peter", "1 John", "2 John", "3 John", 
    "Jude", "Revelation"
]

BOOK_ABBRS = {
    "Genesis": "GEN", "Exodus": "EXO", "Leviticus": "LEV", "Numbers": "NUM", "Deuteronomy": "DEU",
    "Joshua": "JOS", "Judges": "JDG", "Ruth": "RUT", "1 Samuel": "1SA", "2 Samuel": "2SA",
    "1 Kings": "1KI", "2 Kings": "2KI", "1 Chronicles": "1CH", "2 Chronicles": "2CH", "Ezra": "EZR",
    "Nehemiah": "NEH", "Esther": "EST", "Job": "JOB", "Psalms": "PSA", "Proverbs": "PRO",
    "Ecclesiastes": "ECC", "Song of Solomon": "SOS", "Isaiah": "ISA", "Jeremiah": "JER", "Lamentations": "LAM",
    "Ezekiel": "EZE", "Daniel": "DAN", "Hosea": "HOS", "Joel": "JOL", "Amos": "AMO",
    "Obadiah": "OBA", "Jonah": "JON", "Micah": "MIC", "Nahum": "NAM", "Habakkuk": "HAB",
    "Zephaniah": "ZEP", "Haggai": "HAG", "Zechariah": "ZEC", "Malachi": "MAL",
    "Matthew": "MAT", "Mark": "MAR", "Luke": "LUK", "John": "JHN", "Acts": "ACT",
    "Romans": "ROM", "1 Corinthians": "1CO", "2 Corinthians": "2CO", "Galatians": "GAL", "Ephesians": "EPH",
    "Philippians": "PHP", "Colossians": "COL", "1 Thessalonians": "1TH", "2 Thessalonians": "2TH", "1 Timothy": "1TI",
    "2 Timothy": "2TI", "Titus": "TIT", "Philemon": "PHM", "Hebrews": "HEB", "James": "JAS",
    "1 Peter": "1PE", "2 Peter": "2PE", "1 John": "1JN", "2 John": "2JN", "3 John": "3JN",
    "Jude": "JUD", "Revelation": "REV"
}

def get_web_filename(book_name):
    """Maps standard book name to TehShrike WEB json filename."""
    # Special cases
    if book_name == "Song of Solomon": return "songofsolomon.json"
    # General rule: lowercase, remove spaces
    return book_name.lower().replace(" ", "") + ".json"

def load_web_book(filepath):
    """Parses WEB JSON into a dict: {(chapter, verse): text}"""
    if not os.path.exists(filepath):
        print(f"Warning: WEB file not found: {filepath}")
        return {}
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    verses = defaultdict(str)
    
    for item in data:
        # We look for items with chapterNumber and verseNumber
        # item types: 'paragraph text', 'line text', 'stanza start' (ignore), etc.
        if 'chapterNumber' in item and 'verseNumber' in item and 'value' in item:
            ch = item['chapterNumber']
            vs = item['verseNumber']
            val = item['value']
            
            # Key: (ch, vs)
            verses[(ch, vs)] += val
            
    # Clean up whitespace
    return {k: v.strip() for k, v in verses.items()}

# --- Main Logic ---

# 1. Init DB
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
con = duckdb.connect(DB_PATH)
con.execute("DROP TABLE IF EXISTS verses")
con.execute("""
CREATE TABLE verses (
    id VARCHAR PRIMARY KEY,
    book_name VARCHAR,
    book_abbr VARCHAR,
    chapter INT,
    verse INT,
    text_kjv VARCHAR,
    text_web VARCHAR,
    regime_tags VARCHAR[],
    embedding FLOAT[]
);
""")
print("DuckDB schema initialized.")

# 2. Load KJV
print(f"Loading KJV from {KJV_PATH}...")
with open(KJV_PATH, 'r', encoding='utf-8-sig') as f:
    kjv_data = json.load(f)

if len(kjv_data) != 66:
    print(f"Warning: KJV JSON has {len(kjv_data)} books (expected 66). Attempting to proceed mapping by index.")

# 3. Iterate and Merge
total_verses = 0
batch_data = []
BATCH_SIZE = 5000

for i, kjv_book in enumerate(kjv_data):
    if i >= len(BOOK_ORDER): break
    
    book_name = BOOK_ORDER[i]
    book_abbr = BOOK_ABBRS.get(book_name, book_name[:3].upper())
    
    # Load corresponding WEB data
    web_filename = get_web_filename(book_name)
    web_path = os.path.join(WEB_DIR, web_filename)
    web_verses_map = load_web_book(web_path)
    
    print(f"Processing {book_name} ({len(web_verses_map)} WEB verses found)...")
    
    # Iterate KJV chapters
    chapters = kjv_book['chapters']
    for ch_idx, verses_list in enumerate(chapters):
        chapter_num = ch_idx + 1
        
        for v_idx, kjv_text in enumerate(verses_list):
            verse_num = v_idx + 1
            
            # ID: GEN-1-1
            verse_id = f"{book_abbr}-{chapter_num}-{verse_num}"
            
            # Match WEB
            web_text = web_verses_map.get((chapter_num, verse_num), "")
            
            # If WEB is missing but KJV exists, we still insert KJV (common in edge cases)
            # If both missing, skip (unlikely)
            
            batch_data.append((
                verse_id,
                book_name,
                book_abbr,
                chapter_num,
                verse_num,
                kjv_text.strip(),
                web_text,
                None, # tags
                None  # embedding
            ))
            
            if len(batch_data) >= BATCH_SIZE:
                con.executemany("INSERT INTO verses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", batch_data)
                total_verses += len(batch_data)
                batch_data = []

# Flush remaining
if batch_data:
    con.executemany("INSERT INTO verses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", batch_data)
    total_verses += len(batch_data)

print(f"Completed! Total verses inserted: {total_verses}")

# Verify
count = con.execute("SELECT count(*) FROM verses").fetchone()[0]
print(f"DB Row Count: {count}")
sample = con.execute("SELECT * FROM verses WHERE id = 'GEN-1-1'").fetchone()
print(f"Sample (GEN-1-1): {sample}")

con.close()
