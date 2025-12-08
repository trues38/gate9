import os
import sys
# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.supabase_client import run_sql

def check_rpc():
    print("🔍 Checking run_sql RPC with DDL...")
    try:
        # Try to create a temp table
        res1 = run_sql("CREATE TABLE IF NOT EXISTS test_rpc_table (id INT);")
        print(f"Create Result: {res1}")
        
        # Insert
        res2 = run_sql("INSERT INTO test_rpc_table (id) VALUES (123);")
        print(f"Insert Result: {res2}")
        
        # Select
        res3 = run_sql("SELECT * FROM test_rpc_table;")
        print(f"Select Result: {res3}")
        
        # Drop
        res4 = run_sql("DROP TABLE test_rpc_table;")
        print(f"Drop Result: {res4}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_rpc()
