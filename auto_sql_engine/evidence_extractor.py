from utils.openrouter_client import ask_llm

def extract_evidence(sql_result):
    prompt = f"""
    You are Evidence Extractor.
    Here is SQL data:
    {sql_result}

    Summarize patterns, anomalies, correlations in bullet points.
    Return as JSON with key "clean_evidence".
    """
    response = ask_llm(prompt)
    try:
        import json
        import re
        # Try to find JSON block if it's wrapped in markdown
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        return json.loads(response)
    except Exception as e:
        print(f"⚠️ Failed to parse Evidence JSON: {e}")
        return {"clean_evidence": response}
