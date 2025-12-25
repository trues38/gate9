
import os
import subprocess
import sys

# Define steps
STEPS = [
    {
        "name": "1. Enrich Library (Add Context)",
        "script": "/Users/js/g9/nba_data/quant_engine/enrich_upset_library.py",
        "critical": False # Can proceed even if this fails (fallback used)
    },
    {
        "name": "2. Migrate to DuckDB (SQL Init)",
        "script": "/Users/js/g9/nba_data/quant_engine/migrate_to_duckdb.py",
        "critical": True
    },
    {
        "name": "3. Vectorize to ChromaDB (Embeddings)",
        "script": "/Users/js/g9/nba_data/quant_engine/vectorize_to_chromadb.py",
        "critical": True
    }
]

def run_pipeline():
    print("====================================")
    print("   NBA FUSION ENGINE PIPELINE")
    print("====================================")
    
    for step in STEPS:
        print(f"\n[RUNNING] {step['name']}...")
        try:
            # Run script using current python interpreter
            result = subprocess.run(
                [sys.executable, step['script']], 
                check=True,
                text=True,
                capture_output=False  # Let it print to stdout
            )
            print(f"[SUCCESS] {step['name']}")
        except subprocess.CalledProcessError as e:
            print(f"[FAILED] {step['name']} (Exit Code: {e.returncode})")
            if step['critical']:
                print("Critical Step Failed. Aborting Pipeline.")
                sys.exit(1)
            else:
                print("Warning: Non-critical step failed. Proceeding with fallback...")

    print("\n====================================")
    print("   PIPELINE COMPLETED SUCCESSFULLY")
    print("====================================")
    print("Ready for Report Generation.")

if __name__ == "__main__":
    run_pipeline()
