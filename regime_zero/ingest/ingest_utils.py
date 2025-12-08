import re
import hashlib
import os
import pandas as pd

class RegexCleaner:
    """Filters out noise and spam using Regex."""
    def __init__(self, custom_blacklist=None):
        # Default global blacklist
        self.exclude_patterns = [
            r"(?i)sponsored",
            r"(?i)press release",
            r"(?i)promoted",
            r"(?i)gamble",
            r"(?i)casino",
            r"(?i)sex",
            r"(?i)porn",
            r"(?i)dating",
            r"(?i)18\+",
            r"(?i)subscribe",
            r"(?i)newsletter",
            r"(?i)advertorial",
            r"(?i)bonus",
            r"(?i)prediction", # User requested removal of predictions
            r"(?i)forecast",
            r"(?i)price analysis"
        ]
        
        if custom_blacklist:
            self.exclude_patterns.extend(custom_blacklist)
            
        self.compiled_patterns = [re.compile(p) for p in self.exclude_patterns]

    def is_clean(self, text):
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                return False
        return True
    
    def clean_title(self, title):
        # Remove common suffixes
        clean = title
        separators = [" - ", " | "]
        for sep in separators:
            if sep in clean:
                clean = clean.rsplit(sep, 1)[0]
        return clean.strip()

class DeduplicationFilter:
    """
    Simulates a Bloom Filter using a Set of Hashes.
    """
    def __init__(self):
        self.seen_hashes = set()
    
    def _get_hash(self, text):
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def add(self, text):
        h = self._get_hash(text)
        self.seen_hashes.add(h)
        
    def exists(self, text):
        h = self._get_hash(text)
        return h in self.seen_hashes
    
    def load_existing(self, filepath):
        if os.path.exists(filepath):
            print(f"🔄 Loading existing data from {filepath} for deduplication...")
            try:
                df = pd.read_csv(filepath)
                # Assume duplicates are based on Title + Date
                count = 0
                for _, row in df.iterrows():
                    # Handle potential missing date
                    pub = str(row.get('published', ''))
                    unique_str = f"{row['title']}|{pub}"
                    self.add(unique_str)
                    count += 1
                print(f"✅ Loaded {count} unique items into filter.")
            except Exception as e:
                print(f"⚠️ Failed to load existing data: {e}")

class KeywordFilter:
    """
    Whitelists titles based on keywords.
    """
    def __init__(self, keywords):
        self.keywords = [k.lower() for k in keywords]
        
    def passes(self, text):
        text_lower = text.lower()
        for k in self.keywords:
            if k in text_lower:
                return True
        return False
