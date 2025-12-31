import os
import glob
import json
import re
import time
import asyncio
import httpx
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv(override=True)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
EMBEDDING_MODEL = "text-embedding-3-large"
PATTERN_DIR = os.path.join(os.path.dirname(__file__), "g9_rag") # Default to current dir/g9_rag if not found
if not os.path.exists(PATTERN_DIR):
    PATTERN_DIR = os.path.dirname(__file__) # Fallback to current dir

# Initialize Supabase
if not SUPABASE_URL or not SUPABASE_KEY:
    # Try manual parsing if load_dotenv failed
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'), 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY")
        OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    except Exception as e:
        print(f"⚠️ Manual .env load failed: {e}")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize HTTP Client for OpenRouter
headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "https://github.com/gate9/g9-rag",
    "X-Title": "G9 Pattern Engine",
    "Content-Type": "application/json"
}

# Hardcoded Title Map (User Provided)
TITLE_MAP = {
    "P-001": "금리 급등 (Interest Rate Spike)",
    "P-002": "유가 급등 (Oil Price Spike)",
    "P-003": "달러 강세 (Dollar Super-Strength)",
    "P-004": "엔저 심화 (JPY Structural Weakening)",
    "P-005": "인플레이션 급등 (Inflation Spike)",
    "P-006": "경기 침체 시그널 (Recession Signal)",
    "P-007": "기술주 버블 붕괴 (Tech Bubble Burst)",
    "P-008": "지정학적 전쟁 위기 (Geopolitical War)",
    "P-009": "신용 경색 및 유동성 위기 (Credit Crunch)",
    "P-010": "중국 경기 둔화 및 부양책 (China Slowdown/Stimulus)",
    "P-011": "유동성 사이클 급변 (Liquidity Shock)",
    "P-012": "고용 시장 충격 (Labor Market Shock)",
    "P-013": "금융 시스템 스트레스 (Financial Stress)",
    "P-014": "공급망 및 원자재 대란 (Supply Chain Crisis)",
    "P-015": "선거 및 정치적 불확실성 (Political Uncertainty)",
    "P-016": "소비 위축 및 소매 판매 쇼크 (Consumption Shock)",
    "P-017": "국채 금리 역전 및 정상화 (Yield Curve Inversion)",
    "P-018": "캐리 트레이드 청산 (Carry Trade Unwind)",
    "P-019": "신흥국 자금 유출 (EM Capital Flight)",
    "P-020": "중앙은행 정책 전환 (Central Bank Pivot)",
    "P-021": "양적완화/긴축 사이클 (QE/QT Cycle)",
    "P-022": "달러 유동성 경색 (USD Funding Stress)",
    "P-023": "시장 공포 및 투매 (VIX/Capitulation)",
    "P-024": "리스크 온/오프 전환 (Risk On/Off)",
    "P-025": "미중 무역 전쟁 (US-China Trade War)",
    "P-026": "중동 지정학 리스크 (Middle East Risk)",
    "P-027": "유럽 에너지 안보 위기 (EU Energy Crisis)",
    "P-028": "대만 해협 리스크 (Taiwan Flashpoint)",
    "P-029": "글로벌 제재 및 수출 통제 (Global Sanctions)",
    "P-030": "신흥국 부채 위기 (Sovereign Debt Crisis)",
    "P-031": "반도체 사이클 (Semiconductor Cycle)",
    "P-032": "전기차(EV) 과열↔침체 사이클 (EV Boom-Bust Cycle)",
    "P-033": "바이오·제약 임상 / FDA 사이클 (Bio/Pharma Cycle)",
    "P-034": "금융주 스트레스(은행·보험) 패턴 (Financial Sector Stress)",
    "P-035": "빅테크 규제/반독점 패턴 (Tech Regulation)",
    "P-036": "건설·인프라 사이클 (Construction & Infrastructure)",
    "P-037": "항공·관광 리바운드 (Tourism Rebound)",
    "P-038": "커머디티 슈퍼사이클 (Commodity Supercycle)",
    "P-039": "소비재 교체 주기 (Replacement Cycle)",
    "P-040": "방산·국방 업사이클 (Defense Upswing)",
    "P-041": "글로벌 자금 섹터 로테이션 (Global Sector Rotation)",
    "P-042": "환율 붕괴 / 통화위기 (Currency Crisis)",
    "P-043": "안전자산 쏠림 (Flight to Safety)",
    "P-044": "원자재 통화 사이클 (Commodity Currency Cycle)",
    "P-045": "경제지표 서프라이즈/쇼크 (Macro Surprise)",
    "P-046": "장단기 금리 스프레드 트레이드 (Yield Curve Trade)",
    "P-047": "AI 서브업종 과열 (AI Mini-Bubble)",
    "P-048": "Meme Stock / 개인투자자 광풍 (Retail Mania)",
    "P-049": "시장 투매 바닥 패턴 (Market Capitulation)",
    "P-050": "블랙스완 / 미지의 공포 (Black Swan Event)" 
}

