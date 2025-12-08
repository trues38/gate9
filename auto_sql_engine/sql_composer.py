from utils.openrouter_client import ask_llm, MODEL_SQL

def compose_sql(task_description, schema_json):
    prompt = f"""
    You are an expert SQL generator.
    Task: {task_description}

    Database Schema:
    {schema_json}

    Constraints:
    - Use PostgreSQL syntax
    - Only SELECT allowed
    - Never modify tables
    - ALWAYS use table `global_news_all`
    - ALWAYS add `LIMIT 20` to prevent large data fetches
    - Columns available: title, summary, published_at, country, signal_score, ticker, sentiment_label
    - **CRITICAL**: Ensure all parentheses `()` are perfectly balanced.
    - **CRITICAL**: Do NOT use complex nested subqueries unless necessary.
    - Example: SELECT title, summary FROM global_news_all WHERE country = 'KR' ORDER BY published_at DESC LIMIT 20;

    Output only raw SQL. No markdown blocks.
    """
    return ask_llm(prompt, model=MODEL_SQL)
