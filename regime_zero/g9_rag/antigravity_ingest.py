import os
import json
import httpx
import time
from typing import List, Dict, Union, Any
from dotenv import load_dotenv
from supabase import create_client, Client

# === CONFIG ===
load_dotenv(override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
EMBEDDING_MODEL = "text-embedding-3-small"

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize HTTP Client for OpenRouter
headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "https://github.com/gate9/g9-rag",
    "X-Title": "G9 Antigravity Engine",
    "Content-Type": "application/json"
}

# === Antigravity Engine ===

def get_embedding(text: str, retries=3) -> List[float]:
    """Generates embedding using OpenRouter."""
    for attempt in range(retries):
        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{OPENROUTER_BASE_URL}/embeddings",
                    headers=headers,
                    json={
                        "model": EMBEDDING_MODEL,
                        "input": text
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data['data'][0]['embedding']
        except Exception as e:
            if attempt == retries - 1:
                print(f"❌ Embedding failed: {e}")
                raise
            time.sleep(2 ** attempt)
    return []

def store_report(report: Dict[str, Any]):
    print(f"🔄 Ingesting report: {report.get('headline', 'Untitled')[:30]}...")
    
    # 1) Embedding 생성
    embedding_text = report.get("embedding_text", "")
    if not embedding_text:
        # Fallback construction if missing
        embedding_text = f"{report.get('headline', '')} {report.get('final_thesis', '')} {report.get('dominant_narrative', '')}"
    
    embedding = get_embedding(embedding_text)

    # 2) DB Insert Payload 변환
    # Ensure nested dicts are handled if input structure differs slightly
    # The user provided structure:
    # report["analysis"]["thesis"] -> final_thesis
    # report["analysis"]["narrative"] -> dominant_narrative
    # ...
    
    # We need to be robust. If keys are missing, use defaults.
    analysis = report.get("analysis", {})
    action_items = report.get("action_items", {})
    
    payload = {
        "date": report.get("date"),
        "headline": report.get("headline"),
        "pattern_ids": report.get("pattern_ids", []),
        "final_thesis": analysis.get("thesis", report.get("final_thesis")),
        "dominant_narrative": analysis.get("narrative", report.get("dominant_narrative")),
        "strategy_bias": analysis.get("strategy_bias", report.get("strategy_bias")),
        "confirmed_signals": analysis.get("signals", report.get("confirmed_signals", [])),
        "weak_points": analysis.get("risks", report.get("weak_points", [])),
        "counter_scenario": analysis.get("counter_scenario", report.get("counter_scenario")),
        "next_iteration_checklist": action_items.get("checklist", report.get("next_iteration_checklist", [])),
        "embedding_text": embedding_text,
        "embedding": embedding,
        "quality_score": report.get("quality_score", 95)
    }

    # 3) Supabase Insert
    try:
        response = supabase.table("antigravity_reports").insert(payload).execute()
        print(f"   ✅ Stored successfully.")
        return {"stored": True, "id": response.data[0]['id'] if response.data else None}
    except Exception as e:
        print(f"   ❌ Insert failed: {e}")
        return {"stored": False, "error": str(e)}

def ingest(json_input: Union[Dict, List[Dict]]):
    """
    Main entry point for ingestion.
    Accepts a single dict or a list of dicts.
    """
    if isinstance(json_input, list):
        results = []
        for r in json_input:
            results.append(store_report(r))
        return results
    else:
        return store_report(json_input)

# ===== Usage Example =====
if __name__ == "__main__":
    # Test with a dummy report
    test_report = {
        "date": "2025-11-27",
        "headline": "Test Report: Auto-Ingest Engine Live",
        "pattern_ids": ["P-001", "P-002"],
        "embedding_text": "Test report for Antigravity Auto-Ingest Engine. Verifying embedding and storage.",
        "analysis": {
            "thesis": "The engine is operational.",
            "narrative": "Automation is key.",
            "strategy_bias": "Aggressive",
            "signals": ["Code running", "DB connected"],
            "risks": ["API limits"],
            "counter_scenario": "Network failure"
        },
        "action_items": {
            "checklist": ["Verify DB", "Check Logs"]
        },
        "quality_score": 99
    }
    
    print("🧪 Running Test Ingestion...")
    result = ingest(test_report)
    print(f"Result: {result}")
