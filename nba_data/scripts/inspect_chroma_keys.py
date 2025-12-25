
import chromadb
import sys
import os

sys.path.append(os.getcwd())

def inspect():
    db_path = "/Users/js/g9/nba_data/chroma_db"
    client = chromadb.PersistentClient(path=db_path)
    try:
        coll = client.get_collection("nba_narratives")
        print(f"✅ Collection found. Count: {coll.count()}")
        
        # Peek
        res = coll.peek(limit=5)
        print("\n🔍 Sample Metadata:")
        for m in res['metadatas']:
            print(m)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect()
