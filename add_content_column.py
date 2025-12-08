from g9_macro_factory.config import get_supabase_client

def add_columns():
    sb = get_supabase_client()
    print("Adding 'content' column to summary tables...")
    
    # We can't execute DDL directly via supabase-py client usually, unless we use rpc or raw sql if enabled.
    # But we can try to use the 'rpc' if we have a function, or just rely on the user to run SQL.
    # Wait, the user has 'Auto-SQL' capability? No, I am the agent.
    # I can try to use a workaround or ask the user.
    # But wait, I created tables before using `create_tables.py` which likely used a workaround or just standard inserts?
    # No, I used `create_tables.py` which printed SQL instructions for the user?
    # Or I used `run_command` to execute psql?
    # I don't have psql access.
    # I can try to use the `rpc` method if there is a `exec_sql` function.
    # Or I can just use the `add_report_constraints.py` approach? No that was constraints.
    
    # Actually, Supabase Python client doesn't support DDL.
    # I should check if I can use the `postgres` library or if I should just ask the user.
    # BUT, I can try to "update" a row with a new key in a JSONB column? No, `content` is a column.
    
    # Let's try to use a raw SQL execution if possible.
    # If not, I will notify the user.
    # BUT, I can try to use `psycopg2` if installed?
    # Or `subprocess` to run `psql`?
    # I don't have the password.
    
    # Wait, I can use the `sql` tool? No, I don't have it.
    
    # I will notify the user to run the SQL.
    # "Please run this SQL in Supabase SQL Editor".
    pass

if __name__ == "__main__":
    print("Please run the following SQL in Supabase:")
    print("ALTER TABLE weekly_summaries ADD COLUMN IF NOT EXISTS content JSONB;")
    print("ALTER TABLE monthly_summaries ADD COLUMN IF NOT EXISTS content JSONB;")
    print("ALTER TABLE yearly_summaries ADD COLUMN IF NOT EXISTS content JSONB;")
# 시스템 파일 무시
.DS_Store
Thumbs.db

# 파이썬 관련 무시 (가장 중요)
__pycache__/
*.py[cod]
*$py.class
venv/
.venv/
env/

# 데이터 파일 무시 (크롤링한거 수천개)
data/
*.csv
*.json
*.log

# AI 에디터 설정 무시
.cursor/
.vscode/

# 만약 regime_zero 결과물이 너무 많다면
regime_zero/reports/