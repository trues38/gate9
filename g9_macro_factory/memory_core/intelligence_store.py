import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client
from utils.embedding import get_embedding_sync

TABLE_NAME = "g9_intelligence_core"

def save_intelligence_packet(packet, embed=False):
    """
    Upserts an Intelligence Packet to g9_intelligence_core.
    
    Args:
        packet (dict): The intelligence data.
        embed (bool): Whether to generate embedding immediately. Default False to save cost.
    """
    supabase = get_supabase_client()
    
    # 1. Generate Embedding (Optional)
    embedding = None
    if embed:
        macro_str = json.dumps(packet.get("macro_env", {}), sort_keys=True)
        embed_text = f"""
        Date: {packet.get('target_date')}
        Ticker: {packet.get('ticker')}
        Macro: {macro_str}
        Pattern: {packet.get('pattern_id')}
        Logic: {packet.get('final_logic')}
        """
        
        try:
            embedding = get_embedding_sync(embed_text)
        except Exception as e:
            print(f"   ⚠️ Failed to generate embedding for intelligence packet: {e}")
            embedding = None
    else:
        # print("   ⏩ Skipping embedding generation (Cost Saving Mode)")
        pass

    import math
    
    def sanitize(val):
        if isinstance(val, float):
            if math.isnan(val) or math.isinf(val):
                return None
        elif isinstance(val, dict):
            return {k: sanitize(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [sanitize(v) for v in val]
        return val

    record = {
        "target_date": packet.get("target_date"),
        "ticker": packet.get("ticker"),
        "sector": packet.get("sector"),
        "z_score": sanitize(packet.get("z_score")),
        "macro_env": sanitize(packet.get("macro_env")), 
        "pattern_id": packet.get("pattern_id"),
        "strategy_type": packet.get("strategy_type"),
        "confidence_score": sanitize(packet.get("confidence_score")),
        "final_logic": packet.get("final_logic"),
        "return_3d": sanitize(packet.get("return_3d")),
        "return_7d": sanitize(packet.get("return_7d")),
        "success_flag": packet.get("success_flag"),
        "embedding": embedding
    }
    
    # Deep sanitize macro_env if needed
    if record["macro_env"]:
        try:
            # Check if json dumpable
            json.dumps(record["macro_env"])
        except:
            # If not, try to clean
            # For now assume macro_processor returns clean data (it rounds to 2 decimals)
            pass
    
    # 3. Upsert
    try:
        # We don't have a unique constraint on (date, ticker) yet in SQL, 
        # but usually we want to insert new runs.
        # If we want to update, we need an ID. 
        # For now, let's just INSERT.
        res = supabase.table(TABLE_NAME).insert(record).execute()
        print(f"   🧠 Intelligence Saved: {packet.get('ticker')} on {packet.get('target_date')}")
        return True
    except Exception as e:
        print(f"   ❌ Failed to save intelligence: {e}")
        return False
