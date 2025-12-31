import os
import asyncio
import json
import httpx
from typing import List, Dict, Any
from dotenv import load_dotenv
from supabase import create_client, Client

# === CONFIG ===
load_dotenv(override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL_NAME = "openai/gpt-4o"

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize HTTP Client for OpenRouter
headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "https://github.com/gate9/g9-rag",
    "X-Title": "G9 Ticker Mapper",
    "Content-Type": "application/json"
}

BATCH_SIZE = 1000
CONFIDENCE_THRESHOLD_UPDATE = 0.85

async def extract_tickers_batch(news_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extracts tickers for a batch of news items using LLM.
    """
    prompt_items = []
    for item in news_items:
        # Robust text extraction
        raw_text = item.get('raw_text') or item.get('summary') or ""
        if not isinstance(raw_text, str): raw_text = ""
        
        text_content = f"Title: {item.get('title', '')}\nKeywords: {item.get('keywords', '')}\nText: {raw_text[:300]}"
        prompt_items.append({"id": item['id'], "content": text_content})

    prompt_text = json.dumps(prompt_items, indent=2)
    
    system_prompt = """
    너의 역할은 "티커 복원 엔진(Ticker Restoration Engine)"이다.
    global_news_all 테이블 내 ticker 필드가 NULL인 뉴스들을 자동 분석하고
    제목(title), summary, keywords, raw_text 중 기업명/지명/기관명을 탐지하여
    해당 기업의 실제 주식 티커를 추론한 뒤 다시 DB에 매핑해야 한다.

    중요한 원칙
    1) ticker가 NULL이면 반드시 candidate_ticker 1~3개를 제안한다.
    2) 확정이 어려울 경우 "unknown"이 아니라 후보 리스트를 confidence 점수와 함께 제시한다.
    3) 매우 확실할 경우 confidence 기준이 0.85 이상이면 1개 ticker로 단일 확정한다.
    4) 뉴스 텍스트에 명시되지 않은 기업명은 억지로 생성하지 않는다.
    5) 국가/시장/지수와 함께 등장하는지 → 매칭 정확도 상승
       예) "삼성" + "KOSPI" → 005930
           "NVIDIA" + "NASDAQ" → NVDA
           "Sony" + "Tokyo" → 6758.T
    6) 정부·단체·기관은 기업이 아니므로 무조건 제외
       (UN, NATO, WHO, 정부부처 등)

    DB 업데이트 목적 JSON OUTPUT FORMAT
    Return a JSON object with a key "results" containing a list of objects:
    {
      "id": "<uuid>",                       // 뉴스 row id
      "title": "<headline>",                // 참고한 제목
      "company": "<Detected Company Name>", // 기업명
      "candidate_tickers": ["AAPL","GOOG"], // 후보 리스트
      "confidence": 0.79,                   // 0~1.0 점수
      "final": "AAPL",                      // 자동 확정(없으면 null)
      "reasoning": "본문에서 Apple 제품 언급 및 NASDAQ 문맥"
    }
    """

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze these news items:\n{prompt_text}"}
        ],
        "response_format": {"type": "json_object"}
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120.0
            )
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']
            parsed = json.loads(content)
            return parsed.get('results', [])
    except Exception as e:
        print(f"❌ LLM Batch Error: {e}")
        return []

async def process_batch():
    total_processed = 0
    total_mapped = 0
    new_tickers = set()
    low_confidence_companies = []

    while True:
        print(f"\n🔄 Fetching batch of {BATCH_SIZE} NULL tickers...")
        
        # Fetch NULL tickers that haven't been checked yet
        response = supabase.table("global_news_all").select("*").is_("ticker", "null").eq("ai_ticker_checked", False).limit(BATCH_SIZE).execute()
        
        if not response.data:
             response = supabase.table("global_news_all").select("*").eq("ticker", "").eq("ai_ticker_checked", False).limit(BATCH_SIZE).execute()
        
        news_items = response.data
        if not news_items:
            print("✨ No more unchecked NULL tickers found. Process Complete.")
            break
            
        print(f"   Processing {len(news_items)} items...")
        
        chunk_size = 50
        results = []
        
        for i in range(0, len(news_items), chunk_size):
            chunk = news_items[i:i+chunk_size]
            print(f"   - Analyzing chunk {i}-{i+len(chunk)}...")
            chunk_results = await extract_tickers_batch(chunk)
            results.extend(chunk_results)
            
        updates_count = 0
        
        # Mark all processed items as checked
        processed_ids = [item['id'] for item in news_items]
        if processed_ids:
            try:
                # Update ai_ticker_checked = True for all processed IDs
                # Supabase-py .in_() filter
                supabase.table("global_news_all").update({"ai_ticker_checked": True}).in_("id", processed_ids).execute()
            except Exception as e:
                print(f"   ⚠️ Failed to mark items as checked: {e}")

        for res in results:
            news_id = res['id']
            # ... rest of processing ...
        
        for res in results:
            news_id = res['id']
            # title = res.get('title')
            candidates = res.get('candidate_tickers', [])
            conf = res.get('confidence', 0.0)
            final_ticker = res.get('final')
            reasoning = res.get('reasoning')
            
            # Save to ticker_ai_labels
            # We need to handle the unique constraint.
            # If final_ticker is present, use it as 'ticker' for the unique key?
            # Or should we store one row per candidate?
            # The user said "candidate_tickers 1~3개를 제안한다".
            # And "DB 저장 규칙" -> "ticker_ai_labels에 먼저 적재".
            # I'll store the primary candidate or final ticker as 'ticker' and the full list in 'candidate_tickers'.
            
            primary_ticker = final_ticker if final_ticker else (candidates[0] if candidates else None)
            company_name = res.get('company') or (candidates[0] if candidates else "Unknown")
            
            if company_name and company_name != "Unknown":
                 try:
                    supabase.table("ticker_ai_labels").upsert({
                        "company": company_name,
                        "ticker": primary_ticker,
                        "candidate_tickers": candidates,
                        "reasoning": reasoning,
                        "confidence": conf
                    }, on_conflict="company,ticker").execute()
                 except Exception as e:
                    pass

            # Update global_news_all
            if conf >= CONFIDENCE_THRESHOLD_UPDATE and final_ticker:
                try:
                    supabase.table("global_news_all").update({"ticker": final_ticker}).eq("id", news_id).execute()
                    updates_count += 1
                    total_mapped += 1
                    new_tickers.add(final_ticker)
                except Exception as e:
                    print(f"   ⚠️ Update failed for {news_id}: {e}")
            
            if conf < CONFIDENCE_THRESHOLD_UPDATE:
                low_confidence_companies.append((str(candidates), conf))

        total_processed += len(news_items)
        print(f"   ✅ Batch Complete. Updated {updates_count} rows.")

    print("\n" + "="*40)
    print("📊 Ticker Regeneration Report")
    print("="*40)
    print(f"Total Analyzed: {total_processed}")
    print(f"Successfully Mapped: {total_mapped}")
    print(f"Success Rate: {(total_mapped/total_processed*100) if total_processed else 0:.1f}%")
    
    print("\n🆕 New Tickers Found (Top 20):")
    for t in list(new_tickers)[:20]:
        print(f"- {t}")

if __name__ == "__main__":
    asyncio.run(process_batch())
