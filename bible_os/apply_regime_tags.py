import duckdb
from regime_definitions import REGIMES

DB_PATH = "./data/db/bible.duckdb"

def main():
    con = duckdb.connect(DB_PATH)
    
    # Pre-process keywords for efficiency
    # Structure: [ ("R01", ["wilderness", "desert", ...]), ... ]
    # We use regex for word boundary matching, or simple substring? 
    # Let's start with simple substring inclusion for broader matching, 
    # but KJV is archaic. "eat" is in "create" -> Bad.
    # We MUST use word boundaries.
    
    import re
    
    regime_matchers = []
    
    print("Compiling regex patterns...")
    for r_code, r_data in REGIMES.items():
        keywords = r_data.get("keywords_en", [])
        if not keywords:
            continue
            
        # Create a combined regex for this regime: \b(word1|word2|...)\b
        # Escape keywords just in case
        escaped_keywords = [re.escape(k) for k in keywords]
        pattern_str = r'\b(' + '|'.join(escaped_keywords) + r')\b'
        pattern = re.compile(pattern_str, re.IGNORECASE)
        
        regime_matchers.append((r_code, pattern))
        
    print(f"Prepared {len(regime_matchers)} regime matchers.")
    
    # Fetch all verses
    # We only need ID and Text. We generally use KJV for regime matching as decided (richer imagery).
    print("Fetching verses...")
    verses = con.execute("SELECT id, text_kjv FROM verses").fetchall()
    
    print(f"Processing {len(verses)} verses...")
    
    updates = []
    
    for vid, text in verses:
        if not text:
            continue
            
        tags = []
        for r_code, pattern in regime_matchers:
            if pattern.search(text):
                tags.append(r_code)
        
        if tags:
            # DuckDB list format for update? or just pass list in executemany
            updates.append((tags, vid))
            
    print(f"Found tags for {len(updates)} verses.")
    
    # Update DB
    # We can use executemany with UPDATE
    print("Updating database...")
    con.executemany("UPDATE verses SET regime_tags = ? WHERE id = ?", updates)
    
    # Verify
    count = con.execute("SELECT count(*) FROM verses WHERE regime_tags IS NOT NULL").fetchone()[0]
    print(f"Verses with tags: {count}")
    
    sample = con.execute("SELECT id, text_kjv, regime_tags FROM verses WHERE len(regime_tags) > 0 LIMIT 5").fetchall()
    for s in sample:
        print(f"{s[0]} | {s[2]} | {s[1][:50]}...")
        
    con.close()

if __name__ == "__main__":
    main()