def parse_markdown(file_path: str) -> Tuple[Dict[str, Any], List[str]]:
    """Parses markdown and returns data dict and list of corrections made."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    filename = os.path.basename(file_path)
    pattern_id = filename.replace('.md', '')
    corrections = []

    # 1. Category
    category_match = re.search(r'(?:Category|카테고리명|Category\*\*)\s*[:]\s*(.+)', content, re.IGNORECASE)
    category = "Uncategorized"
    if category_match:
        raw_cat = category_match.group(1).strip()
        category = re.sub(r'[\*_]', '', raw_cat).strip()
    else:
        corrections.append("Category missing -> Set to 'Uncategorized'")

    # 2. Title (FORCE OVERRIDE from MAP)
    if pattern_id in TITLE_MAP:
        title = TITLE_MAP[pattern_id]
        # Check if parsed title matches (just for logging)
        # ... (skipping check to save time, map is authority)
    else:
        # Fallback to parsing if not in map (should not happen for P-001 to P-050)
        title = ""
        # Strategy A: **패턴명:** or 패턴명:
        title_match_bold = re.search(r'(?:\*\*|)?(?:패턴명|패턴제목)(?:\*\*|)?\s*[:]\s*(.+)', content)
        if title_match_bold:
            title = title_match_bold.group(1).strip()
        
        # Strategy B: # **P-XXX — Title** or P-XXX — Title
        if not title:
            title_match_header = re.search(r'(?:#\s*)?(?:\*\*)?P-\d+\s*[—–-]\s*(.+?)(?:\*\*)?(?:\n|$)', content)
            if title_match_header:
                title = title_match_header.group(1).strip()
                
        # Strategy C: JSON block "name": "..."
        if not title:
            json_name_match = re.search(r'"name"\s*:\s*"(.+?)"', content)
            if json_name_match:
                title = json_name_match.group(1).strip()

        if not title:
            title = pattern_id
            corrections.append(f"Title missing -> Set to '{pattern_id}'")

    # 3. Core
    core = ""
    core_match_sec8 = re.search(r'(?:Embedding Core|핵심 문장).+?\n+(?:> )?(?:\*\*)?["“](.+?)["”](?:\*\*)?', content, re.DOTALL | re.IGNORECASE)
    if not core_match_sec8:
         core_match_sec8 = re.search(r'(?:Embedding Core|핵심 문장).+?\n+(?:> )?(.+)', content, re.DOTALL | re.IGNORECASE)
    
    if not core_match_sec8:
        core_match_def = re.search(r'(?:Core Definition|본질 정의).+?\n+(?:> )?(?:\*\*)?["“](.+?)["”](?:\*\*)?', content, re.DOTALL | re.IGNORECASE)
        if core_match_def:
            core_match_sec8 = core_match_def

    if core_match_sec8:
        raw_core = core_match_sec8.group(1).replace('\n', ' ').strip()
        core = re.sub(r'[\*_]', '', raw_core).strip()
    else:
        json_core_match = re.search(r'"core_logic"\s*:\s*"(.+?)"', content)
        if json_core_match:
             core = json_core_match.group(1).strip()
    
    if not core:
        corrections.append("Core missing -> Set to empty string")

    # 4. Triggers
    triggers = []
    trigger_section = re.search(r'(?:Trigger Sentences|패턴 트리거).+?(?:##|\Z)', content, re.DOTALL | re.IGNORECASE)
    if trigger_section:
        trigger_text = trigger_section.group(0)
        items = re.findall(r'(?:-|•)\s*["“](.+?)["”]', trigger_text)
        if not items:
             items = re.findall(r'(?:-|•)\s*(.+)', trigger_text)
        triggers = [re.sub(r'[\*_]', '', item).strip() for item in items if item.strip()]
    
    if not triggers:
        corrections.append("Triggers missing -> Set to empty list")

    # 5. SQL Rules
    sql_rules = ""
    sql_section = re.search(r'(?:SQL Rules|SQL 검색 규칙).+?(?:##|\Z)', content, re.DOTALL | re.IGNORECASE)
    if sql_section:
        sql_match = re.search(r'```(?:sql)?\s*(.+?)\s*```', sql_section.group(0), re.DOTALL)
        if sql_match:
            sql_rules = sql_match.group(1).strip()
        else:
            raw_sql_match = re.search(r'(SELECT.+?;)', sql_section.group(0), re.DOTALL | re.IGNORECASE)
            if raw_sql_match:
                sql_rules = raw_sql_match.group(1).strip()
    
    if not sql_rules:
        json_sql_match = re.search(r'"sql_rule"\s*:\s*"(.+?)"', content)
        if json_sql_match:
            sql_rules = json_sql_match.group(1).strip()
    
    if not sql_rules:
        corrections.append("SQL Rules missing -> Set to empty string")

    return {
        "pattern_id": pattern_id,
        "category": category,
        "title": title,
        "core": core,
        "triggers": triggers,
        "sql_rules": sql_rules,
        "full_text": content
    }, corrections

async def get_embedding(text: str, retries=3) -> List[float]:
    """Generates embedding using OpenRouter."""
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
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

async def process_file(file_path: str):
    data, corrections = parse_markdown(file_path)
    
    # Construct Embedding Input: Full Text + Core + Triggers
    embed_input = f"{data['full_text']}\n\nCore: {data['core']}\n\nTriggers: {', '.join(data['triggers'])}"
    
    try:
        embedding = await get_embedding(embed_input)
        
        # Upsert to Supabase
        record = {
            "pattern_id": data['pattern_id'],
            "category": data['category'],
            "title": data['title'],
            "core": data['core'],
            "triggers": data['triggers'],
            "sql_rules": data['sql_rules'],
            "full_text": data['full_text'],
            "embedding": embedding
        }
        
        supabase.table("macro_patterns").upsert(record).execute()
        
        status = "✅ Synced"
        if corrections:
            status = "⚠️  Fixed"
        
        print(f"{data['pattern_id']:<10} {status:<10} {len(embedding):<6} {data['title'][:30]:<30}")
        if corrections:
            for c in corrections:
                print(f"   ↳ {c}")

    except Exception as e:
        print(f"❌ {data['pattern_id']} Failed: {e}")

async def main():
    print("🚀 Starting Pattern Repair Pipeline (with Hardcoded Titles)...")
    print(f"📂 Pattern Directory: {PATTERN_DIR}")
    
    files = sorted(glob.glob(os.path.join(PATTERN_DIR, "P-*.md")))
    print(f"📂 Found {len(files)} files")
    
    print("-" * 80)
    print(f"{'ID':<10} {'Status':<10} {'Dim':<6} {'Title':<30}")
    print("-" * 80)

    for file_path in files:
        await process_file(file_path)
        
    print("-" * 80)
    print("✨ Pattern Repair Complete.")

if __name__ == "__main__":
    asyncio.run(main())
