import json
import os
import numpy as np
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class VectorIndexer:
    def __init__(self, master_file="regime_zero/data/regimes/master_regime_history.jsonl", index_file="regime_zero/data/regimes/vector_index.pkl"):
        self.master_file = master_file
        self.index_file = index_file
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
        self.records = []
        self.vectors = None
        
    def build_index(self):
        """Builds TF-IDF index from master regime history."""
        print("🏗️ Building Vector Index...")
        self.records = []
        corpus = []
        
        if not os.path.exists(self.master_file):
            print("❌ Master file not found.")
            return
            
        with open(self.master_file, 'r') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    self.records.append(record)
                    # Combine all text fields for indexing
                    text = record.get('summary_text', '')
                    corpus.append(text)
                except:
                    continue
                    
        if not corpus:
            print("⚠️ No data to index.")
            return
            
        # Fit Vectorizer
        self.vectors = self.vectorizer.fit_transform(corpus)
        
        # Save Index
        with open(self.index_file, 'wb') as f:
            pickle.dump({
                'vectorizer': self.vectorizer,
                'vectors': self.vectors,
                'records': self.records
            }, f)
            
        print(f"✅ Index built with {len(self.records)} records. Saved to {self.index_file}")
        
    def load_index(self):
        """Loads the index from disk."""
        if not os.path.exists(self.index_file):
            self.build_index()
            return
            
        with open(self.index_file, 'rb') as f:
            data = pickle.load(f)
            self.vectorizer = data['vectorizer']
            self.vectors = data['vectors']
            self.records = data['records']
            
    def search(self, query_text, top_k=10, filter_date=None):
        """Searches the index for similar regimes."""
        if self.vectors is None:
            self.load_index()
            
        # Transform query
        query_vec = self.vectorizer.transform([query_text])
        
        # Calculate Cosine Similarity
        # (1, N) dot (N, M).T -> (1, M)
        scores = cosine_similarity(query_vec, self.vectors).flatten()
        
        # Sort indices
        top_indices = scores.argsort()[::-1]
        
        results = []
        for idx in top_indices:
            record = self.records[idx]
            score = scores[idx]
            
            # Filter Logic
            if filter_date and record['date'] >= filter_date:
                continue
                
            if score < 0.1: # Minimum threshold
                break
                
            results.append((score, record))
            if len(results) >= top_k:
                break
                
        return results

if __name__ == "__main__":
    indexer = VectorIndexer()
    indexer.build_index()
