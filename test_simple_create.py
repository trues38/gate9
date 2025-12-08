from utils.supabase_client import run_sql

def simple_create():
    print("🧪 Testing Simple Table Creation...")
    
    # Simple create
    sql = "CREATE TABLE test_simple (id text primary key)"
    try:
        res = run_sql(sql)
        print(f"   Result: {res}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    # Verify
    try:
        res = run_sql("SELECT table_name FROM information_schema.tables WHERE table_name = 'test_simple'")
        print(f"   Verification: {res}")
    except Exception as e:
        print(f"   ❌ Verify Failed: {e}")

if __name__ == "__main__":
    simple_create()
