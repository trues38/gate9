from auto_sql_engine.schema_loader import load_schema
from auto_sql_engine.sql_composer import compose_sql
from auto_sql_engine.sql_runner import execute_sql
from auto_sql_engine.evidence_extractor import extract_evidence

def run_auto_sql_engine(task: str):
    print(f"🚀 [Auto-SQL] Starting for task: {task}")
    
    # 1. Load Schema
    schema = load_schema()
    
    # 2. Compose SQL
    sql = compose_sql(task, schema)
    print(f"📝 [Auto-SQL] Generated SQL: {sql}")
    
    # 3. Run SQL
    raw_results = execute_sql(sql)
    print(f"📊 [Auto-SQL] Rows fetched: {len(raw_results) if isinstance(raw_results, list) else 'Error'}")
    
    # 4. Extract Evidence
    evidence_packet = extract_evidence(raw_results)
    
    return {
        "sql_queries": [sql],
        "raw_results": raw_results,
        "clean_evidence": evidence_packet
    }
