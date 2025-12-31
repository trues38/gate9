import os
import json
import asyncio
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv(override=True)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

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
    except Exception as e:
        print(f"⚠️ Manual .env load failed: {e}")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Title Map provided by user
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

async def main():
    print("🚀 Starting Pattern Title Fix...")
    
    # 1. Fetch all patterns
    response = supabase.table("macro_patterns").select("pattern_id, title").execute()
    patterns = response.data
    
    print(f"📂 Loaded {len(patterns)} patterns from Supabase.")
    
    fixed_count = 0
    
    for pattern in patterns:
        pid = pattern['pattern_id']
        current_title = pattern.get('title')
        
        if pid in TITLE_MAP:
            correct_title = TITLE_MAP[pid]
            
            # Update if different
            if current_title != correct_title:
                print(f"🔧 Fixing {pid}: '{current_title}' -> '{correct_title}'")
                
                supabase.table("macro_patterns").update({"title": correct_title}).eq("pattern_id", pid).execute()
                fixed_count += 1
            else:
                print(f"✅ {pid} is already correct.")
        else:
            print(f"⚠️ {pid} not in title map!")

    print(f"\n🎉 Fixed {fixed_count} pattern titles.")

if __name__ == "__main__":
    asyncio.run(main())
