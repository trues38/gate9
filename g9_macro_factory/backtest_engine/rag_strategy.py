import os
import sys
import json
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client, TABLE_PRICE_DAILY
from g9_macro_factory.utils.ticker_standardizer import get_standardizer
from utils.embedding import get_embedding_sync

# Load environment variables
load_dotenv(override=True)

# Initialize OpenAI client
api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
base_url = "https://openrouter.ai/api/v1" if os.getenv("OPENROUTER_API_KEY") else None

client = OpenAI(api_key=api_key, base_url=base_url)

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def retrieve_relevant_patterns(context_text, top_k=3):
    """
    Retrieves top_k relevant patterns from macro_patterns table.
    Uses Python-side cosine similarity to avoid DB RPC dependency.
    """
    supabase = get_supabase_client()
    
    # 1. Get Embedding for Context
    try:
        # Summarize context if too long for embedding model
        embed_text = context_text[:8000] 
        query_vec = get_embedding_sync(embed_text)
    except Exception as e:
        print(f"   ⚠️ Failed to embed context: {e}")
        return []

    if not query_vec:
        return []

    # 2. Fetch All Patterns
    try:
        res = supabase.table("macro_patterns").select("pattern_id, title, core, embedding").execute()
        patterns = res.data
    except Exception as e:
        print(f"   ⚠️ Failed to fetch patterns: {e}")
        return []

    if not patterns:
        return []

    # 3. Compute Similarity
    scored_patterns = []
    for p in patterns:
        if not p.get('embedding'):
            continue
        vec = json.loads(p['embedding']) if isinstance(p['embedding'], str) else p['embedding']
        score = cosine_similarity(query_vec, vec)
        scored_patterns.append((score, p))

    # 4. Sort and Return
    scored_patterns.sort(key=lambda x: x[0], reverse=True)
    return [p for score, p in scored_patterns[:top_k]]

