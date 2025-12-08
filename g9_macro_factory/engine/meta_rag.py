import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client

import json
import numpy as np

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def check_meta_fail_log(embedding, threshold=0.45):
    """
    Checks Meta-RAG for similar past failures.
    Uses Python-side cosine similarity.
    [v1.9] Supports Risk Weighting and Override Levels (HARD/SOFT).
    """
    supabase = get_supabase_client()
    
    try:
        # Fetch all failure logs
        res = supabase.table("g9_meta_rag").select("*").execute()
        logs = res.data
        
        if not logs:
            return None
            
        best_match = None
        best_score = -1.0
        best_weighted_score = -1.0
        
        for log in logs:
            if not log.get('embedding'):
                continue
                
            # Parse embedding
            vec = json.loads(log['embedding']) if isinstance(log['embedding'], str) else log['embedding']
            
            score = cosine_similarity(embedding, vec)
            
            # [v1.9] Calculate Weighted Score
            try:
                reason_json = json.loads(log.get('fail_reason', '{}'))
                risk_weight = reason_json.get('risk_weight', 1.0)
            except:
                risk_weight = 1.0
                
            weighted_score = score * risk_weight
            
            # Check if this log is the best match based on WEIGHTED score?
            # Or raw similarity? Usually raw similarity determines "match", weight determines "impact".
            # Let's stick to finding the most similar event first, then applying weight.
            # OR, should we prioritize high-risk events even if slightly less similar?
            # User said: "final_score = similarity * risk_weight".
            # So we should maximize final_score.
            
            if weighted_score > best_weighted_score:
                best_weighted_score = weighted_score
                best_score = score
                best_match = log
                best_match['similarity'] = score # Raw similarity
                best_match['weighted_score'] = weighted_score
                best_match['risk_weight'] = risk_weight

        # Determine Override Level
        if best_match:
            final_score = best_match['weighted_score']
            
            if final_score >= 0.55:
                best_match['override_level'] = 'HARD'
            elif final_score >= 0.40:
                best_match['override_level'] = 'SOFT'
            else:
                return None # No override
                
            return best_match
            
    except Exception as e:
        print(f"⚠️ Meta-RAG Check Failed: {e}")
        
    return None

def save_meta_fail_log(pattern_id, reason, rule, regime, embedding):
    """
    Saves a failure case to Meta-RAG.
    """
    supabase = get_supabase_client()
    try:
        data = {
            "origin_pattern_id": pattern_id,
            "fail_reason": reason,
            "correction_rule": rule,
            "regime_context": regime,
            "embedding": embedding
        }
        supabase.table("g9_meta_rag").insert(data).execute()
        print(f"📝 Saved failure to Meta-RAG: {pattern_id}")
    except Exception as e:
        print(f"❌ Failed to save to Meta-RAG: {e}")

def update_meta_fail_log(log_id, reason):
    """
    Updates an existing Meta-RAG record (e.g., increasing risk_weight).
    """
    supabase = get_supabase_client()
    try:
        supabase.table("g9_meta_rag").update({"fail_reason": reason}).eq("id", log_id).execute()
        print(f"🔄 Updated Meta-RAG Log ID: {log_id}")
    except Exception as e:
        print(f"❌ Failed to update Meta-RAG: {e}")
