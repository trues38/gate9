import pandas as pd
import re
import os
from difflib import SequenceMatcher
from tqdm import tqdm

# ==========================================
# Step 1: Rule-based Cleaning (Regex)
# ==========================================
def clean_headline(text):
    if not isinstance(text, str):
        return ""
    
    # 1. 말머리 제거: [속보], (종합), [특징주] 등
    text = re.sub(r'^\[.*?\]', '', text)
    text = re.sub(r'^\(.*?\)', '', text)
    
    # 2. 끝부분 기자명/언론사명 제거: ... = OOO 기자, - 이데일리 등
    text = re.sub(r'[=-].*?기자$', '', text)
    text = re.sub(r'[=-].*?특파원$', '', text)
    text = re.sub(r' - .*$', '', text) # " - 언론사명" 제거
    
    # 3. 불필요한 특수문자 및 공백 정리
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def is_noise(text):
    # 광고, 부고, 인사, 단순 공시 등 노이즈 필터링
    noise_keywords = ["부고", "인사", "게시판", "포토", "화보", "오늘의 운세", "동정", "모집"]
    for kw in noise_keywords:
        if kw in text:
            return True
    return False

# ==========================================
# Step 2: Semantic Deduplication (Similarity)
# ==========================================
def deduplicate_similar(df, threshold=0.85):
    # Sort by title length (descending) to keep the longest/most informative one
    df['title_len'] = df['title'].apply(len)
    df = df.sort_values('title_len', ascending=False)
    
    kept_indices = []
    seen_titles = [] # Keep track of titles we've decided to keep
    
    print("Running deduplication (this may take a while)...")
    
    # Simple O(N^2) is too slow for 100k+ rows. 
    # Optimization: Group by date or first few chars?
    # For now, let's just do exact dedup first, then similarity on smaller chunks if needed.
    # Actually, for 120k rows, full similarity is hard. 
    # Let's do:
    # 1. Exact Dedup
    # 2. Fuzzy Dedup within same 'published_at' (day) and 'ticker' group
    
    # 1. Exact Dedup
    df = df.drop_duplicates(subset=['title'])
    
    # 2. Group-wise Fuzzy Dedup
    # Group by Ticker + Date (YYYY-MM-DD)
    df['date_str'] = df['published_at'].astype(str).str[:10]
    
    final_rows = []
    
    grouped = df.groupby(['ticker', 'date_str'])
    
    for name, group in tqdm(grouped, desc="Deduplicating groups"):
        titles = group['title'].tolist()
        indices = group.index.tolist()
        
        group_kept = []
        group_seen_titles = []
        
        for i, title in enumerate(titles):
            is_dup = False
            for seen_title in group_seen_titles:
                # Check similarity
                ratio = SequenceMatcher(None, title, seen_title).ratio()
                if ratio > threshold:
                    is_dup = True
                    break
            
            if not is_dup:
                group_kept.append(indices[i])
                group_seen_titles.append(title)
        
        final_rows.extend(group_kept)
        
    return df.loc[final_rows].drop(columns=['title_len', 'date_str'])

def run_pipeline(input_path, output_path):
    print(f"Loading data from {input_path}...")
    df = pd.read_csv(input_path)
    original_len = len(df)
    print(f"Original rows: {original_len}")
    
    # --- Step 1: Cleaning ---
    print("Step 1: Cleaning text...")
    df['title'] = df['title'].apply(clean_headline)
    df = df[~df['title'].apply(is_noise)]
    print(f"Rows after cleaning: {len(df)}")
    
    # --- Step 2: Deduplication ---
    print("Step 2: Deduplicating...")
    df = deduplicate_similar(df)
    print(f"Rows after deduplication: {len(df)}")
    
    print(f"Saving to {output_path}...")
    df.to_csv(output_path, index=False)
    print("Done!")

if __name__ == "__main__":
    # Adjust paths as needed
    BASE_DIR = "/Users/js/g9"
    # The file is in "ticker_global/KR/csv/" (underscore)
    INPUT_CSV = os.path.join(BASE_DIR, "ticker_global/KR/csv/merged_events_extended.csv")
    OUTPUT_CSV = os.path.join(BASE_DIR, "ticker_global/KR/cleaned_events_final.csv")
    
    if not os.path.exists(INPUT_CSV):
        print(f"Error: Input file not found at {INPUT_CSV}")
        exit(1)
        
    run_pipeline(INPUT_CSV, OUTPUT_CSV)