def generate_strategy(news_items, scores=None, patterns=None, macro_state=None, context_data=None):
    """
    Analyzes news items and generates trading strategies using Pattern RAG.
    Returns a list of dicts: [{ticker, action, reason, confidence}]
    """
    if not news_items:
        return []

    print("   🧠 Generating strategies from news (with Pattern RAG)...")
    
    # Prepare Context
    context_lines = []
    for item in news_items[:50]: # Limit to top 50 for focus
        line = f"[{item['published_at']}] {item['ticker']}: {item['title']} - {item['summary']}"
        context_lines.append(line)
        
    context_text = "\n".join(context_lines)
    
    # 1. Retrieve Patterns (if not provided)
    if patterns is None:
        patterns = retrieve_relevant_patterns(context_text)
        
    pattern_context = ""
    if patterns:
        pattern_context = "Relevant Historical Patterns:\n"
        for p in patterns:
            # Handle refined patterns (v1.5)
            p_id = p.get('refined_id', p.get('pattern_id'))
            pattern_context += f"- [{p_id}] {p['title']}: {p['core']}\n"
    
    # 2. Fetch Valid Tickers
    supabase = get_supabase_client()
    try:
        # Fetch distinct tickers from price_daily
        res = supabase.table(TABLE_PRICE_DAILY).select("ticker").execute()
        valid_tickers = list(set([r['ticker'] for r in res.data]))
        valid_tickers_str = ", ".join(valid_tickers)
    except:
        valid_tickers_str = "AAPL, MSFT, TSLA, NVDA, GOOGL" # Fallback

    # 3. Get Macro State (if not provided)
    if macro_state is None:
        from g9_macro_factory.utils.macro_processor import get_macro_processor
        mp = get_macro_processor()
        # Use the date of the LAST news item as the reference date
        ref_date = news_items[0]['published_at'].split('T')[0]
        macro_state = mp.get_state(ref_date)
    
    macro_context = ""
    if macro_state:
        macro_context = "Macro Indicators (The Big 5):\n"
        for k, v in macro_state.items():
            if isinstance(v, dict):
                macro_context += f"- {k}: {v.get('value', 'N/A')} (Trend: {v.get('change_1w', 'N/A')}, Level: {v.get('level', 'N/A')})\n"
            else:
                macro_context += f"- {k}: {v}\n"
    else:
        macro_context = "Macro Indicators: Data Not Available\n"

    # 4. Z-Score Context & Filtering
    z_val = 0.0
    impact = 0.0
    if scores:
        z_val = scores.get('z_score', 0.0)
        impact = scores.get('impact_score', 0.0)

    # [FILTER] Force Quit if Z-Score is too low (Noise Filter)
    # REMOVED: Logic moved to DecisionEngine (Dual Mode)
    # if z_val < 2.5:
    #     print(f"   🚫 [Skip] Z-Score {z_val:.2f} is too low. (Noise Filtered)")
    #     return []

    # [CONTEXT] Determine Market Energy Level
    z_context_data = {}
    if z_val >= 5.0:
        z_context_data = {
            "level": "CRITICAL (Black Swan)",
            "desc": "역사상 상위 0.1%의 충격. 시장이 이성적이지 않음.",
            "instruction": "기존 논리보다 '생존'과 '공포'에 집중하라. 과감한 역발상(Contrarian)이 유효하다."
        }
    elif z_val >= 3.0:
        z_context_data = {
            "level": "EXTREME (Market Moving)",
            "desc": "평소 대비 3배 이상의 뉴스 폭발. 명확한 대형 호재/악재 발생.",
            "instruction": "추세 추종(Trend Following) 전략을 최우선으로 고려하라."
        }
    else: # 2.5 <= z_val < 3.0
        z_context_data = {
            "level": "HIGH (Attention)",
            "desc": "시장의 관심이 쏠리기 시작함.",
            "instruction": "확실한 근거가 없다면 '관망(Hold)'을 추천하라."
        }

    z_prompt_section = f"""
    [MARKET ENERGY LEVEL: {z_context_data['level']}]
    - Z-Score: {z_val:.2f} (Impact: {impact:.2f})
    - Situation: {z_context_data['desc']}
    - ★ ACTION RULE: {z_context_data['instruction']}
    """

    prompt = f"""
    You are a Macro Hedge Fund Manager. Analyze the following news items (Context) and identify the single most promising trading opportunity.
    Use the provided Historical Patterns, Macro Indicators, and Market Energy Level to guide your decision.
    
    {z_prompt_section}
    
    Context:
    {context_text}
    
    {pattern_context}
    
    {macro_context}
    
    [MULTI-TIMEFRAME CONTEXT (3-LAYER PROTOCOL)]
    Layer 1 (Monthly Regime): {context_data.get('monthly_summary', 'N/A') if context_data else 'N/A'}
    Layer 2 (Weekly Trend): {context_data.get('weekly_context', 'N/A') if context_data else 'N/A'}
    Layer 3 (Daily News): See Context below.
    
    [SYNTHESIS LOGIC]
    1. Scenario A (Dip Buy): If Monthly=Bullish AND Weekly=Correction AND Daily=Bad News -> "BUY_THE_DIP" (Opportunity).
    2. Scenario B (Momentum): If Monthly=Bullish AND Weekly=Bullish AND Daily=Good News -> "MOMENTUM_BUY" (Ride the wave).
    3. Exception: If Z-Score > 5.0 (Crisis), IGNORE upper layers and SELL/HEDGE immediately.
    
    Allowed Tickers (You MUST pick one of these if relevant, or finding the closest match):
    {valid_tickers_str}
    
    Rules:
    1. Identify ONE high-confidence trade (BUY or SELL).
    2. The ticker MUST be one of the Allowed Tickers.
    3. Action must be BUY or SELL.
    4. Confidence should be 0.0 to 1.0.
    5. Provide a concise reasoning, referencing Pattern ID and Macro Indicators if used.
    
    Output JSON format:
    {{
        "ticker": "TICKER_SYMBOL",
        "action": "BUY/SELL",
        "reason": "...",
        "confidence": 0.85
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert financial analyst."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        strategy = json.loads(content)
        
        # Normalize
        strategy['action'] = strategy['action'].upper()
        
        # Standardize Ticker
        std = get_standardizer()
        std_ticker = std.standardize(strategy['ticker'])
        if std_ticker:
            strategy['ticker'] = std_ticker
            
        # Attach Context for Intelligence Core
        strategy['macro_state'] = macro_state
        # Find used pattern ID from reasoning or context
        # Simple heuristic: if we retrieved patterns, take the top one as primary context
        # Or ask LLM to output pattern_id.
        # For now, let's attach the top retrieved pattern if available.
        if patterns:
            strategy['pattern_id'] = patterns[0]['pattern_id']
        else:
            strategy['pattern_id'] = None
            
        print(f"   💡 Generated Strategy: {strategy['action']} {strategy['ticker']} (Conf: {strategy['confidence']})")
        return [strategy]
        
    except Exception as e:
        print(f"   ❌ Strategy generation failed: {e}")
        return []
